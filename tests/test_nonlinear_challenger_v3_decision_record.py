from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/nonlinear_challenger_v3_decision_record.md")


def load_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_decision_record_exists() -> None:
    assert DOC_PATH.exists()


def test_decision_record_contains_v3_negative_decision() -> None:
    text = load_doc()

    assert "v3 score builder 通过" in text
    assert "source binding 通过" in text
    assert "real score-layer gate 通过" in text
    assert "model-layer diagnosis 失败" in text
    assert "validation RankIC / ICIR 明显低于 v2 / baseline" in text
    assert "validation top-bottom spread 为负" in text


def test_decision_record_blocks_portfolio_confirmatory_and_shadow() -> None:
    text = load_doc()

    assert "不进入 portfolio dry-run" in text
    assert "不进入 confirmatory / shadow" in text


def test_decision_record_blocks_validation_formula_tuning() -> None:
    text = load_doc()

    assert "不允许围绕 validation 调 v3 formula" in text


def test_decision_record_preserves_frozen_test_and_oos_boundary() -> None:
    text = load_doc()

    assert "不允许读取 frozen test" in text
    assert "不允许把 trainval diagnosis 当 OOS" in text
