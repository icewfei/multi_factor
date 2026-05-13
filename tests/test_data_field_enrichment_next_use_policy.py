from __future__ import annotations

import jsonschema

from conftest import load_json


CONTRACT_PATH = "configs/data_field_enrichment/field_contract_v1.json"
CONFIG_PATH = "configs/data_field_enrichment/enrichment_next_use_policy_v1.json"
SCHEMA_PATH = "schemas/data_field_enrichment_next_use_policy.schema.json"


def load_contract_fields() -> set[str]:
    contract = load_json(CONTRACT_PATH)
    fields: set[str] = set()
    for category in contract["categories"]:
        for field in category["fields"]:
            fields.add(field["field_name"])
    return fields


def test_next_use_policy_schema_loads() -> None:
    schema = load_json(SCHEMA_PATH)
    assert schema["$id"] == "multifactor/data_field_enrichment_next_use_policy.schema.json"
    assert schema["title"] == "Data Field Enrichment Next Use Policy"


def test_next_use_policy_config_loads_and_validates() -> None:
    schema = load_json(SCHEMA_PATH)
    config = load_json(CONFIG_PATH)
    assert config["policy_version"] == "data_field_enrichment_v1_next_use_policy"
    assert config["conditional_pass"] is True
    assert config["no_frozen_test_access"] is True
    jsonschema.validate(config, schema)


def test_next_use_policy_fields_cover_contract_without_leakage() -> None:
    contract_fields = load_contract_fields()
    config = load_json(CONFIG_PATH)

    allowed_fields = set(config["allowed_fields"])
    blocked_fields = set(config["blocked_fields"])
    conditional_fields = set(config["conditional_fields"])

    assert blocked_fields == {"listing_age_trading_days", "newly_listed_flag"}
    assert not (allowed_fields & blocked_fields)
    assert not (conditional_fields & blocked_fields)
    assert allowed_fields == contract_fields - blocked_fields
    assert allowed_fields | blocked_fields | conditional_fields == contract_fields


def test_next_use_policy_locks_fail_fast_and_disclosure_boundaries() -> None:
    config = load_json(CONFIG_PATH)
    disclosure_text = " | ".join(config["required_disclosure"])
    forbidden_text = " | ".join(config["forbidden_downstream_usage"])
    fail_fast_text = " | ".join(config["fail_fast_conditions"])

    assert "no silent fallback" in disclosure_text
    assert "no frozen test access" in disclosure_text
    assert "not alpha" in disclosure_text
    assert "not strategy approval" in disclosure_text
    assert "not OOS" in disclosure_text
    assert "model inputs" in forbidden_text
    assert "clean baseline inputs" in forbidden_text
    assert "challenger inputs" in forbidden_text
    assert "portfolio construction" in forbidden_text
    assert "screening rules" in forbidden_text
    assert "full pass" in forbidden_text
    assert "listing_age_trading_days" in fail_fast_text
    assert "newly_listed_flag" in fail_fast_text
    assert "silent fallback" in fail_fast_text
    assert "frozen test access" in fail_fast_text
