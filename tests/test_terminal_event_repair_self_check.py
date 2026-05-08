from __future__ import annotations

import json
import uuid
from pathlib import Path

from conftest import load_module


def _load_self_check_module():
    module_name = f"run_system_self_check_terminal_repair_{uuid.uuid4().hex}"
    return load_module("scripts/run_system_self_check.py", module_name)


def _write_repair_audit_json(
    path: Path,
    *,
    still_hard_blocker_count: int,
    can_emit_terminal_priced_last_tradable_close_count: int,
    unclassifiable_excluded_count: int,
) -> None:
    payload = {
        "audit_status": "terminal_event_source_repair_audit_only",
        "contract_ref": "contracts/terminal_event_source_repair_plan.v1.json",
        "repair_policy_version": "terminal_event_source_repair_plan_v1",
        "summary": {
            "total_rows": still_hard_blocker_count,
            "degraded_terminal_source_with_auditable_bars_count": 0,
            "declared_last_tradable_date_suspended_count": 0,
            "still_hard_blocker_count": still_hard_blocker_count,
            "can_emit_terminal_priced_last_tradable_close_count": can_emit_terminal_priced_last_tradable_close_count,
            "unclassifiable_excluded_count": unclassifiable_excluded_count,
        },
        "rows": [],
        "notes": [],
    }
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def test_self_check_reports_missing_terminal_event_repair_audit(tmp_path: Path) -> None:
    module = _load_self_check_module()

    result = module.inspect_terminal_event_repair_audit(tmp_path / "terminal_event_repair_audit.json")

    assert result["present"] is False
    assert result["status"] == "missing"
    assert result["pass_flag"] is False
    assert result["portfolio_resolution_allowed"] is False


def test_self_check_reports_terminal_event_repair_blocked(tmp_path: Path) -> None:
    module = _load_self_check_module()
    audit_path = tmp_path / "terminal_event_repair_audit.json"
    _write_repair_audit_json(
        audit_path,
        still_hard_blocker_count=462,
        can_emit_terminal_priced_last_tradable_close_count=0,
        unclassifiable_excluded_count=0,
    )

    result = module.inspect_terminal_event_repair_audit(audit_path)

    assert result["present"] is True
    assert result["status"] == "terminal_event_repair_blocked"
    assert result["still_hard_blocker_count"] == 462
    assert result["pass_flag"] is False
    assert result["hard_blocker_present_flag"] is True


def test_self_check_does_not_report_portfolio_recoverable_when_can_emit_zero(tmp_path: Path) -> None:
    module = _load_self_check_module()
    audit_path = tmp_path / "terminal_event_repair_audit.json"
    _write_repair_audit_json(
        audit_path,
        still_hard_blocker_count=0,
        can_emit_terminal_priced_last_tradable_close_count=0,
        unclassifiable_excluded_count=3,
    )

    result = module.inspect_terminal_event_repair_audit(audit_path)

    assert result["present"] is True
    assert result["can_emit_terminal_priced_last_tradable_close_count"] == 0
    assert result["requires_upstream_execution_path_implementation"] is False
    assert result["portfolio_resolution_allowed"] is False
