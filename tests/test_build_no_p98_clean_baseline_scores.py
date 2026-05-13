from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from conftest import REPO_ROOT


SCRIPT_PATH = "scripts/build_no_p98_clean_baseline_scores.py"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_source_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    try:
        con.execute("CREATE SCHEMA serving")
        con.execute(
            """
            CREATE TABLE serving.vw_bars_daily (
                snapshot_id VARCHAR,
                ts_code VARCHAR,
                trade_date VARCHAR,
                adj_close DOUBLE
            )
            """
        )
        rows = [
            ("snap", "AAA.SZ", "20210101", 10.0),
            ("snap", "AAA.SZ", "20210102", 11.0),
            ("snap", "AAA.SZ", "20210103", 12.0),
            ("snap", "AAA.SZ", "20210104", 13.0),
            ("snap", "AAA.SZ", "20210105", 14.0),
            ("snap", "AAA.SZ", "20210106", 15.0),
            ("snap", "AAA.SZ", "20210107", 16.0),
            ("snap", "BBB.SZ", "20210101", 10.0),
            ("snap", "BBB.SZ", "20210102", 10.0),
            ("snap", "BBB.SZ", "20210103", 10.0),
            ("snap", "BBB.SZ", "20210104", 10.0),
            ("snap", "BBB.SZ", "20210105", 10.0),
            ("snap", "BBB.SZ", "20210106", 9.0),
            ("snap", "BBB.SZ", "20210107", 8.0),
        ]
        con.executemany("INSERT INTO serving.vw_bars_daily VALUES (?, ?, ?, ?)", rows)
    finally:
        con.close()


def write_sample_panel(path: Path, *, include_label_column: bool = False) -> None:
    payload = {
        "snapshot_id": ["snap", "snap", "snap", "snap"],
        "instrument": ["AAA.SZ", "BBB.SZ", "AAA.SZ", "BBB.SZ"],
        "signal_date": ["20210106", "20210106", "20210107", "20210107"],
        "ranking_eligible_D0": [True, True, True, True],
    }
    if include_label_column:
        payload["label_5d_next_open_close"] = [0.1, -0.1, 0.2, -0.2]
    pq.write_table(pa.table(payload), path)


def write_run_input_contract(path: Path, snapshot_root: Path, *, frozen_test_access: bool = False) -> None:
    payload = {
        "snapshot_id": "snap",
        "source_root": {"snapshot_path": str(snapshot_root)},
    }
    if frozen_test_access:
        payload["frozen_test_access"] = True
    write_json(path, payload)


