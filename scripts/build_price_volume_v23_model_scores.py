#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Build a stable model_scores_D0.parquet for v23:
- momentum_60_5_raw
- liquidity_trend_20_60_raw
- amount_shock_5_20_raw as a gated overlay only
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
    parser = argparse.ArgumentParser(description="Build v23 gated-overlay price-volume family scores.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--input-dir", default=None)
    parser.add_argument(
        "--candidate-scheme-id",
        default="price_volume_v23_amount_shock_gated_overlay",
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
                    adj_close,
                    amount
                FROM warehouse_db.serving.vw_bars_daily
                WHERE snapshot_id = {sql_quote(snapshot_id)}
            )
            SELECT
                instrument,
                signal_date,
                (LAG(adj_close, 5) OVER w / LAG(adj_close, 60) OVER w - 1.0) AS momentum_60_5_raw,
                AVG(LN(GREATEST(amount, 0.0) + 1.0)) OVER w20 AS liquidity_20d_raw,
                CASE
                    WHEN AVG(LN(GREATEST(amount, 0.0) + 1.0)) OVER w60 IS NOT NULL
                     AND AVG(LN(GREATEST(amount, 0.0) + 1.0)) OVER w60 != 0
                    THEN AVG(LN(GREATEST(amount, 0.0) + 1.0)) OVER w20
                         - AVG(LN(GREATEST(amount, 0.0) + 1.0)) OVER w60
                    ELSE NULL
                END AS liquidity_trend_20_60_raw,
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
                w60 AS (
                    PARTITION BY instrument
                    ORDER BY signal_date
                    ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
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
                b.liquidity_trend_20_60_raw,
                b.amount_shock_5_20_raw
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
            CREATE OR REPLACE VIEW liquidity_trend_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY liquidity_trend_20_60_raw DESC, instrument ASC
                ) AS liquidity_trend_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND liquidity_trend_20_60_raw IS NOT NULL
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
            CREATE OR REPLACE VIEW amount_shock_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY amount_shock_5_20_raw DESC, instrument ASC
                ) AS amount_shock_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND amount_shock_5_20_raw IS NOT NULL
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
                        lt.liquidity_trend_rank,
                        l.liquidity_rank,
                        a.amount_shock_rank,
                        CASE
                            WHEN m.momentum_rank IS NOT NULL AND lt.liquidity_trend_rank IS NOT NULL
                            THEN (m.momentum_rank + lt.liquidity_trend_rank) / 2.0
                            ELSE CAST(NULL AS DOUBLE)
                        END AS core_score_v18
                    FROM feature_frame f
                    LEFT JOIN momentum_ranks m
                      ON f.snapshot_id = m.snapshot_id
                     AND f.instrument = m.instrument
                     AND f.signal_date = m.signal_date
                    LEFT JOIN liquidity_trend_ranks lt
                      ON f.snapshot_id = lt.snapshot_id
                     AND f.instrument = lt.instrument
                     AND f.signal_date = lt.signal_date
                    LEFT JOIN liquidity_ranks l
                      ON f.snapshot_id = l.snapshot_id
                     AND f.instrument = l.instrument
                     AND f.signal_date = l.signal_date
                    LEFT JOIN amount_shock_ranks a
                      ON f.snapshot_id = a.snapshot_id
                     AND f.instrument = a.instrument
                     AND f.signal_date = a.signal_date
                )
                SELECT
                    snapshot_id,
                    instrument,
                    signal_date,
                    CAST({sql_quote(args.candidate_scheme_id)} AS VARCHAR) AS candidate_scheme_id,
                    CASE
                        WHEN ranking_eligible_D0 AND core_score_v18 IS NOT NULL
                        THEN core_score_v18
                           + CASE
                               WHEN core_score_v18 >= 0.80 AND amount_shock_rank IS NOT NULL
                               THEN 0.05 * amount_shock_rank
                               ELSE 0.0
                             END
                        ELSE CAST(NULL AS DOUBLE)
                    END AS model_score_D0,
                    CASE
                        WHEN momentum_rank IS NOT NULL AND liquidity_trend_rank IS NOT NULL
                        THEN 2
                        ELSE (CASE WHEN momentum_rank IS NOT NULL THEN 1 ELSE 0 END)
                           + (CASE WHEN liquidity_trend_rank IS NOT NULL THEN 1 ELSE 0 END)
                    END AS score_component_count,
                    momentum_rank,
                    liquidity_trend_rank,
                    liquidity_rank,
                    amount_shock_rank,
                    core_score_v18
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
                SUM(CASE WHEN s.liquidity_trend_rank IS NOT NULL THEN 1 ELSE 0 END) AS liquidity_trend_rank_rows,
                SUM(CASE WHEN s.liquidity_rank IS NOT NULL THEN 1 ELSE 0 END) AS liquidity_rank_rows,
                SUM(CASE WHEN s.amount_shock_rank IS NOT NULL THEN 1 ELSE 0 END) AS amount_shock_rank_rows,
                SUM(CASE WHEN s.core_score_v18 IS NOT NULL THEN 1 ELSE 0 END) AS core_score_rows,
                SUM(CASE WHEN s.core_score_v18 >= 0.80 AND s.amount_shock_rank IS NOT NULL THEN 1 ELSE 0 END) AS overlay_active_rows
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
        "feature_preset": "price_volume_v23_amount_shock_gated_overlay",
        "score_file": "model_scores_D0.parquet",
        "min_feature_count": 2,
        "baseline_features": [
            "momentum_60_5_raw",
            "liquidity_trend_20_60_raw",
        ],
        "overlay_feature": "amount_shock_5_20_raw",
        "overlay_contract": {
            "core_score_gate_min": 0.80,
            "overlay_bonus_formula": "0.05 * amount_shock_rank",
        },
        "summary_counts": {
            "total_rows": int(audit_row[0] or 0),
            "ranking_eligible_rows": int(audit_row[1] or 0),
            "scored_rows": int(audit_row[2] or 0),
            "eligible_unscored_rows": int(audit_row[3] or 0),
            "momentum_rank_rows": int(audit_row[4] or 0),
            "liquidity_trend_rank_rows": int(audit_row[5] or 0),
            "liquidity_rank_rows": int(audit_row[6] or 0),
            "amount_shock_rank_rows": int(audit_row[7] or 0),
            "core_score_rows": int(audit_row[8] or 0),
            "overlay_active_rows": int(audit_row[9] or 0),
        },
        "notes": [
            "This is a stable project-owned scorer for the v23 gated overlay round.",
            "All features use D0-and-earlier market data only.",
            "The core family remains the frozen v18 two-signal family.",
            "amount_shock_5_20_raw only acts as a small gated overlay inside strong core-score regions.",
            "amount_unit_assumption = thousand CNY",
            "liquidity_rank_direction = higher liquidity -> higher rank",
        ],
        "unit_sanity": {
            "amount_unit_assumption": "thousand_cny",
            "liquidity_rank_direction": "higher_liquidity_means_higher_rank",
        },
    }
    write_json(audit_output, audit)


if __name__ == "__main__":
    main()
