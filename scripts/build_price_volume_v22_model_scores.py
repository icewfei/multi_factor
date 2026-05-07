#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Build a stable model_scores_D0.parquet for v22:
- momentum_60_5_raw
- breakout_volume_confirmation_20d_raw
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
CONTRACTS_DIR = ROOT / "contracts"
RUN_STATE_DIR = ROOT / "artifacts" / "run_state"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build v22 price-volume family scores.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--input-dir", default=None)
    parser.add_argument(
        "--candidate-scheme-id",
        default="price_volume_v22_breakout_volume_confirmation_substitution",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_path(path: Path) -> str:
    return sql_quote(path.resolve().as_posix())


def main() -> None:
    args = parse_args()
    run_dir = Path(args.input_dir) if args.input_dir else (RUN_STATE_DIR / args.run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    sample_panel = run_dir / "project_sample_panel.parquet"
    if not sample_panel.exists():
        raise FileNotFoundError(f"Required input file not found: {sample_panel}")

    run_input = load_json(CONTRACTS_DIR / "run_input_contract.current.json")
    snapshot_id = run_input["snapshot_id"]
    source_db_path = Path(run_input["source_root"]["snapshot_path"]) / "duckdb" / "warehouse.duckdb"
    if not source_db_path.exists():
        raise FileNotFoundError(f"Shared warehouse DB not found: {source_db_path}")

    score_output = run_dir / "model_scores_D0.parquet"
    audit_output = run_dir / "model_scores_D0_audit.json"

    con = duckdb.connect()
    try:
        con.execute(f"ATTACH {sql_path(source_db_path)} AS warehouse_db (READ_ONLY)")
        con.execute(
            f"""
            CREATE OR REPLACE VIEW project_sample_panel AS
            SELECT * FROM read_parquet({sql_path(sample_panel)})
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW bar_features AS
            WITH bars AS (
                SELECT
                    ts_code AS instrument,
                    trade_date AS signal_date,
                    adj_open,
                    adj_close,
                    amount,
                    pct_chg / 100.0 AS pct_ret
                FROM warehouse_db.serving.vw_bars_daily
                WHERE snapshot_id = {sql_quote(snapshot_id)}
            )
            SELECT
                instrument,
                signal_date,
                (LAG(adj_close, 5) OVER w / LAG(adj_close, 60) OVER w - 1.0) AS momentum_60_5_raw,
                AVG(LN(GREATEST(amount, 0.0) + 1.0)) OVER w20 AS liquidity_20d_raw,
                CASE
                    WHEN MAX(adj_close) OVER w20_prev IS NOT NULL AND MAX(adj_close) OVER w20_prev > 0
                    THEN adj_close / (MAX(adj_close) OVER w20_prev)
                    ELSE NULL
                END AS breakout_proximity_20d_raw,
                AVG(LN(GREATEST(amount, 0.0) + 1.0)) OVER w5
                    - AVG(LN(GREATEST(amount, 0.0) + 1.0)) OVER w20 AS amount_shock_5_20_raw
            FROM bars
            WINDOW
                w AS (PARTITION BY instrument ORDER BY signal_date),
                w5 AS (
                    PARTITION BY instrument
                    ORDER BY signal_date
                    ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
                ),
                w20 AS (
                    PARTITION BY instrument
                    ORDER BY signal_date
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                ),
                w20_prev AS (
                    PARTITION BY instrument
                    ORDER BY signal_date
                    ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING
                )
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW feature_frame AS
            SELECT
                p.snapshot_id,
                p.instrument,
                p.signal_date,
                p.ranking_eligible_D0,
                b.momentum_60_5_raw,
                b.liquidity_20d_raw,
                CASE
                    WHEN b.breakout_proximity_20d_raw IS NOT NULL AND b.amount_shock_5_20_raw IS NOT NULL
                    THEN b.breakout_proximity_20d_raw * b.amount_shock_5_20_raw
                    ELSE NULL
                END AS breakout_volume_confirmation_20d_raw
            FROM project_sample_panel p
            LEFT JOIN bar_features b
              ON p.instrument = b.instrument
             AND p.signal_date = b.signal_date
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW momentum_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY momentum_60_5_raw DESC, instrument ASC
                ) AS momentum_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND momentum_60_5_raw IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW liquidity_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY liquidity_20d_raw ASC, instrument ASC
                ) AS liquidity_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND liquidity_20d_raw IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW breakout_volume_confirmation_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY breakout_volume_confirmation_20d_raw DESC, instrument ASC
                ) AS breakout_volume_confirmation_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND breakout_volume_confirmation_20d_raw IS NOT NULL
            """
        )
        con.execute(
            f"""
            COPY (
                WITH score_frame AS (
                    SELECT
                        f.snapshot_id,
                        f.instrument,
                        f.signal_date,
                        f.ranking_eligible_D0,
                        m.momentum_rank,
                        l.liquidity_rank,
                        b.breakout_volume_confirmation_rank,
                        CASE WHEN m.momentum_rank IS NOT NULL THEN 1 ELSE 0 END
                        + CASE WHEN b.breakout_volume_confirmation_rank IS NOT NULL THEN 1 ELSE 0 END
                        AS score_component_count
                    FROM feature_frame f
                    LEFT JOIN momentum_ranks m
                      ON f.snapshot_id = m.snapshot_id
                     AND f.instrument = m.instrument
                     AND f.signal_date = m.signal_date
                    LEFT JOIN liquidity_ranks l
                      ON f.snapshot_id = l.snapshot_id
                     AND f.instrument = l.instrument
                     AND f.signal_date = l.signal_date
                    LEFT JOIN breakout_volume_confirmation_ranks b
                      ON f.snapshot_id = b.snapshot_id
                     AND f.instrument = b.instrument
                     AND f.signal_date = b.signal_date
                )
                SELECT
                    snapshot_id,
                    instrument,
                    signal_date,
                    CAST({sql_quote(args.candidate_scheme_id)} AS VARCHAR) AS candidate_scheme_id,
                    CASE
                        WHEN ranking_eligible_D0 AND score_component_count >= 2
                        THEN (COALESCE(momentum_rank, 0.0) + COALESCE(breakout_volume_confirmation_rank, 0.0)) / score_component_count
                        ELSE CAST(NULL AS DOUBLE)
                    END AS model_score_D0,
                    score_component_count,
                    momentum_rank,
                    liquidity_rank,
                    breakout_volume_confirmation_rank
                FROM score_frame
            ) TO {sql_path(score_output)} (FORMAT PARQUET)
            """
        )

        audit_row = con.execute(
            f"""
            SELECT
                COUNT(*) AS total_rows,
                SUM(CASE WHEN p.ranking_eligible_D0 THEN 1 ELSE 0 END) AS ranking_eligible_rows,
                SUM(CASE WHEN s.model_score_D0 IS NOT NULL THEN 1 ELSE 0 END) AS scored_rows,
                SUM(CASE WHEN p.ranking_eligible_D0 AND s.model_score_D0 IS NULL THEN 1 ELSE 0 END) AS eligible_unscored_rows,
                SUM(CASE WHEN s.momentum_rank IS NOT NULL THEN 1 ELSE 0 END) AS momentum_rank_rows,
                SUM(CASE WHEN s.liquidity_rank IS NOT NULL THEN 1 ELSE 0 END) AS liquidity_rank_rows,
                SUM(CASE WHEN s.breakout_volume_confirmation_rank IS NOT NULL THEN 1 ELSE 0 END) AS breakout_volume_confirmation_rank_rows
            FROM read_parquet({sql_path(score_output)}) s
            INNER JOIN project_sample_panel p
              ON s.snapshot_id = p.snapshot_id
             AND s.instrument = p.instrument
             AND s.signal_date = p.signal_date
            """
        ).fetchone()
    finally:
        con.close()

    audit = {
        "run_id": args.run_id,
        "snapshot_id": snapshot_id,
        "candidate_scheme_id": args.candidate_scheme_id,
        "feature_preset": "price_volume_v22_breakout_volume_confirmation_substitution",
        "score_file": score_output.name,
        "min_feature_count": 2,
        "baseline_features": ["momentum_60_5_raw", "breakout_volume_confirmation_20d_raw"],
        "summary_counts": {
            "total_rows": int(audit_row[0] or 0),
            "ranking_eligible_rows": int(audit_row[1] or 0),
            "scored_rows": int(audit_row[2] or 0),
            "eligible_unscored_rows": int(audit_row[3] or 0),
            "momentum_rank_rows": int(audit_row[4] or 0),
            "liquidity_rank_rows": int(audit_row[5] or 0),
            "breakout_volume_confirmation_rank_rows": int(audit_row[6] or 0),
        },
        "notes": [
            "Stable dedicated scorer for v22 under the frozen v18 contract.",
            "All features use D0-and-earlier market data only.",
            "The score is the mean of momentum_60_5_rank and breakout_volume_confirmation_20d_rank.",
            "breakout_volume_confirmation_20d_raw = breakout_proximity_20d_raw * amount_shock_5_20_raw",
        ],
    }
    write_json(audit_output, audit)


if __name__ == "__main__":
    main()
