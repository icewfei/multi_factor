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
POLICY_PATH = ROOT / "contracts" / "terminal_exit_policy.v1.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit whether terminal_event_unpriced rows satisfy the formal "
            "last-tradable-close approval gate for repaired_terminal_event_candidate."
        )
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
    parser.add_argument(
        "--policy-contract",
        default=str(POLICY_PATH),
        help="Path to terminal_exit_policy.v1.json",
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
    return {
        cols[i]: (rows[0][i].item() if hasattr(rows[0][i], "item") else rows[0][i])
        for i in range(len(cols))
    }


def infer_actual_last_trade_date(
    con: duckdb.DuckDBPyConnection,
    instrument: str,
    declared_ltd: str,
) -> tuple[str | None, dict[str, Any] | None, dict[str, Any] | None]:
    actual_last = fetch_one(
        con,
        f"""
        SELECT MAX(trade_date) AS max_trade_date
        FROM wh.serving.vw_bars_daily
        WHERE ts_code = '{instrument}' AND trade_date <= '{declared_ltd}'
        """,
    )
    actual_trade_date = None if actual_last is None else actual_last["max_trade_date"]
    if actual_trade_date is None or actual_trade_date == declared_ltd:
        return actual_trade_date, None, None

    actual_bar = fetch_one(
        con,
        f"""
        SELECT close, adj_close, adj_factor, vol, amount
        FROM wh.serving.vw_bars_daily
        WHERE ts_code = '{instrument}' AND trade_date = '{actual_trade_date}'
        """,
    )
    actual_trad = fetch_one(
        con,
        f"""
        SELECT is_suspended_t, no_trade_t, is_listed_t
        FROM wh.serving.vw_tradability_daily
        WHERE ts_code = '{instrument}' AND trade_date = '{actual_trade_date}'
        """,
    )
    return actual_trade_date, actual_bar, actual_trad


def build_required_candidate_flags(
    terminal_event_source_degraded_flag: bool,
    terminal_exit_approximation_flag: bool,
    source_repair_flag: bool,
) -> list[str]:
    flags: list[str] = []
    if terminal_event_source_degraded_flag:
        flags.append("terminal_event_source_degraded_flag")
    if terminal_exit_approximation_flag:
        flags.append("terminal_exit_approximation_flag")
    if source_repair_flag:
        flags.append("source_repair_flag")
    return flags


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
    snapshot_id = row.get("snapshot_id") or ts.get("snapshot_id")
    declared_ltd = ts.get("last_tradable_date")
    degraded = bool(ts.get("contract_degraded_flag", False))
    degraded_reason = ts.get("contract_degraded_reason")
    bridge_required = pricing_method == "terminal_event_bridge_required"

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
        "snapshot_id": snapshot_id,
        "instrument": inst,
        "signal_date": signal_date,
        "entry_date": row.get("entry_date"),
        "planned_exit_date": row.get("planned_exit_date"),
        "terminal_event_date": terminal_date,
        "terminal_event_type": terminal_type,
        "terminal_exit_pricing_method": pricing_method,
        "approval_origin_case": (
            "terminal_event_bridge_required" if bridge_required else "no_terminal_pricing_source"
        ),
        "approval_evidence_case": None,
        "approval_gate_passed": False,
        "approved_for_repaired_terminal_event_candidate": False,
        "candidate_target_state": None,
        "approved_terminal_pricing_path": None,
        "declared_last_tradable_date": declared_ltd,
        "candidate_pricing_date": None,
        "candidate_last_tradable_close": None,
        "candidate_adj_factor": None,
        "candidate_volume": None,
        "terminal_event_source_degraded_flag": degraded,
        "terminal_exit_approximation_flag": False,
        "source_repair_flag": False,
        "terminal_event_bridge_required_flag": bridge_required,
        "required_candidate_flags": [],
        "zero_recovery_approved": False,
        "still_hard_blocker": True,
        "approval_gate_failure_reason": None,
        "required_next_step": None,
        "blocking_reasons": [],
        "contract_degraded_reason": degraded_reason,
        "declared_ltd_is_suspended": None,
        "declared_ltd_is_no_trade": None,
        "declared_ltd_is_listed": None,
        "actual_last_trade_date_in_bars": None,
        "actual_last_trade_date_close_available": False,
    }

    if not declared_ltd:
        result["approval_gate_failure_reason"] = "missing_declared_last_tradable_date"
        result["blocking_reasons"].append("no last_tradable_date in terminal_event source")
        result["required_next_step"] = (
            "Remain hard blocker. terminal_event source does not provide declared last_tradable_date."
        )
        return result

    trad = fetch_one(
        con,
        f"""
        SELECT is_suspended_t, no_trade_t, is_listed_t
        FROM wh.serving.vw_tradability_daily
        WHERE ts_code = '{inst}' AND trade_date = '{declared_ltd}'
        """,
    )
    if trad is None:
        result["approval_gate_failure_reason"] = "missing_declared_last_tradable_tradability"
        result["blocking_reasons"].append(
            f"no tradability data on declared last_tradable_date {declared_ltd}"
        )
        result["required_next_step"] = (
            "Remain hard blocker. tradability_daily coverage is missing on declared last_tradable_date."
        )
        return result

    result["declared_ltd_is_suspended"] = trad["is_suspended_t"]
    result["declared_ltd_is_no_trade"] = trad["no_trade_t"]
    result["declared_ltd_is_listed"] = trad["is_listed_t"]

    declared_bar = fetch_one(
        con,
        f"""
        SELECT close, adj_close, adj_factor, vol, amount
        FROM wh.serving.vw_bars_daily
        WHERE ts_code = '{inst}' AND trade_date = '{declared_ltd}'
        """,
    )

    declared_is_blocked = bool(trad["is_suspended_t"] or trad["no_trade_t"])
    if declared_is_blocked:
        result["approval_evidence_case"] = "declared_last_tradable_date_suspended"
        result["terminal_exit_approximation_flag"] = True
        result["source_repair_flag"] = True

        actual_trade_date, actual_bar, actual_trad = infer_actual_last_trade_date(con, inst, declared_ltd)
        result["actual_last_trade_date_in_bars"] = actual_trade_date
        result["actual_last_trade_date_close_available"] = actual_bar is not None

        if (
            actual_trade_date
            and actual_bar
            and actual_bar.get("close") not in (None, 0)
            and actual_bar.get("adj_factor") not in (None, 0)
            and actual_bar.get("vol") not in (None, 0)
            and actual_trad is not None
            and not actual_trad.get("is_suspended_t")
            and not actual_trad.get("no_trade_t")
        ):
            result["approval_gate_passed"] = True
            result["approved_for_repaired_terminal_event_candidate"] = True
            result["candidate_target_state"] = "repaired_terminal_event_candidate"
            result["approved_terminal_pricing_path"] = "terminal_priced_last_tradable_close"
            result["candidate_pricing_date"] = actual_trade_date
            result["candidate_last_tradable_close"] = actual_bar["close"]
            result["candidate_adj_factor"] = actual_bar["adj_factor"]
            result["candidate_volume"] = actual_bar["vol"]
            result["required_next_step"] = (
                "Approval gate passed for repaired_terminal_event_candidate. "
                "Execution path must still compute formal actual exit fields upstream."
            )
        else:
            result["approval_gate_failure_reason"] = "missing_auditable_actual_last_trade_date"
            result["blocking_reasons"].append(
                f"declared last_tradable_date {declared_ltd} is suspended/no_trade and no auditable earlier trading day was confirmed"
            )
            result["required_next_step"] = (
                "Remain hard blocker. Need auditable actual_last_tradable_date with close/adj_factor/volume."
            )
    else:
        result["approval_evidence_case"] = "degraded_terminal_source_with_auditable_bars"
        result["source_repair_flag"] = True
        if declared_bar is None:
            result["approval_gate_failure_reason"] = "missing_declared_last_tradable_bar"
            result["blocking_reasons"].append(
                f"no bars_daily data on declared last_tradable_date {declared_ltd}"
            )
            result["required_next_step"] = (
                "Remain hard blocker. Need auditable bars_daily close/adj_factor/volume on declared last_tradable_date."
            )
        elif declared_bar.get("close") in (None, 0):
            result["approval_gate_failure_reason"] = "invalid_declared_last_tradable_close"
            result["blocking_reasons"].append("close is NULL or zero on declared last_tradable_date")
            result["required_next_step"] = (
                "Remain hard blocker. close must be > 0 on declared last_tradable_date."
            )
        elif declared_bar.get("adj_factor") in (None, 0):
            result["approval_gate_failure_reason"] = "invalid_declared_last_tradable_adj_factor"
            result["blocking_reasons"].append("adj_factor is NULL or zero on declared last_tradable_date")
            result["required_next_step"] = (
                "Remain hard blocker. adj_factor must be > 0 on declared last_tradable_date."
            )
        elif declared_bar.get("vol") in (None, 0):
            result["approval_gate_failure_reason"] = "invalid_declared_last_tradable_volume"
            result["blocking_reasons"].append("volume is NULL or zero on declared last_tradable_date")
            result["required_next_step"] = (
                "Remain hard blocker. volume must be > 0 on declared last_tradable_date."
            )
        else:
            result["approval_gate_passed"] = True
            result["approved_for_repaired_terminal_event_candidate"] = True
            result["candidate_target_state"] = "repaired_terminal_event_candidate"
            result["approved_terminal_pricing_path"] = "terminal_priced_last_tradable_close"
            result["candidate_pricing_date"] = declared_ltd
            result["candidate_last_tradable_close"] = declared_bar["close"]
            result["candidate_adj_factor"] = declared_bar["adj_factor"]
            result["candidate_volume"] = declared_bar["vol"]
            result["required_next_step"] = (
                "Approval gate passed for repaired_terminal_event_candidate. "
                "Execution path must still compute formal actual exit fields upstream."
            )

    result["required_candidate_flags"] = build_required_candidate_flags(
        terminal_event_source_degraded_flag=result["terminal_event_source_degraded_flag"],
        terminal_exit_approximation_flag=result["terminal_exit_approximation_flag"],
        source_repair_flag=result["source_repair_flag"],
    )
    if bridge_required:
        result["required_candidate_flags"].append("terminal_event_bridge_required")

    if not result["approval_gate_passed"] and not result["blocking_reasons"]:
        result["blocking_reasons"].append("approval gate did not pass")
    if not result["approval_gate_passed"] and result["required_next_step"] is None:
        result["required_next_step"] = "Remain hard blocker until approval gate requirements are satisfied."

    return result


