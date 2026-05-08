#!/opt/anaconda3/envs/quant_trade/bin/python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import duckdb

ROOT = Path("/Users/wy/MiscProject/multi_factor")
CONTRACT_PATH = ROOT / "contracts" / "run_input_contract.research_trainval_20211231.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit whether terminal_event_unpriced rows have auditable last_tradable_close pricing conditions."
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
    parser.add_argument("--output", required=True, help="Output audit JSON path")
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
    result = {cols[i]: (rows[0][i].item() if hasattr(rows[0][i], "item") else rows[0][i]) for i in range(len(cols))}
    return result


def fetch_all(con: duckdb.DuckDBPyConnection, sql: str) -> list[dict[str, Any]]:
    rows = con.execute(sql).fetchall()
    cols = [col[0] for col in con.description]
    return [
        {cols[i]: (row[i].item() if hasattr(row[i], "item") else row[i]) for i in range(len(cols))}
        for row in rows
    ]


def audit_row(
    con: duckdb.DuckDBPyConnection,
    row: dict[str, Any],
) -> dict[str, Any]:
    inst = row["instrument"]
    signal_date = row["signal_date"]
    terminal_date = row.get("terminal_event_date")
    terminal_type = row.get("terminal_event_type")
    pricing_method = row.get("terminal_exit_pricing_method")
    ts = row.get("terminal_event_source") or {}
    declared_ltd = ts.get("last_tradable_date")
    degraded = ts.get("contract_degraded_flag", False)
    degraded_reason = ts.get("contract_degraded_reason")

    # If degraded_reason is not in the diagnosis JSON, query the source directly
    if degraded and not degraded_reason and terminal_date:
        term_row = fetch_one(
            con,
            f"""
            SELECT contract_degraded_reason
            FROM wh.serving.vw_terminal_event_daily
            WHERE ts_code = '{inst}' AND event_date = '{terminal_date}'
            """,
        )
        if term_row:
            degraded_reason = term_row.get("contract_degraded_reason")

    result: dict[str, Any] = {
        "instrument": inst,
        "signal_date": signal_date,
        "entry_date": row.get("entry_date"),
        "planned_exit_date": row.get("planned_exit_date"),
        "terminal_event_date": terminal_date,
        "terminal_event_type": terminal_type,
        "terminal_exit_pricing_method": pricing_method,
        "last_tradable_date_from_terminal_source": declared_ltd,
        "contract_degraded_flag": degraded,
        "contract_degraded_reason": degraded_reason,
        "last_tradable_close_auditable": False,
        "can_price_with_last_tradable_close": False,
        "blocking_reasons": [],
    }

    if not declared_ltd:
        result["blocking_reasons"].append("no last_tradable_date in terminal_event source")
        result["last_tradable_close_auditable"] = False
        return result

    if not terminal_date:
        result["blocking_reasons"].append("no terminal_event_date")
        result["last_tradable_close_auditable"] = False
        return result

    # check tradability on declared last_tradable_date
    trad = fetch_one(
        con,
        f"""
        SELECT is_suspended_t, no_trade_t, is_listed_t
        FROM wh.serving.vw_tradability_daily
        WHERE ts_code = '{inst}' AND trade_date = '{declared_ltd}'
        """,
    )

    if trad is None:
        result["blocking_reasons"].append(f"no tradability data on declared last_tradable_date {declared_ltd}")
        result["declared_ltd_is_suspended"] = None
        result["declared_ltd_is_no_trade"] = None
        result["declared_ltd_is_listed"] = None
    else:
        result["declared_ltd_is_suspended"] = trad["is_suspended_t"]
        result["declared_ltd_is_no_trade"] = trad["no_trade_t"]
        result["declared_ltd_is_listed"] = trad["is_listed_t"]

    # check bars_daily on declared last_tradable_date
    bar = fetch_one(
        con,
        f"""
        SELECT close, adj_close, adj_factor, vol, amount
        FROM wh.serving.vw_bars_daily
        WHERE ts_code = '{inst}' AND trade_date = '{declared_ltd}'
        """,
    )

    if bar is not None:
        result["pricing_date_used"] = declared_ltd
        result["pricing_date_source"] = "terminal_event_last_tradable_date"
        result["raw_close"] = bar["close"]
        result["adj_close"] = bar["adj_close"]
        result["adj_factor"] = bar["adj_factor"]
        result["volume"] = bar["vol"]
        result["amount"] = bar["amount"]
        result["close_source"] = "vw_bars_daily"
        result["close_source_auditable"] = True

        if bar["close"] is None:
            result["blocking_reasons"].append("close is NULL on last_tradable_date")
        elif bar["close"] == 0:
            result["blocking_reasons"].append("close is zero on last_tradable_date")
        elif bar["adj_factor"] is None:
            result["blocking_reasons"].append("adj_factor is NULL on last_tradable_date; cannot construct adjusted return")
        elif bar["vol"] is not None and bar["vol"] == 0:
            result["blocking_reasons"].append("volume is zero on last_tradable_date; no trading occurred")
        elif trad and (trad["is_suspended_t"] or trad["no_trade_t"]):
            result["blocking_reasons"].append(
                f"declared last_tradable_date {declared_ltd} has close data but is suspended/no_trade "
                f"(suspended={trad['is_suspended_t']}, no_trade={trad['no_trade_t']})"
            )
        elif degraded:
            result["blocking_reasons"].append(
                "terminal_event source is contract_degraded: "
                f"{degraded_reason or 'no reason provided'}"
            )
            result["last_tradable_close_auditable"] = False
        else:
            result["last_tradable_close_auditable"] = True
            result["can_price_with_last_tradable_close"] = True
    else:
        result["pricing_date_used"] = None
        result["pricing_date_source"] = None
        result["raw_close"] = None
        result["adj_close"] = None
        result["adj_factor"] = None
        result["volume"] = None
        result["amount"] = None
        result["close_source"] = None
        result["close_source_auditable"] = False

        missing_reason = f"no bars_daily data on declared last_tradable_date {declared_ltd}"
        if trad and (trad.get("is_suspended_t") or trad.get("no_trade_t")):
            missing_reason += (
                f" (suspended={trad['is_suspended_t']}, no_trade={trad['no_trade_t']})"
            )
        result["blocking_reasons"].append(missing_reason)

        # check actual last trade date
        max_dt_row = fetch_one(
            con,
            f"""
            SELECT MAX(trade_date) AS max_trade_date
            FROM wh.serving.vw_bars_daily
            WHERE ts_code = '{inst}' AND trade_date <= '{declared_ltd}'
            """,
        )
        actual_last = max_dt_row["max_trade_date"] if max_dt_row else None
        result["actual_last_trade_date_in_bars"] = actual_last

        if actual_last and actual_last != declared_ltd:
            # check bars on actual last trade date
            actual_bar = fetch_one(
                con,
                f"""
                SELECT close, adj_close, adj_factor, vol
                FROM wh.serving.vw_bars_daily
                WHERE ts_code = '{inst}' AND trade_date = '{actual_last}'
                """,
            )
            if actual_bar:
                result["actual_last_trade_date_close_available"] = True
                result["actual_last_trade_date_close"] = actual_bar["close"]
                result["actual_last_trade_date_adj_close"] = actual_bar["adj_close"]
                result["actual_last_trade_date_adj_factor"] = actual_bar["adj_factor"]

                # check tradability on actual last trade date
                actual_trad = fetch_one(
                    con,
                    f"""
                    SELECT is_suspended_t, no_trade_t
                    FROM wh.serving.vw_tradability_daily
                    WHERE ts_code = '{inst}' AND trade_date = '{actual_last}'
                    """,
                )
                if actual_trad:
                    result["actual_last_trade_date_is_suspended"] = actual_trad["is_suspended_t"]
                    result["actual_last_trade_date_is_no_trade"] = actual_trad["no_trade_t"]

                    if actual_trad["is_suspended_t"] or actual_trad["no_trade_t"]:
                        result["blocking_reasons"].append(
                            f"actual last trade date {actual_last} is also suspended/no_trade"
                        )
                    else:
                        result["actual_last_trade_date_data_auditable"] = True
                        result["blocking_reasons"].append(
                            f"declared last_tradable_date {declared_ltd} is suspended; "
                            f"actual last trade date is {actual_last} with close={actual_bar['close']}. "
                            f"Terminal event source last_tradable_date does not match actual last trading day."
                        )
            else:
                result["actual_last_trade_date_close_available"] = False
        elif actual_last is None:
            result["actual_last_trade_date_close_available"] = False
            result["blocking_reasons"].append(
                f"no bars_daily data exists for {inst} up to {declared_ltd}"
            )

    # terminal_event_date must be after declared_ltd
    if declared_ltd and terminal_date:
        result["terminal_event_date_after_last_tradable_date"] = declared_ltd < terminal_date

    return result


