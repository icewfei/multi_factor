from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/no_p98_clean_baseline_score_layer_decision_record.md")


def load_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_decision_record_exists() -> None:
    assert DOC_PATH.exists()


def test_decision_record_contains_required_score_layer_terms() -> None:
    text = load_doc()

    assert "no p98" in text
    assert "no label diagnostics" in text
    assert "frozen_test_accessed=false" in text
    assert "D0 visibility audit pass" in text
    assert "leakage audit pass" in text
    assert "portfolio_ran=false" in text
    assert "not strategy approval" in text


def test_decision_record_contains_required_counts_and_projection_conclusion() -> None:
    text = load_doc()

    assert "clean projection 通过" in text
    assert "label_defined" in text
    assert "backtest_executable_shared_proxy" in text
    assert "row_count = 11,198,074" in text
    assert "null_score_count = 421,656" in text
    assert "nonfinite_score_count = 0" in text
    assert "score_direction = ASC / reversal_rank" in text
