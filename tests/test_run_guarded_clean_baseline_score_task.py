from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = "scripts/run_guarded_clean_baseline_score_task.py"


def write_request(
    path: Path,
    *,
    audit_path: Path,
    marker_path: Path,
    requested_enrichment_fields: list[str],
    task_type: str = "clean_baseline_score",
) -> None:
    path.write_text(
        json.dumps(
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
                    "dispatch_mode": "fixture_noop",
                    "marker_path": marker_path.as_posix(),
                },
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def run_wrapper(repo_root: Path, request_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(repo_root / SCRIPT_PATH),
            "--request-json",
            str(request_path),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_guarded_clean_baseline_score_wrapper_allows_empty_fields(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    request_path = tmp_path / "request.json"
    audit_path = tmp_path / "audit.json"
    marker_path = tmp_path / "task_marker.json"
    write_request(
        request_path,
        audit_path=audit_path,
        marker_path=marker_path,
        requested_enrichment_fields=[],
    )

    result = run_wrapper(repo_root, request_path)

    assert result.returncode == 0, result.stderr
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    assert audit["task_executed"] is True
    assert audit["task_result"]["dispatch"] == "clean_baseline_score_dry_noop"
    assert marker["builder_invoked"] is False


def test_guarded_clean_baseline_score_wrapper_blocks_before_builder_marker(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    request_path = tmp_path / "request.json"
    audit_path = tmp_path / "audit.json"
    marker_path = tmp_path / "task_marker.json"
    write_request(
        request_path,
        audit_path=audit_path,
        marker_path=marker_path,
        requested_enrichment_fields=["listing_age_trading_days"],
    )

    result = run_wrapper(repo_root, request_path)

    assert result.returncode != 0
    assert audit_path.exists()
    assert not marker_path.exists()
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["task_executed"] is False
    assert audit["next_use_guardrail_audit"]["blocked_fields_requested"] == ["listing_age_trading_days"]
