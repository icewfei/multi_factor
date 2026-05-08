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
ROOT_CAUSE_CLASSES = {
    "calendar_insufficient",
    "tradability_missing",
    "terminal_event_missing",
    "sellable_retry_path_missing",
    "still_open_unresolved",
    "execution_logic_gap",
    "unknown",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose root causes for exit_unresolved rows without changing execution semantics."
    )
    parser.add_argument(
        "--diagnosis-json",
        required=True,
        help="Path to upstream unresolved-row diagnosis JSON. Only exit_unresolved rows are processed.",
    )
    parser.add_argument(
        "--project-execution-panel",
        required=True,
        help="Path to project_execution_panel.parquet.",
    )
    parser.add_argument(
        "--source-db",
        default=None,
        help="Optional warehouse.duckdb path. Overrides --run-input-contract if provided.",
    )
    parser.add_argument(
        "--run-input-contract",
        default=str(CONTRACTS_DIR / "run_input_contract.current.json"),
        help="Run input contract used to resolve the source DB when --source-db is omitted.",
    )
    parser.add_argument("--output", required=True, help="Output diagnosis JSON path.")
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


def classify_root_cause(evidence: dict[str, Any]) -> str:
    if evidence["calendar_coverage_gap"]:
        return "calendar_insufficient"
    if evidence["tradability_coverage_gap"]:
        return "tradability_missing"
    if evidence["future_sellable_open_exists"]:
        return "sellable_retry_path_missing"
    if evidence["planned_exit_sellable_at_close"]:
        return "execution_logic_gap"
    if evidence["future_terminal_event_exists"]:
        return "execution_logic_gap"
    if evidence["terminal_event_missing"]:
        return "terminal_event_missing"
    if evidence["true_unresolved"]:
        return "still_open_unresolved"
    return "unknown"


