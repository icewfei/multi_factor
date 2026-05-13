from __future__ import annotations

from pathlib import Path

from conftest import load_json


DOC_PATH = Path("docs/no_p98_clean_baseline_rebuild_design.md")
CONFIG_PATH = "configs/clean_baselines/no_p98_reversal_baseline_v1.json"
EXPECTED_BASELINE_ID = "no_p98_reversal_baseline_v1"


def load_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_design_doc_exists() -> None:
    assert DOC_PATH.exists()


def test_design_doc_contains_required_boundary_terms() -> None:
    text = load_doc()

    assert "no p98" in text
    assert "no label-based source selection" in text
    assert "D0 visible only" in text
    assert "no frozen test access" in text


def test_config_json_loads_and_has_expected_baseline_id() -> None:
    payload = load_json(CONFIG_PATH)

    assert payload["baseline_id"] == EXPECTED_BASELINE_ID
    assert payload["score_source"]["source_score_definition"] == "c1 ASC / reversal_rank"
    assert payload["score_source"]["p98_used"] is False
    assert payload["score_source"]["label_based_source_selection_used"] is False
    assert payload["input_visibility_policy"] == "D0 visible only"
    assert payload["hard_boundaries"]["frozen_test_access_allowed"] is False
