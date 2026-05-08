from __future__ import annotations

from conftest import load_json


SCHEMA_PATH = "schemas/post_delist_terminal_event_bridge.schema.json"


def test_schema_json_loads() -> None:
    schema = load_json(SCHEMA_PATH)
    assert schema["$id"] == "multifactor/post_delist_terminal_event_bridge.schema.json"
    assert schema["title"] == "Post Delist Terminal Event Bridge Audit"


def test_schema_top_level_required_fields() -> None:
    schema = load_json(SCHEMA_PATH)
    required = schema["required"]
    assert required == ["audit_status", "contract_ref", "summary", "rows", "notes"]


def test_schema_summary_fields() -> None:
    schema = load_json(SCHEMA_PATH)
    summary_required = schema["properties"]["summary"]["required"]
    assert summary_required == [
        "total_candidate_rows",
        "bridge_identified_rows",
        "residual_exit_unresolved_rows",
    ]


def test_schema_row_fields_capture_bridge_evidence_without_exit_pricing() -> None:
    schema = load_json(SCHEMA_PATH)
    row_required = schema["properties"]["rows"]["items"]["required"]
    assert "bridge_marker" in row_required
    assert "post_planned_exit_tradability_rows" in row_required
    assert "post_planned_exit_bars_rows" in row_required
    row_props = schema["properties"]["rows"]["items"]["properties"]
    assert "actual_exit_date" not in row_props
    assert "actual_sell_price" not in row_props


def test_schema_row_status_enum_is_only_unpriced_or_still_unresolved() -> None:
    schema = load_json(SCHEMA_PATH)
    status_enum = schema["properties"]["rows"]["items"]["properties"]["bridged_execution_path_status"]["enum"]
    assert status_enum == ["terminal_event_unpriced", "exit_unresolved"]
