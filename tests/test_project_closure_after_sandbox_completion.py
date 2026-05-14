from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/project_closure_after_sandbox_completion.md")


def read_doc(repo_root: Path) -> str:
    return (repo_root / DOC_PATH).read_text(encoding="utf-8")


def test_project_closure_doc_exists(repo_root: Path) -> None:
    assert (repo_root / DOC_PATH).exists()


def test_project_closure_doc_contains_status(repo_root: Path) -> None:
    text = read_doc(repo_root)

    assert "strategy_research: paused" in text
    assert "sandbox_understanding: completed" in text
    assert "audit asset and engineering asset" in text


def test_project_closure_doc_contains_required_boundaries(repo_root: Path) -> None:
    text = read_doc(repo_root).lower()

    for phrase in [
        "no candidate",
        "no portfolio",
        "no frozen test",
        "not oos",
        "conditional reference only",
        "no v4",
        "no training",
        "no backtest",
    ]:
        assert phrase in text


def test_project_closure_doc_contains_restart_conditions(repo_root: Path) -> None:
    text = read_doc(repo_root).lower()

    assert "new information source" in text
    assert "new data modality" in text
    assert "independently pre-registered research problem" in text
    assert "trainval repetition" in text


def test_project_closure_doc_contains_final_recommendation(repo_root: Path) -> None:
    text = read_doc(repo_root)

    assert "treat sandbox understanding as completed" in text
    assert "do not continue the same research question" in text
    assert "This is a closed-question preservation state, not an unfinished-strategy state." in text
