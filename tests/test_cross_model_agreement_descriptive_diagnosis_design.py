from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/cross_model_agreement_descriptive_diagnosis_design.md")


def test_design_doc_exists(repo_root: Path) -> None:
    assert (repo_root / DOC_PATH).exists()


def test_design_doc_contains_scope_and_boundaries(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for phrase in [
        "exploratory descriptive research only",
        "not alpha research",
        "not a candidate",
        "not portfolio",
        "not OOS",
        "Frozen test remains unread",
        "does not restart strategy research",
        "conditional reference only",
    ]:
        assert phrase in text


def test_design_doc_contains_models_and_outputs(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for phrase in [
        "no_p98_reversal_baseline_v1",
        "clean_reversal_5d_tradability_filtered_v1",
        "clean_reversal_5d_board_neutral_v1",
        "clean_reversal_5d_limit_aware_v1",
        "clean_reversal_5d_liquidity_quality_v1",
        "clean_reversal_5d_listing_age_calendar_v1",
        "clean_composite_reversal_tradability_v1",
        "p98 conditional baseline",
        "multi_equal_weight_v1 conditional baseline",
        "/private/tmp/cross_model_agreement_descriptive_diagnosis.json",
        "/private/tmp/cross_model_agreement_descriptive_diagnosis.md",
    ]:
        assert phrase in text


def test_design_doc_blocks_forbidden_fields_and_requires_unavailable_marking(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for phrase in [
        "`listing_age_trading_days`",
        "`newly_listed_flag`",
        "label diagnostics for source selection",
        "future / realized / `actual_exit` / `sell_price`",
        "Unavailable fields must be explicitly marked `unavailable`",
        "No silent fallback is allowed",
    ]:
        assert phrase in text


def test_design_doc_contains_required_sections(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for phrase in [
        "agreement_count bucket `0..N`",
        "common TopK: `>= 4` clean models",
        "model-specific TopK: exactly `1` clean model",
        "common `nextK` return",
        "common `mid_head` return",
        "TopK by one model but `nextK` / `mid_head` by others",
        "`is_limit_down`",
        "`close_at_down_limit`",
        "`open_at_up_limit`",
        "`entry_buyable`",
        "`no_trade_flag`",
        "validation yearly consistency",
        "agreement_count cannot directly form any trading rule",
    ]:
        assert phrase in text
