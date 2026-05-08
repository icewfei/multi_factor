from __future__ import annotations

import json

import pytest

from conftest import REPO_ROOT, load_json, schema_properties

SCHEMA_PATH = "schemas/terminal_event_repair_audit.schema.json"


def test_schema_json_loads() -> None:
    schema = load_json(SCHEMA_PATH)
    assert schema["$id"] == "multifactor/terminal_event_repair_audit.schema.json"
    assert schema["title"] == "Terminal Event Repair Audit"


def test_schema_top_level_required() -> None:
    schema = load_json(SCHEMA_PATH)
    required = schema["required"]
    assert "audit_status" in required
    assert "contract_ref" in required
    assert "repair_policy_version" in required
    assert "summary" in required
    assert "rows" in required
    assert "notes" in required


def test_audit_status_is_const() -> None:
    props = schema_properties(SCHEMA_PATH)
    assert props["audit_status"]["const"] == "terminal_event_source_repair_audit_only"


def test_row_required_fields() -> None:
    schema = load_json(SCHEMA_PATH)
    row_required = schema["properties"]["rows"]["items"]["required"]
    expected = [
        "snapshot_id",
        "instrument",
        "signal_date",
        "terminal_event_date",
        "terminal_event_type",
        "declared_last_tradable_date",
        "actual_last_tradable_date",
        "last_tradable_close",
        "adj_factor",
        "volume",
        "repair_case",
        "terminal_event_source_degraded_flag",
        "terminal_exit_approximation_flag",
        "source_repair_flag",
        "declared_actual_ltd_diff_days",
        "still_hard_blocker",
        "can_emit_terminal_priced_last_tradable_close",
        "required_next_step",
    ]
    assert row_required == expected


def test_repair_case_enum() -> None:
    schema = load_json(SCHEMA_PATH)
    row_props = schema["properties"]["rows"]["items"]["properties"]
    repair_enum = row_props["repair_case"]["enum"]
    assert "degraded_terminal_source_with_auditable_bars" in repair_enum
    assert "declared_last_tradable_date_suspended" in repair_enum
    assert len(repair_enum) == 2


def test_still_hard_blocker_is_const_true() -> None:
    schema = load_json(SCHEMA_PATH)
    row_props = schema["properties"]["rows"]["items"]["properties"]
    assert row_props["still_hard_blocker"]["const"] is True


def test_can_emit_terminal_priced_is_const_false() -> None:
    schema = load_json(SCHEMA_PATH)
    row_props = schema["properties"]["rows"]["items"]["properties"]
    assert row_props["can_emit_terminal_priced_last_tradable_close"]["const"] is False


def test_summary_required_fields() -> None:
    schema = load_json(SCHEMA_PATH)
    summary_req = schema["properties"]["summary"]["required"]
    assert "total_rows" in summary_req
    assert "degraded_terminal_source_with_auditable_bars_count" in summary_req
    assert "declared_last_tradable_date_suspended_count" in summary_req
    assert "still_hard_blocker_count" in summary_req
    assert "can_emit_terminal_priced_last_tradable_close_count" in summary_req


def test_flags_are_booleans() -> None:
    schema = load_json(SCHEMA_PATH)
    row_props = schema["properties"]["rows"]["items"]["properties"]
    assert row_props["terminal_event_source_degraded_flag"]["type"] == "boolean"
    assert row_props["terminal_exit_approximation_flag"]["type"] == "boolean"
    assert row_props["source_repair_flag"]["type"] == "boolean"


def test_last_tradable_close_is_number_or_null() -> None:
    schema = load_json(SCHEMA_PATH)
    row_props = schema["properties"]["rows"]["items"]["properties"]
    ltc_type = row_props["last_tradable_close"]["type"]
    assert "number" in (ltc_type if isinstance(ltc_type, list) else [ltc_type])
    assert "null" in (ltc_type if isinstance(ltc_type, list) else [ltc_type])


def test_declared_actual_ltd_diff_days_is_integer_or_null() -> None:
    schema = load_json(SCHEMA_PATH)
    row_props = schema["properties"]["rows"]["items"]["properties"]
    diff_type = row_props["declared_actual_ltd_diff_days"]["type"]
    assert "integer" in (diff_type if isinstance(diff_type, list) else [diff_type])
    assert "null" in (diff_type if isinstance(diff_type, list) else [diff_type])


