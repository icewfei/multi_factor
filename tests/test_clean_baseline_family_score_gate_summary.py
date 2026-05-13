from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/clean_baseline_family_score_gate_summary.md")


def load_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_summary_doc_exists() -> None:
    assert DOC_PATH.exists()


def test_summary_doc_contains_all_baseline_ids() -> None:
    text = load_doc()

    for baseline_id in (
        "no_p98_reversal_baseline_v1",
        "clean_momentum_20d_baseline_v1",
        "clean_liquidity_adjusted_reversal_baseline_v1",
        "clean_equal_weight_random_eligible_baseline_v1",
    ):
        assert baseline_id in text


def test_summary_doc_contains_required_governance_terms() -> None:
    text = load_doc()

    assert "p98_used=false" in text
    assert "label_diagnostics_used=false" in text
    assert "frozen_test_accessed=false" in text
    assert "not portfolio approval" in text
    assert "not strategy approval" in text


def test_summary_doc_contains_gate_result_and_next_step() -> None:
    text = load_doc()

    assert "4/4 clean baseline score-layer gate 通过" in text
    assert "下一步才是 clean baseline family model-layer diagnosis" in text
