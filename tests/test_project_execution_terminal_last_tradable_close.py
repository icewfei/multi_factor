from __future__ import annotations

import json
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
                ('snap', 'AAA.SZ', '20210101', '20210104', '20210111', NULL, NULL, NULL, NULL, NULL, 'terminal_event_unpriced', NULL, TRUE, 'delist', '20210110', 'no_terminal_pricing_source', FALSE, FALSE),
                ('snap', 'BBB.SZ', '20210102', '20210105', '20210112', NULL, NULL, NULL, NULL, NULL, 'exit_unresolved', NULL, FALSE, NULL, NULL, NULL, FALSE, FALSE)
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
                event_detail_json VARCHAR
            )
            """
        )
        con.execute(
            """
            INSERT INTO serving.vw_terminal_event_daily VALUES
                ('snap', 'AAA.SZ', '20210110', TRUE, 'delist', 'delist', '20210110', '20210110', '20210107', NULL, FALSE, 'test', 'degraded', TRUE, 'degraded', '{}'),
                ('snap', 'BBB.SZ', '20210108', TRUE, 'delist', 'delist', '20210108', '20210108', '20210107', NULL, FALSE, 'test', 'degraded', TRUE, 'degraded', '{}')
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
                ('snap', 'AAA.SZ', '20210101', '20210104', '20210111', 10.0, 10.3, 1.0, 1.0, 10.0, 10.3, TRUE, 0.03, 0.03, NULL),
                ('snap', 'BBB.SZ', '20210102', '20210105', '20210112', 10.0, 10.3, 1.0, 1.0, 10.0, 10.3, TRUE, 0.03, 0.03, NULL)
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
            CREATE TABLE serving.vw_bars_daily (
                snapshot_id VARCHAR,
                ts_code VARCHAR,
                trade_date VARCHAR
            )
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
                ('20210107'),
                ('20210108'),
                ('20210111'),
                ('20210112')
            """
        )
    finally:
        con.close()


def test_project_execution_panel_consumes_repaired_terminal_event_candidate(tmp_path: Path) -> None:
    module = load_module(
        "scripts/build_project_panels.py",
        "build_project_panels_terminal_last_close",
    )

    source_db = tmp_path / "warehouse.duckdb"
    build_source_db(source_db)

    candidate_path = tmp_path / "candidate.json"
    candidate_payload = {
        "artifact_status": "repaired_terminal_event_candidate_only",
        "source_approval_audit": "tmp",
        "pricing_policy_version": "terminal_exit_policy_v1",
        "summary": {
            "total_rows_in_source_audit": 2,
            "candidate_rows_count": 2,
            "still_hard_blocker_count": 2,
            "priced_rows_count": 0,
        },
        "rows": [
            {
                "snapshot_id": "snap",
                "instrument": "AAA.SZ",
                "signal_date": "20210101",
                "entry_date": "20210104",
                "planned_exit_date": "20210111",
                "terminal_event_date": "20210110",
                "terminal_event_type": "delist",
                "approval_origin_case": "no_terminal_pricing_source",
                "approval_evidence_case": "degraded_terminal_source_with_auditable_bars",
                "candidate_target_state": "repaired_terminal_event_candidate",
                "approved_terminal_pricing_path": "terminal_priced_last_tradable_close",
                "candidate_pricing_date": "20210107",
                "candidate_last_tradable_close": 10.5,
                "candidate_adj_factor": 1.05,
                "candidate_volume": 100000.0,
                "pricing_policy_version": "terminal_exit_policy_v1",
                "terminal_event_source_degraded_flag": True,
                "terminal_exit_approximation_flag": False,
                "source_repair_flag": True,
                "terminal_event_bridge_required_flag": False,
                "required_candidate_flags": ["terminal_event_source_degraded_flag", "source_repair_flag"],
                "still_hard_blocker": True,
                "candidate_notes": ["candidate only"]
            },
            {
                "snapshot_id": "snap",
                "instrument": "BBB.SZ",
                "signal_date": "20210102",
                "entry_date": "20210105",
                "planned_exit_date": "20210112",
                "terminal_event_date": "20210108",
                "terminal_event_type": "delist",
                "approval_origin_case": "terminal_event_bridge_required",
                "approval_evidence_case": "declared_last_tradable_date_suspended",
                "candidate_target_state": "repaired_terminal_event_candidate",
                "approved_terminal_pricing_path": "terminal_priced_last_tradable_close",
                "candidate_pricing_date": "20210107",
                "candidate_last_tradable_close": 9.5,
                "candidate_adj_factor": 1.05,
                "candidate_volume": 50000.0,
                "pricing_policy_version": "terminal_exit_policy_v1",
                "terminal_event_source_degraded_flag": True,
                "terminal_exit_approximation_flag": True,
                "source_repair_flag": True,
                "terminal_event_bridge_required_flag": True,
                "required_candidate_flags": [
                    "terminal_event_source_degraded_flag",
                    "terminal_exit_approximation_flag",
                    "source_repair_flag",
                    "terminal_event_bridge_required",
                ],
                "still_hard_blocker": True,
                "candidate_notes": ["candidate only"]
            }
        ],
        "notes": [],
    }
    candidate_path.write_text(json.dumps(candidate_payload, indent=2) + "\n", encoding="utf-8")

    ctx = module.BuildContext(
        run_id="run",
        snapshot_id="snap",
        source_db_path=source_db,
        output_dir=tmp_path,
        run_input_contract_path=REPO_ROOT / "contracts" / "run_input_contract.current.json",
        repaired_terminal_event_candidate_path=candidate_path,
        run_input_contract={"snapshot_id": "snap"},
        field_mapping=module.load_yaml(REPO_ROOT / "contracts" / "source_field_mapping.yaml"),
        table_mapping=module.load_yaml(REPO_ROOT / "contracts" / "source_table_mapping.yaml"),
    )

    with duckdb.connect(str(source_db), read_only=True) as con:
        table = module.build_project_execution_panel(con, ctx)

    rows = {row["instrument"]: row for row in table.to_pylist()}

    aaa = rows["AAA.SZ"]
    assert aaa["execution_path_status"] == "terminal_priced_last_tradable_close"
    assert aaa["actual_exit_date"] == "20210107"
    assert aaa["actual_exit_event_type"] == "TERMINAL_LAST_CLOSE"
    assert aaa["actual_exit_price_field"] == "close"
    assert aaa["actual_sell_price"] == 10.5
    assert aaa["pricing_policy_version"] == "terminal_exit_policy_v1"
    assert aaa["source_repair_flag"] is True
    assert aaa["terminal_exit_approximation_flag"] is False
    assert aaa["terminal_exit_conservative_flag"] is False
    assert abs(aaa["execution_delayed_realized_return"] - 0.1025) < 1e-9
    assert aaa["exit_delay_days"] == -2

    bbb = rows["BBB.SZ"]
    assert bbb["execution_path_status"] == "terminal_priced_last_tradable_close"
    assert bbb["actual_exit_date"] == "20210107"
    assert bbb["actual_sell_price"] == 9.5
    assert bbb["terminal_event_flag"] is True
    assert bbb["terminal_event_type"] == "delist"
    assert bbb["terminal_event_date"] == "20210108"
    assert bbb["terminal_exit_pricing_method"] == "last_tradable_close"
    assert bbb["source_repair_flag"] is True
    assert bbb["terminal_exit_approximation_flag"] is True
    assert bbb["terminal_exit_conservative_flag"] is False
    assert abs(bbb["execution_delayed_realized_return"] - (-0.0025)) < 1e-9
    assert bbb["exit_delay_days"] == -3
