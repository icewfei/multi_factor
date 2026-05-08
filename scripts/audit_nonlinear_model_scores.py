from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import duckdb


EXPECTED_SCORE_COLUMNS = {
    "run_id",
    "candidate_scheme_id",
    "snapshot_id",
    "instrument",
    "signal_date",
    "model_score_D0",
    "feature_set_id",
    "model_config_id",
    "config_hash",
}
EXPECTED_CANDIDATE_SCHEME_ID = "nlc_v1_confirmed5_lgbm_depth3_seed42"
EXPECTED_FEATURE_SET_ID = "nlc_v1_fset01_confirmed5"
EXPECTED_MODEL_CONFIG_ID = "nlc_v1_lgbm_regressor_depth3_seed42"
EXPECTED_TRAINING_STATUS = "trained_and_scored_minimal"


class AuditError(Exception):
    """Raised when the nonlinear model score audit cannot continue safely."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit nonlinear confirmed5 model_scores_D0 outputs.")
    parser.add_argument("--scores", required=True, type=Path, help="Path to model_scores_D0.parquet.")
    parser.add_argument("--scores-audit", required=True, type=Path, help="Path to model_scores_D0_audit.json.")
    parser.add_argument("--training-manifest", required=True, type=Path, help="Path to training_manifest.json.")
    parser.add_argument("--output", required=True, type=Path, help="Path to write the audit json.")
    return parser


def load_json_file(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AuditError(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AuditError(f"{label} is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise AuditError(f"{label} must be a JSON object: {path}")
    return payload


def describe_columns(con: duckdb.DuckDBPyConnection, parquet_path: Path) -> set[str]:
    rows = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{parquet_path.as_posix()}')").fetchall()
    return {str(row[0]) for row in rows}


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return path


def audit_model_scores_or_fail(
    scores_path: Path,
    scores_audit_path: Path,
    training_manifest_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    if not scores_path.exists():
        raise AuditError(f"model scores parquet not found: {scores_path}")

    scores_audit = load_json_file(scores_audit_path, "model scores audit")
    training_manifest = load_json_file(training_manifest_path, "training manifest")

    con = duckdb.connect()
    try:
        columns = describe_columns(con, scores_path)
        missing_columns = sorted(EXPECTED_SCORE_COLUMNS - columns)

        row_count, duplicate_count, null_score_rows, nonfinite_score_rows, min_score, max_score, avg_score, std_score = (
            con.execute(
                f"""
                WITH scores AS (
                    SELECT * FROM read_parquet('{scores_path.as_posix()}')
                ),
                duplicates AS (
                    SELECT COUNT(*) AS row_count
                    FROM scores
                    GROUP BY snapshot_id, instrument, signal_date, candidate_scheme_id
                    HAVING COUNT(*) > 1
                )
                SELECT
                    (SELECT COUNT(*) FROM scores) AS row_count,
                    (SELECT COALESCE(SUM(row_count - 1), 0) FROM duplicates) AS duplicate_count,
                    (SELECT COUNT(*) FROM scores WHERE model_score_D0 IS NULL) AS null_score_rows,
                    (SELECT COUNT(*) FROM scores WHERE NOT isfinite(model_score_D0)) AS nonfinite_score_rows,
                    (SELECT MIN(model_score_D0) FROM scores) AS min_score,
                    (SELECT MAX(model_score_D0) FROM scores) AS max_score,
                    (SELECT AVG(model_score_D0) FROM scores) AS avg_score,
                    (SELECT STDDEV_SAMP(model_score_D0) FROM scores) AS std_score
                """
            ).fetchone()
        )

        identity_row = con.execute(
            f"""
            SELECT
                COUNT(DISTINCT candidate_scheme_id) AS candidate_id_count,
                MIN(candidate_scheme_id) AS candidate_scheme_id,
                COUNT(DISTINCT feature_set_id) AS feature_set_id_count,
                MIN(feature_set_id) AS feature_set_id,
                COUNT(DISTINCT model_config_id) AS model_config_id_count,
                MIN(model_config_id) AS model_config_id,
                COUNT(DISTINCT config_hash) AS config_hash_count,
                MIN(config_hash) AS config_hash
            FROM read_parquet('{scores_path.as_posix()}')
            """
        ).fetchone()
    finally:
        con.close()

    all_scores_identical = min_score == max_score if min_score is not None and max_score is not None else True
    audit_row_count = int(scores_audit.get("row_count", -1))
    manifest_status = training_manifest.get("status")
    frozen_test_access = scores_audit.get("frozen_test_access")

    checks = {
        "required_columns_present": not missing_columns,
        "primary_key_unique": int(duplicate_count or 0) == 0,
        "row_count_matches_scores_audit": int(row_count or 0) == audit_row_count,
        "null_score_rows_zero": int(null_score_rows or 0) == 0,
        "nonfinite_score_rows_zero": int(nonfinite_score_rows or 0) == 0,
        "scores_not_all_identical": not all_scores_identical,
        "candidate_scheme_id_expected": (
            int(identity_row[0] or 0) == 1 and identity_row[1] == EXPECTED_CANDIDATE_SCHEME_ID
        ),
        "feature_set_id_expected": (
            int(identity_row[2] or 0) == 1 and identity_row[3] == EXPECTED_FEATURE_SET_ID
        ),
        "model_config_id_expected": (
            int(identity_row[4] or 0) == 1 and identity_row[5] == EXPECTED_MODEL_CONFIG_ID
        ),
        "frozen_test_access_false": frozen_test_access is False,
        "training_manifest_status_expected": manifest_status == EXPECTED_TRAINING_STATUS,
    }
    passed = all(checks.values())

    result = {
        "status": "passed" if passed else "failed",
        "scores_path": str(scores_path),
        "scores_audit_path": str(scores_audit_path),
        "training_manifest_path": str(training_manifest_path),
        "row_count": int(row_count or 0),
        "audit_row_count": audit_row_count,
        "duplicate_count": int(duplicate_count or 0),
        "null_score_rows": int(null_score_rows or 0),
        "nonfinite_score_rows": int(nonfinite_score_rows or 0),
        "missing_columns": missing_columns,
        "score_summary": {
            "min_score": None if min_score is None else float(min_score),
            "max_score": None if max_score is None else float(max_score),
            "avg_score": None if avg_score is None else float(avg_score),
            "std_score": None if std_score is None else float(std_score),
            "all_scores_identical": all_scores_identical,
        },
        "candidate_scheme_id": identity_row[1],
        "feature_set_id": identity_row[3],
        "model_config_id": identity_row[5],
        "config_hash": identity_row[7],
        "frozen_test_access": frozen_test_access,
        "training_manifest_status": manifest_status,
        "checks": checks,
    }
    write_json(output_path, result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = audit_model_scores_or_fail(
            scores_path=args.scores,
            scores_audit_path=args.scores_audit,
            training_manifest_path=args.training_manifest,
            output_path=args.output,
        )
        return 0 if result["status"] == "passed" else 1
    except AuditError as exc:
        print(f"audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
