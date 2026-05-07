#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Run the five formal consistency checks for a run-state attempt directory.

Checks:
1. ranking_state_rows == project_sample_panel_rows
2. execution_state_rows == project_sample_panel_rows
3. execution_attempt_D1 == topk_frozen_D0
4. entry_filled_D1 == execution_attempt_D1 & entry_tradeable_shared_flag
5. per-signal_date topk_frozen_D0 <= topk
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
ARTIFACTS_RUN_STATE_DIR = ROOT / "artifacts" / "run_state"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a run-state attempt with five formal checks.")
    parser.add_argument("--run-id", required=True, help="Project-side run identifier.")
    parser.add_argument("--attempt-id", required=True, help="Attempt identifier under artifacts/run_state/<run_id>/attempts/.")
    parser.add_argument(
        "--topk",
        type=int,
        default=10,
        help="Expected TopK cap per signal_date. Defaults to 10.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional explicit output path. Defaults to attempts/<attempt_id>/run_state_acceptance_report.json",
    )
    return parser.parse_args()


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_path(path: Path) -> str:
    return sql_quote(path.resolve().as_posix())


def build_check(name: str, passed: bool, observed, expected, detail: str) -> dict:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
        "detail": detail,
    }


def main() -> None:
    args = parse_args()
    run_dir = ARTIFACTS_RUN_STATE_DIR / args.run_id
    attempt_dir = run_dir / "attempts" / args.attempt_id
    if not attempt_dir.exists():
        raise FileNotFoundError(f"Attempt directory not found: {attempt_dir}")

    attempt_manifest = attempt_dir / "run_state_attempt_manifest.json"
    if not attempt_manifest.exists():
        raise FileNotFoundError(f"Required validation input not found: {attempt_manifest}")

    attempt_manifest_payload = json.loads(attempt_manifest.read_text(encoding="utf-8"))
    input_paths = attempt_manifest_payload.get("input_paths", {})
    sample_panel = Path(input_paths.get("project_sample_panel", run_dir / "project_sample_panel.parquet"))
    ranking_state = attempt_dir / "ranking_state_daily.parquet"
    execution_state = attempt_dir / "execution_state_daily.parquet"
    audit_path = attempt_dir / "data_quality_audit.json"

    for required in (sample_panel, ranking_state, execution_state, audit_path):
        if not required.exists():
            raise FileNotFoundError(f"Required validation input not found: {required}")

    output_path = Path(args.output) if args.output else (attempt_dir / "run_state_acceptance_report.json")

    con = duckdb.connect()
    try:
        sample_rows = con.execute(
            f"SELECT COUNT(*) FROM read_parquet({sql_path(sample_panel)})"
        ).fetchone()[0]
        ranking_rows = con.execute(
            f"SELECT COUNT(*) FROM read_parquet({sql_path(ranking_state)})"
        ).fetchone()[0]
        execution_rows = con.execute(
            f"SELECT COUNT(*) FROM read_parquet({sql_path(execution_state)})"
        ).fetchone()[0]

        execution_attempt_mismatch = con.execute(
            f"""
            SELECT SUM(
                CASE WHEN e.execution_attempt_D1 <> r.topk_frozen_D0 THEN 1 ELSE 0 END
            )
            FROM read_parquet({sql_path(execution_state)}) e
            INNER JOIN read_parquet({sql_path(ranking_state)}) r
                ON e.run_id = r.run_id
               AND e.attempt_id = r.attempt_id
               AND (
                    (e.run_type IS NULL AND r.run_type IS NULL)
                    OR e.run_type = r.run_type
               )
               AND e.snapshot_id = r.snapshot_id
               AND e.instrument = r.instrument
               AND e.signal_date = r.signal_date
            """
        ).fetchone()[0]

        entry_filled_mismatch = con.execute(
            f"""
            SELECT SUM(
                CASE
                    WHEN e.entry_filled_D1 <> (e.execution_attempt_D1 AND e.entry_tradeable_shared_flag)
                    THEN 1 ELSE 0
                END
            )
            FROM read_parquet({sql_path(execution_state)}) e
            """
        ).fetchone()[0]

        topk_breach_count, max_topk_observed = con.execute(
            f"""
            SELECT
                COUNT(*) FILTER (WHERE cnt > {args.topk}) AS breach_count,
                MAX(cnt) AS max_cnt
            FROM (
                SELECT
                    snapshot_id,
                    signal_date,
                    SUM(CASE WHEN topk_frozen_D0 THEN 1 ELSE 0 END) AS cnt
                FROM read_parquet({sql_path(ranking_state)})
                GROUP BY snapshot_id, signal_date
            )
            """
        ).fetchone()

        audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))

        checks = [
            build_check(
                "ranking_state_rows_match_project_sample_panel",
                ranking_rows == sample_rows,
                int(ranking_rows),
                int(sample_rows),
                "ranking_state_daily row count must equal project_sample_panel row count.",
            ),
            build_check(
                "execution_state_rows_match_project_sample_panel",
                execution_rows == sample_rows,
                int(execution_rows),
                int(sample_rows),
                "execution_state_daily row count must equal project_sample_panel row count.",
            ),
            build_check(
                "execution_attempt_equals_topk_frozen",
                int(execution_attempt_mismatch or 0) == 0,
                int(execution_attempt_mismatch or 0),
                0,
                "execution_attempt_D1 must equal topk_frozen_D0 on the joined run-state keys.",
            ),
            build_check(
                "entry_filled_matches_attempt_and_tradeable",
                int(entry_filled_mismatch or 0) == 0,
                int(entry_filled_mismatch or 0),
                0,
                "entry_filled_D1 must equal execution_attempt_D1 AND entry_tradeable_shared_flag.",
            ),
            build_check(
                "topk_cap_per_signal_date",
                int(topk_breach_count or 0) == 0,
                {
                    "breach_count": int(topk_breach_count or 0),
                    "max_topk_observed": int(max_topk_observed or 0),
                },
                {
                    "breach_count": 0,
                    "max_topk_observed_lte": args.topk,
                },
                "Per signal_date, topk_frozen_D0 count must not exceed configured TopK.",
            ),
        ]

        report = {
            "run_id": args.run_id,
            "attempt_id": args.attempt_id,
            "generated_at": datetime.now().astimezone().isoformat(),
            "overall_passed": all(check["passed"] for check in checks),
            "topk": args.topk,
            "paths": {
                "run_dir": run_dir.as_posix(),
                "attempt_dir": attempt_dir.as_posix(),
                "sample_panel": sample_panel.as_posix(),
                "ranking_state": ranking_state.as_posix(),
                "execution_state": execution_state.as_posix(),
                "attempt_manifest": attempt_manifest.as_posix(),
                "audit": audit_path.as_posix(),
            },
            "checks": checks,
            "attempt_manifest": {
                "status": attempt_manifest_payload.get("status"),
                "started_at": attempt_manifest_payload.get("started_at"),
                "completed_at": attempt_manifest_payload.get("completed_at"),
                "parameters": attempt_manifest_payload.get("parameters", {}),
            },
            "audit_summary_counts": audit_payload.get("summary_counts", {}),
            "warnings": audit_payload.get("warnings", []),
            "fatal_blockers": audit_payload.get("fatal_blockers", []),
        }

        write_json(output_path, report)
    finally:
        con.close()


if __name__ == "__main__":
    main()
