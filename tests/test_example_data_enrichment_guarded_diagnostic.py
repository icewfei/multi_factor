from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = "scripts/example_data_enrichment_guarded_diagnostic.py"


def write_request(path: Path, *, requested_fields: list[str], intended_use: str = "diagnostic") -> None:
    path.write_text(
        json.dumps(
            {
                "requested_fields": requested_fields,
                "intended_use": intended_use,
                "consumer_name": "example_guarded_diagnostic_test",
                "run_scope": "fixture_only",
                "declared_no_frozen_test_access": True,
                "declared_conditional_pass": True,
                "requested_layer_status": "conditional_pass",
                "allow_silent_fallback": False,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def run_script(repo_root: Path, tmp_path: Path, request_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(repo_root / SCRIPT_PATH),
            "--request-json",
            str(request_path),
            "--next-use-audit-path",
            str(tmp_path / "next_use_audit.json"),
            "--output-json",
            str(tmp_path / "diagnostic.json"),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_example_guarded_diagnostic_runs_after_allowed_guardrail(repo_root: Path, tmp_path: Path) -> None:
    request_path = tmp_path / "allowed_request.json"
    write_request(
        request_path,
        requested_fields=["is_st", "is_suspended", "entry_buyable", "limit_rule_version"],
    )

    result = run_script(repo_root, tmp_path, request_path)

    assert result.returncode == 0, result.stderr
    payload = json.loads((tmp_path / "diagnostic.json").read_text(encoding="utf-8"))
    audit = json.loads((tmp_path / "next_use_audit.json").read_text(encoding="utf-8"))
    assert payload["dummy_diagnostic_executed"] is True
    assert payload["training_performed"] is False
    assert payload["portfolio_run_executed"] is False
    assert payload["frozen_test_accessed"] is False
    assert audit["status"] == "pass"
    assert audit["allowed_fields_used"] == ["is_st", "is_suspended", "entry_buyable", "limit_rule_version"]


def test_example_guarded_diagnostic_blocks_before_dummy_diagnostic(repo_root: Path, tmp_path: Path) -> None:
    request_path = tmp_path / "blocked_request.json"
    write_request(request_path, requested_fields=["listing_age_trading_days"])

    result = run_script(repo_root, tmp_path, request_path)

    assert result.returncode != 0
    assert "blocked_fields_requested: listing_age_trading_days" in result.stderr
    assert not (tmp_path / "diagnostic.json").exists()
    audit = json.loads((tmp_path / "next_use_audit.json").read_text(encoding="utf-8"))
    assert audit["status"] == "blocked"
    assert audit["blocked_fields_requested"] == ["listing_age_trading_days"]
