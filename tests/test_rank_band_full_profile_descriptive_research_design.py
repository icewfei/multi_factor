from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/rank_band_full_profile_descriptive_research_design.md")


def test_rank_band_full_profile_design_exists(repo_root: Path) -> None:
    assert (repo_root / DOC_PATH).exists()


def test_design_is_descriptive_only(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    assert "descriptive mechanism research only" in text
    assert "not alpha research" in text
    assert "not a candidate design" in text
    assert "not a strategy restart" in text


def test_design_preserves_hard_prohibitions(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    assert "no portfolio" in text
    assert "no portfolio dry-run" in text
    assert "no frozen test" in text
    assert "trainval not OOS" in text
    assert "no validation tuning" in text
    assert "no p98 as clean gold standard" in text


def test_design_covers_required_descriptive_questions(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    assert "rank-band full profile" in text
    assert "market-state conditional diagnostics" in text
    assert "long/short asymmetry" in text
    assert "cross-model agreement/disagreement" in text
    assert "feature interaction description" in text
    assert "failure mechanism summary" in text


def test_design_blocks_candidate_and_promotion_outputs(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    assert "candidate name" in text
    assert "score formula change" in text
    assert "pass/fail promotion decision" in text
    assert "No implementation may start from this document alone" in text
