from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/clean_composite_topk_improvement_decomposition_decision_record.md")


def test_decision_record_answers_required_governance_questions(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    required_phrases = [
        "clean_composite_topk_improvement_decomposition_round_v1",
        "not OOS",
        "not strategy approval",
        "not a portfolio dry-run",
        "Frozen test remains unread",
        "No ML model was trained",
        "No portfolio, backtest, holdings",
        "listing_age_trading_days",
        "newly_listed_flag",
        "conditional reference only",
        "Composite TopK improvement 是否真实存在",
        "Composite RankIC damage 是否严重",
        "TopK improvement 是否稳定",
        "是否只是少数日期",
        "是否能解释为 D0 可见结构",
        "是否建议开下一轮 candidate",
        "是否建议进入 portfolio dry-run",
        "是否继续禁止 portfolio",
        "是否需要补字段或新数据",
        "是否继续把 p98 只作为 conditional reference",
    ]
    for phrase in required_phrases:
        assert phrase in text


def test_decision_record_closes_with_no_candidate_no_portfolio(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for phrase in [
        "Do not open a next pre-registered candidate",
        "Do not enter portfolio dry-run",
        "Continue treating the composite as a diagnostic object only",
        "TopK-minus-nextK stability fails",
        "RankIC damage is severe",
        "not a clean component",
        "not an unconditional gold standard",
    ]:
        assert phrase in text
