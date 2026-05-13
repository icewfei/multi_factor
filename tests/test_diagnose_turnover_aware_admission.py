from __future__ import annotations

import json
import subprocess
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import duckdb
import pandas as pd


SCRIPT_PATH = Path("scripts/diagnose_turnover_aware_admission.py")


def load_module():
    spec = spec_from_file_location("diagnose_turnover_aware_admission", SCRIPT_PATH)
    assert spec is not None
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_parquet(path: Path, rows: list[tuple], columns: list[str]) -> None:
    con = duckdb.connect()
    try:
        quoted_columns = ", ".join(columns)
        placeholders = ", ".join("?" for _ in columns)
        con.execute(f"CREATE TABLE t ({quoted_columns})")
        con.executemany(f"INSERT INTO t VALUES ({placeholders})", rows)
        con.execute(f"COPY t TO '{path.as_posix()}' (FORMAT PARQUET)")
    finally:
        con.close()


def build_source_db(path: Path, trade_dates: list[str]) -> None:
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
                pct_chg DOUBLE,
                amount DOUBLE,
                total_mv DOUBLE,
                circ_mv DOUBLE,
                turnover_rate DOUBLE
            )
            """
        )
        rows = []
        instruments = ["AAA.SZ", "BBB.SZ", "CCC.SZ", "DDD.SZ"]
        for idx, trade_date in enumerate(trade_dates):
            for instrument_idx, instrument in enumerate(instruments):
                rows.append(
                    (
                        "fixture_snapshot",
                        instrument,
                        trade_date,
                        0.5 + instrument_idx * 0.1 + (idx % 4) * 0.05,
                        100.0 + instrument_idx * 30.0 + idx,
                        1000.0 + instrument_idx * 120.0 + idx * 10.0,
                        800.0 + instrument_idx * 90.0 + idx * 8.0,
                        0.7 + instrument_idx * 0.2 + (idx % 3) * 0.05,
                    )
                )
        con.executemany("INSERT INTO serving.vw_bars_daily VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
    finally:
        con.close()


def build_fixture(tmp_path: Path) -> dict[str, Path]:
    trade_dates = [f"202001{day:02d}" for day in range(1, 31)] + [f"202002{day:02d}" for day in range(1, 11)]
    source_db = tmp_path / "duckdb" / "warehouse.duckdb"
    build_source_db(source_db, trade_dates)

    baseline_rows = []
    confirmed5_rows = []
    v2_rows = []
    split_rows = []
    execution_rows = []
    instruments = ["AAA.SZ", "BBB.SZ", "CCC.SZ", "DDD.SZ"]

    for idx, trade_date in enumerate(trade_dates):
        split_bucket = "train" if idx < 30 else "validation"
        baseline_order = ["AAA.SZ", "BBB.SZ", "CCC.SZ", "DDD.SZ"] if idx % 3 else ["AAA.SZ", "CCC.SZ", "BBB.SZ", "DDD.SZ"]
        confirmed5_order = ["AAA.SZ", "BBB.SZ", "CCC.SZ", "DDD.SZ"] if idx % 2 else ["CCC.SZ", "DDD.SZ", "AAA.SZ", "BBB.SZ"]
        v2_order = ["AAA.SZ", "CCC.SZ", "BBB.SZ", "DDD.SZ"] if idx < 20 else ["CCC.SZ", "AAA.SZ", "DDD.SZ", "BBB.SZ"]

        for rank, instrument in enumerate(baseline_order):
            baseline_rows.append(("fixture_snapshot", instrument, trade_date, "baseline_fixture", 1.0 - rank * 0.1))
        for rank, instrument in enumerate(confirmed5_order):
            confirmed5_rows.append(("fixture_snapshot", instrument, trade_date, "confirmed5_fixture", 1.0 - rank * 0.1))
        for rank, instrument in enumerate(v2_order):
            v2_rows.append(("fixture_snapshot", instrument, trade_date, "v2_fixture", 1.0 - rank * 0.1))

        for instrument in instruments:
            split_rows.append(("fixture_snapshot", instrument, trade_date, split_bucket))
            realized = 0.03 if instrument in {"AAA.SZ", "BBB.SZ"} else -0.02
            if split_bucket == "validation" and instrument in {"CCC.SZ", "DDD.SZ"}:
                realized = -0.05
            execution_rows.append(("fixture_snapshot", instrument, trade_date, realized))

    baseline_scores = tmp_path / "baseline_scores.parquet"
    confirmed5_scores = tmp_path / "confirmed5_scores.parquet"
    v2_scores = tmp_path / "v2_scores.parquet"
    split_panel = tmp_path / "split_panel.parquet"
    execution_panel = tmp_path / "execution_panel.parquet"

    write_parquet(
        baseline_scores,
        baseline_rows,
        [
            "snapshot_id VARCHAR",
            "instrument VARCHAR",
            "signal_date VARCHAR",
            "candidate_scheme_id VARCHAR",
            "model_score_D0 DOUBLE",
        ],
    )
    write_parquet(
        confirmed5_scores,
        confirmed5_rows,
        [
            "snapshot_id VARCHAR",
            "instrument VARCHAR",
            "signal_date VARCHAR",
            "candidate_scheme_id VARCHAR",
            "model_score_D0 DOUBLE",
        ],
    )
    write_parquet(
        v2_scores,
        v2_rows,
        [
            "snapshot_id VARCHAR",
            "instrument VARCHAR",
            "signal_date VARCHAR",
            "candidate_scheme_id VARCHAR",
            "model_score_D0 DOUBLE",
        ],
    )
    write_parquet(
        split_panel,
        split_rows,
        [
            "snapshot_id VARCHAR",
            "instrument VARCHAR",
            "signal_date VARCHAR",
            "split_bucket VARCHAR",
        ],
    )
    write_parquet(
        execution_panel,
        execution_rows,
        [
            "snapshot_id VARCHAR",
            "instrument VARCHAR",
            "signal_date VARCHAR",
            "execution_delayed_realized_return DOUBLE",
        ],
    )
    return {
        "source_db": source_db,
        "baseline_scores": baseline_scores,
        "confirmed5_scores": confirmed5_scores,
        "v2_scores": v2_scores,
        "split_panel": split_panel,
        "execution_panel": execution_panel,
    }


def test_annotate_turnover_states() -> None:
    module = load_module()
    frame = pd.DataFrame(
        [
            {"signal_date": "20200101", "instrument": "A", "split_bucket": "train", "rank_position": 1, "model_score_D0": 1.0, "execution_delayed_realized_return": 0.01, "amount": 1.0, "total_mv": 1.0, "turnover_rate": 1.0, "volatility_20d": 1.0},
            {"signal_date": "20200101", "instrument": "B", "split_bucket": "train", "rank_position": 2, "model_score_D0": 0.9, "execution_delayed_realized_return": 0.02, "amount": 1.0, "total_mv": 1.0, "turnover_rate": 1.0, "volatility_20d": 1.0},
            {"signal_date": "20200102", "instrument": "A", "split_bucket": "train", "rank_position": 1, "model_score_D0": 1.0, "execution_delayed_realized_return": 0.01, "amount": 1.0, "total_mv": 1.0, "turnover_rate": 1.0, "volatility_20d": 1.0},
            {"signal_date": "20200102", "instrument": "C", "split_bucket": "train", "rank_position": 2, "model_score_D0": 0.8, "execution_delayed_realized_return": -0.02, "amount": 1.0, "total_mv": 1.0, "turnover_rate": 1.0, "volatility_20d": 1.0},
        ]
    )
    annotated = module.annotate_turnover_states(frame)
    assert len(annotated) == 2
    assert float(annotated["replacement_ratio"].iloc[0]) == 0.5
    assert bool(annotated.loc[annotated["instrument"] == "A", "is_retained"].iloc[0]) is True
    assert bool(annotated.loc[annotated["instrument"] == "C", "is_new_entrant"].iloc[0]) is True


def test_script_does_not_reference_fixed_test() -> None:
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "fixed_test" not in text


def test_script_runs_on_small_fixture(repo_root: Path, tmp_path: Path) -> None:
    fixture = build_fixture(tmp_path)
    output_json = tmp_path / "turnover_aware_admission.json"
    output_md = tmp_path / "turnover_aware_admission.md"

    subprocess.run(
        [
            sys.executable,
            str(repo_root / SCRIPT_PATH),
            "--source-db",
            str(fixture["source_db"]),
            "--split-panel",
            str(fixture["split_panel"]),
            "--execution-panel",
            str(fixture["execution_panel"]),
            "--baseline-scores",
            str(fixture["baseline_scores"]),
            "--confirmed5-scores",
            str(fixture["confirmed5_scores"]),
            "--v2-scores",
            str(fixture["v2_scores"]),
            "--topk",
            "2",
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
        check=True,
        cwd=repo_root,
    )

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    markdown = output_md.read_text(encoding="utf-8")

    assert payload["diagnostic_only"] is True
    assert payload["frozen_test_read"] is False
    assert payload["metrics_readout_generated"] is False
    assert "replacement_ratio" in payload["conclusion"]["checked_d0_visible_metrics"]
    assert "rank_position" in payload["conclusion"]["checked_d0_visible_metrics"]
    assert "recommendation" in payload["conclusion"]
    assert "不建议进入 turnover-aware admission challenger" in markdown
