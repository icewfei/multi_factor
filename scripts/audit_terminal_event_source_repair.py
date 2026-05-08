#!/opt/anaconda3/envs/quant_trade/bin/python
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import duckdb

ROOT = Path("/Users/wy/MiscProject/multi_factor")
CONTRACT_PATH = ROOT / "contracts" / "run_input_contract.current.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit terminal_event_unpriced rows for source repair classification."
    )
    parser.add_argument(
        "--diagnosis-json",
        default="/private/tmp/confirmed5_execution_path_unresolved_exit_diagnosis.json",
        help="Path to the diagnosis JSON",
    )
    parser.add_argument(
        "--run-input-contract",
        default=str(CONTRACT_PATH),
        help="Run input contract to resolve source DB path",
    )
    parser.add_argument("--output", required=True, help="Output repair audit JSON path")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_source_db(contract_path: Path) -> Path:
    contract = load_json(contract_path)
    source_db = Path(contract["source_root"]["snapshot_path"]) / "duckdb" / "warehouse.duckdb"
    if not source_db.exists():
        raise FileNotFoundError(f"Source DB not found: {source_db}")
    return source_db


def fetch_one(con: duckdb.DuckDBPyConnection, sql: str) -> dict[str, Any] | None:
    rows = con.execute(sql).fetchall()
    if not rows:
        return None
    cols = [col[0] for col in con.description]
    return {cols[i]: (rows[0][i].item() if hasattr(rows[0][i], "item") else rows[0][i]) for i in range(len(cols))}


def fetch_all(con: duckdb.DuckDBPyConnection, sql: str) -> list[dict[str, Any]]:
    rows = con.execute(sql).fetchall()
    cols = [col[0] for col in con.description]
    return [
        {cols[i]: (row[i].item() if hasattr(row[i], "item") else row[i]) for i in range(len(cols))}
        for row in rows
    ]


def infer_actual_last_tradable_date(
    con: duckdb.DuckDBPyConnection,
    instrument: str,
    declared_ltd: str,
) -> str | None:
    """Scan backward from declared_ltd through bars_daily to find the most recent
    trading day with close>0, adj_factor>0, volume>0, and tradable."""
    bars = fetch_all(
        con,
        f"""
        SELECT trade_date, close, adj_factor, vol
        FROM wh.serving.vw_bars_daily
        WHERE ts_code = '{instrument}'
          AND trade_date <= '{declared_ltd}'
        ORDER BY trade_date DESC
        """,
    )
    for bar in bars:
        close_val = bar["close"]
        adj_val = bar["adj_factor"]
        vol_val = bar["vol"]
        if close_val is None or close_val == 0:
            continue
        if adj_val is None or adj_val == 0:
            continue
        if vol_val is None or vol_val == 0:
            continue
        trade_date = bar["trade_date"]
        trad = fetch_one(
            con,
            f"""
            SELECT is_suspended_t, no_trade_t
            FROM wh.serving.vw_tradability_daily
            WHERE ts_code = '{instrument}' AND trade_date = '{trade_date}'
            """,
        )
        if trad is None:
            continue
        if trad["is_suspended_t"] or trad["no_trade_t"]:
            continue
        return str(trade_date)
    return None


REPAIR_POLICY_VERSION = "terminal_event_source_repair_plan_v1"


def parse_date(d: str | None) -> date | None:
    if not d:
        return None
    try:
        return date(int(d[:4]), int(d[4:6]), int(d[6:8]))
    except (ValueError, IndexError):
        return None


def calendar_diff_days(d1: str | None, d2: str | None) -> int | None:
    p1 = parse_date(d1)
    p2 = parse_date(d2)
    if p1 is None or p2 is None:
        return None
    return (p1 - p2).days


