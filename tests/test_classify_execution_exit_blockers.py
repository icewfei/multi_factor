from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import REPO_ROOT, load_json


SCRIPT_PATH = "scripts/classify_execution_exit_blockers.py"
POLICY_PATH = "contracts/terminal_exit_policy.v1.json"
DIAGNOSIS_PATH = "/private/tmp/confirmed5_execution_path_unresolved_exit_diagnosis.json"


@pytest.fixture
def policy() -> dict:
    return load_json(POLICY_PATH)


@pytest.fixture
def diagnose_20_rows() -> dict:
    return json.loads(Path(DIAGNOSIS_PATH).read_text(encoding="utf-8"))


@pytest.fixture
def classification_output(tmp_path: Path) -> dict:
    output_path = tmp_path / "classification.json"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / SCRIPT_PATH),
            "--diagnosis-json", DIAGNOSIS_PATH,
            "--policy-contract", str(REPO_ROOT / POLICY_PATH),
            "--output", str(output_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"Script failed: {result.stderr}"
    return json.loads(output_path.read_text(encoding="utf-8"))


def test_script_runs_and_outputs_valid_json(classification_output: dict) -> None:
    assert classification_output["summary"]["total_rows"] == 20
    assert "classifications" in classification_output


def test_all_20_rows_are_hard_blockers(classification_output: dict) -> None:
    assert classification_output["summary"]["hard_blocker_count"] == 20
    for c in classification_output["classifications"]:
        assert c["is_hard_blocker"] is True


def test_exactly_10_terminal_event_unpriced_and_10_exit_unresolved(classification_output: dict) -> None:
    counts = classification_output["summary"]["blocker_category_counts"]
    assert counts["terminal_event_unpriced"] == 10
    assert counts["exit_unresolved"] == 10
    assert "calendar_insufficient" not in counts


def test_terminal_event_unpriced_rows_have_terminal_flag_and_delist(classification_output: dict) -> None:
    tep = [c for c in classification_output["classifications"] if c["blocker_category"] == "terminal_event_unpriced"]
    assert len(tep) == 10
    for c in tep:
        assert c["terminal_event_flag"] is True
        assert c["terminal_event_type"] == "delist"
        assert c["terminal_exit_pricing_method"] == "no_terminal_pricing_source"


def test_exit_unresolved_rows_have_no_terminal_event(classification_output: dict) -> None:
    eu = [c for c in classification_output["classifications"] if c["blocker_category"] == "exit_unresolved"]
    assert len(eu) == 10
    for c in eu:
        assert c["terminal_event_flag"] is False
        assert c["terminal_event_type"] is None
        assert c["terminal_exit_pricing_method"] is None


def test_no_row_auto_priceable_under_policy(classification_output: dict) -> None:
    assert classification_output["judgment"]["any_row_auto_priceable_under_policy"] is False
    assert classification_output["judgment"]["auto_priceable_rows"] == []


def test_upstream_execution_path_terminal_pricing_still_needed(classification_output: dict) -> None:
    assert classification_output["judgment"]["upstream_execution_path_terminal_pricing_still_needed"] is True
    assert len(classification_output["judgment"]["upstream_impl_needed_reason"]) > 0


def test_hierarchy_assessment_no_cash_settlement_available(classification_output: dict) -> None:
    for c in classification_output["classifications"]:
        assert c["hierarchy_assessment"]["cash_settlement_applicable"] is False


def test_all_terminal_event_unpriced_have_last_tradable_close_pending_audit(classification_output: dict) -> None:
    tep = [c for c in classification_output["classifications"] if c["blocker_category"] == "terminal_event_unpriced"]
    for c in tep:
        assert c["hierarchy_assessment"]["best_available_pricing_layer"] == "last_tradable_close_pending_audit"
        assert c["hierarchy_assessment"]["last_tradable_close_applicable"] is True
        assert "degraded" in c["hierarchy_assessment"]["last_tradable_close_blocked_reason"]


def test_blocker_reasons_align_with_policy_contract(classification_output: dict, policy: dict) -> None:
    policy_reasons = {
        "terminal_event_unpriced": policy["hard_blocker_rules"]["terminal_event_unpriced"]["reason"],
        "exit_unresolved": policy["hard_blocker_rules"]["exit_unresolved"]["reason"],
    }
    for c in classification_output["classifications"]:
        assert c["blocker_reason"] == policy_reasons[c["blocker_category"]]


def test_zero_recovery_not_applicable_to_exit_unresolved(classification_output: dict) -> None:
    eu = [c for c in classification_output["classifications"] if c["blocker_category"] == "exit_unresolved"]
    for c in eu:
        assert c["hierarchy_assessment"]["zero_recovery_applicable"] is False
        assert c["hierarchy_assessment"]["best_available_pricing_layer"] is None


def test_each_classification_has_required_keys(classification_output: dict) -> None:
    required = {
        "instrument", "signal_date", "entry_date", "planned_exit_date",
        "execution_path_status", "terminal_event_flag", "terminal_event_type",
        "terminal_event_date", "terminal_exit_pricing_method",
        "blocker_category", "is_hard_blocker", "blocker_reason", "hierarchy_assessment",
    }
    for c in classification_output["classifications"]:
        assert required <= set(c.keys())
