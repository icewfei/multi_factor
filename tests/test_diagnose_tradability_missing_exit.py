from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb

from conftest import REPO_ROOT


SCRIPT_PATH = "scripts/diagnose_tradability_missing_exit.py"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


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
            ('20210104', NULL, '20210105', '20210105', '20210108', 2021, 1, FALSE, FALSE),
            ('20210105', '20210104', '20210106', '20210106', '20210111', 2021, 1, FALSE, FALSE),
            ('20210106', '20210105', '20210107', '20210107', '20210112', 2021, 1, FALSE, FALSE),
            ('20210107', '20210106', '20210108', '20210108', '20210113', 2021, 1, FALSE, FALSE),
            ('20210108', '20210107', '20210111', '20210111', '20210114', 2021, 1, TRUE, FALSE),
            ('20210111', '20210108', '20210112', '20210112', '20210115', 2021, 1, FALSE, FALSE),
            ('20210112', '20210111', NULL, NULL, NULL, 2021, 1, FALSE, FALSE)
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
            ('warehouse_20260429_trainval_20211231', 'AAA.SZ', '20210104', 'main', TRUE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, 'ok', FALSE, FALSE, FALSE, FALSE, FALSE, TRUE, TRUE, TRUE, TRUE, FALSE, NULL, TRUE, TRUE, TRUE),
            ('warehouse_20260429_trainval_20211231', 'BBB.SZ', '20210104', 'main', TRUE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, 'ok', FALSE, FALSE, FALSE, FALSE, FALSE, TRUE, TRUE, TRUE, TRUE, FALSE, NULL, TRUE, TRUE, TRUE),
            ('warehouse_20260429_trainval_20211231', 'BBB.SZ', '20210106', 'main', TRUE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, 'ok', FALSE, FALSE, FALSE, FALSE, FALSE, TRUE, TRUE, TRUE, TRUE, FALSE, NULL, TRUE, TRUE, TRUE),
            ('warehouse_20260429_trainval_20211231', 'CCC.SZ', '20210104', 'main', TRUE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, 'ok', FALSE, FALSE, FALSE, FALSE, FALSE, TRUE, TRUE, TRUE, TRUE, FALSE, NULL, TRUE, TRUE, TRUE),
            ('warehouse_20260429_trainval_20211231', 'DDD.SZ', '20210104', 'main', TRUE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, 'ok', FALSE, FALSE, FALSE, FALSE, FALSE, TRUE, TRUE, TRUE, TRUE, FALSE, NULL, TRUE, TRUE, TRUE)
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
                pb DOUBLE,
                ps_ttm DOUBLE,
                dv_ttm DOUBLE,
                adj_open DOUBLE,
                adj_high DOUBLE,
                adj_low DOUBLE,
                adj_close DOUBLE
            )
            """
        )
        con.execute(
            """
            INSERT INTO serving.vw_bars_daily VALUES
            ('warehouse_20260429_trainval_20211231', 'CCC.SZ', '20210105', 10, 10, 10, 10, 10, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 10, 10, 10, 10)
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
            ('warehouse_20260429_trainval_20211231', 'DDD.SZ', '20210104', TRUE, 'delist', 'delist', '20210104', '20210104', '20210104', NULL, FALSE, 'test', 'degraded', TRUE, 'source degraded', '{}')
            """
        )
    finally:
        con.close()


def test_tradability_missing_exit_diagnosis_outputs_valid_json_and_filters_rows(tmp_path: Path) -> None:
    source_db = tmp_path / "warehouse.duckdb"
    build_source_db(source_db)

    input_path = tmp_path / "exit_unresolved_path_diagnosis.json"
    output_path = tmp_path / "tradability_missing_diagnosis.json"
    write_json(
        input_path,
        {
            "rows": [
                {
                    "instrument": "AAA.SZ",
                    "signal_date": "20210104",
                    "entry_date": "20210105",
                    "planned_exit_date": "20210104",
                    "actual_exit_date": None,
                    "execution_path_status": "exit_unresolved",
                    "snapshot_end_date": "20210112",
                    "root_cause_class": "tradability_missing",
                },
                {
                    "instrument": "BBB.SZ",
                    "signal_date": "20210104",
                    "entry_date": "20210105",
                    "planned_exit_date": "20210104",
                    "actual_exit_date": None,
                    "execution_path_status": "exit_unresolved",
                    "snapshot_end_date": "20210112",
                    "root_cause_class": "tradability_missing",
                },
                {
                    "instrument": "CCC.SZ",
                    "signal_date": "20210104",
                    "entry_date": "20210105",
                    "planned_exit_date": "20210104",
                    "actual_exit_date": None,
                    "execution_path_status": "exit_unresolved",
                    "snapshot_end_date": "20210112",
                    "root_cause_class": "tradability_missing",
                },
                {
                    "instrument": "DDD.SZ",
                    "signal_date": "20210104",
                    "entry_date": "20210105",
                    "planned_exit_date": "20210104",
                    "actual_exit_date": None,
                    "execution_path_status": "exit_unresolved",
                    "snapshot_end_date": "20210112",
                    "root_cause_class": "tradability_missing",
                },
                {
                    "instrument": "EEE.SZ",
                    "signal_date": "20210104",
                    "entry_date": "20210105",
                    "planned_exit_date": "20210104",
                    "actual_exit_date": None,
                    "execution_path_status": "exit_unresolved",
                    "snapshot_end_date": "20210112",
                    "root_cause_class": "still_open_unresolved",
                },
            ]
        },
    )

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / SCRIPT_PATH),
            "--exit-unresolved-diagnosis",
            str(input_path),
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
    assert payload["diagnosis_scope"] == "tradability_missing_exit_only"
    assert payload["total_tradability_missing_rows"] == 4
    assert payload["calendar_without_tradability_count"] == 1
    assert payload["partial_tradability_coverage_gap_count"] == 1
    assert payload["bars_without_tradability_count"] == 1
    assert payload["post_delist_coverage_gap_count"] == 1

    by_instrument = {row["instrument"]: row for row in payload["rows"]}
    assert by_instrument["AAA.SZ"]["tradability_gap_class"] == "calendar_without_tradability"
    assert by_instrument["BBB.SZ"]["tradability_gap_class"] == "partial_tradability_coverage_gap"
    assert by_instrument["CCC.SZ"]["tradability_gap_class"] == "bars_without_tradability"
    assert by_instrument["DDD.SZ"]["tradability_gap_class"] == "post_delist_coverage_gap"

    assert "EEE.SZ" not in by_instrument
    for row in payload["rows"]:
        assert row["actual_exit_date"] is None
        assert "actual_sell_price" not in row
        assert row["tradability_gap_class"] in {
            "full_tradability_coverage_missing",
            "partial_tradability_coverage_gap",
            "post_delist_coverage_gap",
            "bars_without_tradability",
            "calendar_without_tradability",
            "unknown",
        }
