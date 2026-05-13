from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/current_data_regime_research_stop_decision.md")


def test_stop_decision_contains_no_portfolio(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    lower = text.lower()
    assert "no portfolio" in lower


def test_stop_decision_contains_no_v4(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    lower = text.lower()
    assert "no v4" in lower or "not recommend" in lower


def test_stop_decision_contains_no_frozen_test(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    lower = text.lower()
    assert "frozen test" in lower
    assert "prohibited" in lower or "no frozen test" in lower or "remains prohibited" in lower


def test_stop_decision_contains_trainval_not_oos(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    lower = text.lower()
    assert "not oos" in lower
    assert "train/validation diagnosis only" in lower or "trainval" in lower


def test_stop_decision_contains_p98_conditional_reference_only(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    assert "conditional reference only" in text


def test_stop_decision_contains_no_portfolio_ready_candidate(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    lower = text.lower()
    assert "no portfolio-ready candidate" in lower


def test_stop_decision_contains_mid_rank_yearly_stability_insufficient(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    lower = text.lower()
    assert "mid-rank" in lower
    assert "yearly stability" in lower or "yearly consistency" in lower
    assert "insufficient" in lower or "not met" in lower or "not satisfied" in lower


def test_stop_decision_contains_pause_strategy_advancement(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    lower = text.lower()
    assert "pause" in lower and ("strategy" in lower or "advancement" in lower or "research" in lower)


def test_stop_decision_covers_all_five_sub_rounds(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for round_name in [
        "clean_baseline_redesign_round_v1",
        "clean_composite_topk_improvement_decomposition_round_v1",
        "clean_liquidity_quality_failure_decomposition_round_v1",
        "clean_topk_selection_failure_diagnosis_round_v1",
        "clean_mid_rank_portfolio_hypothesis_round_v1",
    ]:
        assert round_name in text


def test_stop_decision_contains_conditions_for_resumption(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    lower = text.lower()
    assert "new information source" in lower
    assert "new data modalit" in lower
    assert "reframed" in lower or "reframe" in lower


def test_stop_decision_contains_not_strategy_effectiveness(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    lower = text.lower()
    assert "not a strategy effectiveness" in lower


def test_stop_decision_contains_blocked_fields(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    assert "listing_age_trading_days" in text
    assert "newly_listed_flag" in text


def test_stop_decision_contains_OHLCV_rule_exhaustion(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    lower = text.lower()
    assert "ohlcv" in lower
    assert "not continue" in lower or "stop" in lower or "exhausted" in lower
