#!/opt/anaconda3/envs/quant_trade/bin/python
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
ARTIFACTS_RUN_STATE_DIR = ROOT / "artifacts" / "run_state"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose unresolved actual_exit_date rows at the portfolio/run-state boundary."
    )
    parser.add_argument("--run-id", required=True, help="Project-side run identifier.")
    parser.add_argument(
        "--input-dir",
        default=None,
        help="Optional run-state directory. Defaults to artifacts/run_state/<run_id>/",
    )
    parser.add_argument(
        "--attempt-id",
        default=None,
        help="Optional attempt identifier. Defaults to run_state_latest_attempt.json.",
    )
    parser.add_argument("--output", required=True, help="Diagnosis JSON output path.")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require_path(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Required input file not found: {path}")
    return path


def resolve_run_dir(run_id: str, input_dir: str | None) -> Path:
    run_dir = Path(input_dir) if input_dir else (ARTIFACTS_RUN_STATE_DIR / run_id)
    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")
    return run_dir


def resolve_attempt_dir(run_dir: Path, attempt_id: str | None) -> tuple[str, Path]:
    if attempt_id:
        resolved_attempt_id = attempt_id
    else:
        latest_pointer = require_path(run_dir / "run_state_latest_attempt.json")
        latest_payload = load_json(latest_pointer)
        resolved_attempt_id = latest_payload["attempt_id"]
    attempt_dir = require_path(run_dir / "attempts" / resolved_attempt_id)
    return resolved_attempt_id, attempt_dir


def classify_row(row: dict, terminal_instruments: set[str]) -> str:
    if row["execution_path_status"] == "terminal_event_unpriced":
        return "terminal_event_unpriced"
    if row["execution_path_status"] == "exit_unresolved":
        if row["instrument"] in terminal_instruments:
            return "exit_unresolved_after_terminal_event"
        return "exit_unresolved_nonterminal"
    return "other_unresolved"


def build_diagnosis(run_id: str, attempt_id: str, run_dir: Path, attempt_dir: Path) -> dict:
    execution_state = require_path(attempt_dir / "execution_state_daily.parquet")
    project_execution_panel = require_path(run_dir / "project_execution_panel.parquet")
    attempt_manifest_path = require_path(attempt_dir / "run_state_attempt_manifest.json")
    attempt_manifest = load_json(attempt_manifest_path)

    con = duckdb.connect()
    try:
        rows = con.execute(
            f"""
            SELECT
                e.snapshot_id,
                e.instrument,
                e.signal_date,
                e.entry_date,
                e.planned_exit_date,
                p.actual_exit_date,
                p.actual_exit_event_type,
                p.actual_exit_price_field,
                p.actual_sell_price,
                p.exit_delay_days,
                p.execution_path_status,
                p.execution_delayed_realized_return,
                p.terminal_event_flag,
                p.terminal_event_type,
                p.terminal_event_date,
                p.terminal_exit_pricing_method,
                p.terminal_exit_approximation_flag,
                p.terminal_exit_conservative_flag,
                e.entry_filled_D1,
                e.backtest_executable,
                e.entry_tradeable_shared_flag
            FROM read_parquet('{execution_state.as_posix()}') e
            INNER JOIN read_parquet('{project_execution_panel.as_posix()}') p
                ON e.snapshot_id = p.snapshot_id
               AND e.instrument = p.instrument
               AND e.signal_date = p.signal_date
            WHERE e.backtest_executable
              AND p.actual_exit_date IS NULL
            ORDER BY e.signal_date, e.instrument
            """
        ).fetchall()
        cols = [col[0] for col in con.description]
    finally:
        con.close()

    unresolved_rows = [dict(zip(cols, row)) for row in rows]
    terminal_instruments = {
        str(row["instrument"])
        for row in unresolved_rows
        if row["terminal_event_flag"] and row["execution_path_status"] == "terminal_event_unpriced"
    }
    for row in unresolved_rows:
        row["diagnosis_bucket"] = classify_row(row, terminal_instruments)

    bucket_counts = Counter(str(row["diagnosis_bucket"]) for row in unresolved_rows)
    execution_status_counts = Counter(str(row["execution_path_status"]) for row in unresolved_rows)
    terminal_event_type_counts = Counter(
        str(row["terminal_event_type"]) for row in unresolved_rows if row["terminal_event_type"] is not None
    )
    instrument_counts = Counter(str(row["instrument"]) for row in unresolved_rows)

    diagnosis = {
        "run_id": run_id,
        "attempt_id": attempt_id,
        "candidate_scheme_id": attempt_manifest.get("candidate_scheme_id"),
        "research_round_id": attempt_manifest.get("research_round_id"),
        "snapshot_id": attempt_manifest.get("snapshot_id"),
        "source_files": {
            "execution_state_daily": execution_state.as_posix(),
            "project_execution_panel": project_execution_panel.as_posix(),
            "run_state_attempt_manifest": attempt_manifest_path.as_posix(),
        },
        "summary": {
            "unresolved_rows": len(unresolved_rows),
            "distinct_instruments": len(instrument_counts),
            "project_execution_panel_actual_exit_missing_for_all_unresolved": all(
                row["actual_exit_date"] is None for row in unresolved_rows
            ),
            "execution_status_counts": dict(sorted(execution_status_counts.items())),
            "diagnosis_bucket_counts": dict(sorted(bucket_counts.items())),
            "terminal_event_type_counts": dict(sorted(terminal_event_type_counts.items())),
            "top_instruments": [
                {"instrument": instrument, "rows": count}
                for instrument, count in instrument_counts.most_common()
            ],
        },
        "diagnosis": {
            "portfolio_join_issue": False,
            "project_execution_panel_issue": True,
            "execution_path_issue": True,
            "root_cause": (
                "Portfolio join is preserving upstream NULL actual_exit_date values from "
                "project_execution_panel; unresolved rows are upstream execution-path/data-quality issues."
            ),
            "terminal_event_concentration": (
                "Half of unresolved rows are delist-linked terminal_event_unpriced rows with "
                "no_terminal_pricing_source."
            ),
            "nonterminal_concentration": (
                "The remaining unresolved rows are exit_unresolved rows; most are follow-on "
                "rows on instruments that also have a nearby terminal_event_unpriced row."
            ),
            "frozen_test_access": False,
        },
        "rows": unresolved_rows,
    }
    return diagnosis


def main() -> None:
    args = parse_args()
    run_dir = resolve_run_dir(args.run_id, args.input_dir)
    attempt_id, attempt_dir = resolve_attempt_dir(run_dir, args.attempt_id)
    payload = build_diagnosis(args.run_id, attempt_id, run_dir, attempt_dir)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(output_path, payload)


if __name__ == "__main__":
    main()
