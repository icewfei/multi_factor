from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/project_governance_addendum_after_guarded_workflow.md")


def test_project_governance_addendum_exists(repo_root: Path) -> None:
    assert (repo_root / DOC_PATH).exists()


def test_addendum_contains_constitution_continuity(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    assert "The original constitution remains valid" in text
    assert "not a mandate to chase historical returns" in text


def test_addendum_contains_new_governance_conclusions(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    assert "conditional baseline / conditional reference only" in text
    assert "conditional enrichment layer" in text
    assert "listing_age_trading_days" in text
    assert "newly_listed_flag" in text
    assert "guarded workflow required" in text


def test_addendum_contains_superseded_clean_baseline_redesign_direction(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    assert "strong baseline is not clean enough" in text
    assert "clean baseline family is clean but not strong enough" in text
    assert "next research direction at that stage was clean baseline redesign" in text
    assert "superseded by `current_data_regime_research_stop_decision`" in text
    assert "not platform expansion" in text


def test_addendum_preserves_hard_boundaries(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    assert "does not change the frozen test rule" in text
    assert "does not change execution semantics" in text
    assert "does not permit trainval-as-OOS" in text


def test_addendum_contains_current_stopped_phase(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    assert "Current phase: `current_data_regime_research_stopped`" in text
    assert "no training" in text
    assert "no backtest" in text
