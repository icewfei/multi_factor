from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb

from conftest import load_module


SCRIPT_PATH = "scripts/diagnose_unresolved_exit_rows.py"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def write_parquet(path: Path, query: str) -> None:
    con = duckdb.connect()
    try:
        con.execute(f"COPY ({query}) TO '{path.as_posix()}' (FORMAT PARQUET)")
    finally:
        con.close()


def test_diagnosis_script_classifies_project_execution_panel_unresolved_rows(tmp_path: Path, repo_root: Path) -> None:
    run_dir = tmp_path / "run"
    attempt_dir = run_dir / "attempts" / "attempt_1"
    output_path = tmp_path / "diagnosis.json"
    attempt_dir.mkdir(parents=True)

    write_parquet(
        run_dir / "project_execution_panel.parquet",
        """
        SELECT *
        FROM (
            VALUES
                ('snap', 'AAA.SZ', '20210101', '20210104', '20210115', NULL, NULL, NULL, NULL, NULL, 'terminal_event_unpriced', NULL, TRUE, 'delist', '20210108', 'no_terminal_pricing_source', TRUE, TRUE),
                ('snap', 'AAA.SZ', '20210102', '20210105', '20210118', NULL, NULL, NULL, NULL, NULL, 'exit_unresolved', NULL, FALSE, NULL, NULL, NULL, FALSE, FALSE),
                ('snap', 'BBB.SZ', '20210103', '20210106', '20210119', NULL, NULL, NULL, NULL, NULL, 'exit_unresolved', NULL, FALSE, NULL, NULL, NULL, FALSE, FALSE)
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
        attempt_dir / "execution_state_daily.parquet",
        """
        SELECT *
        FROM (
            VALUES
                ('run', 'attempt_1', 'exploratory', 'snap', 'AAA.SZ', '20210101', '20210104', '20210115', TRUE, TRUE, TRUE, 0.5, TRUE, 'filled'),
                ('run', 'attempt_1', 'exploratory', 'snap', 'AAA.SZ', '20210102', '20210105', '20210118', TRUE, TRUE, TRUE, 0.5, TRUE, 'filled'),
                ('run', 'attempt_1', 'exploratory', 'snap', 'BBB.SZ', '20210103', '20210106', '20210119', TRUE, TRUE, TRUE, 0.5, TRUE, 'filled')
        ) AS t(
            run_id, attempt_id, run_type, snapshot_id, instrument, signal_date, entry_date,
            planned_exit_date, execution_attempt_D1, entry_filled_D1, backtest_executable,
            target_weight_D0, entry_tradeable_shared_flag, entry_filled_reason
        )
        """,
    )
    write_json(
        attempt_dir / "run_state_attempt_manifest.json",
        {
            "run_id": "run",
            "attempt_id": "attempt_1",
            "candidate_scheme_id": "cand",
            "research_round_id": "round",
            "snapshot_id": "snap",
        },
    )

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / SCRIPT_PATH),
            "--run-id",
            "ignored_run_id",
            "--input-dir",
            str(run_dir),
            "--attempt-id",
            "attempt_1",
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
    assert payload["summary"]["execution_status_counts"] == {
        "exit_unresolved": 2,
        "terminal_event_unpriced": 1,
    }
    assert payload["summary"]["diagnosis_bucket_counts"] == {
        "exit_unresolved_after_terminal_event": 1,
        "exit_unresolved_nonterminal": 1,
        "terminal_event_unpriced": 1,
    }
    assert payload["diagnosis"]["project_execution_panel_issue"] is True
    assert payload["diagnosis"]["portfolio_join_issue"] is False


def build_portfolio_fail_fast_fixture(tmp_path: Path) -> tuple[Path, Path]:
    run_dir = tmp_path / "portfolio_run"
    attempt_id = "attempt_fail_fast"
    attempt_dir = run_dir / "attempts" / attempt_id
    attempt_dir.mkdir(parents=True)

    write_parquet(
        attempt_dir / "execution_state_daily.parquet",
        """
        SELECT *
        FROM (
            VALUES
                ('run', 'attempt_fail_fast', 'exploratory', 'snap', 'AAA.SZ', '20210101', '20210104', '20210115', TRUE, TRUE, TRUE, 1.0, TRUE, 'filled')
        ) AS t(
            run_id, attempt_id, run_type, snapshot_id, instrument, signal_date, entry_date,
            planned_exit_date, execution_attempt_D1, entry_filled_D1, backtest_executable,
            target_weight_D0, entry_tradeable_shared_flag, entry_filled_reason
        )
        """,
    )
    write_parquet(
        attempt_dir / "ranking_state_daily.parquet",
        """
        SELECT *
        FROM (
            VALUES
                ('run', 'attempt_fail_fast', 'exploratory', 'snap', 'AAA.SZ', '20210101', 0.1, TRUE, TRUE, NULL, TRUE, 1, 1, TRUE, 'cand')
        ) AS t(
            run_id, attempt_id, run_type, snapshot_id, instrument, signal_date, model_score_D0,
            ranking_eligible_D0, liquidity_guard_pass_D0, liquidity_guard_reason,
            universe_guard_pass_D0, rank_position, topk_threshold_rank, topk_frozen_D0, candidate_scheme_id
        )
        """,
    )
    write_parquet(
        run_dir / "project_execution_panel.parquet",
        """
        SELECT *
        FROM (
            VALUES
                ('snap', 'AAA.SZ', '20210101', '20210104', '20210115', NULL, NULL, NULL, NULL, NULL, 'exit_unresolved', NULL, FALSE, NULL, NULL, NULL, FALSE, FALSE)
        ) AS t(
            snapshot_id, instrument, signal_date, entry_date, planned_exit_date, actual_exit_date,
            actual_exit_event_type, actual_exit_price_field, actual_sell_price, exit_delay_days,
            execution_path_status, execution_delayed_realized_return, terminal_event_flag,
            terminal_event_type, terminal_event_date, terminal_exit_pricing_method,
            terminal_exit_approximation_flag, terminal_exit_conservative_flag
        )
        """,
    )
    write_json(
        attempt_dir / "run_state_attempt_manifest.json",
        {
            "run_id": "run",
            "attempt_id": attempt_id,
            "research_round_id": None,
            "parameters": {},
        },
    )

    snapshot_root = tmp_path / "snapshot"
    duckdb_dir = snapshot_root / "duckdb"
    duckdb_dir.mkdir(parents=True)
    con = duckdb.connect(str(duckdb_dir / "warehouse.duckdb"))
    try:
        con.execute("CREATE SCHEMA serving")
        con.execute(
            """
            CREATE VIEW serving.vw_calendar AS
            SELECT *
            FROM (
                VALUES
                    ('20210104', '20210105', '20210111'),
                    ('20210105', '20210106', '20210112'),
                    ('20210106', '20210107', '20210113')
            ) AS t(trade_date, next_trade_date_1, next_trade_date_5)
            """
        )
    finally:
        con.close()

    contract_path = tmp_path / "run_input_contract.json"
    write_json(contract_path, {"source_root": {"snapshot_path": str(snapshot_root)}})
    return run_dir, contract_path


def test_portfolio_builder_fails_cleanly_on_unresolved_exit_without_secondary_exception(
    tmp_path: Path, repo_root: Path
) -> None:
    run_dir, contract_path = build_portfolio_fail_fast_fixture(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts/build_portfolio_artifacts.py"),
            "--run-id",
            "ignored_run_id",
            "--input-dir",
            str(run_dir),
            "--attempt-id",
            "attempt_fail_fast",
            "--run-input-contract",
            str(contract_path),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Found backtest_executable positions with actual_exit_date = NULL" in result.stderr
    assert "UnboundLocalError" not in result.stderr
    assert "derived_holding_cohort_count" not in result.stderr
    manifest_path = run_dir / "attempts" / "attempt_fail_fast" / "portfolio_artifacts_manifest.json"
    assert manifest_path.exists()

