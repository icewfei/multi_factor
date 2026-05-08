from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import REPO_ROOT, load_json

SCRIPT_PATH = "scripts/audit_terminal_last_tradable_close.py"
DIAGNOSIS_PATH = "/private/tmp/confirmed5_execution_path_unresolved_exit_diagnosis.json"


@pytest.fixture
def audit_output(tmp_path: Path) -> dict:
    output_path = tmp_path / "audit.json"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / SCRIPT_PATH),
            "--diagnosis-json", DIAGNOSIS_PATH,
            "--output", str(output_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"Script failed: {result.stderr}"
    return json.loads(output_path.read_text(encoding="utf-8"))


def test_audit_output_is_valid_json(audit_output: dict) -> None:
    assert audit_output["audit_status"] == "last_tradable_close_audit_only"
    assert audit_output["total_terminal_event_unpriced_rows"] == 10


def test_only_terminal_event_unpriced_rows_audited(audit_output: dict) -> None:
    for row in audit_output["rows"]:
        assert "exit_unresolved" not in row.get("blocker_category", "")


def test_zero_recovery_not_enabled(audit_output: dict) -> None:
    assert "zero_recovery" not in audit_output["audit_status"].lower()


def test_no_actual_exit_date_backfilled(audit_output: dict) -> None:
    for row in audit_output["rows"]:
        assert "actual_exit_date" not in row or row.get("actual_exit_date") is None


def test_all_rows_have_can_price_with_last_tradable_close(audit_output: dict) -> None:
    for row in audit_output["rows"]:
        assert "can_price_with_last_tradable_close" in row
        assert isinstance(row["can_price_with_last_tradable_close"], bool)


def test_all_rows_have_last_tradable_close_auditable(audit_output: dict) -> None:
    for row in audit_output["rows"]:
        assert "last_tradable_close_auditable" in row
        assert isinstance(row["last_tradable_close_auditable"], bool)


def test_all_rows_have_blocking_reasons(audit_output: dict) -> None:
    for row in audit_output["rows"]:
        assert "blocking_reasons" in row
        assert isinstance(row["blocking_reasons"], list)
        if not row["can_price_with_last_tradable_close"]:
            assert len(row["blocking_reasons"]) > 0


def test_all_rows_have_contract_degraded_flag(audit_output: dict) -> None:
    for row in audit_output["rows"]:
        assert "contract_degraded_flag" in row
        if row.get("raw_close") is not None:
            assert row["contract_degraded_flag"] is True


def test_no_row_has_can_price_true(audit_output: dict) -> None:
    for row in audit_output["rows"]:
        assert row["can_price_with_last_tradable_close"] is False


def test_all_rows_have_last_tradable_date(audit_output: dict) -> None:
    for row in audit_output["rows"]:
        assert row.get("last_tradable_date_from_terminal_source") is not None


def test_summary_counts_are_consistent(audit_output: dict) -> None:
    total = audit_output["total_terminal_event_unpriced_rows"]
    assert audit_output["auditable_count"] + audit_output["not_auditable_count"] == total
    assert audit_output["not_auditable_count"] == 10
    assert audit_output["auditable_count"] == 0


def test_rows_have_audit_source_information(audit_output: dict) -> None:
    rows_with_close = [r for r in audit_output["rows"] if r.get("raw_close") is not None]
    assert len(rows_with_close) == audit_output["summary"]["rows_with_close_on_declared_ltd"]
    for row in rows_with_close:
        assert row["close_source"] == "vw_bars_daily"
        assert row["close_source_auditable"] is True


def test_suspended_rows_have_actual_last_trade_investigation(audit_output: dict) -> None:
    suspended = [
        r for r in audit_output["rows"]
        if r.get("declared_ltd_is_suspended") or r.get("declared_ltd_is_no_trade")
    ]
    assert len(suspended) == 6
    for row in suspended:
        assert row.get("actual_last_trade_date_in_bars") is not None
        assert row.get("actual_last_trade_date_close_available") is True
