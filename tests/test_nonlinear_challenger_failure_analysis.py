from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/nonlinear_challenger_failure_analysis.md")


def load_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_failure_analysis_exists() -> None:
    assert DOC_PATH.exists()


def test_failure_analysis_contains_required_results() -> None:
    text = load_doc()

    assert "RankIC" in text
    assert "ICIR" in text
    assert "Top-Bottom Spread" in text
    assert "Total Equity" in text
    assert "Relative Return" in text
    assert "Relative IR" in text
    assert "Avg Cash Weight" in text
    assert "Avg Invested Weight" in text
    assert "Avg Turnover Daily" in text
    assert "same-contract baseline comparison" in text


def test_failure_analysis_contains_required_failure_causes() -> None:
    text = load_doc()

    assert "model edge 不能自然转化成 TopK Portfolio Edge" in text
    assert "score 排序改善不等于持仓收益改善" in text
    assert "High Cash / Low Deployed Capital" in text
    assert "Volatility Discount 降低了回撤，但也降低了收益捕获" in text
    assert "Baseline 本身在 Portfolio-Layer 很强" in text
    assert "TopK / Holding Cohort / Capital Deployment 可能比模型更重要" in text


def test_failure_analysis_contains_required_boundaries() -> None:
    text = load_doc()

    assert "不围绕 validation 调 `v2` formula" in text
    assert "不继续微调 `confirmed5`" in text
    assert "不读取 frozen test" in text
    assert "不把 `trainval dry-run` 当 `OOS`" in text
    assert "必须预注册单一主变更维度" in text
    assert "same-contract baseline comparison 是最低门槛" in text