def test_build_no_p98_clean_baseline_scores_success_fixture(tmp_path: Path) -> None:
    snapshot_root = tmp_path / "snapshot"
    build_source_db(snapshot_root / "duckdb" / "warehouse.duckdb")

    sample_panel_path = tmp_path / "project_sample_panel.parquet"
    write_sample_panel(sample_panel_path)

    run_input_contract = tmp_path / "run_input_contract.json"
    write_run_input_contract(run_input_contract, snapshot_root)

    output_dir = tmp_path / "run"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / SCRIPT_PATH),
            "--run-id",
            "no_p98_fixture_run",
            "--project-sample-panel",
            str(sample_panel_path),
            "--run-input-contract",
            str(run_input_contract),
            "--output-dir",
            str(output_dir),
            "--attempt-id",
            "attempt_fixture",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    score_output = output_dir / "model_scores_D0.parquet"
    audit_output = output_dir / "model_scores_D0_audit.json"
    source_chain_output = output_dir / "source_chain_audit.json"
    manifest_output = output_dir / "attempts" / "attempt_fixture" / "run_state_attempt_manifest.json"

    assert score_output.exists()
    assert audit_output.exists()
    assert source_chain_output.exists()
    assert manifest_output.exists()

    con = duckdb.connect()
    try:
        rows = con.execute(
            f"""
            SELECT
                instrument,
                signal_date,
                reversal_5d_raw,
                reversal_rank,
                model_score_D0,
                candidate_scheme_id,
                baseline_id
            FROM read_parquet('{score_output.as_posix()}')
            ORDER BY signal_date, instrument
            """
        ).fetchall()
    finally:
        con.close()

    assert len(rows) == 4
    assert all(row[5] == "no_p98_reversal_baseline_v1" for row in rows)
    assert all(row[6] == "no_p98_reversal_baseline_v1" for row in rows)

    by_key = {(row[0], row[1]): row for row in rows}
    aaa_day6 = by_key[("AAA.SZ", "20210106")]
    bbb_day6 = by_key[("BBB.SZ", "20210106")]
    aaa_day7 = by_key[("AAA.SZ", "20210107")]
    bbb_day7 = by_key[("BBB.SZ", "20210107")]

    assert aaa_day6[2] == pytest.approx(0.5)
    assert bbb_day6[2] == pytest.approx(-0.1)
    assert aaa_day7[2] == pytest.approx((16.0 / 11.0) - 1.0)
    assert bbb_day7[2] == pytest.approx(-0.2)

    assert aaa_day6[3] == pytest.approx(1.0)
    assert bbb_day6[3] == pytest.approx(0.0)
    assert aaa_day7[3] == pytest.approx(1.0)
    assert bbb_day7[3] == pytest.approx(0.0)

    assert aaa_day6[4] == aaa_day6[3]
    assert bbb_day6[4] == bbb_day6[3]

    audit = read_json(audit_output)
    assert audit["candidate_scheme_id"] == "no_p98_reversal_baseline_v1"
    assert audit["baseline_id"] == "no_p98_reversal_baseline_v1"
    assert audit["summary_counts"]["row_count"] == 4
    assert audit["summary_counts"]["null_score_count"] == 0
    assert audit["summary_counts"]["nonfinite_score_count"] == 0
    assert audit["score_direction"] == "ASC / reversal_rank"
    assert audit["p98_used"] is False
    assert audit["label_diagnostics_used"] is False
    assert audit["frozen_test_accessed"] is False
    assert audit["d0_visibility_audit"]["pass"] is True
    assert audit["leakage_audit"]["pass"] is True

    source_chain_audit = read_json(source_chain_output)
    assert source_chain_audit["source_chain_status"] == "pass"
    assert source_chain_audit["score_direction"] == "ASC / reversal_rank"
    assert source_chain_audit["p98_used"] is False
    assert source_chain_audit["label_diagnostics_used"] is False
    assert source_chain_audit["frozen_test_accessed"] is False
    assert source_chain_audit["d0_visibility_audit"]["pass"] is True
    assert source_chain_audit["leakage_audit"]["pass"] is True

    manifest = read_json(manifest_output)
    assert manifest["candidate_scheme_id"] == "no_p98_reversal_baseline_v1"
    assert manifest["parameters"]["portfolio_ran"] is False
    assert manifest["parameters"]["formal_metrics_generated"] is False
    assert manifest["parameters"]["frozen_test_accessed"] is False


def test_build_no_p98_clean_baseline_scores_fails_fast_on_label_column(tmp_path: Path) -> None:
    snapshot_root = tmp_path / "snapshot"
    build_source_db(snapshot_root / "duckdb" / "warehouse.duckdb")

    sample_panel_path = tmp_path / "project_sample_panel.parquet"
    write_sample_panel(sample_panel_path, include_label_column=True)

    run_input_contract = tmp_path / "run_input_contract.json"
    write_run_input_contract(run_input_contract, snapshot_root)

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / SCRIPT_PATH),
            "--run-id",
            "no_p98_label_fail",
            "--project-sample-panel",
            str(sample_panel_path),
            "--run-input-contract",
            str(run_input_contract),
            "--output-dir",
            str(tmp_path / "run"),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Forbidden sample panel columns detected" in result.stderr
    assert "label_5d_next_open_close" in result.stderr


def test_build_no_p98_clean_baseline_scores_fails_fast_on_frozen_test_input(tmp_path: Path) -> None:
    snapshot_root = tmp_path / "snapshot"
    build_source_db(snapshot_root / "duckdb" / "warehouse.duckdb")

    sample_panel_path = tmp_path / "project_sample_panel.parquet"
    write_sample_panel(sample_panel_path)

    run_input_contract = tmp_path / "run_input_contract.json"
    write_run_input_contract(run_input_contract, snapshot_root, frozen_test_access=True)

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / SCRIPT_PATH),
            "--run-id",
            "no_p98_frozen_fail",
            "--project-sample-panel",
            str(sample_panel_path),
            "--run-input-contract",
            str(run_input_contract),
            "--output-dir",
            str(tmp_path / "run"),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Frozen/test input detected" in result.stderr
    assert "frozen_test" in result.stderr
