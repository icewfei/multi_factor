#!/opt/anaconda3/envs/quant_trade/bin/python
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
CONTRACTS_DIR = ROOT / "contracts"
TRADABILITY_GAP_CLASSES = {
    "full_tradability_coverage_missing",
    "partial_tradability_coverage_gap",
    "post_delist_coverage_gap",
    "bars_without_tradability",
    "calendar_without_tradability",
    "unknown",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose the specific tradability coverage gap for exit_unresolved tradability_missing rows."
    )
    parser.add_argument(
        "--exit-unresolved-diagnosis",
        required=True,
        help="Path to exit_unresolved path diagnosis JSON from diagnose_exit_unresolved_path.py.",
    )
    parser.add_argument(
        "--source-db",
        default=None,
        help="Optional warehouse.duckdb path. Overrides --run-input-contract if provided.",
    )
    parser.add_argument(
        "--run-input-contract",
        default=str(CONTRACTS_DIR / "run_input_contract.research_trainval_20211231.json"),
        help="Run input contract used to resolve the source DB when --source-db is omitted.",
    )
    parser.add_argument("--output", required=True, help="Output JSON path.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_source_db_path(args: argparse.Namespace) -> Path:
    if args.source_db:
        source_db = Path(args.source_db)
    else:
        contract = load_json(Path(args.run_input_contract))
        source_db = Path(contract["source_root"]["snapshot_path"]) / "duckdb" / "warehouse.duckdb"
    if not source_db.exists():
        raise FileNotFoundError(f"Source DB not found: {source_db}")
    return source_db


def normalize_scalar(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    return value


def fetch_one_dict(con: duckdb.DuckDBPyConnection, sql: str, params: list[Any]) -> dict[str, Any]:
    row = con.execute(sql, params).fetchone()
    cols = [col[0] for col in con.description]
    if row is None:
        return {col: None for col in cols}
    return {col: normalize_scalar(value) for col, value in zip(cols, row)}


def fetch_rows(con: duckdb.DuckDBPyConnection, sql: str, params: list[Any]) -> list[dict[str, Any]]:
    rows = con.execute(sql, params).fetchall()
    cols = [col[0] for col in con.description]
    return [{col: normalize_scalar(value) for col, value in zip(cols, row)} for row in rows]


def classify_gap(evidence: dict[str, Any]) -> str:
    if evidence["post_delist_coverage_gap"]:
        return "post_delist_coverage_gap"
    if evidence["bars_available_during_missing_days"] and evidence["missing_tradability_days"] > 0:
        return "bars_without_tradability"
    if evidence["missing_tradability_days"] > 0 and evidence["present_tradability_days"] > 0:
        return "partial_tradability_coverage_gap"
    if evidence["symbol_has_no_tradability_rows_anywhere"]:
        return "full_tradability_coverage_missing"
    if evidence["calendar_without_tradability"]:
        return "calendar_without_tradability"
    return "unknown"


def build_row_diagnosis(
    con: duckdb.DuckDBPyConnection,
    row: dict[str, Any],
) -> dict[str, Any]:
    snapshot_id = "warehouse_20260429_trainval_20211231"
    instrument = str(row["instrument"])
    planned_exit_date = str(row["planned_exit_date"])
    snapshot_end_date = str(row["snapshot_end_date"])

    future_calendar_rows = fetch_rows(
        con,
        """
        SELECT trade_date
        FROM wh.serving.vw_calendar
        WHERE trade_date > ?
          AND trade_date <= ?
        ORDER BY trade_date
        """,
        [planned_exit_date, snapshot_end_date],
    )
    retry_dates = [str(r["trade_date"]) for r in future_calendar_rows]

    tradability_rows = fetch_rows(
        con,
        """
        SELECT trade_date
        FROM wh.serving.vw_tradability_daily
        WHERE snapshot_id = ?
          AND ts_code = ?
          AND trade_date > ?
          AND trade_date <= ?
        ORDER BY trade_date
        """,
        [snapshot_id, instrument, planned_exit_date, snapshot_end_date],
    )
    tradability_dates = {str(r["trade_date"]) for r in tradability_rows}
    missing_dates = [trade_date for trade_date in retry_dates if trade_date not in tradability_dates]

    bars_rows = fetch_rows(
        con,
        """
        SELECT trade_date
        FROM wh.serving.vw_bars_daily
        WHERE snapshot_id = ?
          AND ts_code = ?
          AND trade_date > ?
          AND trade_date <= ?
        ORDER BY trade_date
        """,
        [snapshot_id, instrument, planned_exit_date, snapshot_end_date],
    )
    bars_dates = {str(r["trade_date"]) for r in bars_rows}
    bars_on_missing_dates = [trade_date for trade_date in missing_dates if trade_date in bars_dates]

    terminal_rows = fetch_rows(
        con,
        """
        SELECT
            event_date,
            terminal_event_type,
            last_trade_date,
            contract_degraded_flag
        FROM wh.serving.vw_terminal_event_daily
        WHERE snapshot_id = ?
          AND ts_code = ?
          AND event_date <= ?
        ORDER BY event_date
        """,
        [snapshot_id, instrument, planned_exit_date],
    )
    latest_terminal = terminal_rows[-1] if terminal_rows else None

    full_tradability = fetch_one_dict(
        con,
        """
        SELECT
            COUNT(*) AS tradability_total_rows,
            MIN(trade_date) AS first_tradability_date,
            MAX(trade_date) AS last_tradability_date
        FROM wh.serving.vw_tradability_daily
        WHERE snapshot_id = ?
          AND ts_code = ?
        """,
        [snapshot_id, instrument],
    )
    full_bars = fetch_one_dict(
        con,
        """
        SELECT
            COUNT(*) AS bars_total_rows,
            MIN(trade_date) AS first_bars_date,
            MAX(trade_date) AS last_bars_date
        FROM wh.serving.vw_bars_daily
        WHERE snapshot_id = ?
          AND ts_code = ?
        """,
        [snapshot_id, instrument],
    )

    symbol_has_no_tradability_rows_anywhere = int(full_tradability["tradability_total_rows"] or 0) == 0
    terminal_event_exists_but_not_connected = latest_terminal is not None
    post_delist_coverage_gap = bool(
        latest_terminal is not None
        and latest_terminal["last_trade_date"] is not None
        and missing_dates
        and str(latest_terminal["last_trade_date"]) < missing_dates[0]
        and len(tradability_rows) == 0
        and len(bars_rows) == 0
    )
    calendar_without_tradability = bool(
        retry_dates
        and len(missing_dates) == len(retry_dates)
        and not bars_on_missing_dates
        and not post_delist_coverage_gap
    )

    evidence = {
        "retry_date_range": {
            "start": None if not retry_dates else retry_dates[0],
            "end": None if not retry_dates else retry_dates[-1],
        },
        "missing_tradability_start_date": None if not missing_dates else missing_dates[0],
        "missing_tradability_end_date": None if not missing_dates else missing_dates[-1],
        "missing_tradability_days": len(missing_dates),
        "present_tradability_days": len(tradability_rows),
        "bars_available_during_missing_days": bool(bars_on_missing_dates),
        "bars_available_during_missing_day_count": len(bars_on_missing_dates),
        "vw_tradability_daily_fully_missing_after_planned_exit": len(tradability_rows) == 0,
        "symbol_has_no_tradability_rows_anywhere": symbol_has_no_tradability_rows_anywhere,
        "calendar_without_tradability": calendar_without_tradability,
        "post_delist_coverage_gap": post_delist_coverage_gap,
        "terminal_event_exists_but_not_connected_to_execution_path": terminal_event_exists_but_not_connected,
    }
    gap_class = classify_gap(evidence)
    if gap_class not in TRADABILITY_GAP_CLASSES:
        raise ValueError(f"Unexpected tradability_gap_class: {gap_class}")

    if gap_class == "post_delist_coverage_gap":
        recommended_resolution = (
            "Investigate post-delist source coverage break and propagate upstream terminal_event context "
            "to exit_unresolved follow-on rows before execution-path pricing decisions."
        )
    elif gap_class == "bars_without_tradability":
        recommended_resolution = (
            "Repair vw_tradability_daily generation for dates where bars exist but tradability rows are absent."
        )
    elif gap_class == "partial_tradability_coverage_gap":
        recommended_resolution = (
            "Repair the missing subset of vw_tradability_daily retry-window dates for this instrument."
        )
    elif gap_class == "full_tradability_coverage_missing":
        recommended_resolution = (
            "Investigate why vw_tradability_daily has no rows for this symbol in the snapshot."
        )
    elif gap_class == "calendar_without_tradability":
        recommended_resolution = (
            "Repair tradability coverage for calendar retry dates that exist without matching tradability rows."
        )
    else:
        recommended_resolution = "Unknown gap pattern; inspect source extraction and symbol lifecycle history."

    return {
        "instrument": instrument,
        "signal_date": row["signal_date"],
        "entry_date": row["entry_date"],
        "planned_exit_date": row["planned_exit_date"],
        "retry_date_range": evidence["retry_date_range"],
        "missing_tradability_dates": missing_dates,
        "vw_tradability_daily_fully_missing_after_planned_exit": evidence["vw_tradability_daily_fully_missing_after_planned_exit"],
        "bars_available_during_missing_days": evidence["bars_available_during_missing_days"],
        "bars_available_during_missing_day_count": evidence["bars_available_during_missing_day_count"],
        "bars_available_dates_during_missing_days": bars_on_missing_dates,
        "calendar_without_tradability": evidence["calendar_without_tradability"],
        "terminal_event_exists_but_not_connected_to_execution_path": terminal_event_exists_but_not_connected,
        "terminal_event_on_or_before_planned_exit": latest_terminal,
        "is_symbol_delist_post_coverage_gap": post_delist_coverage_gap,
        "missing_tradability_start_date": evidence["missing_tradability_start_date"],
        "missing_tradability_end_date": evidence["missing_tradability_end_date"],
        "missing_tradability_days": evidence["missing_tradability_days"],
        "tradability_gap_class": gap_class,
        "recommended_resolution": recommended_resolution,
        "actual_exit_date": row.get("actual_exit_date"),
        "notes": [
            "Diagnosis only. No actual_exit_date or actual_sell_price backfill performed.",
            "Diagnosis does not enable terminal pricing or change execution semantics.",
        ],
    }


def build_diagnosis(input_path: Path, source_db_path: Path) -> dict[str, Any]:
    payload = load_json(input_path)
    target_rows = [
        row
        for row in payload.get("rows", [])
        if row.get("root_cause_class") == "tradability_missing"
    ]

    con = duckdb.connect()
    try:
        con.execute(f"ATTACH '{source_db_path.as_posix()}' AS wh (READ_ONLY)")
        diagnosed_rows = [build_row_diagnosis(con, row) for row in target_rows]
    finally:
        con.close()

    counts = Counter(str(row["tradability_gap_class"]) for row in diagnosed_rows)
    return {
        "diagnosis_scope": "tradability_missing_exit_only",
        "source_paths": {
            "exit_unresolved_diagnosis": input_path.as_posix(),
            "source_db": source_db_path.as_posix(),
        },
        "total_tradability_missing_rows": len(diagnosed_rows),
        "full_tradability_coverage_missing_count": counts["full_tradability_coverage_missing"],
        "partial_tradability_coverage_gap_count": counts["partial_tradability_coverage_gap"],
        "post_delist_coverage_gap_count": counts["post_delist_coverage_gap"],
        "bars_without_tradability_count": counts["bars_without_tradability"],
        "calendar_without_tradability_count": counts["calendar_without_tradability"],
        "unknown_count": counts["unknown"],
        "rows": diagnosed_rows,
    }


def main() -> None:
    args = parse_args()
    payload = build_diagnosis(
        input_path=Path(args.exit_unresolved_diagnosis),
        source_db_path=resolve_source_db_path(args),
    )
    write_json(Path(args.output), payload)


if __name__ == "__main__":
    main()
