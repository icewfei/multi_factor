from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


SCRIPT_PATH = "scripts/run_guarded_clean_baseline_score_task.py"
BASELINE_ID = "clean_equal_weight_random_eligible_baseline_v1"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_sample_panel(path: Path) -> None:
    pq.write_table(
        pa.table(
            {
                "snapshot_id": ["snap", "snap", "snap"],
                "instrument": ["AAA.SZ", "BBB.SZ", "CCC.SZ"],
                "signal_date": ["20210121", "20210121", "20210121"],
                "ranking_eligible_D0": [True, True, True],
            }
        ),
        path,
    )


def write_run_input_contract(path: Path, snapshot_root: Path) -> None:
    write_json(path, {"snapshot_id": "snap", "source_root": {"snapshot_path": snapshot_root.as_posix()}})


def write_request(
    path: Path,
    *,
    audit_path: Path,
    requested_enrichment_fields: list[str],
    sample_panel_path: Path,
    run_input_contract_path: Path,
    output_dir: Path,
    task_type: str = "clean_baseline_score",
) -> None:
    write_json(
        path,
        {
            "task_id": "guarded_clean_baseline_score_fixture",
            "consumer_name": "guarded_clean_baseline_score_wrapper_test",
            "task_type": task_type,
            "run_scope": "fixture_only_no_market_data",
            "requested_enrichment_fields": requested_enrichment_fields,
            "declared_no_frozen_test_access": True,
            "declared_conditional_pass": True,
            "requested_layer_status": "conditional_pass",
            "allow_silent_fallback": False,
            "output_audit_path": audit_path.as_posix(),
            "task_payload": {
                "baseline_id": BASELINE_ID,
                "clean_sample_panel_path": sample_panel_path.as_posix(),
                "run_input_contract_path": run_input_contract_path.as_posix(),
                "output_dir": output_dir.as_posix(),
                "attempt_id": "attempt_guarded_score_fixture",
            },
        },
    )


def build_fixture(tmp_path: Path) -> dict[str, Path]:
    sample_panel_path = tmp_path / "clean_sample_panel.parquet"
    snapshot_root = tmp_path / "snapshot"
    run_input_contract_path = tmp_path / "run_input_contract.json"
    output_dir = tmp_path / "score_output"
    write_sample_panel(sample_panel_path)
    snapshot_root.mkdir(parents=True, exist_ok=True)
    write_run_input_contract(run_input_contract_path, snapshot_root)
    return {
        "sample_panel_path": sample_panel_path,
        "run_input_contract_path": run_input_contract_path,
        "output_dir": output_dir,
    }


def run_wrapper(repo_root: Path, request_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(repo_root / SCRIPT_PATH), "--request-json", str(request_path)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_guarded_clean_baseline_score_wrapper_invokes_real_builder_after_guardrail(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    fixture = build_fixture(tmp_path)
    request_path = tmp_path / "request.json"
    audit_path = tmp_path / "audit.json"
    write_request(
        request_path,
        audit_path=audit_path,
        requested_enrichment_fields=[],
        **fixture,
    )

    result = run_wrapper(repo_root, request_path)

    assert result.returncode == 0, result.stderr
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["task_executed"] is True
    assert audit["guardrail_status"] == "pass"
    assert audit["builder_invoked"] is True
    assert audit["baseline_id"] == BASELINE_ID
    assert audit["portfolio_ran"] is False
    assert audit["formal_metrics_generated"] is False
    assert Path(audit["output_paths"]["score_output_path"]).exists()
    assert Path(audit["output_paths"]["score_audit_path"]).exists()


def test_guarded_clean_baseline_score_wrapper_blocks_before_builder(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    fixture = build_fixture(tmp_path)
    request_path = tmp_path / "request.json"
    audit_path = tmp_path / "audit.json"
    write_request(
        request_path,
        audit_path=audit_path,
        requested_enrichment_fields=["listing_age_trading_days"],
        **fixture,
    )

    result = run_wrapper(repo_root, request_path)

    assert result.returncode != 0
    assert audit_path.exists()
    assert not (fixture["output_dir"] / "model_scores_D0.parquet").exists()
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["task_executed"] is False
    assert audit["builder_invoked"] is False
    assert audit["next_use_guardrail_audit"]["blocked_fields_requested"] == ["listing_age_trading_days"]
