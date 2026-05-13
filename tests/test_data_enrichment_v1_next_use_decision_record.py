from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/data_enrichment_v1_next_use_decision_record.md")


def load_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_decision_record_exists() -> None:
    assert DOC_PATH.exists()


def test_decision_record_contains_required_verdict_terms() -> None:
    text = load_doc()

    assert "conditional enrichment layer" in text
    assert "diagnostic / clean baseline / challenger" in text
    assert "listing_age_trading_days" in text
    assert "newly_listed_flag" in text
    assert "blocked 字段修复前不得使用" in text
    assert "downstream 必须遵守 next-use policy" in text


def test_decision_record_contains_required_boundary_and_next_step_terms() -> None:
    text = load_doc()

    assert "不是 alpha" in text
    assert "不是策略批准" in text
    assert "不是 `OOS`" in text
    assert "不训练，不回测，不跑 portfolio，不读取 frozen test" in text
    assert "先实现 `next-use guardrail`" in text
    assert "或先补交易日历" in text
