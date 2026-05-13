from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/clean_baseline_family_decision_record.md")


def load_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_decision_record_exists() -> None:
    assert DOC_PATH.exists()


def test_decision_record_contains_required_score_gate_terms() -> None:
    text = load_doc()

    assert "clean baseline family score-layer gate 4/4 通过" in text
    assert "4/4 score gate passed" in text
    assert "no p98" in text
    assert "no label diagnostics" in text
    assert "no frozen test access" in text
    assert "D0 visibility audit passed" in text
    assert "leakage audit passed" in text


def test_decision_record_contains_required_portfolio_and_reference_verdicts() -> None:
    text = load_doc()

    assert "no portfolio dry-run" in text
    assert "recommended_same_contract_portfolio_dry_run_candidates = []" in text
    assert "cannot replace or parallel p98 conditional baseline" in text
    assert "conditional reference only" in text


def test_decision_record_contains_required_governance_boundary_terms() -> None:
    text = load_doc()

    assert "not OOS" in text
    assert "not strategy approval" in text
    assert "不替代 p98 conditional baseline" in text
    assert "不并列 p98 conditional baseline" in text
    assert "下一步不应跑 portfolio" in text
    assert "clean baseline family redesign 或数据字段补全" in text
