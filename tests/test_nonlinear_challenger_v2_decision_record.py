from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/nonlinear_challenger_v2_decision_record.md")


def load_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_decision_record_exists() -> None:
    assert DOC_PATH.exists()


def test_decision_record_contains_required_conclusions() -> None:
    text = load_doc()

    assert "portfolio_aware_cross_sectional_score_transformation" in text
    assert "v2 model-layer 结果为正" in text
    assert "v2 portfolio-layer 未超过 baseline" in text
    assert "v2 不晋级" in text
    assert "v2 不建议进入 confirmatory / shadow" in text
    assert "不允许继续围绕 validation 调 v2 formula" in text


def test_decision_record_contains_required_prohibited_phrases() -> None:
    text = load_doc()

    assert "不能把 `trainval dry-run` 当 `OOS`" in text
    assert "不能把 `trainval dry-run` 当 `fixed/frozen test`" in text
    assert "不允许读取 frozen test" in text
    assert "不能说 `策略有效`" in text


def test_decision_record_contains_next_step_boundaries() -> None:
    text = load_doc()

    assert "必须新建 challenger" in text
    assert "必须新建 research round" in text
    assert "必须新建 manifest" in text
    assert "结果必须优于 baseline" in text
