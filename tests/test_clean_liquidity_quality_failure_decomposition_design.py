from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/clean_liquidity_quality_failure_decomposition_design.md")


def test_design_doc_declares_scope_and_boundaries(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for phrase in [
        "clean_liquidity_quality_failure_decomposition_round_v1",
        "only explains",
        "does not modify the liquidity-quality formula",
        "tune thresholds",
        "create a new candidate",
        "run portfolio",
        "read frozen test data",
        "listing_age_trading_days",
        "newly_listed_flag",
        "not clean components",
    ]:
        assert phrase in text


def test_design_doc_lists_required_comparators_and_dimensions(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for phrase in [
        "no_p98_reversal_baseline_v1",
        "clean_reversal_5d_liquidity_quality_v1",
        "clean_composite_reversal_tradability_v1",
        "rejected comparator",
        "p98_conditional_reference",
        "multi_equal_weight_v1",
        "Decile / ventile return curve",
        "TopK / nextK / rank 31-100",
        "TopK winner / loser contribution",
        "Yearly stability",
        "Amount bucket / liquidity exposure",
        "Board / exchange exposure",
        "Tradability / limit status exposure",
        "Overlap / divergence",
        "Score dispersion / rank concentration",
        "Middle-bucket contribution",
    ]:
        assert phrase in text
