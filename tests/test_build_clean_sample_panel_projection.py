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


SCRIPT_PATH = "scripts/build_clean_sample_panel_projection.py"


def write_sample_panel(
    path: Path,
    *,
    include_label_defined: bool = True,
    include_realized_return: bool = False,
    include_future_field: bool = False,
) -> None:
    payload = {
        "snapshot_id": ["snap", "snap"],
        "instrument": ["AAA.SZ", "BBB.SZ"],
        "signal_date": ["20210106", "20210106"],
        "ranking_eligible_D0": [True, False],
        "feature_ready_D0": [True, True],
    }
    if include_label_defined:
        payload["label_defined"] = [True, False]
    if include_realized_return:
        payload["realized_return"] = [0.1, -0.2]
    if include_future_field:
        payload["future_return_5d"] = [0.03, -0.01]
    pq.write_table(pa.table(payload), path)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_projection(input_path: Path, output_path: Path, audit_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / SCRIPT_PATH),
            "--input-path",
            str(input_path),
            "--output-path",
            str(output_path),
            "--audit-path",
            str(audit_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_projection_strips_label_defined_and_forbidden_fields(tmp_path: Path) -> None:
    input_path = tmp_path / "project_sample_panel.parquet"
    output_path = tmp_path / "clean_sample_panel.parquet"
    audit_path = tmp_path / "clean_sample_panel_audit.json"
    write_sample_panel(
        input_path,
        include_label_defined=True,
        include_realized_return=True,
        include_future_field=True,
    )

    result = run_projection(input_path, output_path, audit_path)
    assert result.returncode == 0, result.stderr

    con = duckdb.connect()
    try:
        columns = [row[0] for row in con.execute(
            f"DESCRIBE SELECT * FROM read_parquet('{output_path.as_posix()}')"
        ).fetchall()]
        rows = con.execute(
            f"SELECT * FROM read_parquet('{output_path.as_posix()}') ORDER BY instrument"
        ).fetchall()
    finally:
        con.close()

    assert columns == [
        "snapshot_id",
        "instrument",
        "signal_date",
        "ranking_eligible_D0",
    ]
    assert len(rows) == 2

    audit = read_json(audit_path)
    assert audit["input_path"] == input_path.resolve().as_posix()
    assert audit["output_path"] == output_path.resolve().as_posix()
    assert audit["row_count"] == 2
    assert audit["allowed_columns"] == columns
    assert audit["stripped_forbidden_columns"] == [
        "future_return_5d",
        "label_defined",
        "realized_return",
    ]
    assert audit["label_columns_stripped"] is True
    assert audit["frozen_test_accessed"] is False


def test_projection_strips_realized_return_without_label_columns(tmp_path: Path) -> None:
    input_path = tmp_path / "project_sample_panel.parquet"
    output_path = tmp_path / "clean_sample_panel.parquet"
    audit_path = tmp_path / "clean_sample_panel_audit.json"
    write_sample_panel(
        input_path,
        include_label_defined=False,
        include_realized_return=True,
    )

    result = run_projection(input_path, output_path, audit_path)
    assert result.returncode == 0, result.stderr

    audit = read_json(audit_path)
    assert audit["stripped_forbidden_columns"] == ["realized_return"]
    assert audit["label_columns_stripped"] is False


def test_projection_fails_fast_when_required_column_missing(tmp_path: Path) -> None:
    input_path = tmp_path / "project_sample_panel.parquet"
    output_path = tmp_path / "clean_sample_panel.parquet"
    audit_path = tmp_path / "clean_sample_panel_audit.json"

    pq.write_table(
        pa.table(
            {
                "snapshot_id": ["snap"],
                "instrument": ["AAA.SZ"],
                "signal_date": ["20210106"],
            }
        ),
        input_path,
    )

    result = run_projection(input_path, output_path, audit_path)
    assert result.returncode != 0
    assert "Missing required columns" in result.stderr
    assert "ranking_eligible_D0" in result.stderr


def test_projection_output_contains_only_whitelist_columns(tmp_path: Path) -> None:
    input_path = tmp_path / "project_sample_panel.parquet"
    output_path = tmp_path / "clean_sample_panel.parquet"
    audit_path = tmp_path / "clean_sample_panel_audit.json"
    write_sample_panel(input_path, include_label_defined=True, include_realized_return=False)

    result = run_projection(input_path, output_path, audit_path)
    assert result.returncode == 0, result.stderr

    con = duckdb.connect()
    try:
        columns = [row[0] for row in con.execute(
            f"DESCRIBE SELECT * FROM read_parquet('{output_path.as_posix()}')"
        ).fetchall()]
    finally:
        con.close()

    assert columns == [
        "snapshot_id",
        "instrument",
        "signal_date",
        "ranking_eligible_D0",
    ]
