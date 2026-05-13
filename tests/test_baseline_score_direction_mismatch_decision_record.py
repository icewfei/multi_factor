from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/baseline_score_direction_mismatch_decision_record.md")


def load_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_decision_record_exists() -> None:
    assert DOC_PATH.exists()


def test_decision_record_contains_required_direction_terms() -> None:
    text = load_doc()

    assert "registry DESC" in text
    assert "implementation ASC / reversal_rank" in text
    assert "executed behavior evidence" in text
    assert "baseline remains conditional" in text
    assert "p98 source-selection feedback risk remains" in text
    assert "no frozen test access" in text


def test_decision_record_contains_required_governance_conclusion() -> None:
    text = load_doc()

    assert "registry documentation mismatch" in text
    assert "historical reports must disclose mismatch" in text
    assert "supports ASC / reversal_rank" in text
