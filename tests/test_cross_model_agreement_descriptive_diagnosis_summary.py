from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/cross_model_agreement_descriptive_diagnosis_summary.md")


def test_summary_exists(repo_root: Path) -> None:
    assert (repo_root / DOC_PATH).exists()


def test_summary_contains_required_boundaries(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    for phrase in [
        "exploratory descriptive research only",
        "descriptive-only",
        "not alpha",
        "not a candidate",
        "not portfolio",
        "not OOS",
        "Frozen test remains unread",
        "does not restart strategy research",
        "agreement_count cannot directly form any trading rule",
        "does not treat trainval diagnosis as OOS",
    ]:
        assert phrase in text


def test_summary_contains_outputs_and_conditional_reference(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    assert "/private/tmp/cross_model_agreement_descriptive_diagnosis.json" in text
    assert "/private/tmp/cross_model_agreement_descriptive_diagnosis.md" in text
    assert "`p98` and `multi_equal_weight_v1` are conditional reference only" in text
    assert "not clean gold standards" in text


def test_summary_contains_hypotheses_and_insufficient_evidence(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    assert "Future Paper-Only Hypotheses" in text
    assert "These remain paper-only hypothesis candidates" in text
    assert "Insufficient Evidence Boundary" in text
    assert "candidate creation" in text
    assert "trading rule design" in text
