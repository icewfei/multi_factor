from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb
import jsonschema
import pytest

from conftest import REPO_ROOT, load_json

SCRIPT_PATH = "scripts/audit_terminal_last_tradable_close.py"
SCHEMA_PATH = "schemas/terminal_last_tradable_close_approval.schema.json"


def _make_audit_diagnosis_row(
    instrument: str,
    signal_date: str,
    terminal_event_date: str,
    declared_ltd: str,
    pricing_method: str,
    degraded: bool = True,
) -> dict:
    return {
        "snapshot_id": "snap",
        "instrument": instrument,
        "signal_date": signal_date,
        "entry_date": "20210104",
        "planned_exit_date": "20210111",
        "execution_path_status": "terminal_event_unpriced",
        "terminal_event_flag": True,
        "terminal_event_type": "delist",
        "terminal_event_date": terminal_event_date,
        "terminal_exit_pricing_method": pricing_method,
        "terminal_event_source": {
            "snapshot_id": "snap",
            "last_tradable_date": declared_ltd,
            "contract_degraded_flag": degraded,
            "contract_degraded_reason": "source contract degraded",
        },
    }


@pytest.fixture
def source_db_path(tmp_path: Path) -> Path:
    db_path = tmp_path / "duckdb" / "warehouse.duckdb"
    db_path.parent.mkdir(parents=True)
    con = duckdb.connect(str(db_path))
    try:
        con.execute("CREATE SCHEMA serving")

        con.execute("""
            CREATE TABLE serving.vw_bars_daily (
                ts_code VARCHAR, trade_date VARCHAR, close DOUBLE, adj_close DOUBLE,
                adj_factor DOUBLE, vol DOUBLE, amount DOUBLE
            )
        """)
        con.execute("""
            CREATE TABLE serving.vw_tradability_daily (
                ts_code VARCHAR, trade_date VARCHAR,
                is_suspended_t BOOLEAN, no_trade_t BOOLEAN, is_listed_t BOOLEAN
            )
        """)
        con.execute("""
            CREATE TABLE serving.vw_terminal_event_daily (
                ts_code VARCHAR, event_date VARCHAR, contract_degraded_reason VARCHAR
            )
        """)

        for i in range(4):
            inst = f"DEG{i:03d}.SZ"
            con.execute(
                f"""
                INSERT INTO serving.vw_bars_daily VALUES
                ('{inst}', '20210107', 10.5, 11.0, 1.05, 100000.0, 1050000.0)
                """
            )
            con.execute(
                f"""
                INSERT INTO serving.vw_tradability_daily VALUES
                ('{inst}', '20210107', FALSE, FALSE, TRUE)
                """
            )
            con.execute(
                f"""
                INSERT INTO serving.vw_terminal_event_daily VALUES
                ('{inst}', '20210110', 'source contract degraded')
                """
            )

        for i in range(6):
            inst = f"SUS{i:03d}.SZ"
            con.execute(
                f"""
                INSERT INTO serving.vw_bars_daily VALUES
                ('{inst}', '20210107', 10.0, 10.5, 1.05, 50000.0, 500000.0)
                """
            )
            con.execute(
                f"""
                INSERT INTO serving.vw_tradability_daily VALUES
                ('{inst}', '20210108', TRUE, FALSE, TRUE)
                """
            )
            con.execute(
                f"""
                INSERT INTO serving.vw_tradability_daily VALUES
                ('{inst}', '20210107', FALSE, FALSE, TRUE)
                """
            )
            con.execute(
                f"""
                INSERT INTO serving.vw_terminal_event_daily VALUES
                ('{inst}', '20210110', 'source contract degraded')
                """
            )
    finally:
        con.close()
    return db_path


