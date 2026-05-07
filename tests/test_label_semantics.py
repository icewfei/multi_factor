from __future__ import annotations

import math

from conftest import read_text, schema_properties, schema_required


def compute_label_5d_next_open_close(
    *,
    open_d1: float,
    close_d5: float,
    adj_factor_d1: float,
    adj_factor_d5: float,
) -> float:
    return (close_d5 * adj_factor_d5) / (open_d1 * adj_factor_d1) - 1.0


def test_label_formula_matches_governance_example(label_formula_example: dict[str, float]) -> None:
    label = compute_label_5d_next_open_close(
        open_d1=label_formula_example["open_D1"],
        close_d5=label_formula_example["close_D5"],
        adj_factor_d1=label_formula_example["adj_factor_D1"],
        adj_factor_d5=label_formula_example["adj_factor_D5"],
    )
    expected = (11.0 * 1.3) / (10.0 * 1.2) - 1.0
    assert math.isclose(label, expected, rel_tol=0.0, abs_tol=1e-12)


def test_label_formula_fields_exist_in_project_label_schema() -> None:
    properties = schema_properties("schemas/project_label_panel.schema.json")
    required = schema_required("schemas/project_label_panel.schema.json")

    for field in (
        "open_D1",
        "close_D5",
        "adj_factor_D1",
        "adj_factor_D5",
        "label_5d_next_open_close_raw",
        "label_5d_next_open_close",
    ):
        assert field in properties

    assert "label_5d_next_open_close" in required


def test_label_formula_fields_are_pinned_in_contract_mapping() -> None:
    mapping_text = read_text("contracts/source_field_mapping.yaml")

    for block in (
        "  open_D1:\n    source_field: open_D1\n    local_field: open_D1",
        "  close_D5:\n    source_field: close_D5\n    local_field: close_D5",
        "  adj_factor_D1:\n    source_field: adj_factor_D1\n    local_field: adj_factor_D1",
        "  adj_factor_D5:\n    source_field: adj_factor_D5\n    local_field: adj_factor_D5",
        "  label:\n    source_field: label_5d_next_open_close\n    local_field: label_5d_next_open_close",
        "  label_raw:\n    source_field: label_5d_next_open_close_raw\n    local_field: label_5d_next_open_close_raw",
    ):
        assert block in mapping_text


def test_label_formula_is_frozen_in_governance_docs() -> None:
    spec_text = read_text(
        "项目总纲及计划/multifactor_v1_module_spec_tradability_label_eligibility_realized_return.md"
    )
    framework_text = read_text("项目总纲及计划/项目总纲/new_multifactor_project_framework_v1.md")

    for text in (spec_text, framework_text):
        assert "adj_open_base_D1 = open_D1 * adj_factor_D1" in text
        assert "adj_close_base_D5 = close_D5 * adj_factor_D5" in text
        assert "label_5d_next_open_close_raw = adj_close_base_D5 / adj_open_base_D1 - 1" in text
