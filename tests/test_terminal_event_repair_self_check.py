from __future__ import annotations

import json
import uuid
from pathlib import Path

import duckdb

from conftest import load_module


def _load_self_check_module():
    module_name = f"run_system_self_check_terminal_repair_{uuid.uuid4().hex}"
    return load_module("scripts/run_system_self_check.py", module_name)


def _write_repair_audit_json(
    path: Path,
    *,
    still_hard_blocker_count: int,
    can_emit_terminal_priced_last_tradable_close_count: int,
    unclassifiable_excluded_count: int,
) -> None:
    payload = {
        "audit_status": "terminal_event_source_repair_audit_only",
        "contract_ref": "contracts/terminal_event_source_repair_plan.v1.json",
        "repair_policy_version": "terminal_event_source_repair_plan_v1",
        "summary": {
            "total_rows": still_hard_blocker_count,
            "degraded_terminal_source_with_auditable_bars_count": 0,
            "declared_last_tradable_date_suspended_count": 0,
            "still_hard_blocker_count": still_hard_blocker_count,
            "can_emit_terminal_priced_last_tradable_close_count": can_emit_terminal_priced_last_tradable_close_count,
            "unclassifiable_excluded_count": unclassifiable_excluded_count,
        },
        "rows": [],
        "notes": [],
    }
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def _write_execution_resolution_inputs(
    tmp_path: Path,
    *,
    project_rows: list[tuple],
    execution_rows: list[tuple],
) -> tuple[Path, Path]:
    project_execution_panel = tmp_path / "project_execution_panel.parquet"
    execution_state_daily = tmp_path / "execution_state_daily.parquet"
    con = duckdb.connect()
    try:
        con.execute(
            """
            CREATE TEMP TABLE project_execution_panel_t (
                snapshot_id VARCHAR,
                instrument VARCHAR,
                signal_date VARCHAR,
                actual_exit_date VARCHAR,
                actual_sell_price DOUBLE,
                execution_delayed_realized_return DOUBLE,
                execution_path_status VARCHAR
            )
            """
        )
        con.executemany(
            "INSERT INTO project_execution_panel_t VALUES (?, ?, ?, ?, ?, ?, ?)",
            project_rows,
        )
        con.execute(
            f"""
            COPY project_execution_panel_t TO '{project_execution_panel.as_posix()}'
            (FORMAT PARQUET)
            """
        )

        con.execute(
            """
            CREATE TEMP TABLE execution_state_daily_t (
                snapshot_id VARCHAR,
                instrument VARCHAR,
                signal_date VARCHAR,
                backtest_executable BOOLEAN
            )
            """
        )
        con.executemany(
            "INSERT INTO execution_state_daily_t VALUES (?, ?, ?, ?)",
            execution_rows,
        )
        con.execute(
            f"""
            COPY execution_state_daily_t TO '{execution_state_daily.as_posix()}'
            (FORMAT PARQUET)
            """
        )
    finally:
        con.close()
    return project_execution_panel, execution_state_daily


def _write_approval_audit_json(path: Path, *, candidate_rows_count: int, still_hard_blocker_count: int) -> None:
    payload = {
        "audit_status": "terminal_last_tradable_close_approval_audit_only",
        "approval_policy_version": "terminal_exit_policy_v1",
        "summary": {
            "candidate_rows_count": candidate_rows_count,
            "still_hard_blocker_count": still_hard_blocker_count,
            "approval_gate_passed_count": candidate_rows_count,
            "approval_gate_failed_count": 0,
        },
        "rows": [],
        "notes": [],
    }
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def _write_candidate_json(path: Path, *, candidate_rows_count: int, still_hard_blocker_count: int) -> None:
    payload = {
        "artifact_status": "repaired_terminal_event_candidate_only",
        "pricing_policy_version": "terminal_exit_policy_v1",
        "summary": {
            "candidate_rows_count": candidate_rows_count,
            "still_hard_blocker_count": still_hard_blocker_count,
            "priced_rows_count": 0,
        },
        "rows": [],
        "notes": [],
    }
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def test_self_check_reports_missing_terminal_event_repair_audit(tmp_path: Path) -> None:
    module = _load_self_check_module()

    result = module.inspect_terminal_event_repair_audit(tmp_path / "terminal_event_repair_audit.json")

    assert result["present"] is False
    assert result["status"] == "missing"
    assert result["pass_flag"] is False
    assert result["portfolio_resolution_allowed"] is False


def test_self_check_reports_terminal_event_repair_blocked(tmp_path: Path) -> None:
    module = _load_self_check_module()
    audit_path = tmp_path / "terminal_event_repair_audit.json"
    _write_repair_audit_json(
        audit_path,
        still_hard_blocker_count=462,
        can_emit_terminal_priced_last_tradable_close_count=0,
        unclassifiable_excluded_count=0,
    )

    result = module.inspect_terminal_event_repair_audit(audit_path)

    assert result["present"] is True
    assert result["status"] == "terminal_event_repair_blocked"
    assert result["still_hard_blocker_count"] == 462
    assert result["pass_flag"] is False
    assert result["hard_blocker_present_flag"] is True