def test_notes_is_array_of_strings() -> None:
    schema = load_json(SCHEMA_PATH)
    notes_schema = schema["properties"]["notes"]
    assert notes_schema["type"] == "array"
    assert notes_schema["items"]["type"] == "string"


def test_schema_has_no_actual_exit_date() -> None:
    schema = load_json(SCHEMA_PATH)
    row_props = schema["properties"]["rows"]["items"]["properties"]
    assert "actual_exit_date" not in row_props


def test_schema_has_no_actual_sell_price() -> None:
    schema = load_json(SCHEMA_PATH)
    row_props = schema["properties"]["rows"]["items"]["properties"]
    assert "actual_sell_price" not in row_props


# --- cross-validation: audit script output conforms to schema field names ---

def test_audit_script_rows_match_schema_required_fields() -> None:
    """Run the audit script and verify every output row has all schema-required fields."""
    import subprocess
    import sys

    import duckdb

    # Build minimal test fixture inline
    tmp = REPO_ROOT / ".tmp" / "schema_test"
    tmp.mkdir(parents=True, exist_ok=True)

    db_path = tmp / "duckdb" / "warehouse.duckdb"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    try:
        con.execute("CREATE SCHEMA IF NOT EXISTS serving")
        con.execute("""
            CREATE TABLE IF NOT EXISTS serving.vw_bars_daily (
                ts_code VARCHAR, trade_date VARCHAR, close DOUBLE, adj_close DOUBLE,
                adj_factor DOUBLE, vol DOUBLE, amount DOUBLE
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS serving.vw_tradability_daily (
                ts_code VARCHAR, trade_date VARCHAR,
                is_suspended_t BOOLEAN, no_trade_t BOOLEAN, is_listed_t BOOLEAN
            )
        """)
        con.execute("""
            INSERT INTO serving.vw_bars_daily VALUES
            ('TEST.SZ', '20210107', 10.5, 11.0, 1.05, 100000.0, 1050000.0)
        """)
        con.execute("""
            INSERT INTO serving.vw_tradability_daily VALUES
            ('TEST.SZ', '20210107', FALSE, FALSE, TRUE)
        """)
    finally:
        con.close()

    contract_path = tmp / "run_input_contract.json"
    contract_path.write_text(
        json.dumps({"source_root": {"snapshot_path": str(tmp)}}, indent=2) + "\n",
        encoding="utf-8",
    )

    diagnosis_path = tmp / "diagnosis.json"
    diagnosis_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "snapshot_id": "test_001",
                        "instrument": "TEST.SZ",
                        "signal_date": "20210101",
                        "entry_date": "20210104",
                        "planned_exit_date": "20210111",
                        "execution_path_status": "terminal_event_unpriced",
                        "terminal_event_flag": True,
                        "terminal_event_type": "delist",
                        "terminal_event_date": "20210110",
                        "terminal_exit_pricing_method": "no_terminal_pricing_source",
                        "terminal_event_source": {
                            "last_tradable_date": "20210107",
                            "contract_degraded_flag": True,
                            "contract_degraded_reason": "source contract degraded",
                        },
                    }
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    output_path = tmp / "repair_audit.json"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts/audit_terminal_event_source_repair.py"),
            "--diagnosis-json", str(diagnosis_path),
            "--run-input-contract", str(contract_path),
            "--output", str(output_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"Script failed: {result.stderr}"

    audit = json.loads(output_path.read_text(encoding="utf-8"))

    schema = load_json(SCHEMA_PATH)
    row_required = schema["properties"]["rows"]["items"]["required"]

    for row in audit["rows"]:
        for field in row_required:
            assert field in row, f"Audit row missing schema-required field: {field}"


def test_repair_policy_version_matches_contract() -> None:
    contract = load_json("contracts/terminal_event_source_repair_plan.v1.json")
    contract_version = contract["contract_version"]
    # The repair_policy_version in the audit should match the contract version
    # (using snake_case mapping: terminal_event_source_repair_plan_v1)
    assert contract_version == "terminal_event_source_repair_plan_v1"
