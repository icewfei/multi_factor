from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/data_field_enrichment_roadmap.md")


def load_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_data_field_enrichment_roadmap_exists() -> None:
    assert DOC_PATH.exists()


def test_data_field_enrichment_roadmap_contains_required_scope_terms() -> None:
    text = load_doc()

    assert "industry / sector classification" in text
    assert "ST historical status" in text
    assert "listing age / IPO age" in text
    assert "limit up / limit down status" in text
    assert "suspension / no trade status" in text
    assert "D0 visible only" in text
    assert "no frozen test access" in text
    assert "fail-fast" in text
    assert "not alpha / not strategy approval" in text


def test_data_field_enrichment_roadmap_contains_all_required_categories() -> None:
    text = load_doc()

    assert "### 1. industry / sector classification" in text
    assert "### 2. ST historical status" in text
    assert "### 3. listing age / IPO age" in text
    assert "### 4. board type / exchange segment" in text
    assert "### 5. limit up / limit down status" in text
    assert "### 6. suspension / no trade status" in text
    assert "### 7. liquidity quality fields" in text
    assert "### 8. tradability state fields" in text
    assert "### 9. market cap / float cap fields" in text
    assert "### 10. optional risk exposure fields" in text


def test_data_field_enrichment_roadmap_contains_required_field_template() -> None:
    text = load_doc()

    assert "用途" in text
    assert "是否 D0 可见" in text
    assert "潜在数据源" in text
    assert "对 baseline / challenger 的价值" in text
    assert "泄漏风险" in text
    assert "fail-fast 要求" in text
    assert "是否优先级高" in text


def test_data_field_enrichment_roadmap_contains_explicit_prohibitions() -> None:
    text = load_doc()

    assert "不训练，不回测，不读取 frozen test，不生成 metrics/readout，不设计新策略" in text
    assert "下载新数据" in text
    assert "训练模型" in text
    assert "回测" in text
    assert "读取 `frozen test`" in text
    assert "生成任何新的 `metrics/readout`" in text
    assert "把字段补全包装成 `alpha`" in text