def test_self_check_does_not_report_portfolio_recoverable_when_can_emit_zero(tmp_path: Path) -> None:
    module = _load_self_check_module()
    audit_path = tmp_path / "terminal_event_repair_audit.json"
    _write_repair_audit_json(
        audit_path,
        still_hard_blocker_count=0,
        can_emit_terminal_priced_last_tradable_close_count=0,
        unclassifiable_excluded_count=3,
    )

    result = module.inspect_terminal_event_repair_audit(audit_path)

    assert result["present"] is True
    assert result["can_emit_terminal_priced_last_tradable_close_count"] == 0
    assert result["requires_upstream_execution_path_implementation"] is False
    assert result["portfolio_resolution_allowed"] is False


def test_execution_exit_resolution_reports_fully_resolved(tmp_path: Path) -> None:
    module = _load_self_check_module()
    project_execution_panel, execution_state_daily = _write_execution_resolution_inputs(
        tmp_path,
        project_rows=[
            ("snap", "AAA.SZ", "20210101", "20210107", 10.5, 0.1025, "terminal_priced_last_tradable_close"),
            ("snap", "BBB.SZ", "20210102", "20210107", 9.5, -0.0025, "terminal_priced_last_tradable_close"),
        ],
        execution_rows=[
            ("snap", "AAA.SZ", "20210101", True),
            ("snap", "BBB.SZ", "20210102", True),
        ],
    )
    approval_path = tmp_path / "approval.json"
    candidate_path = tmp_path / "candidate.json"
    _write_approval_audit_json(approval_path, candidate_rows_count=2, still_hard_blocker_count=2)
    _write_candidate_json(candidate_path, candidate_rows_count=2, still_hard_blocker_count=2)

    result = module.inspect_execution_exit_resolution(
        project_execution_panel,
        execution_state_daily,
        repaired_terminal_event_candidate_path=candidate_path,
        terminal_last_tradable_approval_audit_path=approval_path,
    )

    assert result["status"] == "fully_resolved"
    assert result["pass_flag"] is True
    assert result["portfolio_recovery_allowed"] is True
    assert result["backtest_executable_rows"] == 2
    assert result["missing_actual_exit_date_rows"] == 0
    assert result["missing_actual_sell_price_rows"] == 0
    assert result["missing_realized_return_rows"] == 0
    assert result["hard_blocker_rows"] == 0
    assert result["terminal_priced_last_tradable_close_rows"] == 2
    assert result["approval_candidate_rows_count"] == 2
    assert result["repaired_candidate_rows_count"] == 2


def test_execution_exit_resolution_reports_partially_resolved(tmp_path: Path) -> None:
    module = _load_self_check_module()
    project_execution_panel, execution_state_daily = _write_execution_resolution_inputs(
        tmp_path,
        project_rows=[
            ("snap", "AAA.SZ", "20210101", "20210107", 10.5, 0.1025, "terminal_priced_last_tradable_close"),
            ("snap", "BBB.SZ", "20210102", None, None, None, "terminal_event_unpriced"),
        ],
        execution_rows=[
            ("snap", "AAA.SZ", "20210101", True),
            ("snap", "BBB.SZ", "20210102", True),
        ],
    )
    approval_path = tmp_path / "approval.json"
    candidate_path = tmp_path / "candidate.json"
    _write_approval_audit_json(approval_path, candidate_rows_count=2, still_hard_blocker_count=2)
    _write_candidate_json(candidate_path, candidate_rows_count=2, still_hard_blocker_count=2)

    result = module.inspect_execution_exit_resolution(
        project_execution_panel,
        execution_state_daily,
        repaired_terminal_event_candidate_path=candidate_path,
        terminal_last_tradable_approval_audit_path=approval_path,
    )

    assert result["status"] == "partially_resolved"
    assert result["pass_flag"] is False
    assert result["portfolio_recovery_allowed"] is False
    assert result["missing_actual_exit_date_rows"] == 1
    assert result["missing_actual_sell_price_rows"] == 1
    assert result["missing_realized_return_rows"] == 1
    assert result["hard_blocker_rows"] == 1
    assert result["hard_blocker_status_counts"] == {"terminal_event_unpriced": 1}
    assert result["terminal_priced_last_tradable_close_rows"] == 1


def test_execution_exit_resolution_reports_still_blocked_without_candidate_progress(tmp_path: Path) -> None:
    module = _load_self_check_module()
    project_execution_panel, execution_state_daily = _write_execution_resolution_inputs(
        tmp_path,
        project_rows=[
            ("snap", "AAA.SZ", "20210101", None, None, None, "terminal_event_unpriced"),
            ("snap", "BBB.SZ", "20210102", None, None, None, "exit_unresolved"),
        ],
        execution_rows=[
            ("snap", "AAA.SZ", "20210101", True),
            ("snap", "BBB.SZ", "20210102", True),
        ],
    )

    result = module.inspect_execution_exit_resolution(
        project_execution_panel,
        execution_state_daily,
    )

    assert result["status"] == "still_blocked"
    assert result["pass_flag"] is False
    assert result["portfolio_recovery_allowed"] is False
    assert result["missing_actual_exit_date_rows"] == 2
    assert result["hard_blocker_rows"] == 2
    assert result["hard_blocker_status_counts"] == {
        "exit_unresolved": 1,
        "terminal_event_unpriced": 1,
    }
