from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/no_p98_clean_baseline_decision_record.md")


def load_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_decision_record_exists() -> None:
    assert DOC_PATH.exists()


def test_decision_record_contains_required_clean_boundary_terms() -> None:
    text = load_doc()

    assert "no p98" in text
    assert "no label diagnostics" in text
    assert "no frozen test access" in text
    assert "D0 visibility audit passed" in text
    assert "leakage audit passed" in text


def test_decision_record_contains_required_model_layer_conclusion_terms() -> None:
    text = load_doc()

    assert "clean but weak" in text
    assert "validation `RankIC=0.0287`" in text
    assert "validation `ICIR=0.2350`" in text
    assert "validation `top-bottom spread=0.00246`" in text
    assert "validation `TopK head realized return proxy=-0.00543`" in text
    assert "validation `TopK minus nextK=-0.00844`" in text


def test_decision_record_contains_required_governance_verdict_terms() -> None:
    text = load_doc()

    assert "no portfolio dry-run" in text
    assert "not strategy approval" in text
    assert "p98 conditional baseline stronger but not clean" in text
    assert "rebuild clean baseline family" in text