def build_audit(
    diagnosis_path: Path,
    contract_path: Path,
    policy_path: Path,
) -> dict[str, Any]:
    diagnosis = load_json(diagnosis_path)
    source_db_path = resolve_source_db(contract_path)
    policy = load_json(policy_path)
    policy_version = policy["contract_version"]

    tep_rows = [r for r in diagnosis["rows"] if r["execution_path_status"] == "terminal_event_unpriced"]

    con = duckdb.connect()
    try:
        con.execute(f"ATTACH '{source_db_path.as_posix()}' AS wh (READ_ONLY)")
        audited = [audit_row(con, row) for row in tep_rows]
    finally:
        con.close()

    passed_rows = [r for r in audited if r["approval_gate_passed"]]
    failed_rows = [r for r in audited if not r["approval_gate_passed"]]
    bridge_rows = [r for r in audited if r["terminal_event_bridge_required_flag"]]
    suspended_rows = [
        r for r in audited if r["approval_evidence_case"] == "declared_last_tradable_date_suspended"
    ]
    degraded_rows = [
        r
        for r in audited
        if r["approval_evidence_case"] == "degraded_terminal_source_with_auditable_bars"
    ]

    return {
        "audit_status": "terminal_last_tradable_close_approval_audit_only",
        "contract_ref": "contracts/terminal_exit_policy.v1.json",
        "approval_policy_version": policy_version,
        "summary": {
            "total_rows": len(audited),
            "candidate_rows_count": len(passed_rows),
            "approval_gate_passed_count": len(passed_rows),
            "approval_gate_failed_count": len(failed_rows),
            "still_hard_blocker_count": len(audited),
            "zero_recovery_approved_count": 0,
            "terminal_event_bridge_required_count": len(bridge_rows),
            "declared_last_tradable_date_suspended_count": len(suspended_rows),
            "degraded_terminal_source_with_auditable_bars_count": len(degraded_rows),
        },
        "rows": audited,
        "notes": [
            "This approval audit only determines eligibility for repaired_terminal_event_candidate.",
            "Approval gate passed does not mean the row is priced. All rows remain hard blockers until upstream execution path emits actual_exit_date, actual_sell_price, and execution_delayed_realized_return.",
            "zero_recovery remains disabled by default in this audit.",
            "approval audit never backfills actual_exit_date, actual_sell_price, or execution_delayed_realized_return.",
            "Bridge-origin rows must retain terminal_event_bridge_required as an audit breadcrumb when they enter repaired_terminal_event_candidate.",
        ],
    }


def main() -> None:
    args = parse_args()
    diagnosis_path = Path(args.diagnosis_json)
    contract_path = Path(args.run_input_contract)
    policy_path = Path(args.policy_contract)

    if not diagnosis_path.exists():
        print(f"ERROR: diagnosis JSON not found: {diagnosis_path}", file=sys.stderr)
        sys.exit(1)
    if not policy_path.exists():
        print(f"ERROR: policy contract not found: {policy_path}", file=sys.stderr)
        sys.exit(1)

    payload = build_audit(diagnosis_path, contract_path, policy_path)
    output_path = Path(args.output)
    write_json(output_path, payload)
    print(f"Audit written to {output_path}")


if __name__ == "__main__":
    main()
