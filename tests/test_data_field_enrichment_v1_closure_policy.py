from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/data_field_enrichment_v1_closure_policy.md")


def load_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_closure_policy_exists() -> None:
    assert DOC_PATH.exists()


def test_closure_policy_contains_required_status_and_next_use_terms() -> None:
    text = load_doc()

    assert "final_status = conditional_pass" in text
    assert "conditional enrichment layer" in text
    assert "diagnostic / clean baseline / challenger" in text
    assert "D0" in text
    assert "listing_age_trading_days" in text
    assert "newly_listed_flag" in text


def test_closure_policy_locks_required_boundaries() -> None:
    text = load_doc()

    assert "no silent fallback" in text
    assert "no frozen test access" in text
    assert "not alpha / not strategy approval / not OOS" in text
    assert "不能把 `conditional_pass` 包装成 `full pass`" in text
    assert "blocked 字段不得进入模型" in text
    assert "blocked 字段不得进入 `baseline`" in text
    assert "blocked 字段不得进入 `challenger`" in text
    assert "blocked 字段不得进入 `portfolio`" in text
