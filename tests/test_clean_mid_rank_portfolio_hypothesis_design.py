from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/clean_mid_rank_portfolio_hypothesis_design.md")


def test_design_contains_research_question(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    assert "clean_mid_rank_portfolio_hypothesis_round_v1" in text
    assert "not a strategy" in text or "not a portfolio approval" in text
    assert "rank-band" in text or "mid-rank" in text


def test_design_contains_fixed_rank_bands(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for band_range in [
        "1-30",
        "31-60",
        "31-100",
        "31-200",
        "101-300",
    ]:
        assert band_range in text


def test_design_contains_no_tuning_rule(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    assert "must not be tuned" in text
    assert "No band adjustment" in text or "not permitted" in text.lower()


def test_design_contains_boundaries(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    lower = text.lower()
    for phrase in [
        "no new alpha",
        "no ml",
        "no training" if "no training" in lower else "no ml model training",
        "frozen test",
        "no portfolio" if "no portfolio" in lower else "no formal portfolio",
        "conditional reference only",
        "not OOS".lower(),
        "not a strategy effectiveness",
    ]:
        assert phrase in lower


def test_design_contains_allowed_scores(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for score_id in [
        "no_p98_reversal_baseline_v1",
        "clean_reversal_5d_tradability_filtered_v1",
        "clean_reversal_5d_board_neutral_v1",
        "clean_reversal_5d_limit_aware_v1",
        "clean_reversal_5d_liquidity_quality_v1",
        "clean_reversal_5d_listing_age_calendar_v1",
        "clean_composite_reversal_tradability_v1",
        "p98",
        "multi_equal_weight_v1",
    ]:
        assert score_id in text


def test_design_contains_decision_rules(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    lower = text.lower()
    rules_ok = []
    rules_ok.append("validation" in lower and "train" in lower)
    rules_ok.append("yearly" in lower and ("stable" in lower or "stability" in lower))
    rules_ok.append("p98" in lower and "conditional" in lower)
    rules_ok.append("fixed band" in lower)
    assert all(rules_ok)


def test_design_contains_blocked_fields(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for field in [
        "listing_age_trading_days",
        "newly_listed_flag",
    ]:
        assert field in text
