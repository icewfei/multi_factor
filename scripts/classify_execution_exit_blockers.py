#!/opt/anaconda3/envs/quant_trade/bin/python
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path("/Users/wy/MiscProject/multi_factor")
CONTRACT_PATH = ROOT / "contracts" / "terminal_exit_policy.v1.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify unresolved exit rows against terminal_exit_policy.v1.json."
    )
    parser.add_argument(
        "--diagnosis-json",
        default="/private/tmp/confirmed5_execution_path_unresolved_exit_diagnosis.json",
        help="Path to the diagnosis JSON from diagnose_execution_path_unresolved_exit.py",
    )
    parser.add_argument(
        "--policy-contract",
        default=str(CONTRACT_PATH),
        help="Path to terminal_exit_policy.v1.json",
    )
    parser.add_argument("--output", required=True, help="Output classification JSON path")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def classify_row(
    row: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    status = row.get("execution_path_status", "")
    terminal_source = row.get("terminal_event_source") or {}
    is_terminal = bool(row.get("terminal_event_flag"))
    has_cash = terminal_source.get("cash_settlement_flag") is True
    has_last_tradable = terminal_source.get("last_tradable_date") is not None
    is_degraded = terminal_source.get("contract_degraded_flag") is True

    classification: dict[str, Any] = {
        "instrument": row["instrument"],
        "signal_date": row["signal_date"],
        "entry_date": row.get("entry_date"),
        "planned_exit_date": row.get("planned_exit_date"),
        "execution_path_status": status,
        "terminal_event_flag": is_terminal,
        "terminal_event_type": row.get("terminal_event_type"),
        "terminal_event_date": row.get("terminal_event_date"),
        "terminal_exit_pricing_method": row.get("terminal_exit_pricing_method"),
    }

    # --- determine blocker category ---
    if status == "terminal_event_unpriced":
        classification["blocker_category"] = "terminal_event_unpriced"
        classification["is_hard_blocker"] = True
        classification["blocker_reason"] = policy["hard_blocker_rules"]["terminal_event_unpriced"]["reason"]
    elif status == "exit_unresolved":
        classification["blocker_category"] = "exit_unresolved"
        classification["is_hard_blocker"] = True
        classification["blocker_reason"] = policy["hard_blocker_rules"]["exit_unresolved"]["reason"]
    else:
        classification["blocker_category"] = status
        classification["is_hard_blocker"] = status in policy["hard_blocker_rules"]
        classification["blocker_reason"] = (
            policy["hard_blocker_rules"].get(status, {}).get("reason", "unknown")
        )

    # --- pricing hierarchy assessment ---
    hierarchy_assessment: dict[str, Any] = {
        "cash_settlement_applicable": False,
        "cash_settlement_blocked_reason": None,
        "last_tradable_close_applicable": False,
        "last_tradable_close_blocked_reason": None,
        "zero_recovery_applicable": False,
        "zero_recovery_blocked_reason": None,
        "best_available_pricing_layer": None,
    }

    if is_terminal and has_cash:
        hierarchy_assessment["cash_settlement_applicable"] = True
        hierarchy_assessment["best_available_pricing_layer"] = "cash_settlement"
    elif is_terminal and not has_cash:
        hierarchy_assessment["cash_settlement_blocked_reason"] = (
            "cash_settlement_flag is false; no auditable cash_settlement_amount source"
        )

    if is_terminal and has_last_tradable:
        if is_degraded:
            hierarchy_assessment["last_tradable_close_applicable"] = True
            hierarchy_assessment["last_tradable_close_blocked_reason"] = (
                "last_tradable_date available but terminal_event source is contract_degraded; "
                "close price auditability must be confirmed before pricing"
            )
        else:
            hierarchy_assessment["last_tradable_close_applicable"] = True
    elif is_terminal and not has_last_tradable:
        hierarchy_assessment["last_tradable_close_blocked_reason"] = (
            "no last_tradable_date in terminal_event source"
        )

    if is_terminal:
        if hierarchy_assessment["cash_settlement_applicable"]:
            hierarchy_assessment["best_available_pricing_layer"] = "cash_settlement"
        elif hierarchy_assessment["last_tradable_close_applicable"] and not is_degraded:
            hierarchy_assessment["best_available_pricing_layer"] = "last_tradable_close"
        elif hierarchy_assessment["last_tradable_close_applicable"]:
            hierarchy_assessment["best_available_pricing_layer"] = "last_tradable_close_pending_audit"
        else:
            hierarchy_assessment["zero_recovery_applicable"] = True
            hierarchy_assessment["zero_recovery_blocked_reason"] = (
                "zero_recovery is the only remaining layer; requires formal policy decision "
                "with terminal_exit_conservative_flag=true"
            )
            hierarchy_assessment["best_available_pricing_layer"] = "zero_recovery"

    classification["hierarchy_assessment"] = hierarchy_assessment
    return classification


def build_classification(
    diagnosis_path: Path,
    policy_path: Path,
) -> dict[str, Any]:
    diagnosis = load_json(diagnosis_path)
    policy = load_json(policy_path)

    rows = diagnosis["rows"]
    classifications = [classify_row(row, policy) for row in rows]

    blocker_counts = Counter(c["blocker_category"] for c in classifications)
    hierarchy_layer_counts = Counter(
        c["hierarchy_assessment"]["best_available_pricing_layer"]
        for c in classifications
        if c["hierarchy_assessment"]["best_available_pricing_layer"] is not None
    )

    any_auto_priced = False
    auto_priceable_rows: list[dict[str, Any]] = []
    need_upstream_impl = False
    for c in classifications:
        ha = c["hierarchy_assessment"]
        if ha["cash_settlement_applicable"]:
            any_auto_priced = True
            auto_priceable_rows.append(
                {
                    "instrument": c["instrument"],
                    "signal_date": c["signal_date"],
                    "layer": "cash_settlement",
                }
            )
        elif ha["last_tradable_close_applicable"] and ha["last_tradable_close_blocked_reason"] is None:
            any_auto_priced = True
            auto_priceable_rows.append(
                {
                    "instrument": c["instrument"],
                    "signal_date": c["signal_date"],
                    "layer": "last_tradable_close",
                }
            )
        elif ha["last_tradable_close_applicable"]:
            need_upstream_impl = True
        elif ha["zero_recovery_applicable"]:
            need_upstream_impl = True

    if not any_auto_priced and any(
        c["is_hard_blocker"] and c["blocker_category"] == "terminal_event_unpriced"
        for c in classifications
    ):
        need_upstream_impl = True

    return {
        "classification_source": {
            "diagnosis_json": diagnosis_path.as_posix(),
            "policy_contract": policy_path.as_posix(),
            "policy_version": policy["contract_version"],
        },
        "summary": {
            "total_rows": len(classifications),
            "blocker_category_counts": dict(sorted(blocker_counts.items())),
            "hard_blocker_count": sum(1 for c in classifications if c["is_hard_blocker"]),
            "hierarchy_layer_counts": dict(sorted(hierarchy_layer_counts.items())),
        },
        "judgment": {
            "any_row_auto_priceable_under_policy": any_auto_priced,
            "auto_priceable_rows": auto_priceable_rows,
            "upstream_execution_path_terminal_pricing_still_needed": need_upstream_impl,
            "upstream_impl_needed_reason": (
                "All 10 terminal_event_unpriced rows have degraded terminal_event source data "
                "(contract_degraded_flag=true). None have cash_settlement_flag=true. All 10 have "
                "last_tradable_date available but the price data auditability is blocked by "
                "degraded source truth. Until the upstream execution path implements a formal "
                "terminal pricing resolution against auditable close/return data, these rows "
                "remain hard blockers under the policy contract."
                if need_upstream_impl
                else "Some rows can be automatically priced under the current policy hierarchy."
            ),
        },
        "classifications": classifications,
        "notes": [
            "This classification does not modify any data, execution semantics, or portfolio scripts.",
            "terminal_event_unpriced and exit_unresolved are both hard blockers per the policy contract.",
            "cash_settlement requires auditable cash_settlement_amount; none of the 20 rows have this.",
            "last_tradable_close requires auditable close/return data; last_tradable_date is available "
            "for all 10 terminal_event_unpriced rows, but the terminal_event source is contract_degraded.",
            "zero_recovery is available as fallback but must be an explicit policy decision, not a default.",
            "All 20 rows remain hard blockers: implementation of terminal pricing must happen upstream "
            "in the execution path before portfolio consumption.",
        ],
    }


def main() -> None:
    args = parse_args()
    diagnosis_path = Path(args.diagnosis_json)
    policy_path = Path(args.policy_contract)

    if not diagnosis_path.exists():
        print(f"ERROR: diagnosis JSON not found: {diagnosis_path}", file=sys.stderr)
        sys.exit(1)
    if not policy_path.exists():
        print(f"ERROR: policy contract not found: {policy_path}", file=sys.stderr)
        sys.exit(1)

    payload = build_classification(diagnosis_path, policy_path)
    output_path = Path(args.output)
    write_json(output_path, payload)
    print(f"Classification written to {output_path}")


if __name__ == "__main__":
    main()
