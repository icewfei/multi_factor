from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/nonlinear_challenger_v3_research_design_brief.md")


def load_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_v3_brief_exists() -> None:
    assert DOC_PATH.exists()


def test_v3_brief_contains_single_primary_change_dimension() -> None:
    text = load_doc()

    assert "topk_head_quality_conditioned_capital_deployment" in text
    assert "single primary change dimension" in text.lower()
    assert "deployed TopK head quality" in text
    assert "capital deployment efficiency" in text


def test_v3_brief_contains_required_boundaries() -> None:
    text = load_doc()

    assert "不改变 model input features" in text
    assert "不改变 LightGBM hyperparameters" in text
    assert "不改变 execution semantics" in text
    assert "不改变 terminal exit policy" in text
    assert "不改变 portfolio guard" in text
    assert "不设计具体 `v3` 参数" in text


def test_v3_brief_contains_promotion_and_fail_fast_rules() -> None:
    text = load_doc()

    assert "model-layer 不明显劣化" in text
    assert "same-contract portfolio comparison 必须优于 baseline" in text
    assert "total equity 必须报告" in text
    assert "invested capital 必须报告" in text
    assert "cash 必须报告" in text
    assert "turnover 必须报告" in text
    assert "没有 baseline same-contract comparison，不晋级" in text
    assert "高现金口径未披露，不晋级" in text
    assert "TopK head quality 未改善，不晋级" in text
    assert "frozen test 被读取，直接作废" in text
