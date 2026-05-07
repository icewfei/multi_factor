from __future__ import annotations

from conftest import read_text


def test_execution_state_rows_are_counted_from_execution_table() -> None:
    script_text = read_text("scripts/build_run_state_skeleton.py")

    assert "COUNT(*) AS ranking_rows" in script_text
    assert "FROM ranking_state_daily_t" in script_text
    assert "COUNT(*) AS execution_state_rows" in script_text
    assert "FROM execution_state_daily_t" in script_text


def test_run_state_audit_records_execution_row_mismatch_guardrails() -> None:
    script_text = read_text("scripts/build_run_state_skeleton.py")

    assert '"execution_state_row_mismatch"' in script_text
    assert '"execution_state_missing_rows"' in script_text
    assert "execution_state_daily row count does not match ranking_state_daily_t" in script_text
    assert "execution_state_daily row count mismatch versus ranking_state_daily_t." in script_text
