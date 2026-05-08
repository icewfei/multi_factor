from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

from conftest import REPO_ROOT

SCRIPT_PATH = "scripts/audit_terminal_last_tradable_close.py"


def _make_audit_diagnosis_row(
    instrument: str,
    signal_date: str,
    terminal_event_date: str,
    declared_ltd: str,
    degraded: bool = True,
) -> dict:
    return {
        "instrument": instrument,
        "signal_date": signal_date,
        "entry_date": "20210104",
        "planned_exit_date": "20210111",
        "execution_path_status": "terminal_event_unpriced",
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
    """Create a minimal DuckDB with serving.vw_bars_daily, vw_tradability_daily, vw_terminal_event_daily."""
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

        # 4 degraded-source instruments: close data exists on declared LTD 20210107
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

        # 6 suspended-date instruments: no close on declared LTD 20210108,
        # but close exists on actual last trade date 20210107
        for i in range(6):
            inst = f"SUS{i:03d}.SZ"
            # actual last trade date has bars data
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
    """Create a run_input_contract pointing to the test DuckDB snapshot root."""
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
    """Create a minimal diagnosis JSON with 10 terminal_event_unpriced rows:
    4 degraded source with auditable bars on declared LTD,
    6 suspended declared LTD with actual last trade date earlier."""
    rows = []
    for i in range(4):
        rows.append(
            _make_audit_diagnosis_row(
                instrument=f"DEG{i:03d}.SZ",
                signal_date=f"2021010{i+1}",
                terminal_event_date="20210110",
                declared_ltd="20210107",
            )
        )
    for i in range(6):
        rows.append(
            _make_audit_diagnosis_row(
                instrument=f"SUS{i:03d}.SZ",
                signal_date=f"2021011{i+1}",
                terminal_event_date="20210110",
                declared_ltd="20210108",
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
    assert audit_output["audit_status"] == "last_tradable_close_audit_only"
    assert audit_output["total_terminal_event_unpriced_rows"] == 10


def test_only_terminal_event_unpriced_rows_audited(audit_output: dict) -> None:
    for row in audit_output["rows"]:
        assert "exit_unresolved" not in row.get("blocker_category", "")


def test_zero_recovery_not_enabled(audit_output: dict) -> None:
    assert "zero_recovery" not in audit_output["audit_status"].lower()


def test_no_actual_exit_date_backfilled(audit_output: dict) -> None:
    for row in audit_output["rows"]:
        assert "actual_exit_date" not in row or row.get("actual_exit_date") is None


def test_all_rows_have_can_price_with_last_tradable_close(audit_output: dict) -> None:
    for row in audit_output["rows"]:
        assert "can_price_with_last_tradable_close" in row
        assert isinstance(row["can_price_with_last_tradable_close"], bool)


def test_all_rows_have_last_tradable_close_auditable(audit_output: dict) -> None:
    for row in audit_output["rows"]:
        assert "last_tradable_close_auditable" in row
        assert isinstance(row["last_tradable_close_auditable"], bool)


def test_all_rows_have_blocking_reasons(audit_output: dict) -> None:
    for row in audit_output["rows"]:
        assert "blocking_reasons" in row
        assert isinstance(row["blocking_reasons"], list)
        if not row["can_price_with_last_tradable_close"]:
            assert len(row["blocking_reasons"]) > 0


def test_all_rows_have_contract_degraded_flag(audit_output: dict) -> None:
    for row in audit_output["rows"]:
        assert "contract_degraded_flag" in row
        if row.get("raw_close") is not None:
            assert row["contract_degraded_flag"] is True


def test_no_row_has_can_price_true(audit_output: dict) -> None:
    for row in audit_output["rows"]:
        assert row["can_price_with_last_tradable_close"] is False


def test_all_rows_have_last_tradable_date(audit_output: dict) -> None:
    for row in audit_output["rows"]:
        assert row.get("last_tradable_date_from_terminal_source") is not None


def test_summary_counts_are_consistent(audit_output: dict) -> None:
    total = audit_output["total_terminal_event_unpriced_rows"]
    assert audit_output["auditable_count"] + audit_output["not_auditable_count"] == total
    assert audit_output["not_auditable_count"] == 10
    assert audit_output["auditable_count"] == 0


def test_rows_have_audit_source_information(audit_output: dict) -> None:
    rows_with_close = [r for r in audit_output["rows"] if r.get("raw_close") is not None]
    assert len(rows_with_close) == audit_output["summary"]["rows_with_close_on_declared_ltd"]
    for row in rows_with_close:
        assert row["close_source"] == "vw_bars_daily"
        assert row["close_source_auditable"] is True


def test_suspended_rows_have_actual_last_trade_investigation(audit_output: dict) -> None:
    suspended = [
        r for r in audit_output["rows"]
        if r.get("declared_ltd_is_suspended") or r.get("declared_ltd_is_no_trade")
    ]
    assert len(suspended) == 6
    for row in suspended:
        assert row.get("actual_last_trade_date_in_bars") is not None
        assert row.get("actual_last_trade_date_close_available") is True
