from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/market_state_conditional_rank_band_profile_summary.md")


def test_market_state_summary_exists(repo_root: Path) -> None:
    assert (repo_root / DOC_PATH).exists()


def test_summary_contains_required_boundaries(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    for phrase in [
        "exploratory descriptive research",
        "not alpha",
        "not a candidate",
        "not portfolio",
        "not OOS",
        "Frozen test remains unread",
        "No condition in this output can directly form any trading rule",
    ]:
        assert phrase in text


def test_summary_contains_outputs_and_conditional_reference(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    assert "/private/tmp/market_state_conditional_rank_band_profile.json" in text
    assert "/private/tmp/market_state_conditional_rank_band_profile.md" in text
    assert "`p98` and `multi_equal_weight_v1` are conditional reference only" in text
    assert "not OOS" in text
    assert "does not authorize portfolio recommendation" in text


def test_summary_contains_hypotheses_and_insufficient_evidence_boundary(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    assert "Future Paper-Only Hypotheses" in text
    assert "Insufficient Evidence Boundary" in text
    assert "Evidence is insufficient for candidate creation" in text
    assert "trading rule design" in text