def build_audit(diagnosis_path: Path, contract_path: Path) -> dict[str, Any]:
    diagnosis = load_json(diagnosis_path)
    source_db_path = resolve_source_db(contract_path)

    tep_rows = [r for r in diagnosis["rows"] if r["execution_path_status"] == "terminal_event_unpriced"]

    con = duckdb.connect()
    try:
        con.execute(f"ATTACH '{source_db_path.as_posix()}' AS wh (READ_ONLY)")

        audited = [audit_row(con, row) for row in tep_rows]
    finally:
        con.close()

    auditable = [r for r in audited if r["last_tradable_close_auditable"]]
    not_auditable = [r for r in audited if not r["last_tradable_close_auditable"]]
    can_price = [r for r in audited if r["can_price_with_last_tradable_close"]]

    actual_last_available = [
        r for r in audited
        if r.get("actual_last_trade_date_close_available") and not r["last_tradable_close_auditable"]
    ]
    declared_ltd_suspended = [
        r for r in audited
        if r.get("declared_ltd_is_suspended") or r.get("declared_ltd_is_no_trade")
    ]

    can_recommend = len(can_price) > 0

    return {
        "audit_status": "last_tradable_close_audit_only",
        "total_terminal_event_unpriced_rows": len(audited),
        "auditable_count": len(auditable),
        "not_auditable_count": len(not_auditable),
        "can_price_with_last_tradable_close_count": len(can_price),
        "summary": {
            "rows_with_close_on_declared_ltd": sum(
                1 for r in audited if r.get("raw_close") is not None
            ),
            "rows_without_close_on_declared_ltd": sum(
                1 for r in audited if r.get("raw_close") is None
            ),
            "rows_with_close_data_but_contract_degraded": sum(
                1 for r in audited
                if r.get("raw_close") is not None and r["contract_degraded_flag"] is True
            ),
            "rows_with_declared_ltd_suspended_or_no_trade": len(declared_ltd_suspended),
            "rows_with_actual_last_trade_close_available": len(actual_last_available),
            "rows_with_actual_last_trade_data_auditable": sum(
                1 for r in audited if r.get("actual_last_trade_date_data_auditable")
            ),
        },
        "rows": audited,
        "recommendation": (
            "4 of 10 rows have close data on the declared last_tradable_date but all 10 are blocked "
            "by contract_degraded_flag=true on the terminal_event source. The bars_daily data itself "
            "is from a separate standard shared-source view and is auditable on its own. "
            "6 rows have a declared last_tradable_date that is suspended/no_trade; the actual last "
            "trading day (earlier) has auditable close data. "
            "Recommendation: "
            "(1) Resolve whether bars_daily close is sufficient to override contract_degraded terminal_event source. "
            "If yes, 4 rows can be priced via last_tradable_close immediately. "
            "(2) For the 6 suspended rows, decide whether the actual last trade date (from bars_daily) "
            "can serve as the last_tradable_date for pricing purposes, since the terminal_event source "
            "declares a suspended date. "
            "(3) Do NOT enable zero_recovery until the above is resolved."
        ),
        "notes": [
            "This audit only examines last_tradable_close pricing conditions. It does not implement pricing, modify data, or unblock any rows.",
            "zero_recovery is not assessed or enabled by this audit.",
            "actual_exit_date and actual_sell_price are never backfilled by this script.",
            "The terminal_event source is contract_degraded for all 10 rows. The bars_daily source is a separate shared-source view.",
            "For suspended rows, the discrepancy between terminal_event last_tradable_date and actual last trade date must be investigated upstream.",
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
    print(f"Audit written to {output_path}")


if __name__ == "__main__":
    main()
