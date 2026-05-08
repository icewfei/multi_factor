from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb

from conftest import REPO_ROOT


SCRIPT_PATH = "scripts/diagnose_exit_unresolved_path.py"


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
            CREATE TABLE serving.vw_calendar (
                trade_date VARCHAR,
                prev_trade_date VARCHAR,
                next_trade_date VARCHAR,
                next_trade_date_1 VARCHAR,
                next_trade_date_5 VARCHAR,
                year BIGINT,
                month BIGINT,
                is_week_end BOOLEAN,
                is_month_end BOOLEAN
            )
            """
        )
        con.execute(
            """
            INSERT INTO serving.vw_calendar VALUES
            ('20210111', '20210108', '20210112', '20210112', '20210115', 2021, 1, FALSE, FALSE),
            ('20210112', '20210111', '20210113', '20210113', '20210118', 2021, 1, FALSE, FALSE),
            ('20210113', '20210112', '20210114', '20210114', '20210119', 2021, 1, FALSE, FALSE),
            ('20210114', '20210113', '20210115', '20210115', '20210120', 2021, 1, FALSE, FALSE),
            ('20210115', '20210114', NULL, NULL, NULL, 2021, 1, TRUE, FALSE)
            """
        )
        con.execute(
            """
            CREATE TABLE serving.vw_tradability_daily (
                snapshot_id VARCHAR,
                ts_code VARCHAR,
                trade_date VARCHAR,
                board VARCHAR,
                is_listed_t BOOLEAN,
                is_suspended_t BOOLEAN,
                is_st_t BOOLEAN,
                no_trade_t BOOLEAN,
                low_liquidity_flag_t BOOLEAN,
                open_at_up_limit_t BOOLEAN,
                open_at_down_limit_t BOOLEAN,
                close_at_down_limit_t BOOLEAN,
                one_word_up_limit_t BOOLEAN,
                one_word_down_limit_t BOOLEAN,
                buyable_at_open BOOLEAN,
                sellable_at_open BOOLEAN,
                sellable_at_close BOOLEAN,
                has_suspend_data BOOLEAN,
                has_namechange_data BOOLEAN,
                has_stk_limit_data BOOLEAN,
                tradability_tier VARCHAR,
                is_suspended BOOLEAN,
                is_st BOOLEAN,
                open_at_up_limit BOOLEAN,
                open_at_down_limit BOOLEAN,
                close_at_down_limit BOOLEAN,
                buyable_at_open_1 BOOLEAN,
                sellable_at_open_1 BOOLEAN,
                sellable_at_close_1 BOOLEAN,
                tradability_rule_complete_flag BOOLEAN,
                tradability_degraded_flag BOOLEAN,
                tradability_degraded_reason VARCHAR,
                sellable_retry_next_open BOOLEAN,
                entry_buyable_D1_open BOOLEAN,
                exit_sellable_D5_close BOOLEAN
            )
            """
        )
        con.execute(
            """
            INSERT INTO serving.vw_tradability_daily VALUES
            ('snap', 'AAA.SZ', '20210111', 'main', TRUE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, TRUE, FALSE, FALSE, TRUE, TRUE, FALSE, TRUE, TRUE, TRUE, 'ok', FALSE, FALSE, FALSE, FALSE, TRUE, TRUE, TRUE, FALSE, TRUE, FALSE, NULL, FALSE, TRUE, FALSE),
            ('snap', 'AAA.SZ', '20210112', 'main', TRUE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, 'ok', FALSE, FALSE, FALSE, FALSE, FALSE, TRUE, TRUE, TRUE, TRUE, FALSE, NULL, TRUE, TRUE, TRUE),
            ('snap', 'BBB.SZ', '20210111', 'main', TRUE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, TRUE, FALSE, FALSE, TRUE, TRUE, FALSE, TRUE, TRUE, TRUE, 'ok', FALSE, FALSE, FALSE, FALSE, TRUE, TRUE, TRUE, FALSE, TRUE, FALSE, NULL, FALSE, TRUE, FALSE),
            ('snap', 'BBB.SZ', '20210112', 'main', TRUE, TRUE, FALSE, TRUE, FALSE, FALSE, TRUE, TRUE, FALSE, FALSE, FALSE, FALSE, FALSE, TRUE, TRUE, TRUE, 'ok', TRUE, FALSE, FALSE, TRUE, TRUE, FALSE, FALSE, FALSE, TRUE, FALSE, NULL, FALSE, TRUE, FALSE),
            ('snap', 'BBB.SZ', '20210113', 'main', TRUE, TRUE, FALSE, TRUE, FALSE, FALSE, TRUE, TRUE, FALSE, FALSE, FALSE, FALSE, FALSE, TRUE, TRUE, TRUE, 'ok', TRUE, FALSE, FALSE, TRUE, TRUE, FALSE, FALSE, FALSE, TRUE, FALSE, NULL, FALSE, TRUE, FALSE),
            ('snap', 'CCC.SZ', '20210114', 'main', TRUE, TRUE, FALSE, TRUE, FALSE, FALSE, TRUE, TRUE, FALSE, FALSE, FALSE, FALSE, FALSE, TRUE, TRUE, TRUE, 'ok', TRUE, FALSE, FALSE, TRUE, TRUE, FALSE, FALSE, FALSE, TRUE, FALSE, NULL, FALSE, TRUE, FALSE),
            ('snap', 'CCC.SZ', '20210115', 'main', TRUE, TRUE, FALSE, TRUE, FALSE, FALSE, TRUE, TRUE, FALSE, FALSE, FALSE, FALSE, FALSE, TRUE, TRUE, TRUE, 'ok', TRUE, FALSE, FALSE, TRUE, TRUE, FALSE, FALSE, FALSE, TRUE, FALSE, NULL, FALSE, TRUE, FALSE)
            """
        )
        con.execute(
            """
            CREATE TABLE serving.vw_terminal_event_daily (
                snapshot_id VARCHAR,
                ts_code VARCHAR,
                trade_date VARCHAR,
                terminal_event_flag BOOLEAN,
                event_type VARCHAR,
                terminal_event_type VARCHAR,
                event_date VARCHAR,
                effective_date VARCHAR,
                last_trade_date VARCHAR,
                settlement_date VARCHAR,
                cash_settlement_flag BOOLEAN,
                event_source VARCHAR,
                event_truth_level VARCHAR,
                contract_degraded_flag BOOLEAN,
                contract_degraded_reason VARCHAR,
                event_detail_json JSON
            )
            """
        )
        con.execute(
            """
            INSERT INTO serving.vw_terminal_event_daily VALUES
            ('snap', 'DDD.SZ', '20210112', TRUE, 'delist', 'delist', '20210112', '20210112', '20210111', NULL, FALSE, 'test', 'ok', FALSE, NULL, '{}')
            """
        )
        con.execute(
            """
            CREATE TABLE serving.vw_bars_daily (
                snapshot_id VARCHAR,
                ts_code VARCHAR,
                trade_date VARCHAR,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                pre_close DOUBLE,
                change DOUBLE,
                pct_chg DOUBLE,
                vol DOUBLE,
                amount DOUBLE,
                adj_factor DOUBLE,
                turnover_rate DOUBLE,
                turnover_rate_f DOUBLE,
                volume_ratio DOUBLE,
                total_mv DOUBLE,
                circ_mv DOUBLE,
                pe_ttm DOUBLE,
                pb DOUBLE
            )
            """
        )
        con.execute(
            """
            INSERT INTO serving.vw_bars_daily VALUES
            ('snap', 'AAA.SZ', '20210112', 10, 10, 10, 10, 10, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0),
            ('snap', 'BBB.SZ', '20210112', 10, 10, 10, 10, 10, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0),
            ('snap', 'BBB.SZ', '20210113', 10, 10, 10, 10, 10, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0),
            ('snap', 'CCC.SZ', '20210115', 10, 10, 10, 10, 10, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0)
            """
        )
    finally:
        con.close()


def test_exit_unresolved_path_diagnosis_outputs_valid_json_and_ignores_terminal_event_rows(tmp_path: Path) -> None:
    source_db = tmp_path / "warehouse.duckdb"
    build_source_db(source_db)

    project_execution_panel = tmp_path / "project_execution_panel.parquet"
    diagnosis_json = tmp_path / "upstream_diagnosis.json"
    output_path = tmp_path / "exit_unresolved_diagnosis.json"

    write_parquet(
        project_execution_panel,
        """
        SELECT *
        FROM (
            VALUES
                ('snap', 'AAA.SZ', '20210106', '20210107', '20210111', NULL, NULL, NULL, NULL, NULL, 'exit_unresolved', NULL, FALSE, NULL, NULL, NULL, FALSE, FALSE),
                ('snap', 'BBB.SZ', '20210106', '20210107', '20210111', NULL, NULL, NULL, NULL, NULL, 'exit_unresolved', NULL, FALSE, NULL, NULL, NULL, FALSE, FALSE),
                ('snap', 'CCC.SZ', '20210108', '20210111', '20210114', NULL, NULL, NULL, NULL, NULL, 'exit_unresolved', NULL, FALSE, NULL, NULL, NULL, FALSE, FALSE),
                ('snap', 'DDD.SZ', '20210106', '20210107', '20210111', NULL, NULL, NULL, NULL, NULL, 'terminal_event_unpriced', NULL, TRUE, 'delist', '20210112', 'no_terminal_pricing_source', TRUE, TRUE)
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
        diagnosis_json,
        {
            "rows": [
                {
                    "snapshot_id": "snap",
                    "instrument": "AAA.SZ",
                    "signal_date": "20210106",
                    "entry_date": "20210107",
                    "planned_exit_date": "20210111",
                    "actual_exit_date": None,
                    "execution_path_status": "exit_unresolved",
                },
                {
                    "snapshot_id": "snap",
                    "instrument": "BBB.SZ",
                    "signal_date": "20210106",
                    "entry_date": "20210107",
                    "planned_exit_date": "20210111",
                    "actual_exit_date": None,
                    "execution_path_status": "exit_unresolved",
                },
                {
                    "snapshot_id": "snap",
                    "instrument": "CCC.SZ",
                    "signal_date": "20210108",
                    "entry_date": "20210111",
                    "planned_exit_date": "20210114",
                    "actual_exit_date": None,
                    "execution_path_status": "exit_unresolved",
                },
                {
                    "snapshot_id": "snap",
                    "instrument": "DDD.SZ",
                    "signal_date": "20210106",
                    "entry_date": "20210107",
                    "planned_exit_date": "20210111",
                    "actual_exit_date": None,
                    "execution_path_status": "terminal_event_unpriced",
                },
            ]
        },
    )

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / SCRIPT_PATH),
            "--diagnosis-json",
            str(diagnosis_json),
            "--project-execution-panel",
            str(project_execution_panel),
            "--source-db",
            str(source_db),
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
    assert payload["diagnosis_scope"] == "exit_unresolved_path_only"
    assert payload["total_exit_unresolved_rows"] == 3
    assert payload["sellable_retry_path_missing_count"] == 1
    assert payload["terminal_event_missing_count"] == 1
    assert payload["still_open_unresolved_count"] == 1

    instruments = {row["instrument"] for row in payload["rows"]}
    assert instruments == {"AAA.SZ", "BBB.SZ", "CCC.SZ"}
    for row in payload["rows"]:
        assert row["execution_path_status"] == "exit_unresolved"
        assert row["root_cause_class"] in {
            "calendar_insufficient",
            "tradability_missing",
            "terminal_event_missing",
            "sellable_retry_path_missing",
            "still_open_unresolved",
            "execution_logic_gap",
            "unknown",
        }
        assert row["actual_exit_date"] is None
        assert "actual_sell_price" not in row
        assert row["terminal_pricing_used"] is False
