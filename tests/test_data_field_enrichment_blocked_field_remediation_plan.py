from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/data_field_enrichment_blocked_field_remediation_plan.md")


def load_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_remediation_plan_exists() -> None:
    assert DOC_PATH.exists()


def test_remediation_plan_contains_root_cause_and_dependency() -> None:
    text = load_doc()

    assert "本地交易日历起点不足" in text
    assert "2000-01-04" in text
    assert "listing_age_trading_days" in text
    assert "newly_listed_flag" in text
    assert "newly_listed_flag 依赖 `listing_age_trading_days`" in text


def test_remediation_plan_contains_all_required_options_and_boundaries() -> None:
    text = load_doc()

    assert "Option 1: 补足更早历史交易日历" in text
    assert "Option 2: 新建 conservative calendar-day listing age proxy contract" in text
    assert "Option 3: 继续禁用 blocked 字段" in text
    assert "Pros" in text
    assert "Cons" in text
    assert "Leakage Risk" in text
    assert "Fail-Fast" in text
    assert "New Contract Requirement" in text
    assert "在未完成修复前，blocked 字段不得进入研究链路" in text
    assert "不允许 silent fallback" in text
