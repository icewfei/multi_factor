from __future__ import annotations

import json
from pathlib import Path

import duckdb

from conftest import load_module


MODULE_PATH = "scripts/build_data_field_enrichment_v1.py"
FIELD_CONTRACT_PATH = Path("configs/data_field_enrichment/field_contract_v1.json")


def write_parquet(path: Path, schema: list[tuple[str, str]], rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    try:
        columns_sql = ", ".join(f"{name} {dtype}" for name, dtype in schema)
        placeholders = ", ".join("?" for _ in schema)
        con.execute(f"CREATE TABLE tmp ({columns_sql})")
        con.executemany(f"INSERT INTO tmp VALUES ({placeholders})", rows)
        con.execute(f"COPY tmp TO '{path.as_posix()}' (FORMAT PARQUET)")
    finally:
        con.close()


def build_snapshot_fixture(tmp_path: Path, *, is_st: bool, include_st_interval: bool) -> tuple[Path, Path]:
    snapshot_id = "fixture_trainval_snapshot"
    snapshot_root = tmp_path / "snapshot"
    warehouse_root = snapshot_root / "warehouse"

    write_parquet(
        warehouse_root / "market" / "bars_daily.parquet",
        [
            ("snapshot_id", "VARCHAR"),
            ("ts_code", "VARCHAR"),
            ("trade_date", "VARCHAR"),
            ("open", "DOUBLE"),
            ("high", "DOUBLE"),
            ("low", "DOUBLE"),
            ("close", "DOUBLE"),
            ("pre_close", "DOUBLE"),
            ("change", "DOUBLE"),
            ("pct_chg", "DOUBLE"),
            ("vol", "DOUBLE"),
            ("amount", "DOUBLE"),
            ("adj_factor", "DOUBLE"),
            ("turnover_rate", "DOUBLE"),
            ("turnover_rate_f", "DOUBLE"),
            ("volume_ratio", "DOUBLE"),
            ("total_mv", "DOUBLE"),
            ("circ_mv", "DOUBLE"),
            ("pe_ttm", "DOUBLE"),
            ("pb", "DOUBLE"),
            ("ps_ttm", "DOUBLE"),
            ("dv_ttm", "DOUBLE"),
            ("adj_open", "DOUBLE"),
            ("adj_high", "DOUBLE"),
            ("adj_low", "DOUBLE"),
            ("adj_close", "DOUBLE"),
        ],
        [
            (
                snapshot_id,
                "000001.SZ",
                "20210104",
                10.0,
                11.0,
                9.8,
                11.0,
                10.0,
                1.0,
                10.0,
                100.0,
                1000.0,
                1.0,
                1.0,
                1.0,
                1.0,
                100000.0,
                90000.0,
                10.0,
                1.0,
                1.0,
                0.0,
                10.0,
                11.0,
                9.8,
                11.0,
            )
        ],
    )

    write_parquet(
        warehouse_root / "state" / "instrument_status_daily.parquet",
        [
            ("snapshot_id", "VARCHAR"),
            ("ts_code", "VARCHAR"),
            ("trade_date", "VARCHAR"),
            ("board", "VARCHAR"),
            ("exchange", "VARCHAR"),
            ("is_listed_t", "BOOLEAN"),
            ("is_suspended_t", "BOOLEAN"),
            ("is_st_t", "BOOLEAN"),
            ("has_suspend_data", "BOOLEAN"),
            ("has_namechange_data", "BOOLEAN"),
            ("status_source_flags", "VARCHAR"),
        ],
        [
            (
                snapshot_id,
                "000001.SZ",
                "20210104",
                "主板",
                "SZ",
                True,
                False,
                is_st,
                True,
                True,
                "namechange",
            )
        ],
    )

    write_parquet(
        warehouse_root / "market" / "tradability_daily.parquet",
        [
            ("snapshot_id", "VARCHAR"),
            ("ts_code", "VARCHAR"),
            ("trade_date", "VARCHAR"),
            ("board", "VARCHAR"),
            ("is_listed_t", "BOOLEAN"),
            ("is_suspended_t", "BOOLEAN"),
            ("is_st_t", "BOOLEAN"),
            ("no_trade_t", "BOOLEAN"),
            ("low_liquidity_flag_t", "BOOLEAN"),
            ("open_at_up_limit_t", "BOOLEAN"),
            ("open_at_down_limit_t", "BOOLEAN"),
            ("close_at_down_limit_t", "BOOLEAN"),
            ("one_word_up_limit_t", "BOOLEAN"),
            ("one_word_down_limit_t", "BOOLEAN"),
            ("buyable_at_open", "BOOLEAN"),
            ("sellable_at_open", "BOOLEAN"),
            ("sellable_at_close", "BOOLEAN"),
            ("has_suspend_data", "BOOLEAN"),
            ("has_namechange_data", "BOOLEAN"),
            ("has_stk_limit_data", "BOOLEAN"),
            ("tradability_tier", "VARCHAR"),
            ("is_suspended", "BOOLEAN"),
            ("is_st", "BOOLEAN"),
            ("open_at_up_limit", "BOOLEAN"),
            ("open_at_down_limit", "BOOLEAN"),
            ("close_at_down_limit", "BOOLEAN"),
            ("buyable_at_open_1", "BOOLEAN"),
            ("sellable_at_open_1", "BOOLEAN"),
            ("sellable_at_close_1", "BOOLEAN"),
            ("tradability_rule_complete_flag", "BOOLEAN"),
            ("tradability_degraded_flag", "BOOLEAN"),
            ("tradability_degraded_reason", "VARCHAR"),
            ("sellable_retry_next_open", "BOOLEAN"),
            ("entry_buyable_D1_open", "BOOLEAN"),
            ("exit_sellable_D5_close", "BOOLEAN"),
        ],
        [
            (
                snapshot_id,
                "000001.SZ",
                "20210104",
                "主板",
                True,
                False,
                is_st,
                False,
                False,
                False,
                False,
                False,
                False,
                False,
                True,
                True,
                True,
                True,
                True,
                True,
                "fixture_tier",
                False,
                is_st,
                False,
                False,
                False,
                True,
                True,
                True,
                True,
                False,
                None,
                True,
                True,
                True,
            )
        ],
    )

    write_parquet(
        warehouse_root / "market" / "limit_rules_daily.parquet",
        [
            ("snapshot_id", "VARCHAR"),
            ("ts_code", "VARCHAR"),
            ("trade_date", "VARCHAR"),
            ("board", "VARCHAR"),
            ("pre_close", "DOUBLE"),
            ("is_st_t", "BOOLEAN"),
            ("limit_pct", "DOUBLE"),
            ("price_tick_quantize_t", "DOUBLE"),
            ("up_limit_price_t", "DOUBLE"),
            ("down_limit_price_t", "DOUBLE"),
            ("has_namechange_data", "BOOLEAN"),
            ("has_stk_limit_data", "BOOLEAN"),
            ("rule_version", "VARCHAR"),
            ("limit_rule_source", "VARCHAR"),
        ],
        [
            (
                snapshot_id,
                "000001.SZ",
                "20210104",
                "主板",
                10.0,
                is_st,
                0.10,
                0.01,
                11.0,
                9.0,
                True,
                True,
                "fixture_rule_v1",
                "fixture.limit",
            )
        ],
    )

    write_parquet(
        warehouse_root / "core" / "instruments.parquet",
        [
            ("snapshot_id", "VARCHAR"),
            ("ts_code", "VARCHAR"),
            ("symbol", "VARCHAR"),
            ("name", "VARCHAR"),
            ("list_date", "VARCHAR"),
            ("delist_date", "VARCHAR"),
            ("list_status", "VARCHAR"),
            ("board", "VARCHAR"),
            ("exchange", "VARCHAR"),
        ],
        [
            (
                snapshot_id,
                "000001.SZ",
                "000001",
                "平安银行",
                "20210104",
                None,
                "L",
                "主板",
                "SZ",
            )
        ],
    )

    write_parquet(
        warehouse_root / "core" / "calendar.parquet",
        [
            ("trade_date", "VARCHAR"),
            ("prev_trade_date", "VARCHAR"),
            ("next_trade_date", "VARCHAR"),
            ("next_trade_date_1", "VARCHAR"),
            ("next_trade_date_5", "VARCHAR"),
            ("year", "BIGINT"),
            ("month", "BIGINT"),
            ("is_week_end", "BOOLEAN"),
            ("is_month_end", "BOOLEAN"),
        ],
        [
            ("20210104", None, "20210105", "20210105", "20210111", 2021, 1, False, False),
            ("20210105", "20210104", "20210106", "20210106", "20210112", 2021, 1, False, False),
        ],
    )

    if include_st_interval:
        write_parquet(
            warehouse_root / "state" / "st_status_interval.parquet",
            [
                ("snapshot_id", "VARCHAR"),
                ("ts_code", "VARCHAR"),
                ("name", "VARCHAR"),
                ("start_date", "VARCHAR"),
                ("end_date", "VARCHAR"),
                ("effective_start_date", "VARCHAR"),
                ("effective_end_date", "VARCHAR"),
                ("ann_date", "VARCHAR"),
                ("change_reason", "VARCHAR"),
                ("st_source", "VARCHAR"),
                ("st_inference_method", "VARCHAR"),
            ],
            [
                (
                    snapshot_id,
                    "000001.SZ",
                    "*ST平安",
                    "20210104",
                    "20991231",
                    "20210104",
                    "20991231",
                    "20210103",
                    "ST",
                    "namechange",
                    "contains_ST",
                )
            ],
        )

    run_input_contract = tmp_path / "run_input_contract.json"
    run_input_contract.write_text(
        json.dumps(
            {
                "snapshot_id": snapshot_id,
                "source_root": {
                    "snapshot_path": snapshot_root.as_posix(),
                },
                "notes": [
                    "trainval_only research snapshot",
                    "test window excluded by construction",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return snapshot_root, run_input_contract


def test_builder_marks_missing_source_fields_without_fabrication(tmp_path: Path) -> None:
    module = load_module(MODULE_PATH, "build_data_field_enrichment_v1_test")
    _, run_input_contract = build_snapshot_fixture(
        tmp_path,
        is_st=False,
        include_st_interval=False,
    )
    output_dir = tmp_path / "output"

    result = module.build_data_field_enrichment_v1(
        field_contract_path=FIELD_CONTRACT_PATH.resolve(),
        run_input_contract_path=run_input_contract,
        output_dir=output_dir,
    )

    summary = result["field_coverage_summary"]
    assert summary["row_count"] == 1
    assert summary["pass_fields"]
    assert "snapshot_id" in summary["pass_fields"]
    assert "entry_buyable" in summary["pass_fields"]
    assert "st_effective_start" in summary["missing_source_fields"]
    assert "st_effective_end" in summary["missing_source_fields"]
    assert "st_source" in summary["missing_source_fields"]

    build_audit = result["build_audit"]
    field_records = {record["field_name"]: record for record in build_audit["field_records"]}
    assert field_records["st_effective_start"]["source_status"] == "missing_source"
    assert field_records["st_effective_start"]["null_count"] == 1
    assert field_records["entry_buyable"]["source_status"] == "pass"
    assert result["output_parquet_path"].exists()
