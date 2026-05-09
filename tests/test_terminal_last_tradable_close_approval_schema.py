from __future__ import annotations

from conftest import load_json


SCHEMA_PATH = "schemas/terminal_last_tradable_close_approval.schema.json"


def test_schema_json_loads() -> None:
    schema = load_json(SCHEMA_PATH)
    assert schema["$id"] == "multifactor/terminal_last_tradable_close_approval.schema.json"
    assert schema["title"] == "Terminal Last Tradable Close Approval Audit"


def test_schema_top_level_required_fields() -> None:
    schema = load_json(SCHEMA_PATH)
    required = schema["required"]
    assert required == [
        "audit_status",
        "contract_ref",
        "approval_policy_version",
        "summary",
        "rows",
        "notes",
    ]


def test_summary_required_fields_cover_candidate_and_blocker_counts() -> None:
    schema = load_json(SCHEMA_PATH)
    required = schema["properties"]["summary"]["required"]
    assert "candidate_rows_count" in required
    assert "approval_gate_passed_count" in required
    assert "approval_gate_failed_count" in required
    assert "still_hard_blocker_count" in required
    assert "terminal_event_bridge_required_count" in required


def test_row_required_fields_cover_origin_evidence_and_candidate_flags() -> None:
    schema = load_json(SCHEMA_PATH)
    row_required = schema["properties"]["rows"]["items"]["required"]
    assert "approval_origin_case" in row_required
    assert "approval_evidence_case" in row_required
    assert "approved_for_repaired_terminal_event_candidate" in row_required
    assert "terminal_event_bridge_required_flag" in row_required
    assert "required_candidate_flags" in row_required


def test_row_enums_distinguish_bridge_and_evidence_cases() -> None:
    schema = load_json(SCHEMA_PATH)
    row_props = schema["properties"]["rows"]["items"]["properties"]
    assert row_props["approval_origin_case"]["enum"] == [
        "no_terminal_pricing_source",
        "terminal_event_bridge_required",
    ]
    evidence_enum = row_props["approval_evidence_case"]["enum"]
    assert "degraded_terminal_source_with_auditable_bars" in evidence_enum
    assert "declared_last_tradable_date_suspended" in evidence_enum


def test_zero_recovery_and_hard_blocker_consts_are_fixed() -> None:
    schema = load_json(SCHEMA_PATH)
    row_props = schema["properties"]["rows"]["items"]["properties"]
    assert row_props["zero_recovery_approved"]["const"] is False
    assert row_props["still_hard_blocker"]["const"] is True
