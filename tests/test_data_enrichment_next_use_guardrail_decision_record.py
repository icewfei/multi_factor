from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/data_enrichment_next_use_guardrail_decision_record.md")


def load_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_guardrail_decision_record_exists() -> None:
    assert DOC_PATH.exists()


def test_guardrail_decision_record_contains_required_guardrail_terms() -> None:
    text = load_doc()

    assert "guardrail 已实现" in text
    assert "blocked fields 会 `fail-fast`" in text
    assert "`conditional_pass` 必须披露" in text
    assert "`portfolio / screening` 使用当前不允许" in text
    assert "`no frozen test access` 必须为 true" in text
    assert "`no silent fallback` 是硬边界" in text


def test_guardrail_decision_record_contains_required_governance_boundary_terms() -> None:
    text = load_doc()

    assert "这不是 alpha。" in text
    assert "这不是 strategy approval。" in text
    assert "这不是 OOS。" in text
    assert "必须先通过该 guardrail" in text
