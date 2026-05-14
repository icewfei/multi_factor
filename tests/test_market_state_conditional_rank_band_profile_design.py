from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/market_state_conditional_rank_band_profile_design.md")


def test_market_state_design_exists(repo_root: Path) -> None:
    assert (repo_root / DOC_PATH).exists()


def test_design_contains_descriptive_boundaries(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    for phrase in [
        "exploratory descriptive research only",
        "not alpha research",
        "not a candidate",
        "not portfolio",
        "not OOS",
        "Frozen test remains unread",
    ]:
        assert phrase in text


def test_design_blocks_forbidden_fields(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    assert "`listing_age_trading_days`" in text
    assert "`newly_listed_flag`" in text
    assert "future / realized / `actual_exit` / `sell_price`" in text
    assert "Unavailable fields must be explicitly marked `unavailable`" in text


def test_design_contains_required_conditions_and_outputs(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    for phrase in [
        "amount bucket",
        "board_type",
        "exchange",
        "is_limit_up",
        "is_limit_down",
        "entry_buyable",
        "exit_sellable",
        "sellable_retry_next_open",
        "listing_age_days",
        "daily amount aggregate bucket",
        "TopK-minus-rank31_100",
        "rank31_100-minus-TopK",
    ]:
        assert phrase in text
