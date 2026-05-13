#!/usr/bin/env python3
"""
Build a governed clean sample-panel projection for no-p98 baseline score builds.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb


ALLOWED_COLUMNS = [
    "snapshot_id",
    "instrument",
    "signal_date",
    "ranking_eligible_D0",
]
REQUIRED_COLUMNS = ALLOWED_COLUMNS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Project project_sample_panel.parquet into a clean whitelist-only sample panel."
    )
    parser.add_argument(
        "--input-path",
        required=True,
        help="Path to input project_sample_panel.parquet.",
    )
    parser.add_argument(
        "--output-path",
        required=True,
        help="Path to output clean_sample_panel.parquet.",
    )
    parser.add_argument(
        "--audit-path",
        required=True,
        help="Path to output audit JSON.",
    )
    return parser.parse_args()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_path(path: Path) -> str:
    return sql_quote(path.resolve().as_posix())


def list_columns(input_path: Path) -> list[str]:
    con = duckdb.connect()
    try:
        rows = con.execute(
            f"DESCRIBE SELECT * FROM read_parquet({sql_path(input_path)})"
        ).fetchall()
    finally:
        con.close()
    return [row[0] for row in rows]


def count_rows(path: Path) -> int:
    con = duckdb.connect()
    try:
        row_count = con.execute(
            f"SELECT COUNT(*) FROM read_parquet({sql_path(path)})"
        ).fetchone()[0]
    finally:
        con.close()
    return int(row_count or 0)


def find_missing_required_columns(columns: list[str]) -> list[str]:
    available = set(columns)
    return [column for column in REQUIRED_COLUMNS if column not in available]


def is_forbidden_column(column: str) -> bool:
    lowered = column.lower()
    return (
        lowered.startswith("label_")
        or "realized_return" in lowered
        or "future" in lowered
        or "actual_exit" in lowered
        or "sell_price" in lowered
        or "frozen" in lowered
        or "test" in lowered
    )


def build_projection(input_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    projection_sql = ", ".join(ALLOWED_COLUMNS)
    con = duckdb.connect()
    try:
        con.execute(
            f"""
            COPY (
                SELECT {projection_sql}
                FROM read_parquet({sql_path(input_path)})
            ) TO {sql_path(output_path)} (FORMAT PARQUET)
            """
        )
    finally:
        con.close()


def build_audit(
    *,
    input_path: Path,
    output_path: Path,
    row_count: int,
    stripped_forbidden_columns: list[str],
) -> dict:
    return {
        "input_path": input_path.resolve().as_posix(),
        "output_path": output_path.resolve().as_posix(),
        "row_count": row_count,
        "allowed_columns": ALLOWED_COLUMNS,
        "stripped_forbidden_columns": stripped_forbidden_columns,
        "frozen_test_accessed": False,
        "label_columns_stripped": any(
            column.lower().startswith("label_") for column in stripped_forbidden_columns
        ),
    }


def validate_output(
    *,
    input_row_count: int,
    output_path: Path,
) -> tuple[int, list[str]]:
    output_columns = list_columns(output_path)
    output_row_count = count_rows(output_path)
    forbidden_output_columns = [column for column in output_columns if is_forbidden_column(column)]

    if forbidden_output_columns:
        raise ValueError(f"Output still contains forbidden columns: {forbidden_output_columns}")
    if output_columns != ALLOWED_COLUMNS:
        raise ValueError(f"Output columns must equal whitelist: {output_columns}")
    if output_row_count != input_row_count:
        raise ValueError(
            "Output row_count mismatch: "
            f"input_row_count={input_row_count}, output_row_count={output_row_count}"
        )
    return output_row_count, output_columns


def main() -> None:
    args = parse_args()

    input_path = Path(args.input_path)
    output_path = Path(args.output_path)
    audit_path = Path(args.audit_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input project_sample_panel not found: {input_path}")

    input_columns = list_columns(input_path)
    missing_required_columns = find_missing_required_columns(input_columns)
    if missing_required_columns:
        raise ValueError(f"Missing required columns: {missing_required_columns}")

    input_row_count = count_rows(input_path)
    stripped_forbidden_columns = sorted(
        column for column in input_columns if column not in ALLOWED_COLUMNS and is_forbidden_column(column)
    )

    build_projection(input_path, output_path)
    output_row_count, _ = validate_output(input_row_count=input_row_count, output_path=output_path)

    audit = build_audit(
        input_path=input_path,
        output_path=output_path,
        row_count=output_row_count,
        stripped_forbidden_columns=stripped_forbidden_columns,
    )
    write_json(audit_path, audit)


if __name__ == "__main__":
    main()
