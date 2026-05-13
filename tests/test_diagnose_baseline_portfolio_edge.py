from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb


SCRIPT_PATH = Path("scripts/diagnose_baseline_portfolio_edge.py")
DOC_PATH = Path("docs/baseline_portfolio_edge_decomposition.md")


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
                pct_chg DOUBLE,
                amount DOUBLE,
                total_mv DOUBLE,
                circ_mv DOUBLE,
                turnover_rate DOUBLE
            )
            """
        )
        rows = []
        trade_dates = [
            f"202001{day:02d}" for day in range(1, 23)
        ]
        instruments = {
            "AAA.SZ": {"amount": 100.0, "mv": 1000.0, "turn": 1.0, "chg": 1.0},
            "BBB.SZ": {"amount": 80.0, "mv": 900.0, "turn": 1.5, "chg": 0.5},
            "CCC.SZ": {"amount": 30.0, "mv": 500.0, "turn": 0.4, "chg": 3.0},
        }
        for idx, trade_date in enumerate(trade_dates):
            for instrument, spec in instruments.items():
                rows.append(
                    (
                        "warehouse_fixture",
                        instrument,
                        trade_date,
                        spec["chg"] + (idx % 3) * 0.1,
                        spec["amount"] + idx,
                        spec["mv"] + idx * 10,
                        spec["mv"] * 0.8 + idx * 7,
                        spec["turn"] + (idx % 2) * 0.1,
                    )
                )
        con.executemany("INSERT INTO serving.vw_bars_daily VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
    finally:
        con.close()


def build_fixture(tmp_path: Path) -> dict[str, Path]:
    source_db = tmp_path / "duckdb" / "warehouse.duckdb"
    build_source_db(source_db)

    trade_dates = [f"202001{day:02d}" for day in range(1, 23)]
    score_rows_baseline = []
    score_rows_confirmed5 = []
    execution_rows = []
    split_rows = []

    for idx, trade_date in enumerate(trade_dates):
        baseline_scores = {
            "AAA.SZ": 0.90 if idx % 2 == 0 else 0.80,
            "BBB.SZ": 0.80 if idx % 2 == 0 else 0.90,
            "CCC.SZ": 0.10,
        }
        confirmed5_scores = {
            "AAA.SZ": 0.20,
            "BBB.SZ": 0.95,
            "CCC.SZ": 0.85 if idx % 2 == 0 else 0.75,
        }
        realized = {
            "AAA.SZ": 0.06 if idx >= 20 else 0.03,
            "BBB.SZ": 0.04 if idx >= 20 else 0.02,
            "CCC.SZ": -0.12 if idx >= 20 else -0.04,
        }
        split_bucket = "validation" if idx >= 20 else "train"
        for instrument in ("AAA.SZ", "BBB.SZ", "CCC.SZ"):
            score_rows_baseline.append(
                ("warehouse_fixture", instrument, trade_date, "multi_equal_weight_v1", baseline_scores[instrument])
            )
            score_rows_confirmed5.append(
                ("warehouse_fixture", instrument, trade_date, "nlc_v1_confirmed5_lgbm_depth3_seed42", confirmed5_scores[instrument])
            )
            execution_rows.append(
                (
                    "warehouse_fixture",
                    instrument,
                    trade_date,
                    realized[instrument],
                    "resolved",
                )
            )
            split_rows.append(("warehouse_fixture", instrument, trade_date, split_bucket))

    baseline_scores_path = tmp_path / "baseline_scores.parquet"
    confirmed5_scores_path = tmp_path / "confirmed5_scores.parquet"
    execution_panel_path = tmp_path / "execution_panel.parquet"
    split_panel_path = tmp_path / "split_panel.parquet"

    write_parquet(
        baseline_scores_path,
        score_rows_baseline,
        ["snapshot_id VARCHAR", "instrument VARCHAR", "signal_date VARCHAR", "candidate_scheme_id VARCHAR", "model_score_D0 DOUBLE"],
    )
    write_parquet(
        confirmed5_scores_path,
        score_rows_confirmed5,
        ["snapshot_id VARCHAR", "instrument VARCHAR", "signal_date VARCHAR", "candidate_scheme_id VARCHAR", "model_score_D0 DOUBLE"],
    )
    write_parquet(
        execution_panel_path,
        execution_rows,
        ["snapshot_id VARCHAR", "instrument VARCHAR", "signal_date VARCHAR", "execution_delayed_realized_return DOUBLE", "execution_path_status VARCHAR"],
    )
    write_parquet(
        split_panel_path,
        split_rows,
        ["snapshot_id VARCHAR", "instrument VARCHAR", "signal_date VARCHAR", "split_bucket VARCHAR"],
    )

    confirmed5_readout_path = tmp_path / "confirmed5_readout.json"
    v2_readout_path = tmp_path / "v2_readout.json"
    write_json(
        confirmed5_readout_path,
        {
            "windows": {
                "primary": {
                    "train": {
                        "final_total_equity_estimate": 1.3,
                        "annual_relative_return_trainval_dry_run_estimate": 0.01,
                        "relative_ir_estimate": 0.1,
                        "avg_cash_weight": 0.72,
                        "avg_invested_weight": 0.28,
                        "avg_turnover_daily": 0.20,
                        "max_drawdown_trainval_dry_run_estimate": -0.08,
                    },
                    "validation": {
                        "final_total_equity_estimate": 1.1,
                        "annual_relative_return_trainval_dry_run_estimate": -0.02,
                        "relative_ir_estimate": -0.3,
                        "avg_cash_weight": 0.74,
                        "avg_invested_weight": 0.26,
                        "avg_turnover_daily": 0.22,
                        "max_drawdown_trainval_dry_run_estimate": -0.11,
                    },
                },
                "baseline": {
                    "train": {
                        "final_total_equity_estimate": 1.5,
                        "annual_relative_return_trainval_dry_run_estimate": 0.03,
                        "relative_ir_estimate": 0.2,
                        "avg_cash_weight": 0.78,
                        "avg_invested_weight": 0.22,
                        "avg_turnover_daily": 0.18,
                        "max_drawdown_trainval_dry_run_estimate": -0.05,
                    },
                    "validation": {
                        "final_total_equity_estimate": 1.4,
                        "annual_relative_return_trainval_dry_run_estimate": 0.02,
                        "relative_ir_estimate": 0.15,
                        "avg_cash_weight": 0.79,
                        "avg_invested_weight": 0.21,
                        "avg_turnover_daily": 0.17,
                        "max_drawdown_trainval_dry_run_estimate": -0.04,
                    },
                },
            }
        },
    )
    write_json(
        v2_readout_path,
        {
            "windows": {
                "primary": {
                    "train": {
                        "final_total_equity_estimate": 1.2,
                        "annual_relative_return_trainval_dry_run_estimate": 0.00,
                        "relative_ir_estimate": 0.0,
                        "avg_cash_weight": 0.82,
                        "avg_invested_weight": 0.18,
                        "avg_turnover_daily": 0.10,
                        "max_drawdown_trainval_dry_run_estimate": -0.06,
                    },
                    "validation": {
                        "final_total_equity_estimate": 1.0,
                        "annual_relative_return_trainval_dry_run_estimate": -0.01,
                        "relative_ir_estimate": -0.1,
                        "avg_cash_weight": 0.84,
                        "avg_invested_weight": 0.16,
                        "avg_turnover_daily": 0.09,
                        "max_drawdown_trainval_dry_run_estimate": -0.05,
                    },
                },
                "baseline": {
                    "train": {
                        "final_total_equity_estimate": 1.5,
                        "annual_relative_return_trainval_dry_run_estimate": 0.03,
                        "relative_ir_estimate": 0.2,
                        "avg_cash_weight": 0.78,
                        "avg_invested_weight": 0.22,
                        "avg_turnover_daily": 0.18,
                        "max_drawdown_trainval_dry_run_estimate": -0.05,
                    },
                    "validation": {
                        "final_total_equity_estimate": 1.4,
                        "annual_relative_return_trainval_dry_run_estimate": 0.02,
                        "relative_ir_estimate": 0.15,
                        "avg_cash_weight": 0.79,
                        "avg_invested_weight": 0.21,
                        "avg_turnover_daily": 0.17,
                        "max_drawdown_trainval_dry_run_estimate": -0.04,
                    },
                },
            }
        },
    )
    return {
        "source_db": source_db,
        "execution_panel": execution_panel_path,
        "split_panel": split_panel_path,
        "baseline_scores": baseline_scores_path,
        "confirmed5_scores": confirmed5_scores_path,
        "confirmed5_readout": confirmed5_readout_path,
        "v2_readout": v2_readout_path,
    }


def test_script_runs_on_small_fixture(repo_root: Path, tmp_path: Path) -> None:
    fixture = build_fixture(tmp_path)
    output_json = tmp_path / "baseline_edge.json"
    output_md = tmp_path / "baseline_edge.md"

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / SCRIPT_PATH),
            "--source-db",
            str(fixture["source_db"]),
            "--execution-panel",
            str(fixture["execution_panel"]),
            "--split-panel",
            str(fixture["split_panel"]),
            "--baseline-scores",
            str(fixture["baseline_scores"]),
            "--confirmed5-scores",
            str(fixture["confirmed5_scores"]),
            "--confirmed5-readout-json",
            str(fixture["confirmed5_readout"]),
            "--v2-readout-json",
            str(fixture["v2_readout"]),
            "--topk",
            "2",
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    text = output_md.read_text(encoding="utf-8")

    assert payload["no_frozen_test_access"] is True
    assert "TopK Realized Return Decomposition" in text
    assert "Win/Loss Day Summary" in text
    assert "Turnover / Overlap / Cash" in text
    assert "baseline" in payload["candidates"]
    assert "confirmed5_vs_baseline" in payload["relative_day_summary"]
    assert payload["field_availability"]["industry"] == "不可得"
    assert payload["field_availability"]["concentration"] == "不可得"


def test_doc_contains_required_boundaries() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "不训练" in text
    assert "不回测" in text
    assert "不读取 frozen test" in text
    assert "不把 trainval 当 OOS" in text
