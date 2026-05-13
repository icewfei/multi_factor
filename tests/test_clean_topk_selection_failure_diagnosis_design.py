from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/clean_topk_selection_failure_diagnosis_design.md")


def test_design_doc_declares_scope_and_boundaries(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for phrase in [
        "clean_topk_selection_failure_diagnosis_round_v1",
        "only diagnoses clean TopK selection failure",
        "does not design a new candidate",
        "change `TopK` / `nextK` definitions",
        "run portfolio",
        "read frozen test data",
        "listing_age_trading_days",
        "newly_listed_flag",
    ]:
        assert phrase in text


def test_design_doc_lists_required_comparators_and_dimensions(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for phrase in [
        "no_p98_reversal_baseline_v1",
        "clean_reversal_5d_liquidity_quality_v1",
        "clean_composite_reversal_tradability_v1",
        "clean_reversal_5d_limit_aware_v1",
        "clean_reversal_5d_board_neutral_v1",
        "clean_reversal_5d_tradability_filtered_v1",
        "p98_conditional_reference",
        "TopK` vs `nextK` vs `rank 31-100` return",
        "Yearly stability",
        "Daily win rate",
        "Score extremeness / score dispersion",
        "Reversal extremeness",
        "Liquidity exposure",
        "Board / exchange exposure",
        "Limit / suspension / tradability exposure",
        "Large winner / large loser contribution",
        "Overlap / divergence across clean baselines",
        "Whether head-exclusion evidence exists",
    ]:
        assert phrase in text
