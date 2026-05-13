from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/clean_topk_selection_failure_diagnosis_decision_record.md")


def test_decision_record_answers_required_questions(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for phrase in [
        "clean_topk_selection_failure_diagnosis_round_v1",
        "not OOS",
        "not strategy approval",
        "not a portfolio dry-run",
        "Frozen test remains unread",
        "No ML model was trained",
        "No portfolio, backtest, holdings",
        "listing_age_trading_days",
        "newly_listed_flag",
        "TopK selection failure 是否是 clean baselines 的共性问题",
        "TopK 是否稳定弱于 nextK / rank 31-100",
        "是否存在稳定 D0-visible head-exclusion evidence",
        "是否建议进入下一轮 preregistered head-exclusion candidate design",
        "是否建议进入 portfolio dry-run",
        "p98 / multi_equal_weight_v1 是否仍只作为 conditional reference",
        "是否继续禁止使用 blocked fields",
        "是否继续禁止 frozen test",
    ]:
        assert phrase in text


def test_decision_record_closes_with_no_candidate_no_portfolio(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for phrase in [
        "Do not open a generic head-exclusion candidate",
        "Do not enter portfolio dry-run",
        "conditional reference only",
        "continue blocking frozen test",
        "continue blocking blocked fields",
    ]:
        assert phrase in text
