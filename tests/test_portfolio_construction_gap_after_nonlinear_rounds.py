from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/portfolio_construction_gap_after_nonlinear_rounds.md")


def load_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_summary_doc_exists() -> None:
    assert DOC_PATH.exists()


def test_summary_doc_contains_required_failure_points() -> None:
    text = load_doc()

    assert "nonlinear model-layer edge 没有转成 TopK portfolio edge" in text
    assert "confirmed5 高 churn 且 head quality 不够强" in text
    assert "v2 降低风险但牺牲收益捕获" in text
    assert "baseline 的 selected-head realized return 更强" in text


def test_summary_doc_contains_required_next_step_direction() -> None:
    text = load_doc()

    assert "不应继续盲目增加模型复杂度" in text
    assert "portfolio construction / capital deployment" in text
    assert "不设计具体 `v3` 参数" in text


def test_summary_doc_contains_required_boundaries() -> None:
    text = load_doc()

    assert "不跑回测" in text
    assert "不生成 metrics/readout" in text
    assert "不读取 frozen test" in text
    assert "不把 trainval dry-run 当 OOS" in text
