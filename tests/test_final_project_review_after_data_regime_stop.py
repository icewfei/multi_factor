from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/final_project_review_after_data_regime_stop.md")


def read_doc(repo_root: Path) -> str:
    return (repo_root / DOC_PATH).read_text(encoding="utf-8")


def test_final_project_review_exists(repo_root: Path) -> None:
    assert (repo_root / DOC_PATH).exists()


def test_final_project_review_contains_current_stop_status(repo_root: Path) -> None:
    text = read_doc(repo_root)

    assert "current_data_regime_research_stopped" in text
    assert "pause strategy research" in text
    assert "audit asset and engineering asset" in text


def test_final_project_review_covers_required_review_areas(repo_root: Path) -> None:
    text = read_doc(repo_root)

    for phrase in [
        "Research Path Review",
        "Engineering Implementation Review",
        "Project Progress Review",
        "Why The Project Cannot Continue On The Same Path",
        "Recommended Actions",
        "Future Restart Conditions",
        "Final Recommendation",
    ]:
        assert phrase in text


def test_final_project_review_preserves_hard_boundaries(repo_root: Path) -> None:
    text = read_doc(repo_root).lower()

    for phrase in [
        "does not train",
        "backtest",
        "run portfolio",
        "formal metrics/readout",
        "read frozen test",
        "concrete trading rules",
        "strategy effectiveness",
    ]:
        assert phrase in text


def test_final_project_review_explains_stop_causes(repo_root: Path) -> None:
    text = read_doc(repo_root).lower()

    for phrase in [
        "information source is too limited",
        "model-layer edge did not reliably convert",
        "clean-versus-strong gap",
        "stability checks failed",
        "trainval tuning",
    ]:
        assert phrase in text


def test_final_project_review_lists_restart_conditions(repo_root: Path) -> None:
    text = read_doc(repo_root).lower()

    assert "new information source" in text
    assert "new data modality" in text
    assert "new research problem" in text
    assert "independently pre-registered" in text
