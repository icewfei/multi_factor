from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb


SCRIPT_PATH = "scripts/diagnose_execution_path_unresolved_exit.py"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def write_parquet(path: Path, query: str) -> None:
    con = duckdb.connect()
    try:
        con.execute(f"COPY ({query}) TO '{path.as_posix()}' (FORMAT PARQUET)")
    finally:
        con.close()


def build_source_db(path: Path) -> None:
    con = duckdb.connect(str(path))
    try:
        con.execute("CREATE SCHEMA serving")
        con.execute(
            """
            CREATE VIEW serving.vw_execution_path_daily AS
            SELECT *
            FROM (
                VALUES
                    ('snap', 'AAA.SZ', '20210101', '20210104', '20210111', NULL, NULL, TRUE, TRUE, FALSE, 10.0, 10.5, NULL, NULL, NULL, TRUE, 'delist', '20210108', 'no_terminal_pricing_source', TRUE, TRUE, 'terminal_event_unpriced', NULL, NULL),
                    ('snap', 'AAA.SZ', '20210102', '20210105', '20210112', NULL, NULL, TRUE, TRUE, FALSE, 10.0, 10.5, NULL, NULL, NULL, FALSE, NULL, NULL, NULL, FALSE, FALSE, 'exit_unresolved', NULL, NULL),
                    ('snap', 'BBB.SZ', '20210103', '20210106', '20210113', NULL, NULL, TRUE, TRUE, FALSE, 10.0, 10.5, NULL, NULL, NULL, FALSE, NULL, NULL, NULL, FALSE, FALSE, 'exit_unresolved', NULL, NULL)
            ) AS t(
                snapshot_id, ts_code, trade_date, entry_date_D1, planned_exit_date_D5, actual_exit_date,
                exit_delay_days, entry_buyable_D1_open, exit_sellable_D5_close, used_sellable_retry_next_open,
                adj_open_base_D1, adj_close_base_D5, actual_exit_event_type, actual_exit_price_field,
                actual_sell_price, terminal_event_flag, terminal_event_type, terminal_event_date,
                terminal_exit_pricing_method, terminal_exit_approximation_flag, terminal_exit_conservative_flag,
                execution_path_status, adj_sell_base_actual_exit, execution_delayed_realized_return
            )
            """
        )
        con.execute(
            """
            CREATE VIEW serving.vw_terminal_event_daily AS
            SELECT *
            FROM (
                VALUES
                    ('snap', 'AAA.SZ', '20210108', TRUE, 'delist', 'delist', '20210108', '20210108', '20210107', NULL, FALSE, 'test', 'degraded', TRUE, 'no_pricing', '{}')
            ) AS t(
                snapshot_id, ts_code, trade_date, terminal_event_flag, event_type, terminal_event_type,
                event_date, effective_date, last_trade_date, settlement_date, cash_settlement_flag,
                event_source, event_truth_level, contract_degraded_flag, contract_degraded_reason, event_detail_json
            )
            """
        )
    finally:
        con.close()


def test_execution_path_unresolved_exit_diagnosis_flags_upstream_source_and_policy_gap(
    tmp_path: Path, repo_root: Path
) -> None:
    source_db_path = tmp_path / "warehouse.duckdb"
    build_source_db(source_db_path)

    project_execution_panel = tmp_path / "project_execution_panel.parquet"
    execution_state = tmp_path / "execution_state_daily.parquet"
    output_path = tmp_path / "diagnosis.json"

    write_parquet(
        project_execution_panel,
        """
        SELECT *
        FROM (
            VALUES
                ('snap', 'AAA.SZ', '20210101', '20210104', '20210111', NULL, NULL, NULL, NULL, NULL, 'terminal_event_unpriced', NULL, TRUE, 'delist', '20210108', 'no_terminal_pricing_source', TRUE, TRUE),
                ('snap', 'AAA.SZ', '20210102', '20210105', '20210112', NULL, NULL, NULL, NULL, NULL, 'exit_unresolved', NULL, FALSE, NULL, NULL, NULL, FALSE, FALSE),
                ('snap', 'BBB.SZ', '20210103', '20210106', '20210113', NULL, NULL, NULL, NULL, NULL, 'exit_unresolved', NULL, FALSE, NULL, NULL, NULL, FALSE, FALSE)
        ) AS t(
            snapshot_id, instrument, signal_date, entry_date, planned_exit_date, actual_exit_date,
            actual_exit_event_type, actual_exit_price_field, actual_sell_price, exit_delay_days,
            execution_path_status, execution_delayed_realized_return, terminal_event_flag,
            terminal_event_type, terminal_event_date, terminal_exit_pricing_method,
            terminal_exit_approximation_flag, terminal_exit_conservative_flag
        )
        """,
    )

    write_parquet(
        execution_state,
        """
        SELECT *
        FROM (
            VALUES
                ('run', 'attempt', 'exploratory', 'snap', 'AAA.SZ', '20210101', '20210104', '20210111', TRUE, TRUE, TRUE, 0.33, TRUE, 'filled'),
                ('run', 'attempt', 'exploratory', 'snap', 'AAA.SZ', '20210102', '20210105', '20210112', TRUE, TRUE, TRUE, 0.33, TRUE, 'filled'),
                ('run', 'attempt', 'exploratory', 'snap', 'BBB.SZ', '20210103', '20210106', '20210113', TRUE, TRUE, TRUE, 0.34, TRUE, 'filled')
        ) AS t(
            run_id, attempt_id, run_type, snapshot_id, instrument, signal_date, entry_date,
            planned_exit_date, execution_attempt_D1, entry_filled_D1, backtest_executable,
            target_weight_D0, entry_tradeable_shared_flag, entry_filled_reason
        )
        """,
    )

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / SCRIPT_PATH),
            "--project-execution-panel",
            str(project_execution_panel),
            "--execution-state",
            str(execution_state),
            "--source-db",
            str(source_db_path),
            "--output",
            str(output_path),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["unresolved_rows"] == 3
    assert payload["summary"]["source_execution_path_actual_exit_null_rows"] == 3
    assert payload["judgment"]["upstream_execution_path_null_actual_exit_date"] is True
    assert payload["judgment"]["build_project_panels_join_issue"] is False
    assert payload["judgment"]["terminal_pricing_policy_needed"] is True
    assert payload["judgment"]["data_source_gap_present"] is True
    assert payload["evidence"]["panel_vs_source_root_cause_field_mismatch_counts"] == {}
    assert payload["summary"]["terminal_event_source_rows_matched"] == 1
