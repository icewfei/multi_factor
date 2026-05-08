from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import duckdb


REQUIRED_SAMPLE_PANEL_COLUMNS = {"snapshot_id", "instrument", "signal_date"}
REQUIRED_CONFIG_FIELDS = {
    "split_config_id",
    "snapshot_id",
    "train_start",
    "train_end",
    "validation_start",
    "validation_end",
    "test_excluded_start",
    "test_excluded_end",
    "split_policy",
    "frozen_test_access",
}
BUCKET_TRAIN = "train"
BUCKET_VALIDATION = "validation"
BUCKET_EXCLUDED_TEST = "excluded_test_period"
BUCKET_OUTSIDE_RANGE = "outside_config_range"


class BuildError(Exception):
    """Raised when the dataset split builder cannot continue safely."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build dataset_split_daily parquet from sample panel dates.")
    parser.add_argument("--config", required=True, type=Path, help="Path to dataset split config JSON.")
    parser.add_argument("--sample-panel", required=True, type=Path, help="Path to project_sample_panel parquet.")
    parser.add_argument("--output", required=True, type=Path, help="Path to dataset_split_daily parquet output.")
    return parser


def load_json_file(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BuildError(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise BuildError(f"{label} is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise BuildError(f"{label} must be a JSON object: {path}")
    return payload


def ensure_required_keys(payload: dict[str, Any], required_keys: set[str], label: str) -> None:
    missing_keys = sorted(key for key in required_keys if key not in payload)
    if missing_keys:
        raise BuildError(f"{label} missing required fields: {', '.join(missing_keys)}")


def ensure_iso_date(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise BuildError(f"config field must be a string date: {field_name}")
    parts = value.split("-")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise BuildError(f"config field must use YYYY-MM-DD: {field_name}={value!r}")
    return value


def validate_config(config: dict[str, Any]) -> dict[str, str]:
    ensure_required_keys(config, REQUIRED_CONFIG_FIELDS, "dataset split config")

    if config.get("frozen_test_access") is not False:
        raise BuildError("dataset split config must keep frozen_test_access=false")

    validated_dates = {
        "train_start": ensure_iso_date(config["train_start"], "train_start"),
        "train_end": ensure_iso_date(config["train_end"], "train_end"),
        "validation_start": ensure_iso_date(config["validation_start"], "validation_start"),
        "validation_end": ensure_iso_date(config["validation_end"], "validation_end"),
        "test_excluded_start": ensure_iso_date(config["test_excluded_start"], "test_excluded_start"),
        "test_excluded_end": ensure_iso_date(config["test_excluded_end"], "test_excluded_end"),
    }

    if not isinstance(config.get("split_config_id"), str) or not config["split_config_id"]:
        raise BuildError("dataset split config split_config_id must be a non-empty string")
    if not isinstance(config.get("snapshot_id"), str) or not config["snapshot_id"]:
        raise BuildError("dataset split config snapshot_id must be a non-empty string")
    if not isinstance(config.get("split_policy"), str) or not config["split_policy"]:
        raise BuildError("dataset split config split_policy must be a non-empty string")

    date_order = [
        validated_dates["train_start"],
        validated_dates["train_end"],
        validated_dates["validation_start"],
        validated_dates["validation_end"],
        validated_dates["test_excluded_start"],
        validated_dates["test_excluded_end"],
    ]
    if date_order != sorted(date_order):
        raise BuildError("dataset split config dates must be non-decreasing across train/validation/test ranges")

    return validated_dates


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def describe_columns(con: duckdb.DuckDBPyConnection, relation_name: str) -> set[str]:
    rows = con.execute(f"DESCRIBE {relation_name}").fetchall()
    return {str(row[0]) for row in rows}


def ensure_required_columns(available_columns: set[str], required_columns: set[str], relation_label: str) -> None:
    missing_columns = sorted(required_columns - available_columns)
    if missing_columns:
        raise BuildError(f"{relation_label} missing required columns: {', '.join(missing_columns)}")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def default_audit_output_path(output_path: Path) -> Path:
    return output_path.with_name(f"{output_path.stem}_audit.json")


def build_dataset_split_daily(
    config: dict[str, Any],
    sample_panel_path: Path,
    output_path: Path,
) -> tuple[Path, Path]:
    if not sample_panel_path.exists():
        raise BuildError(f"sample panel path not found: {sample_panel_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path = default_audit_output_path(output_path)
    validated_dates = validate_config(config)

    con = duckdb.connect()
    try:
        con.execute(
            f"""
            CREATE OR REPLACE VIEW sample_panel_input AS
            SELECT
                snapshot_id,
                instrument,
                signal_date
            FROM read_parquet({sql_quote(sample_panel_path.as_posix())})
            """
        )
        sample_columns = describe_columns(con, "sample_panel_input")
        ensure_required_columns(sample_columns, REQUIRED_SAMPLE_PANEL_COLUMNS, "sample_panel_input")

        expected_snapshot_id = str(config["snapshot_id"])
        mismatch_rows = int(
            con.execute(
                f"""
                SELECT COUNT(*)
                FROM sample_panel_input
                WHERE snapshot_id <> {sql_quote(expected_snapshot_id)}
                """
            ).fetchone()[0]
            or 0
        )
        if mismatch_rows:
            raise BuildError(
                "sample panel snapshot_id does not match split config snapshot_id: "
                f"{expected_snapshot_id}"
            )

        con.execute(
            f"""
            CREATE OR REPLACE VIEW normalized_split_input AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                COALESCE(
                    TRY_CAST(signal_date AS DATE),
                    CAST(TRY_STRPTIME(signal_date, '%Y%m%d') AS DATE)
                ) AS signal_date_d
            FROM sample_panel_input
            """
        )

        unparsable_dates = int(
            con.execute(
                """
                SELECT COUNT(*)
                FROM normalized_split_input
                WHERE signal_date_d IS NULL
                """
            ).fetchone()[0]
            or 0
        )
        if unparsable_dates:
            raise BuildError(
                f"sample panel signal_date contains unparsable rows: {unparsable_dates}"
            )

        con.execute(
            f"""
            CREATE OR REPLACE VIEW dataset_split_daily AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                CASE
                    WHEN signal_date_d BETWEEN DATE {sql_quote(validated_dates['train_start'])}
                                         AND DATE {sql_quote(validated_dates['train_end'])}
                    THEN {sql_quote(BUCKET_TRAIN)}
                    WHEN signal_date_d BETWEEN DATE {sql_quote(validated_dates['validation_start'])}
                                         AND DATE {sql_quote(validated_dates['validation_end'])}
                    THEN {sql_quote(BUCKET_VALIDATION)}
                    WHEN signal_date_d BETWEEN DATE {sql_quote(validated_dates['test_excluded_start'])}
                                         AND DATE {sql_quote(validated_dates['test_excluded_end'])}
                    THEN {sql_quote(BUCKET_EXCLUDED_TEST)}
                    ELSE {sql_quote(BUCKET_OUTSIDE_RANGE)}
                END AS split_bucket,
                CASE
                    WHEN signal_date_d BETWEEN DATE {sql_quote(validated_dates['train_start'])}
                                         AND DATE {sql_quote(validated_dates['train_end'])}
                    THEN TRUE
                    ELSE FALSE
                END AS train_flag,
                CASE
                    WHEN signal_date_d BETWEEN DATE {sql_quote(validated_dates['validation_start'])}
                                         AND DATE {sql_quote(validated_dates['validation_end'])}
                    THEN TRUE
                    ELSE FALSE
                END AS validation_flag,
                CASE
                    WHEN signal_date_d BETWEEN DATE {sql_quote(validated_dates['test_excluded_start'])}
                                         AND DATE {sql_quote(validated_dates['test_excluded_end'])}
                    THEN TRUE
                    ELSE FALSE
                END AS test_flag,
                {sql_quote(str(config['split_config_id']))} AS split_config_id,
                {sql_quote(str(config['split_policy']))} AS split_policy,
                {sql_quote(str(config['split_config_id']))} AS split_version,
                FALSE AS purge_gap_applied
            FROM normalized_split_input
            """
        )

        empty_bucket_rows = int(
            con.execute(
                """
                SELECT COUNT(*)
                FROM dataset_split_daily
                WHERE split_bucket IS NULL OR split_bucket = ''
                """
            ).fetchone()[0]
            or 0
        )
        if empty_bucket_rows:
            raise BuildError(f"dataset split contains empty split_bucket rows: {empty_bucket_rows}")

        overlapping_rows = int(
            con.execute(
                """
                SELECT COUNT(*)
                FROM dataset_split_daily
                WHERE train_flag AND validation_flag
                """
            ).fetchone()[0]
            or 0
        )
        if overlapping_rows:
            raise BuildError(
                f"dataset split contains rows marked both train and validation: {overlapping_rows}"
            )

        con.execute(
            f"""
            COPY dataset_split_daily
            TO {sql_quote(output_path.as_posix())}
            (FORMAT PARQUET)
            """
        )

        bucket_rows = con.execute(
            """
            SELECT split_bucket, COUNT(*) AS row_count
            FROM dataset_split_daily
            GROUP BY 1
            ORDER BY 1
            """
        ).fetchall()
        total_rows = int(
            con.execute("SELECT COUNT(*) FROM dataset_split_daily").fetchone()[0] or 0
        )
    finally:
        con.close()

    bucket_counts = {str(bucket): int(row_count) for bucket, row_count in bucket_rows}
    write_json(
        audit_path,
        {
            "status": "built_dataset_split_daily",
            "split_config_id": config["split_config_id"],
            "snapshot_id": config["snapshot_id"],
            "split_policy": config["split_policy"],
            "sample_panel_path": str(sample_panel_path),
            "output_path": str(output_path),
            "total_rows": total_rows,
            "split_bucket_counts": bucket_counts,
        },
    )
    return output_path, audit_path


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_json_file(args.config, "dataset split config")
        build_dataset_split_daily(config, args.sample_panel, args.output)
        return 0
    except BuildError as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
