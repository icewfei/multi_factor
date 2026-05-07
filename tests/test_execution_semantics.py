from __future__ import annotations

from conftest import normalize_markdown_text, read_text, schema_properties


def test_execution_fields_exist_in_project_execution_outputs() -> None:
    execution_properties = schema_properties("schemas/project_execution_panel.schema.json")
    holdings_properties = schema_properties("schemas/holdings_csv.schema.json")

    for field in (
        "actual_exit_date",
        "actual_sell_price",
        "exit_delay_days",
        "execution_delayed_realized_return",
    ):
        assert field in execution_properties
        assert field in holdings_properties


def test_execution_fields_are_mapped_in_contracts() -> None:
    mapping_text = read_text("contracts/source_field_mapping.yaml")

    for block in (
        "  actual_exit_date:\n    source_field: actual_exit_date\n    local_field: actual_exit_date",
        "  actual_sell_price:\n    source_field: actual_sell_price\n    local_field: actual_sell_price",
        "  exit_delay_days:\n    source_field: exit_delay_days\n    local_field: exit_delay_days",
        "  execution_delayed_realized_return:\n    source_field: execution_delayed_realized_return\n    local_field: execution_delayed_realized_return",
    ):
        assert block in mapping_text


def test_execution_semantics_are_frozen_in_governance_docs() -> None:
    framework_text = normalize_markdown_text(
        read_text("项目总纲及计划/项目总纲/new_multifactor_project_framework_v1.md")
    )
    spec_text = normalize_markdown_text(
        read_text("项目总纲及计划/multifactor_v1_module_spec_tradability_label_eligibility_realized_return.md")
    )

    for text in (framework_text, spec_text):
        assert "D0" in text
        assert "D1" in text
        assert "D5" in text

    assert "D0 收盘后出信号" in framework_text or "D0 收盘出信号" in framework_text
    assert "D1 开盘买入" in framework_text
    assert "持有到 D5 收盘" in framework_text
    assert "从后续每个开盘继续卖，直到卖出" in framework_text

    assert "actual_exit_date = planned_exit_date" in spec_text
    assert "actual_exit_event_type = D5_CLOSE" in spec_text
    assert "actual_sell_price = close_D5" in spec_text
    assert "只检查该日开盘 sellable_retry_next_open" in spec_text
    assert "actual_exit_event_type = RETRY_OPEN" in spec_text
