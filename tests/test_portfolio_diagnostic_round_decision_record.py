from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/portfolio_diagnostic_round_decision_record.md")


def load_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_decision_record_exists() -> None:
    assert DOC_PATH.exists()


def test_decision_record_contains_three_diagnostic_directions() -> None:
    text = load_doc()

    assert "`TopK head quality gate`" in text
    assert "`turnover-aware admission`" in text
    assert "`baseline overlap / divergence`" in text


def test_decision_record_contains_do_not_enter_challenger_conclusions() -> None:
    text = load_doc()

    assert "不建议进入 challenger" in text
    assert "不建议进入 TopK head quality gate challenger" in text
    assert "不建议进入 turnover-aware admission challenger" in text
    assert "不建议进入 divergence-aware challenger" in text
    assert "不建议开新 challenger / v4" in text


def test_decision_record_contains_divergence_phenomenon_but_not_rule() -> None:
    text = load_doc()

    assert "`baseline-only names` 系统性优于 `nonlinear-only names`" in text
    assert "`divergence spread` 在 `train / validation` 同方向" in text
    assert "`baseline` 赢的日期主要来自 `divergence selection`" in text
    assert "`divergence 有现象`" in text
    assert "`规则证据不足`" in text


def test_decision_record_contains_next_step_recommendation() -> None:
    text = load_doc()

    assert "`baseline divergence exposure decomposition`" in text
    assert "`baseline divergence names` 的 `D0` 暴露来源" in text


def test_decision_record_preserves_frozen_test_and_oos_boundary() -> None:
    text = load_doc()

    assert "不读取 frozen test" in text
    assert "不把 trainval diagnosis 当 OOS" in text
    assert "这是一个 `trainval diagnostic-only decision`" in text
