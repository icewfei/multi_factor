from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from conftest import REPO_ROOT, load_json


SCRIPT_PATH = "scripts/build_trainval_dryrun_validation_readout.py"


def build_source_db(path: Path) -> None:
    import duckdb

    con = duckdb.connect(str(path))
    try:
        con.execute("CREATE SCHEMA serving")
        con.execute(
            """
            CREATE TABLE serving.vw_bars_daily (
                snapshot_id VARCHAR,
                ts_code VARCHAR,
                trade_date VARCHAR,
                open DOUBLE,
                close DOUBLE,
                pre_close DOUBLE,
                pct_chg DOUBLE
            )
            """
        )
        con.execute(
            """
            INSERT INTO serving.vw_bars_daily VALUES
                ('snap', 'AAA.SZ', '20210104', 10.0, 10.5, 10.0, 5.0),
                ('snap', 'AAA.SZ', '20210105', 10.6, 10.8, 10.5, 2.857142857142857)
            """
        )
        con.execute(
            """
            CREATE TABLE serving.vw_calendar (
                trade_date VARCHAR
            )
            """
        )
        con.execute(
            """
            INSERT INTO serving.vw_calendar VALUES
                ('20210104'),
                ('20210105')
            """
        )
        con.execute(
            """
            CREATE TABLE serving.vw_benchmark_daily (
                snapshot_id VARCHAR,
                trade_date VARCHAR,
                benchmark_code VARCHAR,
                benchmark_name VARCHAR,
                daily_return DOUBLE,
                is_total_return BOOLEAN
            )
            """
        )
        con.execute(
            """
            INSERT INTO serving.vw_benchmark_daily VALUES
                ('snap', '20210104', 'CSI_ALL_SHARE_TR', 'CSI All Share TR', 0.01, TRUE),
                ('snap', '20210105', 'CSI_ALL_SHARE_TR', 'CSI All Share TR', 0.02, TRUE)
            """
        )
    finally:
        con.close()


def write_run_artifacts(run_dir: Path, attempt_id: str) -> None:
    attempt_dir = run_dir / "attempts" / attempt_id
    attempt_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "run_state_latest_attempt.json").write_text(
        json.dumps({"run_id": run_dir.name, "attempt_id": attempt_id}, indent=2) + "\n",
        encoding="utf-8",
    )
    (attempt_dir / "portfolio_artifacts_manifest.json").write_text(
        json.dumps(
            {
                "summary_counts": {
                    "holdings_rows": 1,
                    "portfolio_daily_summary_rows": 2,
                    "turnover_daily_rows": 2,
                }
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (attempt_dir / "run_state_acceptance_report.json").write_text(
        json.dumps({"overall_passed": True}, indent=2) + "\n",
        encoding="utf-8",
    )
    (attempt_dir / "run_state_attempt_manifest.json").write_text(
        json.dumps({"parameters": {"candidate_scheme_id": "test_scheme"}}, indent=2) + "\n",
        encoding="utf-8",
    )
    (attempt_dir / "holdings.csv").write_text(
        "\n".join(
            [
                "run_id,attempt_id,run_type,position_id,instrument,signal_date,entry_date,actual_exit_date,planned_exit_date,entry_fill_weight,actual_exit_event_type,actual_exit_price_field,actual_sell_price,exit_delay_days,execution_delayed_realized_return,execution_path_status,pricing_policy_version,source_repair_flag,terminal_exit_approximation_flag,terminal_exit_conservative_flag",
                f"{run_dir.name},{attempt_id},research,pos1,AAA.SZ,20210104,20210104,20210105,20210108,0.2,TERMINAL_LAST_CLOSE,close,10.8,0,0.08,terminal_priced_last_tradable_close,terminal_exit_policy_v1,true,false,false",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (attempt_dir / "portfolio_daily_summary.csv").write_text(
        "\n".join(
            [
                "run_id,attempt_id,run_type,trade_date,cash_weight,invested_weight,max_single_name_weight,top3_weight,portfolio_herfindahl_index",
                f"{run_dir.name},{attempt_id},research,20210104,0.8,0.2,0.2,0.2,0.04",
                f"{run_dir.name},{attempt_id},research,20210105,0.8,0.2,0.2,0.2,0.04",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (attempt_dir / "turnover_daily.csv").write_text(
        "\n".join(
            [
                "run_id,attempt_id,run_type,trade_date,buy_notional_daily,sell_notional_daily,turnover_daily,rebalance_event_flag",
                f"{run_dir.name},{attempt_id},research,20210104,0.2,0.0,0.2,true",
                f"{run_dir.name},{attempt_id},research,20210105,0.0,0.2,0.2,false",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_build_trainval_dryrun_validation_readout(tmp_path: Path) -> None:
    source_root = tmp_path / "snapshot"
    duckdb_dir = source_root / "duckdb"
    duckdb_dir.mkdir(parents=True, exist_ok=True)
    build_source_db(duckdb_dir / "warehouse.duckdb")

    run_input_contract = tmp_path / "run_input_contract.json"
    run_input_contract.write_text(
        json.dumps(
            {
                "snapshot_id": "snap",
                "source_root": {"snapshot_path": str(source_root)},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    split_config = tmp_path / "split.json"
    split_config.write_text(
        json.dumps(
            {
                "train_start": "2021-01-04",
                "train_end": "2021-01-05",
                "validation_start": "2021-01-04",
                "validation_end": "2021-01-05",
                "test_excluded_start": "2021-01-06",
                "test_excluded_end": "2021-12-31",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    run_dir = tmp_path / "run"
    attempt_id = "attempt_test"
    write_run_artifacts(run_dir, attempt_id)

    output_json = tmp_path / "readout.json"
    output_md = tmp_path / "readout.md"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / SCRIPT_PATH),
            "--run-dir",
            str(run_dir),
            "--attempt-id",
            attempt_id,
            "--run-input-contract",
            str(run_input_contract),
            "--split-config",
            str(split_config),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    payload = load_json(output_json)
    assert payload["frozen_test_accessed"] is False
    assert payload["formal_metrics_generated"] is False
    assert payload["primary_run"]["candidate_scheme_id"] == "test_scheme"
    assert payload["windows"]["primary"]["train"]["terminal_last_close_impact_summary"]["positions"] == 1
    assert payload["windows"]["primary"]["train"]["avg_cash_weight"] == 0.8
    assert payload["windows"]["primary"]["train"]["avg_invested_weight"] == 0.2
    assert payload["windows"]["primary"]["train"]["annualized_return_trainval_dry_run_estimate"] is not None

    markdown = output_md.read_text(encoding="utf-8")
    assert "TRAINVAL PORTFOLIO DRY-RUN ESTIMATE ONLY" in markdown
    assert "Distinct from model edge diagnosis" in markdown
