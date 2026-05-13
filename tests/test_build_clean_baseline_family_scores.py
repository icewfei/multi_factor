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


SCRIPT_PATH = "scripts/build_clean_baseline_family_scores.py"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_source_db(path: Path, rows: list[tuple]) -> None:
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
                volume DOUBLE
            )
            """
        )
        if rows:
            con.executemany("INSERT INTO serving.vw_bars_daily VALUES (?, ?, ?, ?, ?)", rows)
    finally:
        con.close()


def write_sample_panel(path: Path, payload: dict) -> None:
    pq.write_table(pa.table(payload), path)


def write_run_input_contract(path: Path, snapshot_root: Path, *, frozen_test_access: bool = False) -> None:
    payload = {
        "snapshot_id": "snap",
        "source_root": {"snapshot_path": str(snapshot_root)},
    }
    if frozen_test_access:
        payload["frozen_test_access"] = True
    write_json(path, payload)


def run_builder(
    *,
    tmp_path: Path,
    baseline_id: str,
    sample_panel_path: Path,
    run_input_contract: Path,
    output_dir: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / SCRIPT_PATH),
            "--run-id",
            f"{baseline_id}_fixture_run",
            "--baseline-id",
            baseline_id,
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


def load_score_rows(score_output: Path, select_sql: str) -> list[tuple]:
    con = duckdb.connect()
    try:
        return con.execute(select_sql.format(score_output=score_output.as_posix())).fetchall()
    finally:
        con.close()


def momentum_fixture_rows() -> list[tuple]:
    rows: list[tuple] = []
    for day in range(1, 22):
        date = f"202101{day:02d}"
        aaa_close = 100.0 + float(day - 1)
        bbb_close = 100.0 - float(day - 1)
        rows.append(("snap", "AAA.SZ", date, aaa_close, 100.0))
        rows.append(("snap", "BBB.SZ", date, bbb_close, 100.0))
    return rows


def liquidity_fixture_rows() -> list[tuple]:
    rows: list[tuple] = []
    for day in range(1, 21):
        date = f"202101{day:02d}"
        aaa_close = 100.0 if day < 20 else 90.0
        bbb_close = 100.0 if day < 20 else 90.0
        ccc_close = 100.0 if day < 20 else 80.0
        rows.append(("snap", "AAA.SZ", date, aaa_close, 10.0))
        rows.append(("snap", "BBB.SZ", date, bbb_close, 1000.0))
        rows.append(("snap", "CCC.SZ", date, ccc_close, 100.0))
    return rows


def test_build_clean_momentum_20d_baseline_scores_success_fixture(tmp_path: Path) -> None:
    snapshot_root = tmp_path / "snapshot"
    build_source_db(snapshot_root / "duckdb" / "warehouse.duckdb", momentum_fixture_rows())

    sample_panel_path = tmp_path / "clean_sample_panel.parquet"
    write_sample_panel(
        sample_panel_path,
        {
            "snapshot_id": ["snap", "snap"],
            "instrument": ["AAA.SZ", "BBB.SZ"],
            "signal_date": ["20210121", "20210121"],
            "ranking_eligible_D0": [True, True],
        },
    )

    run_input_contract = tmp_path / "run_input_contract.json"
    write_run_input_contract(run_input_contract, snapshot_root)

    output_dir = tmp_path / "momentum_run"
    result = run_builder(
        tmp_path=tmp_path,
        baseline_id="clean_momentum_20d_baseline_v1",
        sample_panel_path=sample_panel_path,
        run_input_contract=run_input_contract,
        output_dir=output_dir,
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

    rows = load_score_rows(
        score_output,
        """
        SELECT
            instrument,
            momentum_20d_raw,
            momentum_rank,
            model_score_D0,
            candidate_scheme_id,
            baseline_id
        FROM read_parquet('{score_output}')
        ORDER BY instrument
        """,
    )
    assert rows[0][0] == "AAA.SZ"
    assert rows[1][0] == "BBB.SZ"
    assert rows[0][1] > rows[1][1]
    assert rows[0][2] == pytest.approx(0.0)
    assert rows[1][2] == pytest.approx(1.0)
    assert rows[0][3] == rows[0][2]
    assert rows[1][3] == rows[1][2]
    assert all(row[4] == "clean_momentum_20d_baseline_v1" for row in rows)
    assert all(row[5] == "clean_momentum_20d_baseline_v1" for row in rows)

    audit = read_json(audit_output)
    assert audit["row_count"] == 2
    assert audit["null_score_count"] == 0
    assert audit["nonfinite_score_count"] == 0
    assert audit["score_direction"] == "descending 20d cumulative return / stronger momentum first"
    assert audit["p98_used"] is False
    assert audit["label_diagnostics_used"] is False
    assert audit["frozen_test_accessed"] is False
    assert audit["d0_visibility_audit"]["pass"] is True
    assert audit["leakage_audit"]["pass"] is True

    source_chain_audit = read_json(source_chain_output)
    assert source_chain_audit["source_chain_status"] == "pass"
    assert source_chain_audit["score_direction"] == audit["score_direction"]
    assert source_chain_audit["p98_used"] is False
    assert source_chain_audit["label_diagnostics_used"] is False
    assert source_chain_audit["frozen_test_accessed"] is False
    assert source_chain_audit["d0_visibility_audit"]["pass"] is True
    assert source_chain_audit["leakage_audit"]["pass"] is True

    manifest = read_json(manifest_output)
    assert manifest["candidate_scheme_id"] == "clean_momentum_20d_baseline_v1"
    assert manifest["parameters"]["portfolio_ran"] is False
    assert manifest["parameters"]["formal_metrics_generated"] is False
    assert manifest["parameters"]["frozen_test_accessed"] is False


def test_build_clean_liquidity_adjusted_reversal_scores_success_fixture(tmp_path: Path) -> None:
    snapshot_root = tmp_path / "snapshot"
    build_source_db(snapshot_root / "duckdb" / "warehouse.duckdb", liquidity_fixture_rows())

    sample_panel_path = tmp_path / "clean_sample_panel.parquet"
    write_sample_panel(
        sample_panel_path,
        {
            "snapshot_id": ["snap", "snap", "snap"],
            "instrument": ["AAA.SZ", "BBB.SZ", "CCC.SZ"],
            "signal_date": ["20210120", "20210120", "20210120"],
            "ranking_eligible_D0": [True, True, True],
        },
    )

    run_input_contract = tmp_path / "run_input_contract.json"
    write_run_input_contract(run_input_contract, snapshot_root)

    output_dir = tmp_path / "liquidity_run"
    result = run_builder(
        tmp_path=tmp_path,
        baseline_id="clean_liquidity_adjusted_reversal_baseline_v1",
        sample_panel_path=sample_panel_path,
        run_input_contract=run_input_contract,
        output_dir=output_dir,
    )
    assert result.returncode == 0, result.stderr

    score_output = output_dir / "model_scores_D0.parquet"
    rows = load_score_rows(
        score_output,
        """
        SELECT
            instrument,
            reversal_1d_raw,
            median_dollar_volume_20d,
            reversal_liquidity_rank,
            model_score_D0
        FROM read_parquet('{score_output}')
        ORDER BY reversal_liquidity_rank, instrument
        """,
    )

    by_instrument = {row[0]: row for row in rows}
    assert by_instrument["CCC.SZ"][1] < by_instrument["AAA.SZ"][1]
    assert by_instrument["CCC.SZ"][1] < by_instrument["BBB.SZ"][1]
    assert by_instrument["AAA.SZ"][1] == pytest.approx(by_instrument["BBB.SZ"][1])
    assert by_instrument["BBB.SZ"][2] > by_instrument["AAA.SZ"][2]
    assert by_instrument["CCC.SZ"][3] == pytest.approx(0.0)
    assert by_instrument["BBB.SZ"][3] < by_instrument["AAA.SZ"][3]
    assert by_instrument["BBB.SZ"][4] == by_instrument["BBB.SZ"][3]


def test_build_clean_equal_weight_random_eligible_scores_hash_is_stable(tmp_path: Path) -> None:
    snapshot_root = tmp_path / "snapshot"
    build_source_db(snapshot_root / "duckdb" / "warehouse.duckdb", [])

    sample_panel_path = tmp_path / "clean_sample_panel.parquet"
    write_sample_panel(
        sample_panel_path,
        {
            "snapshot_id": ["snap", "snap", "snap"],
            "instrument": ["AAA.SZ", "BBB.SZ", "CCC.SZ"],
            "signal_date": ["20210121", "20210121", "20210121"],
            "ranking_eligible_D0": [True, True, True],
        },
    )

    run_input_contract = tmp_path / "run_input_contract.json"
    write_run_input_contract(run_input_contract, snapshot_root)

    output_dir_a = tmp_path / "random_run_a"
    output_dir_b = tmp_path / "random_run_b"
    result_a = run_builder(
        tmp_path=tmp_path,
        baseline_id="clean_equal_weight_random_eligible_baseline_v1",
        sample_panel_path=sample_panel_path,
        run_input_contract=run_input_contract,
        output_dir=output_dir_a,
    )
    result_b = run_builder(
        tmp_path=tmp_path,
        baseline_id="clean_equal_weight_random_eligible_baseline_v1",
        sample_panel_path=sample_panel_path,
        run_input_contract=run_input_contract,
        output_dir=output_dir_b,
    )
    assert result_a.returncode == 0, result_a.stderr
    assert result_b.returncode == 0, result_b.stderr

    rows_a = load_score_rows(
        output_dir_a / "model_scores_D0.parquet",
        """
        SELECT instrument, stable_hash, hash_rank, model_score_D0
        FROM read_parquet('{score_output}')
        ORDER BY instrument
        """,
    )
    rows_b = load_score_rows(
        output_dir_b / "model_scores_D0.parquet",
        """
        SELECT instrument, stable_hash, hash_rank, model_score_D0
        FROM read_parquet('{score_output}')
        ORDER BY instrument
        """,
    )
    assert rows_a == rows_b
    assert len({row[1] for row in rows_a}) == 3


def test_build_clean_baseline_family_scores_delegates_no_p98_builder(tmp_path: Path) -> None:
    snapshot_root = tmp_path / "snapshot"
    build_source_db(snapshot_root / "duckdb" / "warehouse.duckdb", momentum_fixture_rows())

    sample_panel_path = tmp_path / "clean_sample_panel.parquet"
    write_sample_panel(
        sample_panel_path,
        {
            "snapshot_id": ["snap", "snap"],
            "instrument": ["AAA.SZ", "BBB.SZ"],
            "signal_date": ["20210121", "20210121"],
            "ranking_eligible_D0": [True, True],
        },
    )

    run_input_contract = tmp_path / "run_input_contract.json"
    write_run_input_contract(run_input_contract, snapshot_root)

    output_dir = tmp_path / "no_p98_run"
    result = run_builder(
        tmp_path=tmp_path,
        baseline_id="no_p98_reversal_baseline_v1",
        sample_panel_path=sample_panel_path,
        run_input_contract=run_input_contract,
        output_dir=output_dir,
    )
    assert result.returncode == 0, result.stderr

    rows = load_score_rows(
        output_dir / "model_scores_D0.parquet",
        """
        SELECT DISTINCT candidate_scheme_id, baseline_id
        FROM read_parquet('{score_output}')
        """,
    )
    assert rows == [("no_p98_reversal_baseline_v1", "no_p98_reversal_baseline_v1")]


@pytest.mark.parametrize(
    ("extra_column", "extra_values", "frozen_test_access", "expected_message"),
    [
        ("label_5d_next_open_close", [0.1, -0.1], False, "Forbidden sample panel columns detected"),
        ("future_return", [0.1, -0.1], False, "Forbidden sample panel columns detected"),
        ("unused_safe_column", [1, 2], True, "Frozen/test input detected"),
    ],
)
def test_build_clean_baseline_family_scores_fail_fast_on_forbidden_inputs(
    tmp_path: Path,
    extra_column: str,
    extra_values: list,
    frozen_test_access: bool,
    expected_message: str,
) -> None:
    snapshot_root = tmp_path / "snapshot"
    build_source_db(snapshot_root / "duckdb" / "warehouse.duckdb", momentum_fixture_rows())

    payload = {
        "snapshot_id": ["snap", "snap"],
        "instrument": ["AAA.SZ", "BBB.SZ"],
        "signal_date": ["20210121", "20210121"],
        "ranking_eligible_D0": [True, True],
        extra_column: extra_values,
    }
    sample_panel_path = tmp_path / "clean_sample_panel.parquet"
    write_sample_panel(sample_panel_path, payload)

    run_input_contract = tmp_path / "run_input_contract.json"
    write_run_input_contract(
        run_input_contract,
        snapshot_root,
        frozen_test_access=frozen_test_access,
    )

    result = run_builder(
        tmp_path=tmp_path,
        baseline_id="clean_momentum_20d_baseline_v1",
        sample_panel_path=sample_panel_path,
        run_input_contract=run_input_contract,
        output_dir=tmp_path / "fail_run",
    )
    assert result.returncode != 0
    assert expected_message in result.stderr


def test_build_clean_baseline_family_scores_fails_on_manifest_baseline_mismatch(tmp_path: Path) -> None:
    snapshot_root = tmp_path / "snapshot"
    build_source_db(snapshot_root / "duckdb" / "warehouse.duckdb", momentum_fixture_rows())

    sample_panel_path = tmp_path / "clean_sample_panel.parquet"
    write_sample_panel(
        sample_panel_path,
        {
            "snapshot_id": ["snap"],
            "instrument": ["AAA.SZ"],
            "signal_date": ["20210121"],
            "ranking_eligible_D0": [True],
        },
    )

    run_input_contract = tmp_path / "run_input_contract.json"
    write_run_input_contract(run_input_contract, snapshot_root)

    result = run_builder(
        tmp_path=tmp_path,
        baseline_id="not_in_manifest_baseline_v1",
        sample_panel_path=sample_panel_path,
        run_input_contract=run_input_contract,
        output_dir=tmp_path / "bad_manifest_run",
    )
    assert result.returncode != 0
    assert "baseline_id not found in clean baseline family manifest" in result.stderr