def build_row_diagnosis(
    con: duckdb.DuckDBPyConnection,
    row: dict[str, Any],
    snapshot_end_date: str | None,
) -> dict[str, Any]:
    snapshot_id = str(row["snapshot_id"])
    instrument = str(row["instrument"])
    planned_exit_date = str(row["planned_exit_date"])

    calendar_row = fetch_one_dict(
        con,
        """
        SELECT trade_date, next_trade_date
        FROM wh.serving.vw_calendar
        WHERE trade_date = ?
        """,
        [planned_exit_date],
    )
    first_future_trade = fetch_one_dict(
        con,
        """
        SELECT MIN(trade_date) AS first_trade_date_after_planned_exit
        FROM wh.serving.vw_calendar
        WHERE trade_date > ?
        """,
        [planned_exit_date],
    )["first_trade_date_after_planned_exit"]
    has_future_trading_day = first_future_trade is not None
    calendar_row_present = calendar_row["trade_date"] is not None
    calendar_coverage_gap = (
        snapshot_end_date is not None
        and planned_exit_date < snapshot_end_date
        and (
            not calendar_row_present
            or (has_future_trading_day and calendar_row["next_trade_date"] is None)
        )
    )

    planned_exit_tradability = fetch_one_dict(
        con,
        """
        SELECT
            sellable_at_close,
            exit_sellable_D5_close,
            tradability_rule_complete_flag,
            tradability_degraded_flag
        FROM wh.serving.vw_tradability_daily
        WHERE snapshot_id = ?
          AND ts_code = ?
          AND trade_date = ?
        """,
        [snapshot_id, instrument, planned_exit_date],
    )
    planned_exit_sellable_at_close = bool(
        planned_exit_tradability["sellable_at_close"]
        or planned_exit_tradability["exit_sellable_D5_close"]
    )

    future_tradability = fetch_one_dict(
        con,
        """
        SELECT
            COUNT(*) AS tradability_rows_after_planned_exit,
            MIN(trade_date) AS first_tradability_date_after_planned_exit,
            MAX(trade_date) AS last_tradability_date_after_planned_exit,
            MIN(trade_date) FILTER (WHERE sellable_retry_next_open) AS first_future_sellable_open_date,
            BOOL_OR(COALESCE(sellable_retry_next_open, FALSE)) AS future_sellable_open_exists,
            BOOL_OR(COALESCE(NOT is_listed_t, FALSE)) AS any_future_not_listed,
            BOOL_OR(COALESCE(tradability_degraded_flag, FALSE)) AS any_future_tradability_degraded
        FROM wh.serving.vw_tradability_daily
        WHERE snapshot_id = ?
          AND ts_code = ?
          AND trade_date > ?
        """,
        [snapshot_id, instrument, planned_exit_date],
    )
    future_tradability_count = int(future_tradability["tradability_rows_after_planned_exit"] or 0)
    tradability_coverage_after_planned_exit = future_tradability_count > 0
    next_trade_tradability = None
    if first_future_trade is not None:
        next_trade_tradability = fetch_one_dict(
            con,
            """
            SELECT trade_date
            FROM wh.serving.vw_tradability_daily
            WHERE snapshot_id = ?
              AND ts_code = ?
              AND trade_date = ?
            """,
            [snapshot_id, instrument, first_future_trade],
        )["trade_date"]
    tradability_coverage_gap = bool(
        has_future_trading_day
        and (not tradability_coverage_after_planned_exit or next_trade_tradability is None)
    )

    future_terminal = fetch_one_dict(
        con,
        """
        SELECT
            COUNT(*) AS future_terminal_event_count,
            MIN(event_date) AS first_future_terminal_event_date
        FROM wh.serving.vw_terminal_event_daily
        WHERE snapshot_id = ?
          AND ts_code = ?
          AND terminal_event_flag
          AND event_date > ?
        """,
        [snapshot_id, instrument, planned_exit_date],
    )
    future_terminal_event_exists = int(future_terminal["future_terminal_event_count"] or 0) > 0

    future_bars = fetch_one_dict(
        con,
        """
        SELECT
            COUNT(*) AS bars_rows_after_planned_exit,
            MIN(trade_date) AS first_bars_date_after_planned_exit,
            MAX(trade_date) AS last_bars_date_after_planned_exit
        FROM wh.serving.vw_bars_daily
        WHERE snapshot_id = ?
          AND ts_code = ?
          AND trade_date > ?
        """,
        [snapshot_id, instrument, planned_exit_date],
    )

    coverage_stops_before_snapshot_end = bool(
        snapshot_end_date is not None
        and (
            (
                future_tradability["last_tradability_date_after_planned_exit"] is not None
                and str(future_tradability["last_tradability_date_after_planned_exit"]) < snapshot_end_date
            )
            or (
                future_bars["last_bars_date_after_planned_exit"] is not None
                and str(future_bars["last_bars_date_after_planned_exit"]) < snapshot_end_date
            )
        )
    )
    terminal_event_missing = bool(
        not calendar_coverage_gap
        and not tradability_coverage_gap
        and not future_terminal_event_exists
        and not bool(future_tradability["future_sellable_open_exists"])
        and (
            bool(future_tradability["any_future_not_listed"])
            or coverage_stops_before_snapshot_end
        )
    )

    true_unresolved = bool(
        row["actual_exit_date"] is None
        and row["execution_path_status"] == "exit_unresolved"
        and not calendar_coverage_gap
        and not tradability_coverage_gap
        and not future_terminal_event_exists
        and not bool(future_tradability["future_sellable_open_exists"])
        and not terminal_event_missing
    )

    evidence = {
        "snapshot_end_date": snapshot_end_date,
        "planned_exit_has_future_trading_day": has_future_trading_day,
        "first_trade_date_after_planned_exit": first_future_trade,
        "tradability_coverage_after_planned_exit": tradability_coverage_after_planned_exit,
        "first_tradability_date_after_planned_exit": future_tradability["first_tradability_date_after_planned_exit"],
        "last_tradability_date_after_planned_exit": future_tradability["last_tradability_date_after_planned_exit"],
        "future_sellable_open_exists": bool(future_tradability["future_sellable_open_exists"]),
        "first_future_sellable_open_date": future_tradability["first_future_sellable_open_date"],
        "future_terminal_event_exists": future_terminal_event_exists,
        "first_future_terminal_event_date": future_terminal["first_future_terminal_event_date"],
        "calendar_coverage_gap": calendar_coverage_gap,
        "tradability_coverage_gap": tradability_coverage_gap,
        "terminal_event_missing": terminal_event_missing,
        "true_unresolved": true_unresolved,
        "planned_exit_sellable_at_close": planned_exit_sellable_at_close,
        "bars_coverage_after_planned_exit": int(future_bars["bars_rows_after_planned_exit"] or 0) > 0,
        "last_bars_date_after_planned_exit": future_bars["last_bars_date_after_planned_exit"],
        "future_tradability_degraded": bool(future_tradability["any_future_tradability_degraded"]),
        "terminal_pricing_used": False,
    }
    root_cause_class = classify_root_cause(evidence)
    if root_cause_class not in ROOT_CAUSE_CLASSES:
        raise ValueError(f"Unexpected root_cause_class: {root_cause_class}")

    return {
        "instrument": instrument,
        "signal_date": row["signal_date"],
        "entry_date": row["entry_date"],
        "planned_exit_date": row["planned_exit_date"],
        "actual_exit_date": row["actual_exit_date"],
        "execution_path_status": row["execution_path_status"],
        "snapshot_end_date": snapshot_end_date,
        "planned_exit_has_future_trading_day": has_future_trading_day,
        "tradability_coverage_after_planned_exit": tradability_coverage_after_planned_exit,
        "future_sellable_open_exists": bool(future_tradability["future_sellable_open_exists"]),
        "future_terminal_event_exists": future_terminal_event_exists,
        "calendar_coverage_gap": calendar_coverage_gap,
        "tradability_coverage_gap": tradability_coverage_gap,
        "terminal_event_missing": terminal_event_missing,
        "true_unresolved": true_unresolved,
        "root_cause_class": root_cause_class,
        "terminal_pricing_used": False,
        "notes": [
            "Diagnosis only. No actual_exit_date or actual_sell_price backfill performed.",
            "Diagnosis does not enable terminal_priced_last_tradable_close or zero_recovery.",
        ],
    }


