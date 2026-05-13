from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/research_problem_reframing_options_after_data_regime_stop.md")


def read_doc(repo_root: Path) -> str:
    return (repo_root / DOC_PATH).read_text(encoding="utf-8")


def test_reframing_doc_contains_required_boundary_terms(repo_root: Path) -> None:
    text = read_doc(repo_root)
    lower = text.lower()

    for phrase in [
        "current_data_regime_research_stopped",
        "no new information source",
        "no new data modality",
        "no portfolio",
        "no frozen test",
        "not oos",
        "p98 conditional reference only",
    ]:
        assert phrase in lower


def test_reframing_doc_contains_at_least_six_options(repo_root: Path) -> None:
    text = read_doc(repo_root)
    assert text.count("### Option ") >= 6


def test_reframing_doc_covers_required_reframing_directions(repo_root: Path) -> None:
    text = read_doc(repo_root).lower()

    for phrase in [
        "wider quantile",
        "lower-frequency",
        "longer-holding",
        "risk-control / filter",
        "stability / risk-control objective",
        "portfolio construction",
        "pause a-share daily clean alpha research",
    ]:
        assert phrase in text


def test_each_option_contains_required_assessment_fields(repo_root: Path) -> None:
    text = read_doc(repo_root)

    for phrase in [
        "Research question",
        "Difference from original problem",
        "New label / execution contract",
        "Independent pre-registration",
        "Existing evidence supports",
        "Existing evidence does not support",
        "Maximum risk",
        "Recommended as next stage",
        "Recommendation level",
    ]:
        assert text.count(phrase) >= 6


def test_reframing_doc_preserves_evidence_boundaries(repo_root: Path) -> None:
    text = read_doc(repo_root).lower()

    for phrase in [
        "mid-rank yearly stability is insufficient",
        "current head-exclusion evidence is unstable",
        "previous portfolio diagnostic did not find strong enough clean evidence",
        "the 5d conclusions cannot be transferred",
        "not a stable topk head improvement",
    ]:
        assert phrase in text


def test_reframing_doc_contains_recommendation_levels(repo_root: Path) -> None:
    text = read_doc(repo_root).lower()

    for phrase in [
        "recommended",
        "conditional",
        "not recommended",
    ]:
        assert phrase in text


def test_reframing_doc_contains_final_recommendation(repo_root: Path) -> None:
    text = read_doc(repo_root).lower()

    assert "final recommendation" in text
    assert "b. do not continue strategy research" in text
    assert "pause a-share daily clean alpha research" in text


def test_reframing_doc_blocks_forbidden_actions(repo_root: Path) -> None:
    text = read_doc(repo_root).lower()

    for phrase in [
        "no training",
        "no backtest",
        "no portfolio or portfolio dry-run",
        "no formal metrics/readout",
        "no frozen test",
        "no concrete trading rules",
        "no claim of strategy effectiveness",
    ]:
        assert phrase in text
