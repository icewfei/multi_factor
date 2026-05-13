from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


SCRIPT_PATH = "scripts/run_guarded_research_task.py"
BASELINE_ID = "clean_equal_weight_random_eligible_baseline_v1"


def write_request(
    path: Path,
    *,
    audit_path: Path,
    marker_path: Path,
    task_type: str = "diagnostic",
    requested_enrichment_fields: list[str] | None = None,
    declared_no_frozen_test_access: bool = True,
    declared_conditional_pass: bool = True,
    requested_layer_status: str = "conditional_pass",
    allow_silent_fallback: bool = False,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "task_id": f"{task_type}_fixture_task",
        "consumer_name": "guarded_runner_unit_test",
        "task_type": task_type,
        "run_scope": "fixture_only_no_market_data",
        "requested_enrichment_fields": (
            ["is_st", "is_suspended", "entry_buyable", "limit_rule_version"]
            if requested_enrichment_fields is None
            else requested_enrichment_fields
        ),
        "declared_no_frozen_test_access": declared_no_frozen_test_access,
        "declared_conditional_pass": declared_conditional_pass,
        "requested_layer_status": requested_layer_status,
        "allow_silent_fallback": allow_silent_fallback,
        "output_audit_path": audit_path.as_posix(),
        "task_payload": {
            "dispatch_mode": "fixture_noop",
            "marker_path": marker_path.as_posix(),
        },
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def run_runner(repo_root: Path, request_path: Path) -> subprocess.CompletedProcess[str]:
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


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_sample_panel(path: Path) -> None:
    pq.write_table(
        pa.table(
            {
                "snapshot_id": ["snap", "snap"],
                "instrument": ["AAA.SZ", "BBB.SZ"],
                "signal_date": ["20210121", "20210121"],
                "ranking_eligible_D0": [True, True],
            }
        ),
        path,
    )


def build_score_payload_fixture(tmp_path: Path) -> dict[str, str]:
    sample_panel_path = tmp_path / "clean_sample_panel.parquet"
    snapshot_root = tmp_path / "snapshot"
    run_input_contract_path = tmp_path / "run_input_contract.json"
    output_dir = tmp_path / "score_output"
    write_sample_panel(sample_panel_path)
    snapshot_root.mkdir(parents=True, exist_ok=True)
    run_input_contract_path.write_text(
        json.dumps(
            {
                "snapshot_id": "snap",
                "source_root": {"snapshot_path": snapshot_root.as_posix()},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "baseline_id": BASELINE_ID,
        "clean_sample_panel_path": sample_panel_path.as_posix(),
        "run_input_contract_path": run_input_contract_path.as_posix(),
        "output_dir": output_dir.as_posix(),
        "attempt_id": "attempt_guarded_runner_fixture",
    }


def assert_blocked_without_task(repo_root: Path, tmp_path: Path, **overrides) -> dict:
    request_path = tmp_path / "request.json"
    audit_path = tmp_path / "audit.json"
    marker_path = tmp_path / "task_marker.json"
    write_request(request_path, audit_path=audit_path, marker_path=marker_path, **overrides)

    result = run_runner(repo_root, request_path)

    assert result.returncode != 0
    assert audit_path.exists()
    assert not marker_path.exists()
    audit = read_json(audit_path)
    assert audit["task_executed"] is False
    assert audit["blocked_reason"]
    return audit


def test_allowed_diagnostic_request_executes_task(repo_root: Path, tmp_path: Path) -> None:
    request_path = tmp_path / "request.json"
    audit_path = tmp_path / "audit.json"
    marker_path = tmp_path / "task_marker.json"
    write_request(request_path, audit_path=audit_path, marker_path=marker_path)

    result = run_runner(repo_root, request_path)

    assert result.returncode == 0, result.stderr
    audit = read_json(audit_path)
    marker = read_json(marker_path)
    assert audit["task_executed"] is True
    assert audit["task_result"]["dispatch"] == "example_diagnostic"
    assert audit["next_use_guardrail_audit"]["status"] == "pass"
    assert audit["training_performed"] is False
    assert audit["backtest_run"] is False
    assert audit["portfolio_run_executed"] is False
    assert audit["no_frozen_test_access"] is True
    assert marker["dummy_diagnostic_executed"] is True


def test_allowed_clean_baseline_score_empty_fields_executes_dry_dispatch(
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
        task_type="clean_baseline_score",
        requested_enrichment_fields=[],
    )
    request = read_json(request_path)
    request["task_payload"] = build_score_payload_fixture(tmp_path)
    request_path.write_text(json.dumps(request, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    result = run_runner(repo_root, request_path)

    assert result.returncode == 0, result.stderr
    audit = read_json(audit_path)
    assert audit["task_executed"] is True
    assert audit["requested_enrichment_fields"] == []
    assert audit["next_use_guardrail_audit"]["allowed_fields_used"] == []
    assert audit["task_result"]["dispatch"] == "clean_baseline_score_builder"
    assert audit["builder_invoked"] is True
    assert audit["baseline_id"] == BASELINE_ID
    assert Path(audit["output_paths"]["score_output_path"]).exists()


def test_blocked_listing_age_trading_days_does_not_execute_task(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    audit = assert_blocked_without_task(
        repo_root,
        tmp_path,
        requested_enrichment_fields=["listing_age_trading_days"],
    )
    assert audit["next_use_guardrail_audit"]["blocked_fields_requested"] == ["listing_age_trading_days"]


def test_blocked_newly_listed_flag_does_not_execute_task(repo_root: Path, tmp_path: Path) -> None:
    audit = assert_blocked_without_task(
        repo_root,
        tmp_path,
        requested_enrichment_fields=["newly_listed_flag"],
    )
    assert audit["next_use_guardrail_audit"]["blocked_fields_requested"] == ["newly_listed_flag"]


def test_unknown_field_does_not_execute_task(repo_root: Path, tmp_path: Path) -> None:
    audit = assert_blocked_without_task(
        repo_root,
        tmp_path,
        requested_enrichment_fields=["unknown_enrichment_field"],
    )
    assert audit["next_use_guardrail_audit"]["unknown_fields_requested"] == ["unknown_enrichment_field"]


def test_portfolio_task_type_does_not_execute_task(repo_root: Path, tmp_path: Path) -> None:
    audit = assert_blocked_without_task(repo_root, tmp_path, task_type="portfolio")
    assert "intended_use_not_allowed_by_policy: portfolio" in audit["blocked_reason"]
    assert audit["portfolio_run_executed"] is False


def test_missing_conditional_disclosure_does_not_execute_task(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    audit = assert_blocked_without_task(repo_root, tmp_path, declared_conditional_pass=False)
    assert "declared_conditional_pass must be true" in audit["blocked_reason"]


def test_missing_conditional_disclosure_field_does_not_execute_task(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    request_path = tmp_path / "request.json"
    audit_path = tmp_path / "audit.json"
    marker_path = tmp_path / "task_marker.json"
    request = write_request(request_path, audit_path=audit_path, marker_path=marker_path)
    del request["declared_conditional_pass"]
    request_path.write_text(json.dumps(request, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    result = run_runner(repo_root, request_path)

    assert result.returncode != 0
    assert audit_path.exists()
    assert not marker_path.exists()
    audit = read_json(audit_path)
    assert audit["task_executed"] is False
    assert audit["request_validation"]["status"] == "blocked"
    assert "declared_conditional_pass" in audit["blocked_reason"]


def test_allow_silent_fallback_true_does_not_execute_task(repo_root: Path, tmp_path: Path) -> None:
    audit = assert_blocked_without_task(repo_root, tmp_path, allow_silent_fallback=True)
    assert "allow_silent_fallback must be false" in audit["blocked_reason"]


def test_audit_json_fields_complete(repo_root: Path, tmp_path: Path) -> None:
    request_path = tmp_path / "request.json"
    audit_path = tmp_path / "audit.json"
    marker_path = tmp_path / "task_marker.json"
    write_request(request_path, audit_path=audit_path, marker_path=marker_path)

    result = run_runner(repo_root, request_path)

    assert result.returncode == 0, result.stderr
    audit = read_json(audit_path)
    assert {
        "request_validation",
        "next_use_guardrail_audit",
        "task_executed",
        "blocked_reason",
        "no_frozen_test_access",
        "training_performed",
        "backtest_run",
        "portfolio_run_executed",
        "formal_metrics_generated",
        "holdings_generated",
        "backtest_daily_generated",
    } <= set(audit)
    assert audit["request_validation"]["status"] == "pass"
    assert audit["next_use_guardrail_audit"]["required_disclosure"]
    assert audit["formal_metrics_generated"] is False
