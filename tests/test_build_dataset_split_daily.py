from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb

from conftest import load_json, load_module, schema_properties, schema_required


SCRIPT_PATH = "scripts/build_dataset_split_daily.py"
CONFIG_PATH = "configs/dataset_split/dataset_split_research_trainval_20211231.json"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def write_sample_panel(path: Path) -> None:
    con = duckdb.connect()
    try:
        con.execute(
            f"""
            COPY (
                SELECT *
                FROM (
                    VALUES
                        ('warehouse_20260429_trainval_20211231', '000001.SZ', '2015-06-01'),
                        ('warehouse_20260429_trainval_20211231', '000002.SZ', '20200615'),
                        ('warehouse_20260429_trainval_20211231', '000003.SZ', '2023-03-03'),
                        ('warehouse_20260429_trainval_20211231', '000004.SZ', '2009-12-31')
                ) AS t(snapshot_id, instrument, signal_date)
            ) TO '{path.as_posix()}' (FORMAT PARQUET)
            """
        )
    finally:
        con.close()


def run_builder(
    repo_root: Path,
    config_path: Path,
    sample_panel_path: Path,
    output_path: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(repo_root / SCRIPT_PATH),
            "--config",
            str(config_path),
            "--sample-panel",
            str(sample_panel_path),
            "--output",
            str(output_path),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_dataset_split_config_exists_and_matches_expected_contract() -> None:
    payload = load_json(CONFIG_PATH)

    assert payload["split_config_id"] == "dataset_split_research_trainval_20211231"
    assert payload["snapshot_id"] == "warehouse_20260429_trainval_20211231"
    assert payload["train_start"] == "2010-01-01"
    assert payload["train_end"] == "2018-12-31"
    assert payload["validation_start"] == "2019-01-01"
    assert payload["validation_end"] == "2021-12-31"
    assert payload["test_excluded_start"] == "2022-01-01"
    assert payload["test_excluded_end"] == "2025-12-31"
    assert payload["split_policy"] == "fixed_calendar_date_split_v1"
    assert payload["frozen_test_access"] is False


def test_dataset_split_schema_includes_builder_fields() -> None:
    properties = schema_properties("schemas/dataset_split_daily.schema.json")
    required = set(schema_required("schemas/dataset_split_daily.schema.json"))

    assert "snapshot_id" in properties
    assert "split_config_id" in properties
    assert "split_policy" in properties
    assert {"snapshot_id", "split_config_id", "split_policy", "split_bucket"} <= required


def test_dataset_split_builder_cli_help_runs(repo_root: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(repo_root / SCRIPT_PATH), "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--config" in result.stdout
    assert "--sample-panel" in result.stdout
    assert "--output" in result.stdout


def test_dataset_split_builder_writes_expected_buckets_and_audit(repo_root: Path, tmp_path: Path) -> None:
    sample_panel_path = tmp_path / "project_sample_panel.parquet"
    config_path = tmp_path / "dataset_split_config.json"
    output_path = tmp_path / "dataset_split_daily.parquet"
    audit_path = tmp_path / "dataset_split_daily_audit.json"

    write_sample_panel(sample_panel_path)
    write_json(config_path, load_json(CONFIG_PATH))

    result = run_builder(repo_root, config_path, sample_panel_path, output_path)

    assert result.returncode == 0
    assert output_path.exists()
    assert audit_path.exists()

    con = duckdb.connect()
    try:
        rows = con.execute(
            f"""
            SELECT
                instrument,
                signal_date,
                split_bucket,
                train_flag,
                validation_flag,
                test_flag,
                split_config_id,
                split_policy,
                snapshot_id
            FROM read_parquet('{output_path.as_posix()}')
            ORDER BY instrument
            """
        ).fetchall()
        overlap_rows = con.execute(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{output_path.as_posix()}')
            WHERE train_flag AND validation_flag
            """
        ).fetchone()[0]
        empty_bucket_rows = con.execute(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{output_path.as_posix()}')
            WHERE split_bucket IS NULL OR split_bucket = ''
            """
        ).fetchone()[0]
    finally:
        con.close()

    assert rows == [
        (
            "000001.SZ",
            "2015-06-01",
            "train",
            True,
            False,
            False,
            "dataset_split_research_trainval_20211231",
            "fixed_calendar_date_split_v1",
            "warehouse_20260429_trainval_20211231",
        ),
        (
            "000002.SZ",
            "20200615",
            "validation",
            False,
            True,
            False,
            "dataset_split_research_trainval_20211231",
            "fixed_calendar_date_split_v1",
            "warehouse_20260429_trainval_20211231",
        ),
        (
            "000003.SZ",
            "2023-03-03",
            "excluded_test_period",
            False,
            False,
            True,
            "dataset_split_research_trainval_20211231",
            "fixed_calendar_date_split_v1",
            "warehouse_20260429_trainval_20211231",
        ),
        (
            "000004.SZ",
            "2009-12-31",
            "outside_config_range",
            False,
            False,
            False,
            "dataset_split_research_trainval_20211231",
            "fixed_calendar_date_split_v1",
            "warehouse_20260429_trainval_20211231",
        ),
    ]
    assert overlap_rows == 0
    assert empty_bucket_rows == 0

    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["status"] == "built_dataset_split_daily"
    assert audit["total_rows"] == 4
    assert audit["split_bucket_counts"] == {
        "excluded_test_period": 1,
        "outside_config_range": 1,
        "train": 1,
        "validation": 1,
    }


def test_dataset_split_builder_module_fails_when_sample_panel_snapshot_mismatches(tmp_path: Path) -> None:
    module = load_module(SCRIPT_PATH, "build_dataset_split_daily_module")
    sample_panel_path = tmp_path / "project_sample_panel.parquet"
    config = load_json(CONFIG_PATH)
    output_path = tmp_path / "dataset_split_daily.parquet"

    con = duckdb.connect()
    try:
        con.execute(
            f"""
            COPY (
                SELECT *
                FROM (
                    VALUES ('other_snapshot', '000001.SZ', '2015-06-01')
                ) AS t(snapshot_id, instrument, signal_date)
            ) TO '{sample_panel_path.as_posix()}' (FORMAT PARQUET)
            """
        )
    finally:
        con.close()

    try:
        module.build_dataset_split_daily(config, sample_panel_path, output_path)
    except module.BuildError as exc:
        assert "sample panel snapshot_id does not match split config snapshot_id" in str(exc)
    else:
        raise AssertionError("expected BuildError for snapshot mismatch")
