from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/guarded_research_runner_decision_record.md")
SCHEMA_PATH = Path("schemas/guarded_research_request.schema.json")
RUNNER_PATH = Path("scripts/run_guarded_research_task.py")
WRAPPER_PATH = Path("scripts/run_guarded_clean_baseline_score_task.py")


def test_guarded_research_runner_decision_record_captures_required_boundaries(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    required_phrases = [
        "guarded research runner is implemented",
        "before research task dispatch",
        "listing_age_trading_days",
        "newly_listed_flag",
        "`portfolio` and `screening` task types are currently blocked",
        "clean baseline score task can pass with `requested_enrichment_fields=[]`",
        "thin clean-baseline wrapper",
        "Future enrichment-consuming clean baseline or challenger work must declare",
        "No frozen test access is allowed",
        "not alpha",
        "not strategy approval",
        "not OOS",
    ]
    for phrase in required_phrases:
        assert phrase in text


def test_guarded_research_runner_artifacts_exist(repo_root: Path) -> None:
    assert (repo_root / DOC_PATH).exists()
    assert (repo_root / SCHEMA_PATH).exists()
    assert (repo_root / RUNNER_PATH).exists()
    assert (repo_root / WRAPPER_PATH).exists()


def test_guarded_runner_source_keeps_portfolio_as_blocked_not_dispatchable(repo_root: Path) -> None:
    text = (repo_root / RUNNER_PATH).read_text(encoding="utf-8")
    assert '"portfolio": "portfolio"' in text
    assert '"screening": "screening"' in text
    assert 'DISPATCHABLE_TASK_TYPES = {"diagnostic", "clean_baseline_score"}' in text
    assert "portfolio_run_executed" in text
    assert "holdings_generated" in text
