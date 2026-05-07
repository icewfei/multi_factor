from __future__ import annotations

import pytest

from conftest import read_text, schema_properties, schema_required


def test_core_no_future_leakage_fields_exist_in_schemas() -> None:
    sample_properties = schema_properties("schemas/project_sample_panel.schema.json")
    ranking_properties = schema_properties("schemas/ranking_state_daily.schema.json")
    score_properties = schema_properties("schemas/model_scores_D0.schema.json")
    ranking_required = schema_required("schemas/ranking_state_daily.schema.json")

    assert "feature_ready_D0" in sample_properties
    assert "pit_state_complete_D0" in sample_properties
    assert "ranking_eligible_D0" in sample_properties
    assert "model_score_D0" in ranking_properties
    assert "topk_frozen_D0" in ranking_properties
    assert "model_score_D0" in score_properties
    assert "ranking_eligible_D0" in ranking_required


def test_core_no_future_leakage_fields_exist_in_contracts() -> None:
    mapping_text = read_text("contracts/source_field_mapping.yaml")
    current_contract_text = read_text("contracts/run_input_contract.current.json")

    for block in (
        "  feature_ready_D0:\n    source_field: feature_ready_D0\n    local_field: feature_ready_D0",
        "  pit_state_complete_D0:\n    source_field: pit_state_complete_D0\n    local_field: pit_state_complete_D0",
        "  ranking_eligible_D0:\n    source_field: ranking_eligible_D0\n    local_field: ranking_eligible_D0",
    ):
        assert block in mapping_text

    assert '"model_score_D0"' in current_contract_text
    assert '"topk_frozen_D0"' in current_contract_text


def test_governance_docs_pin_d0_only_audit_subfields() -> None:
    framework_text = read_text("项目总纲及计划/项目总纲/new_multifactor_project_framework_v1.md")

    assert "feature_ready_D0 = price_window_ready_D0 & core_features_complete_D0 & pit_state_complete_D0" in framework_text
    assert "ranking_eligible_D0 = signal_emittable" in framework_text
    assert "price_window_ready_D0" in framework_text
    assert "core_features_complete_D0" in framework_text
    assert "pit_state_complete_D0" in framework_text


@pytest.mark.xfail(
    reason="Feature timestamp / PIT freshness audit is not yet materialized as a machine-readable testable contract.",
    strict=False,
)
def test_future_timestamp_audit_placeholder() -> None:
    assert "feature_timestamp_D0" in read_text("contracts/project_field_dictionary.md")
