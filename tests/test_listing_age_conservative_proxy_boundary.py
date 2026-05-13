from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/listing_age_conservative_proxy_boundary.md")


def load_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_proxy_boundary_doc_exists() -> None:
    assert DOC_PATH.exists()


def test_proxy_boundary_doc_contains_required_independent_field_rules() -> None:
    text = load_doc()

    assert "listing_age_calendar_days" in text
    assert "newly_listed_calendar_proxy" in text
    assert "不得冒充 `listing_age_trading_days`" in text
    assert "必须单独 contract" in text
    assert "必须单独 audit" in text
    assert "必须单独 disclosure" in text


def test_proxy_boundary_doc_locks_no_fallback_and_no_substitution() -> None:
    text = load_doc()

    assert "不能 silent fallback 到 `listing_age_trading_days`" in text
    assert "不能用于替代 blocked 字段，除非通过独立决策记录批准" in text
    assert "不能直接替代 `newly_listed_flag`" in text
