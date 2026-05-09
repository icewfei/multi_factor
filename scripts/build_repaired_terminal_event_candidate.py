#!/opt/anaconda3/envs/quant_trade/bin/python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build repaired_terminal_event_candidate from terminal last tradable close approval audit."
        )
    )
    parser.add_argument(
        "--approval-audit",
        required=True,
        help="Path to terminal_last_tradable_close approval audit JSON.",
    )
    parser.add_argument("--output", required=True, help="Output candidate JSON path.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def transform_row(row: dict[str, Any], pricing_policy_version: str) -> dict[str, Any]:
    return {
        "snapshot_id": row.get("snapshot_id"),
        "instrument": row["instrument"],
        "signal_date": row["signal_date"],
        "entry_date": row.get("entry_date"),
        "planned_exit_date": row.get("planned_exit_date"),
        "terminal_event_date": row.get("terminal_event_date"),
        "terminal_event_type": row.get("terminal_event_type"),
        "approval_origin_case": row["approval_origin_case"],
        "approval_evidence_case": row["approval_evidence_case"],
        "candidate_target_state": "repaired_terminal_event_candidate",
        "approved_terminal_pricing_path": row["approved_terminal_pricing_path"],
        "candidate_pricing_date": row["candidate_pricing_date"],
        "candidate_last_tradable_close": row["candidate_last_tradable_close"],
        "candidate_adj_factor": row["candidate_adj_factor"],
        "candidate_volume": row["candidate_volume"],
        "pricing_policy_version": pricing_policy_version,
        "terminal_event_source_degraded_flag": row["terminal_event_source_degraded_flag"],
        "terminal_exit_approximation_flag": row["terminal_exit_approximation_flag"],
        "source_repair_flag": row["source_repair_flag"],
        "terminal_event_bridge_required_flag": row["terminal_event_bridge_required_flag"],
        "required_candidate_flags": row["required_candidate_flags"],
        "still_hard_blocker": True,
        "candidate_notes": [
            "Candidate artifact only. This row is not yet a priced exit.",
            "Execution path must still emit formal actual_exit_date, actual_sell_price, and execution_delayed_realized_return.",
        ],
    }


def build_candidate(approval_audit_path: Path) -> dict[str, Any]:
    approval = load_json(approval_audit_path)
    pricing_policy_version = str(approval["approval_policy_version"])
    approved_rows = [
        row for row in approval["rows"] if row.get("approved_for_repaired_terminal_event_candidate") is True
    ]
    candidates = [transform_row(row, pricing_policy_version) for row in approved_rows]
    return {
        "artifact_status": "repaired_terminal_event_candidate_only",
        "source_approval_audit": approval_audit_path.as_posix(),
        "pricing_policy_version": pricing_policy_version,
        "summary": {
            "total_rows_in_source_audit": len(approval["rows"]),
            "candidate_rows_count": len(candidates),
            "still_hard_blocker_count": len(candidates),
            "priced_rows_count": 0,
        },
        "rows": candidates,
        "notes": [
            "This artifact contains only approval-passed candidate rows.",
            "Rows remain hard blockers until upstream execution path emits complete actual exit fields.",
            "No pricing, no actual_exit_date, and no actual_sell_price are backfilled by this builder.",
        ],
    }


def main() -> None:
    args = parse_args()
    approval_audit_path = Path(args.approval_audit)
    if not approval_audit_path.exists():
        print(f"ERROR: approval audit not found: {approval_audit_path}", file=sys.stderr)
        sys.exit(1)
    payload = build_candidate(approval_audit_path)
    write_json(Path(args.output), payload)


if __name__ == "__main__":
    main()
