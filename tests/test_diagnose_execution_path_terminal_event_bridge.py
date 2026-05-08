from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb

from conftest import REPO_ROOT


SCRIPT_PATH = "scripts/diagnose_execution_path_unresolved_exit.py"


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
                    ('snap', 'AAA.SZ', '20210106', '20210107', '20210111', NULL, NULL, NULL, NULL, NULL, 'exit_unresolved', NULL, FALSE, NULL, NULL, NULL, FALSE, FALSE)
            ) AS t(
                snapshot_id, ts_code, trade_date, entry_date_D1, planned_exit_date_D5, actual_exit_date,
                actual_exit_event_type, actual_exit_price_field, actual_sell_price, exit_delay_days,
                execution_path_status, execution_delayed_realized_return, terminal_event_flag,
                terminal_event_type, terminal_event_date, terminal_exit_pricing_method,
                terminal_exit_approximation_flag, terminal_exit_conservative_flag
            )
            """
        )
        con.execute(
            """
            CREATE VIEW serving.vw_terminal_event_daily AS
            SELECT *
            FROM (
                VALUES
                    ('snap', 'AAA.SZ', '20210108', 'delist', '20210107', FALSE, TRUE)
            ) AS t(
                snapshot_id, ts_code, event_date, terminal_event_type, last_trade_date,
                cash_settlement_flag, contract_degraded_flag
            )
            """
        )
    finally:
        con.close()


def test_diagnosis_treats_bridge_standardization_as_expected_not_join_bug(
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
                ('snap', 'AAA.SZ', '20210106', '20210107', '20210111', NULL, NULL, NULL, NULL, NULL, 'terminal_event_unpriced', NULL, TRUE, 'delist', '20210108', 'terminal_event_bridge_required', FALSE, FALSE)
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
                ('run', 'attempt', 'exploratory', 'snap', 'AAA.SZ', '20210106', '20210107', '20210111', TRUE, TRUE, TRUE, 0.33, TRUE, 'filled')
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
    assert payload["summary"]["unresolved_rows"] == 1
    assert payload["summary"]["terminal_event_bridge_rows"] == 1
    assert payload["judgment"]["build_project_panels_join_issue"] is False
    assert payload["rows"][0]["terminal_exit_pricing_method"] == "terminal_event_bridge_required"