def build_diagnosis(
    diagnosis_json_path: Path,
    project_execution_panel_path: Path,
    source_db_path: Path,
) -> dict[str, Any]:
    upstream = load_json(diagnosis_json_path)
    target_rows = [
        row
        for row in upstream.get("rows", [])
        if row.get("execution_path_status") == "exit_unresolved"
    ]

    keys = {
        (
            str(row["snapshot_id"]),
            str(row["instrument"]),
            str(row["signal_date"]),
        )
        for row in target_rows
    }

    con = duckdb.connect()
    try:
        con.execute(f"ATTACH '{source_db_path.as_posix()}' AS wh (READ_ONLY)")

        panel_rows = fetch_rows(
            con,
            f"""
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                entry_date,
                planned_exit_date,
                actual_exit_date,
                execution_path_status
            FROM read_parquet('{project_execution_panel_path.as_posix()}')
            WHERE execution_path_status = 'exit_unresolved'
            ORDER BY signal_date, instrument
            """,
            [],
        )

        if keys:
            panel_rows = [
                row
                for row in panel_rows
                if (str(row["snapshot_id"]), str(row["instrument"]), str(row["signal_date"])) in keys
            ]

        snapshot_end_date = fetch_one_dict(
            con,
            "SELECT MAX(trade_date) AS snapshot_end_date FROM wh.serving.vw_calendar",
            [],
        )["snapshot_end_date"]
        diagnosed_rows = [
            build_row_diagnosis(con, row, snapshot_end_date)
            for row in panel_rows
        ]
    finally:
        con.close()

    counts = Counter(str(row["root_cause_class"]) for row in diagnosed_rows)
    return {
        "diagnosis_scope": "exit_unresolved_path_only",
        "source_paths": {
            "diagnosis_json": diagnosis_json_path.as_posix(),
            "project_execution_panel": project_execution_panel_path.as_posix(),
            "source_db": source_db_path.as_posix(),
        },
        "total_exit_unresolved_rows": len(diagnosed_rows),
        "calendar_insufficient_count": counts["calendar_insufficient"],
        "tradability_missing_count": counts["tradability_missing"],
        "terminal_event_missing_count": counts["terminal_event_missing"],
        "sellable_retry_path_missing_count": counts["sellable_retry_path_missing"],
        "still_open_unresolved_count": counts["still_open_unresolved"],
        "execution_logic_gap_count": counts["execution_logic_gap"],
        "unknown_count": counts["unknown"],
        "rows": diagnosed_rows,
    }


def main() -> None:
    args = parse_args()
    payload = build_diagnosis(
        diagnosis_json_path=Path(args.diagnosis_json),
        project_execution_panel_path=Path(args.project_execution_panel),
        source_db_path=resolve_source_db_path(args),
    )
    write_json(Path(args.output), payload)


if __name__ == "__main__":
    main()
