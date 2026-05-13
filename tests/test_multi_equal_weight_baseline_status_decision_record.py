from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/multi_equal_weight_baseline_status_decision_record.md")


def load_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_decision_record_exists() -> None:
    assert DOC_PATH.exists()


def test_decision_record_contains_required_status_terms() -> None:
    text = load_doc()

    assert "conditional baseline" in text
    assert "not unconditional gold standard" in text
    assert "upstream source-chain provenance blocked" in text
    assert "score_rule direction mismatch" in text
    assert "source-selection feedback risk" in text
    assert "no frozen test access" in text


def test_decision_record_contains_required_policy_language() -> None:
    text = load_doc()

    assert "downstream same-contract comparison 仍然可用，但必须同步披露 baseline provenance blocker" in text
    assert "did not beat conditional baseline" in text
    assert "当前不建议继续开新 challenger" in text
    assert "clean baseline rebuild" in text
