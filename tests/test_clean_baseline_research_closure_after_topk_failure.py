from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/clean_baseline_research_closure_after_topk_failure.md")


def test_closure_doc_contains_no_portfolio(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for phrase in [
        "no portfolio",
        "No portfolio",
        "Do not enter portfolio dry-run",
        "not a portfolio dry-run",
    ]:
        assert phrase in text


def test_closure_doc_contains_no_v4(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    assert "Do not open v4" in text
    assert "no v4" in text or "v4" in text  # at minimum v4 is discussed


def test_closure_doc_contains_no_frozen_test(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for phrase in [
        "Frozen test remains unread",
        "No frozen test was read",
        "frozen test",
    ]:
        assert phrase in text


def test_closure_doc_contains_not_oos(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for phrase in [
        "not OOS",
        "not out-of-sample",
        "Trainval diagnosis is not OOS",
    ]:
        assert phrase in text


def test_closure_doc_contains_p98_conditional_reference_only(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for phrase in [
        "conditional reference only",
        "p98",
        "multi_equal_weight_v1",
    ]:
        assert phrase in text


def test_closure_doc_contains_no_portfolio_ready_candidate(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for phrase in [
        "no portfolio-ready candidate",
        "No portfolio-ready candidate",
        "No Portfolio-Ready Candidate",
    ]:
        assert phrase in text


def test_closure_doc_contains_new_data_modality_or_new_information_source(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    found_modality = "new data modality" in text
    found_info_source = "new information source" in text
    assert found_modality or found_info_source


def test_closure_doc_closes_all_four_sub_rounds(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for round_name in [
        "clean_baseline_redesign_round_v1",
        "clean_composite_topk_improvement_decomposition_round_v1",
        "clean_liquidity_quality_failure_decomposition_round_v1",
        "clean_topk_selection_failure_diagnosis_round_v1",
    ]:
        assert round_name in text


def test_closure_doc_contains_blocked_fields(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for field in [
        "listing_age_trading_days",
        "newly_listed_flag",
    ]:
        assert field in text


def test_closure_doc_contains_not_strategy_effectiveness(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    assert "not a strategy effectiveness conclusion" in text


def test_closure_doc_rejects_composite_route(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    assert "composite" in text.lower()
    assert "RankIC damage" in text


def test_closure_doc_rejects_liquidity_quality_route(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    assert "liquidity quality" in text.lower() or "liquidity_quality" in text
    assert "middle" in text.lower() or "tail" in text.lower()


def test_closure_doc_rejects_hard_coding_rules(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    assert "hard" in text.lower() or "rule" in text.lower()
    assert "OHLCV" in text
