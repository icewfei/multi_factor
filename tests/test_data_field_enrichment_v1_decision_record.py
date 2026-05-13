from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/data_field_enrichment_v1_decision_record.md")


def load_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_decision_record_exists() -> None:
    assert DOC_PATH.exists()


def test_decision_record_contains_required_boundary_statements() -> None:
    text = load_doc()

    assert "当前状态为 `conditional_pass`" in text
    assert "这不是 alpha。" in text
    assert "这不是 strategy approval。" in text
    assert "本流程不读取 frozen test。" in text
    assert "本流程不训练，不回测，不跑 portfolio。" in text


def test_decision_record_contains_usable_and_unavailable_field_sections() -> None:
    text = load_doc()

    assert "以下字段当前可用于后续 `clean baseline / challenger`" in text
    assert "`entry_buyable`" in text
    assert "`listing_age_days`" in text
    assert "以下字段当前不可用" in text
    assert "`listing_age_trading_days`" in text
    assert "`newly_listed_flag`" in text


def test_decision_record_contains_missing_source_and_next_step_language() -> None:
    text = load_doc()

    assert "`missing_source`: `none`" in text
    assert "`blocked`: `listing_age_trading_days`, `newly_listed_flag`" in text
    assert "不下载新数据" in text
    assert "仅重跑 builder + audit" in text
