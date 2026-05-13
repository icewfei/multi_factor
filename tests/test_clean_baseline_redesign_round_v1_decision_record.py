from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/clean_baseline_redesign_round_v1_decision_record.md")


def test_redesign_round_v1_decision_record_closes_required_questions(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    required_phrases = [
        "clean_baseline_redesign_round_v1",
        "No `p98` was used",
        "No frozen test was read",
        "No portfolio",
        "listing_age_trading_days",
        "newly_listed_flag",
        "full-cross-section edge",
        "TopK head quality",
        "No new clean redesign candidate is recommended",
        "same-contract portfolio dry-run preparation",
        "continue not running portfolio",
        "not a strategy effectiveness conclusion",
        "not OOS evidence",
        "conditional reference only",
    ]
    for phrase in required_phrases:
        assert phrase in text


def test_redesign_round_v1_decision_record_mentions_all_candidates(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for baseline_id in [
        "clean_reversal_5d_tradability_filtered_v1",
        "clean_reversal_5d_board_neutral_v1",
        "clean_reversal_5d_limit_aware_v1",
        "clean_reversal_5d_liquidity_quality_v1",
        "clean_reversal_5d_listing_age_calendar_v1",
        "clean_composite_reversal_tradability_v1",
        "no_p98_reversal_baseline_v1",
        "p98_conditional_reference",
        "multi_equal_weight_v1_conditional_reference",
    ]:
        assert baseline_id in text
