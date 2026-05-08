from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

from conftest import REPO_ROOT

SCRIPT_PATH = "scripts/audit_terminal_event_source_repair.py"


def _make_audit_diagnosis_row(
    instrument: str,
    signal_date: str,
    terminal_event_date: str,
    declared_ltd: str,
    degraded: bool = True,
    execution_path_status: str = "terminal_event_unpriced",
) -> dict:
    return {
        "snapshot_id": "test_snapshot_001",
        "instrument": instrument,
        "signal_date": signal_date,
        "entry_date": "20210104",
        "planned_exit_date": "20210111",
        "execution_path_status": execution_path_status,
        "terminal_event_flag": True,
        "terminal_event_type": "delist",
        "terminal_event_date": terminal_event_date,
        "terminal_exit_pricing_method": "no_terminal_pricing_source",
        "terminal_event_source": {
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

        # 4 degraded-source instruments: close data exists on declared LTD 20210107,
        # not suspended, not no_trade
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

        # 6 suspended-date instruments: declared LTD 20210108 is suspended,
        # actual last trade date 20210107 has bars and is tradable
        for i in range(6):
            inst = f"SUS{i:03d}.SZ"
            # actual last trade date has bars
            con.execute(
                f"""
                INSERT INTO serving.vw_bars_daily VALUES
                ('{inst}', '20210107', 10.0, 10.5, 1.05, 50000.0, 500000.0)
                """
            )
            # declared LTD is suspended
            con.execute(
                f"""
                INSERT INTO serving.vw_tradability_daily VALUES
                ('{inst}', '20210108', TRUE, FALSE, TRUE)
                """
            )
            # actual last trade date is tradable
            con.execute(
                f"""
                INSERT INTO serving.vw_tradability_daily VALUES
                ('{inst}', '20210107', FALSE, FALSE, TRUE)
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
                execution_path_status="terminal_event_unpriced",
            )
        )
    for i in range(6):
        rows.append(
            _make_audit_diagnosis_row(
                instrument=f"SUS{i:03d}.SZ",
                signal_date=f"2021011{i+1}",
                terminal_event_date="20210110",
                declared_ltd="20210108",
                execution_path_status="terminal_event_unpriced",
            )
        )
    # Add 2 exit_unresolved rows that should NOT be processed
    for i in range(2):
        rows.append(
            _make_audit_diagnosis_row(
                instrument=f"EXU{i:03d}.SZ",
                signal_date=f"2021012{i+1}",
                terminal_event_date="20210110",
                declared_ltd="20210107",
                execution_path_status="exit_unresolved",
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
    output_path = tmp_path / "repair_audit.json"
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


# --- valid JSON ---

def test_audit_output_is_valid_json(audit_output: dict) -> None:
    assert audit_output["audit_status"] == "terminal_event_source_repair_audit_only"
    assert audit_output["summary"]["total_rows"] == 10


# --- only terminal_event_unpriced, not exit_unresolved ---

def test_only_terminal_event_unpriced_rows_audited(audit_output: dict) -> None:
    for row in audit_output["rows"]:
        assert "exit_unresolved" not in str(row.get("repair_case", ""))


def test_exit_unresolved_rows_excluded(audit_output: dict) -> None:
    instruments = {row["instrument"] for row in audit_output["rows"]}
    assert "EXU000.SZ" not in instruments
    assert "EXU001.SZ" not in instruments


# --- both repair cases present ---

def test_both_repair_cases_present(audit_output: dict) -> None:
    cases = {row["repair_case"] for row in audit_output["rows"]}
    assert "degraded_terminal_source_with_auditable_bars" in cases
    assert "declared_last_tradable_date_suspended" in cases
    assert len(cases) == 2


def test_degraded_case_count_is_4(audit_output: dict) -> None:
    degraded = [
        r for r in audit_output["rows"]
        if r["repair_case"] == "degraded_terminal_source_with_auditable_bars"
    ]
    assert len(degraded) == 4


def test_suspended_case_count_is_6(audit_output: dict) -> None:
    suspended = [
        r for r in audit_output["rows"]
        if r["repair_case"] == "declared_last_tradable_date_suspended"
    ]
    assert len(suspended) == 6


# --- all rows still_hard_blocker=true ---

def test_all_rows_still_hard_blocker_true(audit_output: dict) -> None:
    for row in audit_output["rows"]:
        assert row["still_hard_blocker"] is True, (
            f"{row['instrument']} still_hard_blocker should be True"
        )


# --- all rows can_emit_terminal_priced_last_tradable_close=false ---

def test_all_rows_cannot_emit_terminal_priced(audit_output: dict) -> None:
    for row in audit_output["rows"]:
        assert row["can_emit_terminal_priced_last_tradable_close"] is False, (
            f"{row['instrument']} can_emit should be False"
        )


# --- zero recovery not enabled ---

def test_zero_recovery_not_enabled(audit_output: dict) -> None:
    for row in audit_output["rows"]:
        assert "zero_recovery_enabled" not in row
        assert "zero_recovery_recommended" not in row
    assert audit_output.get("zero_recovery_enabled") is None
    assert audit_output.get("enable_zero_recovery") is None


# --- no actual_exit_date backfill ---

def test_no_actual_exit_date_backfilled(audit_output: dict) -> None:
    for row in audit_output["rows"]:
        assert "actual_exit_date" not in row


def test_no_actual_sell_price(audit_output: dict) -> None:
    for row in audit_output["rows"]:
        assert "actual_sell_price" not in row


# --- summary counts ---

def test_summary_total_rows_is_10(audit_output: dict) -> None:
    assert audit_output["summary"]["total_rows"] == 10


def test_summary_degraded_count_is_4(audit_output: dict) -> None:
    assert audit_output["summary"]["degraded_terminal_source_with_auditable_bars_count"] == 4


def test_summary_suspended_count_is_6(audit_output: dict) -> None:
    assert audit_output["summary"]["declared_last_tradable_date_suspended_count"] == 6


def test_summary_still_hard_blocker_count_is_10(audit_output: dict) -> None:
    assert audit_output["summary"]["still_hard_blocker_count"] == 10


def test_summary_can_emit_count_is_0(audit_output: dict) -> None:
    assert audit_output["summary"]["can_emit_terminal_priced_last_tradable_close_count"] == 0


def test_summary_counts_consistent(audit_output: dict) -> None:
    s = audit_output["summary"]
    assert s["degraded_terminal_source_with_auditable_bars_count"] + s["declared_last_tradable_date_suspended_count"] == s["total_rows"]


# --- required fields per row ---

def test_all_rows_have_required_fields(audit_output: dict) -> None:
    required = [
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
    for row in audit_output["rows"]:
        for field in required:
            assert field in row, f"Missing field '{field}' in row {row.get('instrument')}"


def test_degraded_rows_have_close_data(audit_output: dict) -> None:
    degraded = [
        r for r in audit_output["rows"]
        if r["repair_case"] == "degraded_terminal_source_with_auditable_bars"
    ]
    for row in degraded:
        assert row["last_tradable_close"] is not None, f"{row['instrument']} degraded row missing last_tradable_close"
        assert row["adj_factor"] is not None, f"{row['instrument']} degraded row missing adj_factor"
        assert row["volume"] is not None, f"{row['instrument']} degraded row missing volume"
        assert row["actual_last_tradable_date"] == row["declared_last_tradable_date"]


def test_suspended_rows_have_inferred_actual_date(audit_output: dict) -> None:
    suspended = [
        r for r in audit_output["rows"]
        if r["repair_case"] == "declared_last_tradable_date_suspended"
    ]
    for row in suspended:
        assert row["actual_last_tradable_date"] is not None
        assert row["actual_last_tradable_date"] != row["declared_last_tradable_date"]
        assert row["last_tradable_close"] is not None
        assert row["adj_factor"] is not None
        assert row["volume"] is not None


def test_all_rows_have_required_next_step(audit_output: dict) -> None:
    for row in audit_output["rows"]:
        assert row["required_next_step"] is not None
        assert len(row["required_next_step"]) > 0


def test_degraded_rows_next_step_mentions_source_repair(audit_output: dict) -> None:
    degraded = [
        r for r in audit_output["rows"]
        if r["repair_case"] == "degraded_terminal_source_with_auditable_bars"
    ]
    for row in degraded:
        assert "source_repair" in row["required_next_step"].lower()


def test_suspended_rows_next_step_mentions_date_discrepancy(audit_output: dict) -> None:
    suspended = [
        r for r in audit_output["rows"]
        if r["repair_case"] == "declared_last_tradable_date_suspended"
    ]
    for row in suspended:
        assert "date_discrepancy" in row["required_next_step"].lower()


# --- notes ---

def test_audit_has_notes(audit_output: dict) -> None:
    assert "notes" in audit_output
    assert isinstance(audit_output["notes"], list)
    assert len(audit_output["notes"]) > 0


def test_notes_mention_no_price_output(audit_output: dict) -> None:
    notes_text = " ".join(audit_output["notes"]).lower()
    assert "does not implement repair logic" in notes_text or "does not implement" in notes_text


# --- schema-aligned fields ---

def test_all_rows_have_snapshot_id(audit_output: dict) -> None:
    for row in audit_output["rows"]:
        assert row["snapshot_id"] is not None


def test_all_rows_have_terminal_event_type(audit_output: dict) -> None:
    for row in audit_output["rows"]:
        assert "terminal_event_type" in row


def test_repair_policy_version_present(audit_output: dict) -> None:
    assert audit_output["repair_policy_version"] == "terminal_event_source_repair_plan_v1"


# --- flag assignments per repair case ---

def test_degraded_rows_have_source_degraded_flag_true(audit_output: dict) -> None:
    degraded = [
        r for r in audit_output["rows"]
        if r["repair_case"] == "degraded_terminal_source_with_auditable_bars"
    ]
    for row in degraded:
        assert row["terminal_event_source_degraded_flag"] is True
        assert row["terminal_exit_approximation_flag"] is False
        assert row["source_repair_flag"] is False


def test_suspended_rows_have_approximation_and_repair_flags_true(audit_output: dict) -> None:
    suspended = [
        r for r in audit_output["rows"]
        if r["repair_case"] == "declared_last_tradable_date_suspended"
    ]
    for row in suspended:
        assert row["terminal_event_source_degraded_flag"] is False
        assert row["terminal_exit_approximation_flag"] is True
        assert row["source_repair_flag"] is True


# --- declared_actual_ltd_diff_days ---

def test_degraded_rows_have_zero_diff_days(audit_output: dict) -> None:
    degraded = [
        r for r in audit_output["rows"]
        if r["repair_case"] == "degraded_terminal_source_with_auditable_bars"
    ]
    for row in degraded:
        assert row["declared_actual_ltd_diff_days"] == 0


def test_suspended_rows_have_positive_diff_days(audit_output: dict) -> None:
    suspended = [
        r for r in audit_output["rows"]
        if r["repair_case"] == "declared_last_tradable_date_suspended"
    ]
    for row in suspended:
        assert row["declared_actual_ltd_diff_days"] is not None
        assert row["declared_actual_ltd_diff_days"] > 0


# --- last_tradable_close is not actual_sell_price ---

def test_no_actual_sell_price_field(audit_output: dict) -> None:
    for row in audit_output["rows"]:
        assert "actual_sell_price" not in row


# --- actual_last_tradable_date is not actual_exit_date ---

def test_no_actual_exit_date_field(audit_output: dict) -> None:
    for row in audit_output["rows"]:
        assert "actual_exit_date" not in row
