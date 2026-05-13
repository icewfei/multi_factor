from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/next_research_roadmap_after_nonlinear_rounds.md")


def load_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_roadmap_doc_exists() -> None:
    assert DOC_PATH.exists()


def test_roadmap_doc_contains_current_conclusions() -> None:
    text = load_doc()

    assert "confirmed5 / v2 / v3` 均不晋级" in text
    assert "model-layer edge 不等于 TopK portfolio edge" in text
    assert "nonlinear `model-layer edge 未能稳定转化为 portfolio-layer edge`" in text
    assert "baseline 的优势主要来自 `selected-head realized return` 更强" in text
    assert "`baseline` 仍是当前必须正面超过的最低门槛" in text


def test_roadmap_doc_contains_next_stage_focus() -> None:
    text = load_doc()

    assert "`portfolio construction`" in text
    assert "`capital deployment`" in text
    assert "`TopK head quality`" in text
    assert "`turnover-aware deployment`" in text
    assert "`cash / invested capital 口径`" in text
    assert "`selected-head realized return decomposition`" in text


def test_roadmap_doc_contains_prohibited_directions_and_boundaries() -> None:
    text = load_doc()

    assert "不继续堆 `LightGBM / nonlinear` 模型复杂度" in text
    assert "不继续围绕 `confirmed5 / v2 / v3` 微调" in text
    assert "不直接开 `v4` 训练" in text
    assert "不读取 frozen test" in text
    assert "不生成 metrics/readout" in text
    assert "不继续调 `confirmed5 / v2 / v3`" in text
    assert "不把 trainval dry-run 当 OOS" in text


def test_roadmap_doc_contains_low_degree_research_directions() -> None:
    text = load_doc()

    assert "### A. TopK Head Quality Gate" in text
    assert "### B. Turnover-Aware Admission Rule" in text
    assert "### C. Baseline Overlap / Divergence Analysis" in text
    assert "### D. Capital Deployment Schedule" in text
    assert "### E. Tail-Loss Containment" in text
    assert "以下只列低自由度研究方向，不实现" in text


def test_roadmap_doc_contains_required_template_fields() -> None:
    text = load_doc()

    assert "研究假设" in text
    assert "可用数据" in text
    assert "禁止使用的数据" in text
    assert "可能的 fail-fast 条件" in text
    assert "是否需要新 challenger" in text
    assert "是否可能引入过拟合风险" in text


def test_roadmap_doc_contains_next_step_recommendation() -> None:
    text = load_doc()

    assert "先做 `diagnostic-only research`" in text
    assert "不立刻开新 challenger" in text
    assert "只有当某个方向出现稳定、低自由度、D0 可见证据时" in text
    assert "才允许进入 `new research_round / new manifest`" in text