def classify_repair_case(
    con: duckdb.DuckDBPyConnection,
    row: dict[str, Any],
) -> dict[str, Any]:
    inst = row["instrument"]
    signal_date = row["signal_date"]
    terminal_date = row.get("terminal_event_date")
    terminal_type = row.get("terminal_event_type")
    snapshot = row.get("snapshot_id")
    ts = row.get("terminal_event_source") or {}
    declared_ltd = ts.get("last_tradable_date")

    result: dict[str, Any] = {
        "snapshot_id": snapshot,
        "instrument": inst,
        "signal_date": signal_date,
        "terminal_event_date": terminal_date,
        "terminal_event_type": terminal_type,
        "declared_last_tradable_date": declared_ltd,
        "actual_last_tradable_date": None,
        "last_tradable_close": None,
        "adj_factor": None,
        "volume": None,
        "repair_case": None,
        "terminal_event_source_degraded_flag": False,
        "terminal_exit_approximation_flag": False,
        "source_repair_flag": False,
        "declared_actual_ltd_diff_days": None,
        "still_hard_blocker": True,
        "can_emit_terminal_priced_last_tradable_close": False,
        "required_next_step": None,
    }

    if not declared_ltd:
        result["repair_case"] = "unclassifiable"
        result["required_next_step"] = "no_declared_last_tradable_date: cannot determine repair path"
        return result

    # Check tradability on declared last_tradable_date
    trad = fetch_one(
        con,
        f"""
        SELECT is_suspended_t, no_trade_t
        FROM wh.serving.vw_tradability_daily
        WHERE ts_code = '{inst}' AND trade_date = '{declared_ltd}'
        """,
    )

    is_suspended = trad is not None and (trad["is_suspended_t"] or trad["no_trade_t"])

    if is_suspended:
        # declared_last_tradable_date_suspended case
        actual_ltd = infer_actual_last_tradable_date(con, inst, declared_ltd)
        result["repair_case"] = "declared_last_tradable_date_suspended"
        result["actual_last_tradable_date"] = actual_ltd
        result["terminal_exit_approximation_flag"] = True
        result["source_repair_flag"] = True
        result["declared_actual_ltd_diff_days"] = calendar_diff_days(declared_ltd, actual_ltd)

        if actual_ltd:
            bar = fetch_one(
                con,
                f"""
                SELECT close, adj_factor, vol
                FROM wh.serving.vw_bars_daily
                WHERE ts_code = '{inst}' AND trade_date = '{actual_ltd}'
                """,
            )
            if bar:
                result["last_tradable_close"] = bar["close"]
                result["adj_factor"] = bar["adj_factor"]
                result["volume"] = bar["vol"]

        result["required_next_step"] = (
            "date_discrepancy_resolution_required: declared last_tradable_date "
            f"{declared_ltd} is suspended; actual last trading day is {actual_ltd}. "
            "Declared-vs-actual date difference must be recorded with "
            "terminal_exit_approximation_flag or source_repair_flag set before "
            "entry to terminal_priced_last_tradable_close."
        )
    else:
        # degraded_terminal_source_with_auditable_bars case
        bar = fetch_one(
            con,
            f"""
            SELECT close, adj_factor, vol
            FROM wh.serving.vw_bars_daily
            WHERE ts_code = '{inst}' AND trade_date = '{declared_ltd}'
            """,
        )

        result["repair_case"] = "degraded_terminal_source_with_auditable_bars"
        result["actual_last_tradable_date"] = declared_ltd
        result["terminal_event_source_degraded_flag"] = True
        result["declared_actual_ltd_diff_days"] = 0

        if bar:
            result["last_tradable_close"] = bar["close"]
            result["adj_factor"] = bar["adj_factor"]
            result["volume"] = bar["vol"]

        result["required_next_step"] = (
            "source_repair_required: terminal_event source must be upgraded from "
            "contract_degraded to auditable by cross-validating terminal_event_daily "
            "against bars_daily and tradability_daily. terminal_event_source_degraded_flag "
            "must be retained. Only after source credibility is upgraded may the row enter "
            "terminal_priced_last_tradable_close."
        )

    return result


def build_audit(diagnosis_path: Path, contract_path: Path) -> dict[str, Any]:
    diagnosis = load_json(diagnosis_path)
    source_db_path = resolve_source_db(contract_path)

    tep_rows = [r for r in diagnosis["rows"] if r["execution_path_status"] == "terminal_event_unpriced"]

    con = duckdb.connect()
    try:
        con.execute(f"ATTACH '{source_db_path.as_posix()}' AS wh (READ_ONLY)")

        audited = [classify_repair_case(con, row) for row in tep_rows]
    finally:
        con.close()

    unclassifiable = [r for r in audited if r["repair_case"] == "unclassifiable"]
    classified = [r for r in audited if r["repair_case"] != "unclassifiable"]

    degraded = [r for r in classified if r["repair_case"] == "degraded_terminal_source_with_auditable_bars"]
    suspended = [r for r in classified if r["repair_case"] == "declared_last_tradable_date_suspended"]

    return {
        "audit_status": "terminal_event_source_repair_audit_only",
        "contract_ref": "contracts/terminal_event_source_repair_plan.v1.json",
        "repair_policy_version": REPAIR_POLICY_VERSION,
        "summary": {
            "total_rows": len(classified),
            "degraded_terminal_source_with_auditable_bars_count": len(degraded),
            "declared_last_tradable_date_suspended_count": len(suspended),
            "still_hard_blocker_count": sum(1 for r in audited if r["still_hard_blocker"]),
            "can_emit_terminal_priced_last_tradable_close_count": sum(
                1 for r in audited if r["can_emit_terminal_priced_last_tradable_close"]
            ),
            "unclassifiable_excluded_count": len(unclassifiable),
        },
        "rows": classified,
        "notes": [
            "This audit classifies terminal_event_unpriced rows into repair cases only. It does not implement repair logic, produce prices, or unblock rows.",
            "All rows remain still_hard_blocker=true. No row can emit terminal_priced_last_tradable_close.",
            "zero_recovery is not assessed, enabled, or recommended by this audit.",
            "actual_exit_date and actual_sell_price are never backfilled by this script.",
            "This audit implements step 1 of the terminal_event_source_repair_plan.v1.json recommended implementation order.",
        ],
    }


def main() -> None:
    args = parse_args()
    diagnosis_path = Path(args.diagnosis_json)
    contract_path = Path(args.run_input_contract)

    if not diagnosis_path.exists():
        print(f"ERROR: diagnosis JSON not found: {diagnosis_path}", file=sys.stderr)
        sys.exit(1)

    payload = build_audit(diagnosis_path, contract_path)
    output_path = Path(args.output)
    write_json(output_path, payload)
    print(f"Repair audit written to {output_path}")


if __name__ == "__main__":
    main()
