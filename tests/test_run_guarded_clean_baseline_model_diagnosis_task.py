from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


SCRIPT_PATH = "scripts/run_guarded_clean_baseline_model_diagnosis_task.py"
BASELINE_ID = "clean_equal_weight_random_eligible_baseline_v1"


def write_parquet(path: Path, payload: dict) -> None:
    pq.write_table(pa.table(payload), path)


def build_fixture(tmp_path: Path) -> dict[str, Path]:
    score_path = tmp_path / "model_scores_D0.parquet"
    label_panel_path = tmp_path / "label_panel.parquet"
    split_panel_path = tmp_path / "split_panel.parquet"
    rows = {
        "snapshot_id": ["snap"] * 8,
        "instrument": ["AAA.SZ", "BBB.SZ", "CCC.SZ", "DDD.SZ"] * 2,
        "signal_date": ["20210104"] * 4 + ["20210105"] * 4,
    }
    write_parquet(
        score_path,
        rows
        | {
            "candidate_scheme_id": [BASELINE_ID] * 8,
            "model_score_D0": [0.0, 0.3, 0.6, 0.9, 0.0, 0.4, 0.5, 0.9],
        },
    )
    write_parquet(
        label_panel_path,
        rows
        | {
            "label_5d_next_open_close": [0.04, 0.02, -0.01, -0.03, 0.03, 0.01, -0.02, -0.04],
            "label_defined": [True] * 8,
        },
    )
    write_parquet(
        split_panel_path,
        rows | {"split_bucket": ["train"] * 4 + ["validation"] * 4},
    )
    return {
        "score_path": score_path,
        "label_panel_path": label_panel_path,
        "split_panel_path": split_panel_path,
    }


def write_request(
    path: Path,
    *,
    audit_path: Path,
    fixture: dict[str, Path],
    requested_enrichment_fields: list[str],
) -> None:
    path.write_text(
        json.dumps(
            {
                "task_id": "guarded_model_diagnosis_fixture",
                "consumer_name": "guarded_model_diagnosis_test",
                "task_type": "diagnostic",
                "run_scope": "fixture_trainval_model_layer_only",
                "requested_enrichment_fields": requested_enrichment_fields,
                "declared_no_frozen_test_access": True,
                "declared_conditional_pass": True,
                "requested_layer_status": "conditional_pass",
                "allow_silent_fallback": False,
                "output_audit_path": audit_path.as_posix(),
                "task_payload": {
                    "baseline_id": BASELINE_ID,
                    "score_path": fixture["score_path"].as_posix(),
                    "label_panel_path": fixture["label_panel_path"].as_posix(),
                    "split_panel_path": fixture["split_panel_path"].as_posix(),
                    "topk": 2,
                },
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def run_task(repo_root: Path, request_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(repo_root / SCRIPT_PATH), "--request-json", str(request_path)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_guarded_model_diagnosis_runs_after_guardrail(repo_root: Path, tmp_path: Path) -> None:
    fixture = build_fixture(tmp_path)
    request_path = tmp_path / "request.json"
    audit_path = tmp_path / "diagnosis_audit.json"
    write_request(
        request_path,
        audit_path=audit_path,
        fixture=fixture,
        requested_enrichment_fields=[],
    )

    result = run_task(repo_root, request_path)

    assert result.returncode == 0, result.stderr
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["diagnosis_invoked"] is True
    assert audit["task_executed"] is True
    assert audit["guardrail_status"] == "pass"
    assert audit["no_frozen_test_access"] is True
    assert audit["portfolio_ran"] is False
    assert audit["formal_metrics_generated"] is False
    assert audit["not_oos"] is True
    metrics = audit["diagnosis_metrics"]["splits"]
    assert metrics["train"]["coverage"]["rows"] == 4
    assert metrics["validation"]["coverage"]["rows"] == 4
    assert "rank_ic" in metrics["train"]
    assert "icir" in metrics["train"]
    assert "top_bottom" in metrics["train"]
    assert "topk_proxy" in metrics["train"]


def test_guarded_model_diagnosis_blocks_before_input_read(repo_root: Path, tmp_path: Path) -> None:
    fixture = build_fixture(tmp_path)
    request_path = tmp_path / "request.json"
    audit_path = tmp_path / "diagnosis_audit.json"
    write_request(
        request_path,
        audit_path=audit_path,
        fixture=fixture,
        requested_enrichment_fields=["listing_age_trading_days"],
    )

    result = run_task(repo_root, request_path)

    assert result.returncode != 0
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["diagnosis_invoked"] is False
    assert audit["task_executed"] is False
    assert audit["next_use_guardrail_audit"]["blocked_fields_requested"] == ["listing_age_trading_days"]
