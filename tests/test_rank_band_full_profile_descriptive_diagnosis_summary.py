from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/rank_band_full_profile_descriptive_diagnosis_summary.md")


def test_rank_band_full_profile_summary_exists(repo_root: Path) -> None:
    assert (repo_root / DOC_PATH).exists()


def test_summary_contains_descriptive_boundaries(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    assert "descriptive-only" in text
    assert "does not make an alpha claim" in text
    assert "does not create a candidate" in text
    assert "does not run portfolio" in text
    assert "does not read frozen test" in text
    assert "does not treat trainval diagnosis as OOS" in text


def test_summary_contains_outputs_and_fixed_bands(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    assert "/private/tmp/rank_band_full_profile_descriptive_diagnosis.json" in text
    assert "/private/tmp/rank_band_full_profile_descriptive_diagnosis.md" in text
    for band in ["1-30", "31-60", "31-100", "31-200", "101-300", "301-600", "bottom 30"]:
        assert band in text


def test_summary_contains_required_metrics_and_exposures(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    for phrase in [
        "mean",
        "median",
        "volatility",
        "daily win rate vs 0",
        "yearly mean",
        "best 5% contribution",
        "worst 5% damage",
        "amount bucket",
        "board / exchange",
        "limit / tradability",
        "listing_age_days bucket",
    ]:
        assert phrase in text


def test_summary_marks_conditional_references(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    assert "`p98` and `multi_equal_weight_v1` are reported only as conditional references" in text
    assert "not clean gold standards" in text
    assert "no deployment conclusion and no portfolio recommendation" in text
