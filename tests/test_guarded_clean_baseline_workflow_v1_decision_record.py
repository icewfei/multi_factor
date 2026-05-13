from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/guarded_clean_baseline_workflow_v1_decision_record.md")
WORKFLOW_PATH = Path("scripts/run_guarded_clean_baseline_research_workflow.py")
DIAGNOSIS_PATH = Path("scripts/run_guarded_clean_baseline_model_diagnosis_task.py")


def test_guarded_clean_baseline_workflow_v1_decision_record_boundaries(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    required_phrases = [
        "guarded_clean_baseline_research_workflow_v1",
        "Guardrail pass is required before the score builder",
        "Guardrail pass is also required before model-layer diagnosis",
        "listing_age_trading_days",
        "newly_listed_flag",
        "stop the entire workflow",
        "does not run portfolio construction",
        "No frozen test access is allowed",
        "does not generate formal metrics/readout",
        "not strategy approval",
        "not OOS",
        "Future baseline and challenger research",
    ]
    for phrase in required_phrases:
        assert phrase in text


def test_guarded_clean_baseline_workflow_v1_artifacts_exist(repo_root: Path) -> None:
    assert (repo_root / DOC_PATH).exists()
    assert (repo_root / WORKFLOW_PATH).exists()
    assert (repo_root / DIAGNOSIS_PATH).exists()
