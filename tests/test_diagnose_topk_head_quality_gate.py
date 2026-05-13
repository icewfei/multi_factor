from __future__ import annotations

import json
import subprocess
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import duckdb


SCRIPT_PATH = Path("scripts/diagnose_topk_head_quality_gate.py")


def load_module():
    spec = spec_from_file_location("diagnose_topk_head_quality_gate", SCRIPT_PATH)
    assert spec is not None
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
                base_amount = 100.0 + instrument_idx * 20.0
                base_mv = 1000.0 + instrument_idx * 100.0
                base_turn = 0.8 + instrument_idx * 0.2
                pct_chg = 0.5 + instrument_idx * 0.1 + (idx % 5) * 0.05
                rows.append(
                    (
                        "fixture_snapshot",
                        instrument,
                        trade_date,
                        pct_chg,
                        base_amount + idx * 3.0,
                        base_mv + idx * 20.0,
                        base_mv * 0.8 + idx * 16.0,
                        base_turn + (idx % 3) * 0.05,
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
        for instrument in instruments:
            if instrument == "AAA.SZ":
                baseline_score = 0.90 - (0.05 if idx % 4 == 0 else 0.0)
                confirmed5_score = 0.85
                v2_score = 0.80
            elif instrument == "BBB.SZ":
                baseline_score = 0.85
                confirmed5_score = 0.84 if idx % 3 else 0.83
                v2_score = 0.79
            elif instrument == "CCC.SZ":
                baseline_score = 0.20
                confirmed5_score = 0.82 if idx % 2 == 0 else 0.30
                v2_score = 0.25 if idx % 5 == 0 else 0.70
            else:
                baseline_score = 0.10
                confirmed5_score = 0.05
                v2_score = 0.10

            baseline_rows.append(("fixture_snapshot", instrument, trade_date, "baseline_fixture", baseline_score))
            confirmed5_rows.append(("fixture_snapshot", instrument, trade_date, "confirmed5_fixture", confirmed5_score))
            v2_rows.append(("fixture_snapshot", instrument, trade_date, "v2_fixture", v2_score))
            split_rows.append(("fixture_snapshot", instrument, trade_date, split_bucket))

            if instrument in {"AAA.SZ", "BBB.SZ"}:
                realized = 0.04
            elif instrument == "CCC.SZ":
                realized = -0.08 if split_bucket == "validation" and idx % 5 == 0 else -0.03
            else:
                realized = -0.01
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


def test_evaluate_metric_state_identifies_consistent_weak_side() -> None:
    module = load_module()
    frame = module.pd.DataFrame(
        {
            "split_bucket": ["train"] * 8 + ["validation"] * 4,
            "metric_x": [1.0, 1.1, 1.2, 1.3, 5.0, 5.1, 5.2, 5.3, 1.0, 1.2, 5.1, 5.2],
            "topk_realized_return_mean": [-0.03, -0.02, -0.01, -0.02, 0.01, 0.02, 0.03, 0.02, -0.02, -0.01, 0.01, 0.02],
        }
    )
    payload = module.evaluate_metric_state(frame, "metric_x")
    assert payload["weak_side"] == "low"
    assert payload["direction_consistent_train_validation"] is True
    assert payload["train_delta_weak_minus_strong"] < 0
    assert payload["validation_delta_weak_minus_other"] < 0


def test_script_does_not_reference_fixed_test() -> None:
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "fixed_test" not in text


def test_script_runs_on_small_fixture(repo_root: Path, tmp_path: Path) -> None:
    fixture = build_fixture(tmp_path)
    output_json = tmp_path / "topk_head_quality_gate.json"
    output_md = tmp_path / "topk_head_quality_gate.md"

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
    assert "top1_minus_top2" in payload["checked_d0_visible_metrics"]
    assert "topk_avg_volatility_20d" in payload["checked_d0_visible_metrics"]
    assert "recommendation" in payload["conclusion"]
    assert "不建议进入 gate challenger" in markdown
