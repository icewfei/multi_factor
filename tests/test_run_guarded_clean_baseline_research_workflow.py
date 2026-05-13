from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


SCRIPT_PATH = "scripts/run_guarded_clean_baseline_research_workflow.py"
BASELINE_ID = "clean_equal_weight_random_eligible_baseline_v1"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_parquet(path: Path, payload: dict) -> None:
    pq.write_table(pa.table(payload), path)


def build_fixture(tmp_path: Path) -> dict[str, Path]:
    snapshot_root = tmp_path / "snapshot"
    snapshot_root.mkdir(parents=True, exist_ok=True)
    sample_panel_path = tmp_path / "clean_sample_panel.parquet"
    run_input_contract_path = tmp_path / "run_input_contract.json"
    label_panel_path = tmp_path / "label_panel.parquet"
    split_panel_path = tmp_path / "split_panel.parquet"
    output_dir = tmp_path / "score_output"
    workflow_dir = tmp_path / "workflow"

    rows = {
        "snapshot_id": ["snap"] * 6,
        "instrument": ["AAA.SZ", "BBB.SZ", "CCC.SZ"] * 2,
        "signal_date": ["20210104"] * 3 + ["20210105"] * 3,
    }
    write_parquet(
        sample_panel_path,
        rows | {"ranking_eligible_D0": [True] * 6},
    )
    write_parquet(
        label_panel_path,
        rows
        | {
            "label_5d_next_open_close": [0.03, 0.01, -0.02, 0.04, 0.00, -0.03],
            "label_defined": [True] * 6,
        },
    )
    write_parquet(split_panel_path, rows | {"split_bucket": ["train"] * 3 + ["validation"] * 3})
    write_json(run_input_contract_path, {"snapshot_id": "snap", "source_root": {"snapshot_path": snapshot_root.as_posix()}})
    return {
        "sample_panel_path": sample_panel_path,
        "run_input_contract_path": run_input_contract_path,
        "label_panel_path": label_panel_path,
        "split_panel_path": split_panel_path,
        "output_dir": output_dir,
        "workflow_dir": workflow_dir,
    }


def write_request(
    path: Path,
    *,
    audit_path: Path,
    fixture: dict[str, Path],
    requested_enrichment_fields: list[str],
    task_type: str = "clean_baseline_score",
    declared_no_frozen_test_access: bool = True,
) -> None:
    write_json(
        path,
        {
            "task_id": "guarded_clean_baseline_workflow_fixture",
            "consumer_name": "guarded_clean_baseline_workflow_test",
            "task_type": task_type,
            "run_scope": "fixture_trainval_clean_baseline_workflow",
            "requested_enrichment_fields": requested_enrichment_fields,
            "declared_no_frozen_test_access": declared_no_frozen_test_access,
            "declared_conditional_pass": True,
            "requested_layer_status": "conditional_pass",
            "allow_silent_fallback": False,
            "output_audit_path": audit_path.as_posix(),
            "task_payload": {
                "baseline_id": BASELINE_ID,
                "clean_sample_panel_path": fixture["sample_panel_path"].as_posix(),
                "run_input_contract_path": fixture["run_input_contract_path"].as_posix(),
                "output_dir": fixture["output_dir"].as_posix(),
                "workflow_dir": fixture["workflow_dir"].as_posix(),
                "label_panel_path": fixture["label_panel_path"].as_posix(),
                "split_panel_path": fixture["split_panel_path"].as_posix(),
                "attempt_id": "attempt_guarded_workflow_fixture",
                "topk": 2,
            },
        },
    )


def run_workflow(repo_root: Path, request_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(repo_root / SCRIPT_PATH), "--request-json", str(request_path)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_guarded_clean_baseline_workflow_runs_score_and_diagnosis(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    fixture = build_fixture(tmp_path)
    request_path = tmp_path / "workflow_request.json"
    audit_path = tmp_path / "workflow_audit.json"
    write_request(
        request_path,
        audit_path=audit_path,
        fixture=fixture,
        requested_enrichment_fields=[],
    )

    result = run_workflow(repo_root, request_path)

    assert result.returncode == 0, result.stderr
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["workflow_executed"] is True
    assert audit["guardrail_status"] == "pass"
    assert audit["score_builder_invoked"] is True
    assert audit["diagnosis_invoked"] is True
    assert audit["portfolio_ran"] is False
    assert audit["formal_metrics_generated"] is False
    assert Path(audit["score_artifact_paths"]["score_output_path"]).exists()
    assert Path(audit["diagnosis_artifact_paths"]["diagnosis_audit_path"]).exists()


def test_guarded_clean_baseline_workflow_blocks_before_artifacts(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    fixture = build_fixture(tmp_path)
    request_path = tmp_path / "workflow_request.json"
    audit_path = tmp_path / "workflow_audit.json"
    write_request(
        request_path,
        audit_path=audit_path,
        fixture=fixture,
        requested_enrichment_fields=["listing_age_trading_days"],
    )

    result = run_workflow(repo_root, request_path)

    assert result.returncode != 0
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["workflow_executed"] is False
    assert audit["score_builder_invoked"] is False
    assert audit["diagnosis_invoked"] is False
    assert not (fixture["output_dir"] / "model_scores_D0.parquet").exists()
    assert not (fixture["workflow_dir"] / "model_layer_diagnosis_audit.json").exists()


def test_guarded_clean_baseline_workflow_blocks_portfolio_task(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    fixture = build_fixture(tmp_path)
    request_path = tmp_path / "workflow_request.json"
    audit_path = tmp_path / "workflow_audit.json"
    write_request(
        request_path,
        audit_path=audit_path,
        fixture=fixture,
        requested_enrichment_fields=[],
        task_type="portfolio",
    )

    result = run_workflow(repo_root, request_path)

    assert result.returncode != 0
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["score_builder_invoked"] is False
    assert audit["diagnosis_invoked"] is False
    assert audit["blocked_reason"] == "workflow_requires_task_type_clean_baseline_score"


def test_guarded_clean_baseline_workflow_blocks_frozen_test_access_false_required(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    fixture = build_fixture(tmp_path)
    request_path = tmp_path / "workflow_request.json"
    audit_path = tmp_path / "workflow_audit.json"
    write_request(
        request_path,
        audit_path=audit_path,
        fixture=fixture,
        requested_enrichment_fields=[],
        declared_no_frozen_test_access=False,
    )

    result = run_workflow(repo_root, request_path)

    assert result.returncode != 0
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["score_builder_invoked"] is False
    assert audit["diagnosis_invoked"] is False
    assert "declared_no_frozen_test_access must be true" in audit["blocked_reason"]
