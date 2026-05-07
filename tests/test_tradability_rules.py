from __future__ import annotations

from conftest import read_text, schema_properties


def test_tradability_contract_fields_exist() -> None:
    mapping_text = read_text("contracts/source_field_mapping.yaml")

    for block in (
        "  entry_tradeable:\n    source_field: entry_buyable_D1_open\n    local_field: entry_tradeable",
        "  planned_exit_tradeable:\n    source_field: exit_sellable_D5_close\n    local_field: planned_exit_tradeable",
        "  sellable_retry_next_open:\n    source_field: sellable_retry_next_open\n    local_field: sellable_retry_next_open",
    ):
        assert block in mapping_text


def test_tradability_flags_exist_in_sample_schema() -> None:
    properties = schema_properties("schemas/project_sample_panel.schema.json")

    for field in ("entry_tradeable", "planned_exit_tradeable"):
        assert field in properties


def test_tradability_docs_require_decimal_round_half_up() -> None:
    framework_text = read_text("项目总纲及计划/项目总纲/new_multifactor_project_framework_v1.md")

    assert "Decimal" in framework_text
    assert "ROUND_HALF_UP" in framework_text
    assert "entry_buyable_D1_open" in framework_text
    assert "exit_sellable_D5_close" in framework_text
    assert "sellable_retry_next_open" in framework_text


def test_tradability_module_spec_keeps_daily_field_aliases() -> None:
    spec_text = read_text(
        "项目总纲及计划/multifactor_v1_module_spec_tradability_label_eligibility_realized_return.md"
    )

    assert "对应总纲 `entry_buyable_D1_open` 的日频版" in spec_text
    assert "对应总纲 `exit_sellable_D5_close` 的日频版" in spec_text
    assert "对应总纲 `sellable_retry_next_open` 的日频版" in spec_text
