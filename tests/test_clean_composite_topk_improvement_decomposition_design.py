from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/clean_composite_topk_improvement_decomposition_design.md")


def test_design_doc_declares_scope_and_boundaries(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    required_phrases = [
        "clean_composite_topk_improvement_decomposition_round_v1",
        "only explains",
        "does not change the composite formula",
        "does not change the composite formula, tune weights",
        "does not",
        "run portfolio",
        "read frozen test data",
        "not a clean component",
        "conditional reference only",
        "listing_age_trading_days",
        "newly_listed_flag",
    ]
    for phrase in required_phrases:
        assert phrase in text


def test_design_doc_lists_required_comparators_and_dimensions(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for phrase in [
        "no_p98_reversal_baseline_v1",
        "clean_liquidity_adjusted_reversal_baseline_v1",
        "clean_reversal_5d_liquidity_quality_v1",
        "clean_composite_reversal_tradability_v1",
        "p98_conditional_reference",
        "Full-cross-section rank correlation",
        "TopK / nextK / bottom bucket",
        "Decile return shape",
        "Yearly stability",
        "Board / exchange exposure",
        "Liquidity bucket exposure",
        "Tradability / limit status exposure",
        "Overlap / divergence",
        "Score compression / dispersion",
        "Large winner / large loser contribution",
    ]:
        assert phrase in text
