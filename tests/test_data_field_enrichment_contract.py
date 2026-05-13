from __future__ import annotations

import jsonschema

from conftest import load_json, read_text


DOC_PATH = "docs/data_field_enrichment_contract.md"
SCHEMA_PATH = "schemas/data_field_enrichment_contract.schema.json"
CONFIG_PATH = "configs/data_field_enrichment/field_contract_v1.json"


def load_fields_by_name() -> dict[str, dict]:
    config = load_json(CONFIG_PATH)
    fields: dict[str, dict] = {}
    for category in config["categories"]:
        for field in category["fields"]:
            fields[field["field_name"]] = field
    return fields


def test_schema_json_loads() -> None:
    schema = load_json(SCHEMA_PATH)
    assert schema["$id"] == "multifactor/data_field_enrichment_contract.schema.json"
    assert schema["title"] == "Data Field Enrichment Contract"


def test_config_json_loads_and_matches_contract_version() -> None:
    config = load_json(CONFIG_PATH)
    assert config["contract_version"] == "data_field_enrichment_contract_v1"
    assert config["entity_name"] == "enriched_security_state_daily_v1"


def test_config_validates_against_schema() -> None:
    schema = load_json(SCHEMA_PATH)
    config = load_json(CONFIG_PATH)
    jsonschema.validate(config, schema)


def test_all_high_priority_fields_exist() -> None:
    fields = load_fields_by_name()
    expected = {
        "is_st",
        "st_source",
        "st_effective_start",
        "st_effective_end",
        "is_suspended",
        "no_trade_flag",
        "volume_zero_flag",
        "amount_zero_flag",
        "is_limit_up",
        "is_limit_down",
        "open_at_up_limit",
        "close_at_down_limit",
        "limit_rule_version",
        "entry_buyable",
        "exit_sellable",
        "sellable_retry_next_open",
        "list_date",
        "listing_age_days",
        "listing_age_trading_days",
        "newly_listed_flag",
    }
    assert expected <= set(fields.keys())


def test_contract_covers_all_required_categories() -> None:
    config = load_json(CONFIG_PATH)
    category_names = {category["category_name"] for category in config["categories"]}
    assert category_names == {
        "identity fields",
        "ST fields",
        "suspension / no trade fields",
        "limit status fields",
        "tradability state fields",
        "listing age fields",
        "board / segment fields",
        "audit/provenance fields",
    }


def test_every_field_has_d0_visibility_and_fail_fast_condition() -> None:
    fields = load_fields_by_name()
    assert fields
    for field_name, field in fields.items():
        assert field["d0_visibility"], f"{field_name} missing d0_visibility"
        assert field["fail_fast_condition"], f"{field_name} missing fail_fast_condition"


def test_audit_provenance_fields_exist() -> None:
    fields = load_fields_by_name()
    assert "source_snapshot_id" in fields
    assert "build_time" in fields
    assert "builder_version" in fields
    assert "d0_visible" in fields
    assert "no_frozen_test_access" in fields


def test_document_contains_required_boundary_terms() -> None:
    text = read_text(DOC_PATH)
    assert "no frozen test access" in text
    assert "not alpha / not strategy approval" in text
    assert "D0 visible only" in text
    assert "fail-fast" in text


def test_document_contains_explicit_prohibitions() -> None:
    text = read_text(DOC_PATH)
    assert "不下载新数据" in text
    assert "不训练" in text
    assert "不回测" in text
    assert "不读取 frozen test" in text
    assert "不生成 metrics/readout" in text
    assert "不把字段设计包装成 alpha" in text
