from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/clean_mid_rank_portfolio_hypothesis_decision_record.md")


def test_decision_record_contains_no_frozen_test(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for phrase in [
        "Frozen test remains unread",
        "No frozen test was read",
        "Frozen test was not read",
    ]:
        assert phrase in text


def test_decision_record_contains_no_formal_portfolio(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for phrase in [
        "No portfolio",
        "no portfolio",
    ]:
        assert phrase in text


def test_decision_record_contains_not_oos(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    assert "not OOS" in text
    assert "not a strategy" in text.lower() or "not a strategy effectiveness" in text


def test_decision_record_does_not_recommend_dry_run(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    assert "Do not recommend a diagnostic portfolio dry-run" in text


def test_decision_record_contains_no_training_backtest(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for phrase in [
        "No model was trained",
        "No backtest was run",
        "No portfolio or holdings were generated",
    ]:
        assert phrase in text


def test_decision_record_contains_p98_conditional_reference(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    assert "conditional reference only" in text


def test_decision_record_contains_blocked_fields(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for field in [
        "listing_age_trading_days",
        "newly_listed_flag",
    ]:
        assert field in text


def test_decision_record_contains_new_info_source_recommendation(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    assert "new information source" in text or "new data modalit" in text or "reframed research question" in text


def test_decision_record_answers_all_required_questions(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for question in [
        "是否存在稳定 mid-rank edge",
        "是否 rank31-100 / rank31-200 系统性优于 TopK",
        "是否可解释为 TopK extreme reversal failure",
        "是否建议下一阶段做 pre-registered same-contract diagnostic portfolio dry-run",
        "如果建议，必须强调仍不是 formal portfolio approval",
        "如果不建议",
        "是否读取 frozen test",
        "是否训练/回测/portfolio",
    ]:
        assert question in text
