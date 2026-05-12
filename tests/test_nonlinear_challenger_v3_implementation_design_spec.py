from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/nonlinear_challenger_v3_implementation_design_spec.md")


def load_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_v3_implementation_design_spec_exists() -> None:
    assert DOC_PATH.exists()


def test_v3_spec_contains_conditioning_calculation_contract() -> None:
    text = load_doc()

    assert "topk_head_quality_conditioned_capital_deployment" in text
    assert "raw_score_D0" in text
    assert "adjusted_score_D0" in text
    assert "capital_deployment_multiplier = clip(0.50 + 0.50 * head_quality_cell_percentile_rank, 0.50, 1.00)" in text
    assert "TopK membership = false" in text
    assert "adjusted_score_D0 = 0.0" in text


def test_v3_spec_contains_required_allowed_and_prohibited_inputs() -> None:
    text = load_doc()

    assert "confirmed5 raw_score_D0" in text
    assert "v2 adjusted_score_D0" in text
    assert "historical train-only head-quality estimates" in text
    assert "`volatility` 允许" in text
    assert "`liquidity` 允许" in text
    assert "`turnover` 只允许使用 `ex-ante turnover proxy`" in text
    assert "`realized label proxy` 只允许用于 historical head-quality estimation" in text
    assert "`validation outcome`" in text
    assert "`frozen test`" in text
    assert "`future realized return`" in text
    assert "`portfolio result feedback`" in text


def test_v3_spec_contains_leakage_prevention_rules() -> None:
    text = load_doc()

    assert "head-quality conditioning 只能由 train window 或 expanding past data 产生" in text
    assert "不能用当前 signal_date 之后的信息" in text
    assert "不能用 validation 结果调门槛" in text
    assert "no_validation_lookup" in text
    assert "no_frozen_test_lookup" in text
    assert "no_future_signal_date_lookup" in text
    assert "no_portfolio_feedback_lookup" in text


def test_v3_spec_contains_output_fields_and_policy_version() -> None:
    text = load_doc()

    assert "`raw_score_D0`" in text
    assert "`adjusted_score_D0`" in text
    assert "`capital_deployment_multiplier`" in text
    assert "`head_quality_conditioning_source`" in text
    assert "`conditioning_policy_version`" in text
    assert "`leakage_audit_flags`" in text
    assert "conditioning_policy_version = nlc_v3_hqcd_v1" in text


def test_v3_spec_contains_fail_fast_guardrails() -> None:
    text = load_doc()

    assert "`conditioning source 缺失`" in text
    assert "`使用 validation/frozen 信息`" in text
    assert "`multiplier 超出预设范围`" in text
    assert "`TopK head quality 未改善`" in text
    assert "`baseline same-contract comparison 缺失`" in text
    assert "`capital_deployment_multiplier` 不在 `[0.50, 1.00]` 内" in text


def test_v3_spec_contains_unchanged_constraints_and_non_goals() -> None:
    text = load_doc()

    assert "不改 feature list" in text
    assert "不改 LightGBM 参数" in text
    assert "不改 execution semantics" in text
    assert "不改 terminal exit policy" in text
    assert "不改 portfolio guard" in text
    assert "不准写实现脚本" in text
    assert "不准训练" in text
    assert "不准跑 portfolio" in text
    assert "不准生成 metrics/readout" in text
    assert "不准读取 frozen test" in text
    assert "不准围绕 validation 筛优" in text
