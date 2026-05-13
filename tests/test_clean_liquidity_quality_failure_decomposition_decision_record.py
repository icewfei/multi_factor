from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/clean_liquidity_quality_failure_decomposition_decision_record.md")


def test_decision_record_answers_required_questions(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for phrase in [
        "clean_liquidity_quality_failure_decomposition_round_v1",
        "not OOS",
        "not strategy approval",
        "not a portfolio dry-run",
        "Frozen test remains unread",
        "No ML model was trained",
        "No portfolio, backtest, holdings",
        "listing_age_trading_days",
        "newly_listed_flag",
        "liquidity_quality 的 RankIC 改善是否真实存在",
        "RankIC 改善主要来自头部、中段、还是尾部",
        "TopK-minus-nextK 为负的主因是什么",
        "是否是 nextK 比 TopK 更强",
        "是否是 liquidity filter 把 alpha 从 top head 推到中高分位",
        "是否是高流动性/低风险结构稀释了 reversal edge",
        "train / validation / yearly",
        "是否建议开下一轮 preregistered candidate",
        "是否建议进入 portfolio dry-run",
        "是否继续把 p98 只作为 conditional reference",
    ]:
        assert phrase in text


def test_decision_record_closes_with_no_candidate_no_portfolio(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for phrase in [
        "Do not open a new candidate",
        "Do not enter portfolio dry-run",
        "TopK-minus-nextK remains negative",
        "not head-driven",
        "conditional reference only",
        "not as a clean component",
    ]:
        assert phrase in text
