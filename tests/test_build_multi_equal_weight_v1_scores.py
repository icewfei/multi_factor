from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from conftest import REPO_ROOT, load_json


SCRIPT_PATH = "scripts/build_multi_equal_weight_v1_scores.py"


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
                adj_close DOUBLE,
                amount DOUBLE,
                vol DOUBLE,
                pct_chg DOUBLE
            )
            """
        )
        rows: list[tuple[str, str, str, float, float, float, float]] = []
        for day in range(1, 66):
            trade_date = f"202101{day:02d}"
            aaa_close = 10.0 + day * 0.2
            bbb_close = 12.0 + day * 0.05
            aaa_vol = 1000.0 + day * 20.0
            bbb_vol = 800.0 + day * 5.0
            aaa_amount = aaa_close * aaa_vol
            bbb_amount = bbb_close * bbb_vol
            aaa_pct = 1.0 if day > 1 else 0.0
            bbb_pct = 0.2 if day > 1 else 0.0
            rows.append(("snap", "AAA.SZ", trade_date, aaa_close, aaa_amount, aaa_vol, aaa_pct))
            rows.append(("snap", "BBB.SZ", trade_date, bbb_close, bbb_amount, bbb_vol, bbb_pct))
        con.executemany(
            "INSERT INTO serving.vw_bars_daily VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
    finally:
        con.close()


def write_sample_panel(path: Path) -> None:
    table = pa.table(
        {
            "snapshot_id": ["snap", "snap", "snap"],
            "instrument": ["AAA.SZ", "AAA.SZ", "BBB.SZ"],
            "signal_date": ["20210110", "20210165", "20210165"],
            "ranking_eligible_D0": [True, True, True],
        }
    )
    pq.write_table(table, path)


def write_p98_scores(path: Path) -> None:
    table = pa.table(
        {
            "snapshot_id": ["snap", "snap", "snap"],
            "instrument": ["AAA.SZ", "AAA.SZ", "BBB.SZ"],
            "signal_date": ["20210110", "20210165", "20210165"],
            "candidate_scheme_id": [
                "reversal_tail_exclude_p98_v1",
                "reversal_tail_exclude_p98_v1",
                "reversal_tail_exclude_p98_v1",
            ],
            "model_score_D0": [0.6, 0.8, 0.2],
        }
    )
    pq.write_table(table, path)


def test_build_multi_equal_weight_v1_scores_cli(tmp_path: Path) -> None:
    snapshot_root = tmp_path / "snapshot"
    build_source_db(snapshot_root / "duckdb" / "warehouse.duckdb")

    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    write_sample_panel(run_dir / "project_sample_panel.parquet")
    p98_score_path = tmp_path / "p98_scores.parquet"
    write_p98_scores(p98_score_path)

    run_input_contract = tmp_path / "run_input_contract.json"
    run_input_contract.write_text(
        json.dumps(
            {
                "snapshot_id": "snap",
                "source_root": {"snapshot_path": str(snapshot_root)},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / SCRIPT_PATH),
            "--run-id",
            "tmp_multi_equal_weight_v1",
            "--input-dir",
            str(run_dir),
            "--run-input-contract",
            str(run_input_contract),
            "--p98-score-path",
            str(p98_score_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    score_output = run_dir / "model_scores_D0.parquet"
    audit_output = run_dir / "model_scores_D0_audit.json"
    assert score_output.exists()
    assert audit_output.exists()

    con = duckdb.connect()
    try:
        rows = con.execute(
            f"""
            SELECT instrument, signal_date, candidate_scheme_id, model_score_D0, score_component_count
            FROM read_parquet('{score_output.as_posix()}')
            ORDER BY signal_date, instrument
            """
        ).fetchall()
    finally:
        con.close()

    assert len(rows) == 3
    assert all(row[2] == "multi_equal_weight_v1" for row in rows)
    assert all(row[4] == 4 for row in rows)

    early_row = next(row for row in rows if row[1] == "20210110")
    assert early_row[0] == "AAA.SZ"
    assert early_row[3] == 0.15

    late_scores = {row[0]: row[3] for row in rows if row[1] == "20210165"}
    assert late_scores["AAA.SZ"] != late_scores["BBB.SZ"]
    assert 0.0 <= late_scores["BBB.SZ"] <= 1.0
    assert 0.0 <= late_scores["AAA.SZ"] <= 1.0

    audit = load_json(audit_output)
    assert audit["candidate_scheme_id"] == "multi_equal_weight_v1"
    assert audit["component_contract"]["frozen_test_access"] is False
    assert audit["summary_counts"]["total_rows"] == 3
