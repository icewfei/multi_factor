from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/exploratory_sandbox_policy_after_data_regime_stop.md")


def test_exploratory_sandbox_policy_exists(repo_root: Path) -> None:
    assert (repo_root / DOC_PATH).exists()


def test_policy_allows_paper_only_and_descriptive_mechanism_research(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    assert "Paper-only pre-registration is explicitly allowed" in text
    assert "Descriptive mechanism research is allowed" in text


def test_policy_preserves_hard_no_portfolio_and_no_frozen_test(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    assert "no portfolio" in text
    assert "no frozen test" in text


def test_policy_states_trainval_is_not_oos(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    assert "trainval not OOS" in text
    assert "no trainval-as-OOS" in text


def test_policy_defines_four_governance_levels(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    assert "four governance levels" in text.lower()
    assert "paper-only" in text
    assert "exploratory descriptive" in text
    assert "pre-registered implementation" in text
    assert "promotion / portfolio" in text


def test_policy_defines_allowed_descriptive_questions(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    assert "rank-band full profile" in text
    assert "market-state conditional diagnostics" in text
    assert "long/short asymmetry" in text
    assert "cross-model agreement/disagreement" in text
    assert "feature interaction description" in text
    assert "failure mechanism summary" in text


def test_policy_defines_listing_age_repair_as_data_quality_remediation(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    assert "listing_age repair is data-quality remediation" in text
    assert "`listing_age_trading_days` repair is data-quality remediation" in text
    assert "not a strategy restart" in text
