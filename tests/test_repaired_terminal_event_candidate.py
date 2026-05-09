from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

from conftest import REPO_ROOT, load_json


SCRIPT_PATH = "scripts/build_repaired_terminal_event_candidate.py"
SCHEMA_PATH = "schemas/repaired_terminal_event_candidate.schema.json"


def test_candidate_builder_filters_only_approved_rows(tmp_path: Path) -> None:
    approval_audit = {
        "audit_status": "terminal_last_tradable_close_approval_audit_only",
        "contract_ref": "contracts/terminal_exit_policy.v1.json",
        "approval_policy_version": "terminal_exit_policy_v1",
        "summary": {
            "total_rows": 2,
            "candidate_rows_count": 1,
            "approval_gate_passed_count": 1,
            "approval_gate_failed_count": 1,
            "still_hard_blocker_count": 2,
            "zero_recovery_approved_count": 0,
            "terminal_event_bridge_required_count": 1,
            "declared_last_tradable_date_suspended_count": 1,
            "degraded_terminal_source_with_auditable_bars_count": 1,
        },
        "rows": [
            {
                "snapshot_id": "snap",
                "instrument": "AAA.SZ",
                "signal_date": "20210101",
                "entry_date": "20210104",
                "planned_exit_date": "20210111",
                "terminal_event_date": "20210110",
                "terminal_event_type": "delist",
                "terminal_exit_pricing_method": "terminal_event_bridge_required",
                "approval_origin_case": "terminal_event_bridge_required",
                "approval_evidence_case": "declared_last_tradable_date_suspended",
                "approval_gate_passed": True,
                "approved_for_repaired_terminal_event_candidate": True,
                "candidate_target_state": "repaired_terminal_event_candidate",
                "approved_terminal_pricing_path": "terminal_priced_last_tradable_close",
                "declared_last_tradable_date": "20210108",
                "candidate_pricing_date": "20210107",
                "candidate_last_tradable_close": 10.0,
                "candidate_adj_factor": 1.05,
                "candidate_volume": 50000.0,
                "terminal_event_source_degraded_flag": True,
                "terminal_exit_approximation_flag": True,
                "source_repair_flag": True,
                "terminal_event_bridge_required_flag": True,
                "required_candidate_flags": [
                    "terminal_event_source_degraded_flag",
                    "terminal_exit_approximation_flag",
                    "source_repair_flag",
                    "terminal_event_bridge_required",
                ],
                "zero_recovery_approved": False,
                "still_hard_blocker": True,
                "approval_gate_failure_reason": None,
                "required_next_step": "Execution path must price upstream.",
                "blocking_reasons": [],
            },
            {
                "snapshot_id": "snap",
                "instrument": "BBB.SZ",
                "signal_date": "20210102",
                "entry_date": "20210105",
                "planned_exit_date": "20210112",
                "terminal_event_date": "20210111",
                "terminal_event_type": "delist",
                "terminal_exit_pricing_method": "no_terminal_pricing_source",
                "approval_origin_case": "no_terminal_pricing_source",
                "approval_evidence_case": "degraded_terminal_source_with_auditable_bars",
                "approval_gate_passed": False,
                "approved_for_repaired_terminal_event_candidate": False,
                "candidate_target_state": None,
                "approved_terminal_pricing_path": None,
                "declared_last_tradable_date": "20210111",
                "candidate_pricing_date": None,
                "candidate_last_tradable_close": None,
                "candidate_adj_factor": None,
                "candidate_volume": None,
                "terminal_event_source_degraded_flag": True,
                "terminal_exit_approximation_flag": False,
                "source_repair_flag": True,
                "terminal_event_bridge_required_flag": False,
                "required_candidate_flags": [
                    "terminal_event_source_degraded_flag",
                    "source_repair_flag",
                ],
                "zero_recovery_approved": False,
                "still_hard_blocker": True,
                "approval_gate_failure_reason": "missing_declared_last_tradable_bar",
                "required_next_step": "Remain blocked.",
                "blocking_reasons": ["missing bar"],
            },
        ],
        "notes": [],
    }
    approval_path = tmp_path / "approval_audit.json"
    approval_path.write_text(json.dumps(approval_audit, indent=2) + "\n", encoding="utf-8")
    output_path = tmp_path / "candidate.json"

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / SCRIPT_PATH),
            "--approval-audit",
            str(approval_path),
            "--output",
            str(output_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    schema = load_json(SCHEMA_PATH)
    jsonschema.validate(payload, schema)

    assert payload["artifact_status"] == "repaired_terminal_event_candidate_only"
    assert payload["summary"]["candidate_rows_count"] == 1
    assert payload["summary"]["still_hard_blocker_count"] == 1
    assert payload["summary"]["priced_rows_count"] == 0
    assert len(payload["rows"]) == 1
    row = payload["rows"][0]
    assert row["instrument"] == "AAA.SZ"
    assert row["terminal_event_bridge_required_flag"] is True
    assert row["still_hard_blocker"] is True
