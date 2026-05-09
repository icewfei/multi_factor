from __future__ import annotations

from pathlib import Path

import duckdb

from conftest import REPO_ROOT, load_module


def build_source_db(path: Path) -> None:
    con = duckdb.connect(str(path))
    try:
        con.execute("CREATE SCHEMA serving")
        con.execute(
            """
            CREATE TABLE serving.vw_execution_path_daily (
                snapshot_id VARCHAR,
                ts_code VARCHAR,
                trade_date VARCHAR,
                entry_date_D1 VARCHAR,
                planned_exit_date_D5 VARCHAR,
                actual_exit_date VARCHAR,
                actual_exit_event_type VARCHAR,
                actual_exit_price_field VARCHAR,
                actual_sell_price DOUBLE,
                exit_delay_days BIGINT,
                execution_path_status VARCHAR,
                execution_delayed_realized_return DOUBLE,
                terminal_event_flag BOOLEAN,
                terminal_event_type VARCHAR,
                terminal_event_date VARCHAR,
                terminal_exit_pricing_method VARCHAR,
                terminal_exit_approximation_flag BOOLEAN,
                terminal_exit_conservative_flag BOOLEAN
            )
            """
        )
        con.execute(
            """
            INSERT INTO serving.vw_execution_path_daily VALUES
                ('snap', 'AAA.SZ', '20210106', '20210107', '20210111', NULL, NULL, NULL, NULL, NULL, 'exit_unresolved', NULL, FALSE, NULL, NULL, NULL, FALSE, FALSE),
                ('snap', 'BBB.SZ', '20210106', '20210107', '20210111', NULL, NULL, NULL, NULL, NULL, 'exit_unresolved', NULL, FALSE, NULL, NULL, NULL, FALSE, FALSE),
                ('snap', 'CCC.SZ', '20210106', '20210107', '20210111', NULL, NULL, NULL, NULL, NULL, 'terminal_event_unpriced', NULL, TRUE, 'delist', '20210108', 'no_terminal_pricing_source', TRUE, TRUE)
            """
        )
        con.execute(
            """
            CREATE TABLE serving.vw_terminal_event_daily (
                snapshot_id VARCHAR,
                ts_code VARCHAR,
                event_date VARCHAR,
                terminal_event_type VARCHAR,
                last_trade_date VARCHAR
            )
            """
        )
        con.execute(
            """
            INSERT INTO serving.vw_terminal_event_daily VALUES
                ('snap', 'AAA.SZ', '20210108', 'delist', '20210107'),
                ('snap', 'BBB.SZ', '20210108', 'delist', '20210107'),
                ('snap', 'CCC.SZ', '20210108', 'delist', '20210107')
            """
        )
        con.execute(
            """
            CREATE TABLE serving.vw_tradability_daily (
                snapshot_id VARCHAR,
                ts_code VARCHAR,
                trade_date VARCHAR
            )
            """
        )
        con.execute(
            """
            INSERT INTO serving.vw_tradability_daily VALUES
                ('snap', 'BBB.SZ', '20210112')
            """
        )
        con.execute(
            """
            CREATE TABLE serving.vw_bars_daily (
                snapshot_id VARCHAR,
                ts_code VARCHAR,
                trade_date VARCHAR
            )
            """
        )
        con.execute(
            """
            INSERT INTO serving.vw_bars_daily VALUES
                ('snap', 'BBB.SZ', '20210112')
            """
        )
        con.execute(
            """
            CREATE TABLE serving.vw_labels_daily (
                snapshot_id VARCHAR,
                ts_code VARCHAR,
                trade_date VARCHAR,
                entry_date_D1 VARCHAR,
                planned_exit_date_D5 VARCHAR,
                open_D1 DOUBLE,
                close_D5 DOUBLE,
                adj_factor_D1 DOUBLE,
                adj_factor_D5 DOUBLE,
                adj_open_base_D1 DOUBLE,
                adj_close_base_D5 DOUBLE,
                label_defined BOOLEAN,
                label_5d_next_open_close_raw DOUBLE,
                label_5d_next_open_close DOUBLE,
                label_masked_reason VARCHAR
            )
            """
        )
        con.execute(
            """
            INSERT INTO serving.vw_labels_daily VALUES
                ('snap', 'AAA.SZ', '20210106', '20210107', '20210111', 10.0, 10.5, 1.0, 1.0, 10.0, 10.5, TRUE, 0.05, 0.05, NULL),
                ('snap', 'BBB.SZ', '20210106', '20210107', '20210111', 10.0, 10.5, 1.0, 1.0, 10.0, 10.5, TRUE, 0.05, 0.05, NULL),
                ('snap', 'CCC.SZ', '20210106', '20210107', '20210111', 10.0, 10.5, 1.0, 1.0, 10.0, 10.5, TRUE, 0.05, 0.05, NULL)
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
                ('20210111'),
                ('20210112'),
                ('20210113')
            """
        )
    finally:
        con.close()


def test_project_execution_panel_bridges_post_delist_gap_without_pricing(tmp_path: Path) -> None:
    module = load_module("scripts/build_project_panels.py", "build_project_panels_terminal_bridge")

    source_db = tmp_path / "warehouse.duckdb"
    build_source_db(source_db)

    ctx = module.BuildContext(
        run_id="run",
        snapshot_id="snap",
        source_db_path=source_db,
        output_dir=tmp_path,
        run_input_contract_path=REPO_ROOT / "contracts" / "run_input_contract.current.json",
        repaired_terminal_event_candidate_path=None,
        run_input_contract={"snapshot_id": "snap"},
        field_mapping=module.load_yaml(REPO_ROOT / "contracts" / "source_field_mapping.yaml"),
        table_mapping=module.load_yaml(REPO_ROOT / "contracts" / "source_table_mapping.yaml"),
    )

    with duckdb.connect(str(source_db), read_only=True) as con:
        table = module.build_project_execution_panel(con, ctx)

    rows = {row["instrument"]: row for row in table.to_pylist()}

    bridged = rows["AAA.SZ"]
    assert bridged["execution_path_status"] == "terminal_event_unpriced"
    assert bridged["terminal_event_flag"] is True
    assert bridged["terminal_event_type"] == "delist"
    assert bridged["terminal_event_date"] == "20210108"
    assert bridged["terminal_exit_pricing_method"] == "terminal_event_bridge_required"
    assert bridged["actual_exit_date"] is None
    assert bridged["actual_sell_price"] is None

    unresolved = rows["BBB.SZ"]
    assert unresolved["execution_path_status"] == "exit_unresolved"
    assert unresolved["terminal_event_flag"] is False
    assert unresolved["terminal_event_type"] is None
    assert unresolved["terminal_event_date"] is None
    assert unresolved["terminal_exit_pricing_method"] is None

    existing = rows["CCC.SZ"]
    assert existing["execution_path_status"] == "terminal_event_unpriced"
    assert existing["terminal_event_date"] == "20210108"
    assert existing["terminal_exit_pricing_method"] == "no_terminal_pricing_source"
