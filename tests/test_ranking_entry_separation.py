from __future__ import annotations

from conftest import read_text, schema_properties


def test_ranking_and_entry_fields_exist_without_being_collapsed() -> None:
    sample_properties = schema_properties("schemas/project_sample_panel.schema.json")
    execution_properties = schema_properties("schemas/execution_state_daily.schema.json")
    ranking_properties = schema_properties("schemas/ranking_state_daily.schema.json")

    assert "ranking_eligible_D0" in sample_properties
    assert "entry_tradeable" in sample_properties
    assert "entry_filled_D1_shared_proxy" in sample_properties
    assert "entry_filled_D1" in execution_properties
    assert "topk_frozen_D0" in ranking_properties


def test_contracts_keep_ranking_and_execution_fields_separate() -> None:
    mapping_text = read_text("contracts/source_field_mapping.yaml")
    dictionary_text = read_text("contracts/project_field_dictionary.md")

    assert "  ranking_eligible_D0:\n    source_field: ranking_eligible_D0\n    local_field: ranking_eligible_D0" in mapping_text
    assert "  entry_tradeable:\n    source_field: entry_tradeable\n    local_field: entry_tradeable" in mapping_text
    assert "  entry_filled_D1:\n    source_field: entry_filled_D1\n    local_field: entry_filled_D1_shared_proxy" in mapping_text

    assert "| `model_score_D0` | `project_run_state_field` | project-only | 排序模型分数 |" in dictionary_text
    assert "| `topk_frozen_D0` | `project_run_state_field` | project-only | 是否进入冻结 `TopK` |" in dictionary_text
    assert "| `entry_filled_D1` | `project_run_state_field` | project-only | 最终运行态建仓是否成交 |" in dictionary_text


def test_governance_docs_forbid_prefiltering_by_entry_tradeable() -> None:
    framework_text = read_text("项目总纲及计划/项目总纲/new_multifactor_project_framework_v1.md")
    dual_probe_text = read_text("项目总纲及计划/dual_probe_design.md")

    assert "entry_tradeable 只能在 `TopK` 冻结后于执行层生效，不得用于排序前过滤" in framework_text
    assert "明确禁止在排序前用 `entry_tradeable` 过滤宇宙" in framework_text
    assert "entry_filled_D1 = execution_attempt_D1 & entry_tradeable" in framework_text
    assert "D0 仅按 `ranking_eligible_D0 = signal_emittable` 排序" in framework_text
    assert "从 `ranking_eligible_D0` 中冻结 `topk_frozen_D0`" in framework_text
    assert "D1 开盘执行时才应用 `entry_tradeable`" in framework_text
    assert "execution: override — force entry_filled_D1 = true" in dual_probe_text