@pytest.fixture
def run_input_contract_path(tmp_path: Path) -> Path:
    path = tmp_path / "run_input_contract.json"
    path.write_text(
        json.dumps(
            {"source_root": {"snapshot_path": str(tmp_path)}},
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def diagnosis_path(tmp_path: Path) -> str:
    rows = []
    for i in range(4):
        rows.append(
            _make_audit_diagnosis_row(
                instrument=f"DEG{i:03d}.SZ",
                signal_date=f"2021010{i+1}",
                terminal_event_date="20210110",
                declared_ltd="20210107",
                pricing_method="terminal_event_bridge_required" if i < 2 else "no_terminal_pricing_source",
            )
        )
    for i in range(6):
        rows.append(
            _make_audit_diagnosis_row(
                instrument=f"SUS{i:03d}.SZ",
                signal_date=f"2021011{i+1}",
                terminal_event_date="20210110",
                declared_ltd="20210108",
                pricing_method="terminal_event_bridge_required" if i < 3 else "no_terminal_pricing_source",
            )
        )
    path = tmp_path / "diagnosis.json"
    path.write_text(
        json.dumps({"rows": rows}, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return str(path)


@pytest.fixture
def audit_output(
    tmp_path: Path,
    diagnosis_path: str,
    run_input_contract_path: Path,
    source_db_path: Path,
) -> dict:
    output_path = tmp_path / "audit.json"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / SCRIPT_PATH),
            "--diagnosis-json", diagnosis_path,
            "--run-input-contract", str(run_input_contract_path),
            "--output", str(output_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"Script failed: {result.stderr}"
    return json.loads(output_path.read_text(encoding="utf-8"))


def test_audit_output_is_valid_json(audit_output: dict) -> None:
    assert audit_output["audit_status"] == "terminal_last_tradable_close_approval_audit_only"
    assert audit_output["approval_policy_version"] == "terminal_exit_policy_v1"


def test_audit_output_conforms_to_schema(audit_output: dict) -> None:
    schema = load_json(SCHEMA_PATH)
    jsonschema.validate(audit_output, schema)


def test_all_rows_still_hard_blockers(audit_output: dict) -> None:
    for row in audit_output["rows"]:
        assert row["still_hard_blocker"] is True
        assert row["zero_recovery_approved"] is False


def test_no_actual_exit_fields_are_backfilled(audit_output: dict) -> None:
    row_props = load_json(SCHEMA_PATH)["properties"]["rows"]["items"]["properties"]
    assert "actual_exit_date" not in row_props
    assert "actual_sell_price" not in row_props
    assert "execution_delayed_realized_return" not in row_props


def test_all_fixture_rows_pass_candidate_approval_gate(audit_output: dict) -> None:
    assert audit_output["summary"]["candidate_rows_count"] == 10
    assert audit_output["summary"]["approval_gate_passed_count"] == 10
    assert audit_output["summary"]["approval_gate_failed_count"] == 0
    for row in audit_output["rows"]:
        assert row["approval_gate_passed"] is True
        assert row["approved_for_repaired_terminal_event_candidate"] is True
        assert row["candidate_target_state"] == "repaired_terminal_event_candidate"
        assert row["approved_terminal_pricing_path"] == "terminal_priced_last_tradable_close"


def test_summary_distinguishes_bridge_and_evidence_cases(audit_output: dict) -> None:
    summary = audit_output["summary"]
    assert summary["terminal_event_bridge_required_count"] == 5
    assert summary["degraded_terminal_source_with_auditable_bars_count"] == 4
    assert summary["declared_last_tradable_date_suspended_count"] == 6
    assert summary["still_hard_blocker_count"] == 10


def test_degraded_rows_use_declared_last_tradable_date(audit_output: dict) -> None:
    degraded_rows = [
        row
        for row in audit_output["rows"]
        if row["approval_evidence_case"] == "degraded_terminal_source_with_auditable_bars"
    ]
    assert len(degraded_rows) == 4
    for row in degraded_rows:
        assert row["terminal_exit_approximation_flag"] is False
        assert row["source_repair_flag"] is True
        assert row["candidate_pricing_date"] == row["declared_last_tradable_date"]
        assert row["candidate_last_tradable_close"] == 10.5
        assert "terminal_event_source_degraded_flag" in row["required_candidate_flags"]


def test_suspended_rows_use_actual_last_trade_date_with_flags(audit_output: dict) -> None:
    suspended_rows = [
        row
        for row in audit_output["rows"]
        if row["approval_evidence_case"] == "declared_last_tradable_date_suspended"
    ]
    assert len(suspended_rows) == 6
    for row in suspended_rows:
        assert row["terminal_exit_approximation_flag"] is True
        assert row["source_repair_flag"] is True
        assert row["actual_last_trade_date_in_bars"] == "20210107"
        assert row["candidate_pricing_date"] == "20210107"
        assert row["candidate_last_tradable_close"] == 10.0
        assert "terminal_exit_approximation_flag" in row["required_candidate_flags"]
        assert "source_repair_flag" in row["required_candidate_flags"]


def test_bridge_rows_retain_bridge_marker_requirement(audit_output: dict) -> None:
    bridge_rows = [row for row in audit_output["rows"] if row["terminal_event_bridge_required_flag"]]
    assert len(bridge_rows) == 5
    for row in bridge_rows:
        assert row["approval_origin_case"] == "terminal_event_bridge_required"
        assert "terminal_event_bridge_required" in row["required_candidate_flags"]


def test_notes_state_candidate_not_equal_priced_exit(audit_output: dict) -> None:
    notes = "\n".join(audit_output["notes"])
    assert "does not mean the row is priced" in notes
    assert "zero_recovery remains disabled by default" in notes
