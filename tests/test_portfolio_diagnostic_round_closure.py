from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/portfolio_diagnostic_round_closure.md")


def load_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_closure_doc_exists() -> None:
    assert DOC_PATH.exists()


def test_closure_doc_contains_four_negative_conclusions() -> None:
    text = load_doc()

    assert "不建议进入 TopK head quality gate challenger" in text
    assert "不建议进入 turnover-aware admission challenger" in text
    assert "不建议进入 divergence-aware challenger" in text
    assert "不建议进入 exposure rule challenger" in text


def test_closure_doc_contains_divergence_phenomenon_but_insufficient_rule_evidence() -> None:
    text = load_doc()

    assert "`baseline` 确实赢在 `divergence selection`" in text
    assert "`baseline divergence 有现象`" in text
    assert "`规则证据不足`" in text


def test_closure_doc_contains_no_new_challenger_recommendation() -> None:
    text = load_doc()

    assert "不建议开新 challenger / v4" in text


def test_closure_doc_contains_next_stage_recommendation() -> None:
    text = load_doc()

    assert "`数据字段补全`" in text
    assert "`baseline 机制复核`" in text


def test_closure_doc_preserves_frozen_test_and_oos_boundary() -> None:
    text = load_doc()

    assert "不读取 frozen test" in text
    assert "不把 trainval diagnosis 当 OOS" in text
