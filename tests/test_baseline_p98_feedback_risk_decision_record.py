from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/baseline_p98_feedback_risk_decision_record.md")


def load_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_decision_record_exists() -> None:
    assert DOC_PATH.exists()


def test_decision_record_contains_required_feedback_risk_terms() -> None:
    text = load_doc()

    assert "p98 source-selection feedback risk" in text
    assert "not clean baseline component" in text
    assert "conditional baseline" in text
    assert "no-p98 clean baseline rebuild" in text
    assert "no frozen test access" in text


def test_decision_record_contains_required_governance_conclusions() -> None:
    text = load_doc()

    assert "trainval label-based diagnostics" in text
    assert "不能作为 clean baseline source selection 的无条件依据" in text
    assert "后续报告必须披露 `p98 feedback risk`" in text
    assert "did not beat conditional baseline" in text
