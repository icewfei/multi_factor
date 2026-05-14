from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/descriptive_mechanism_synthesis_after_sandbox_diagnostics.md")


def test_synthesis_doc_exists(repo_root: Path) -> None:
    assert (repo_root / DOC_PATH).exists()


def test_synthesis_doc_contains_required_boundaries(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for phrase in [
        "no portfolio",
        "no frozen test",
        "not OOS",
        "no candidate",
        "conditional reference only",
        "strategy_research: paused",
        "no strategy restart",
    ]:
        assert phrase in text


def test_synthesis_doc_contains_required_mechanism_topics(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for phrase in [
        "near-head consensus hypothesis",
        "TopK stress / extreme / limit-like hypothesis",
        "rank-band non-monotonic profile",
        "market-state conditional findings",
        "cross-model agreement findings",
        "TopK head placement",
        "nextK",
        "rank_31_100",
    ]:
        assert phrase in text


def test_synthesis_doc_answers_required_questions(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for phrase in [
        "Current strongest mechanism explanation",
        "Mechanisms with stronger evidence",
        "Mechanisms with insufficient evidence",
        "Future paper-only hypotheses",
        "Candidate allowed?",
        "Portfolio allowed?",
        "Does this change `strategy_research: paused`?",
        "This is sandbox understanding only, no strategy restart.",
    ]:
        assert phrase in text
