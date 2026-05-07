#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Build 5-signal confirmatory baseline model_scores_D0.parquet.

The 5 signals are non-redundant, each from a distinct mechanism family:
1. price_volume_beta_20d — 量价敏感度 (price_volume family)
2. intraday_trend_bias_20d — 日内趋势 (intraday family)
3. liquidity_trend_20_60 — 流动性趋势 (liquidity family)
4. momentum_60_5 — 中期动量 (momentum family)
5. upside_range_share_20d — 上涨占比 (intraday structure family)

All features use D0-and-earlier market data only, from serving.vw_bars_daily.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
CONTRACTS_DIR = ROOT / "contracts"
ARTIFACTS_RUN_STATE_DIR = ROOT / "artifacts" / "run_state"

CANDIDATE_SCHEME_ID = "confirmatory_baseline_v1_equally_weighted_5sig"
FEATURE_NAMES = [
    "price_volume_beta_20d_raw",
    "intraday_trend_bias_20d_raw",
    "liquidity_trend_20_60_raw",
    "momentum_60_5_raw",
    "upside_range_share_20d_raw",
]
RANK_COLUMNS = [
    "pv_beta_rank",
    "intraday_trend_rank",
    "liq_trend_rank",
    "momentum_rank",
    "upside_share_rank",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build 5-signal confirmatory baseline scores.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--input-dir", default=None)
    parser.add_argument("--min-feature-count", type=int, default=3)
    return parser.parse_args()


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_path(path: Path) -> str:
    return sql_quote(path.resolve().as_posix())


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    if args.min_feature_count <= 0 or args.min_feature_count > 5:
        raise ValueError("--min-feature-count must be between 1 and 5")

    run_dir = Path(args.input_dir) if args.input_dir else (ARTIFACTS_RUN_STATE_DIR / args.run_id)
    sample_panel = run_dir / "project_sample_panel.parquet"
    if not sample_panel.exists():
        raise FileNotFoundError(f"Required input file not found: {sample_panel}")

    run_input = json.loads((CONTRACTS_DIR / "run_input_contract.current.json").read_text("utf-8"))
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

        # Build all features in one pass
        con.execute(
            f"""
            CREATE OR REPLACE VIEW bar_features AS
            WITH bars AS (
                SELECT
                    ts_code AS instrument,
                    trade_date AS signal_date,
                    adj_open,
                    adj_high,
                    adj_low,
                    adj_close,
                    amount,
                    pct_chg / 100.0 AS pct_ret,
                    LN(GREATEST(amount, 0.0) + 1.0) AS log_amount,
                    CASE
                        WHEN adj_open > 0 THEN adj_close / adj_open - 1.0
                        ELSE NULL
                    END AS intraday_trend_daily,
                    CASE
                        WHEN pct_ret > 0 AND adj_close > 0
                        THEN (adj_high - adj_low) / adj_close
                        ELSE 0.0
                    END AS upside_range_daily,
                    LN(GREATEST(amount, 0.0) + 1.0)
                        - LAG(LN(GREATEST(amount, 0.0) + 1.0), 1) OVER w AS dlog_amount
                FROM warehouse_db.serving.vw_bars_daily
                WHERE snapshot_id = {sql_quote(snapshot_id)}
                WINDOW w AS (PARTITION BY ts_code ORDER BY trade_date)
            )
            SELECT
                instrument,
                signal_date,
                CASE
                    WHEN VAR_SAMP(dlog_amount) OVER w20 > 1e-12
                    THEN COVAR_SAMP(pct_ret, dlog_amount) OVER w20
                         / VAR_SAMP(dlog_amount) OVER w20
                    ELSE NULL
                END AS price_volume_beta_20d_raw,
                AVG(intraday_trend_daily) OVER w20 AS intraday_trend_bias_20d_raw,
                CASE
                    WHEN AVG(log_amount) OVER w60 IS NOT NULL
                     AND AVG(log_amount) OVER w60 != 0
                    THEN AVG(log_amount) OVER w20 - AVG(log_amount) OVER w60
                    ELSE NULL
                END AS liquidity_trend_20_60_raw,
                (LAG(adj_close, 5) OVER w / LAG(adj_close, 60) OVER w - 1.0)
                    AS momentum_60_5_raw,
                CASE
                    WHEN SUM(
                        CASE WHEN adj_close > 0
                        THEN (adj_high - adj_low) / adj_close
                        ELSE 0.0 END
                    ) OVER w20 > 0
                    THEN SUM(upside_range_daily) OVER w20
                         / SUM(
                            CASE WHEN adj_close > 0
                            THEN (adj_high - adj_low) / adj_close
                            ELSE 0.0 END
                         ) OVER w20
                    ELSE NULL
                END AS upside_range_share_20d_raw
            FROM bars
            WINDOW
                w AS (PARTITION BY instrument ORDER BY signal_date),
                w5 AS (
                    PARTITION BY instrument ORDER BY signal_date
                    ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
                ),
                w20 AS (
                    PARTITION BY instrument ORDER BY signal_date
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                ),
                w60 AS (
                    PARTITION BY instrument ORDER BY signal_date
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
                b.price_volume_beta_20d_raw,
                b.intraday_trend_bias_20d_raw,
                b.liquidity_trend_20_60_raw,
                b.momentum_60_5_raw,
                b.upside_range_share_20d_raw
            FROM project_sample_panel p
            LEFT JOIN bar_features b
              ON p.instrument = b.instrument
             AND p.signal_date = b.signal_date
            """
        )

        # Cross-sectional percentile ranks
        con.execute(
            """
            CREATE OR REPLACE VIEW pv_beta_ranks AS
            SELECT snapshot_id, instrument, signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY price_volume_beta_20d_raw DESC, instrument ASC
                ) AS pv_beta_rank
            FROM feature_frame
            WHERE ranking_eligible_D0 AND price_volume_beta_20d_raw IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW intraday_trend_ranks AS
            SELECT snapshot_id, instrument, signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY intraday_trend_bias_20d_raw DESC, instrument ASC
                ) AS intraday_trend_rank
            FROM feature_frame
            WHERE ranking_eligible_D0 AND intraday_trend_bias_20d_raw IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW liq_trend_ranks AS
            SELECT snapshot_id, instrument, signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY liquidity_trend_20_60_raw DESC, instrument ASC
                ) AS liq_trend_rank
            FROM feature_frame
            WHERE ranking_eligible_D0 AND liquidity_trend_20_60_raw IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW momentum_ranks AS
            SELECT snapshot_id, instrument, signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY momentum_60_5_raw DESC, instrument ASC
                ) AS momentum_rank
            FROM feature_frame
            WHERE ranking_eligible_D0 AND momentum_60_5_raw IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW upside_share_ranks AS
            SELECT snapshot_id, instrument, signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY upside_range_share_20d_raw DESC, instrument ASC
                ) AS upside_share_rank
            FROM feature_frame
            WHERE ranking_eligible_D0 AND upside_range_share_20d_raw IS NOT NULL
            """
        )

        component_count_expr = " + ".join(
            f"CASE WHEN {col} IS NOT NULL THEN 1 ELSE 0 END" for col in RANK_COLUMNS
        )
        score_sum_expr = " + ".join(f"COALESCE({col}, 0.0)" for col in RANK_COLUMNS)

        con.execute(
            f"""
            COPY (
                WITH score_frame AS (
                    SELECT
                        f.snapshot_id,
                        f.instrument,
                        f.signal_date,
                        f.ranking_eligible_D0,
                        pv.pv_beta_rank,
                        it.intraday_trend_rank,
                        lt.liq_trend_rank,
                        m.momentum_rank,
                        us.upside_share_rank,
                        ({component_count_expr}) AS score_component_count
                    FROM feature_frame f
                    LEFT JOIN pv_beta_ranks pv
                      ON f.snapshot_id = pv.snapshot_id
                     AND f.instrument = pv.instrument
                     AND f.signal_date = pv.signal_date
                    LEFT JOIN intraday_trend_ranks it
                      ON f.snapshot_id = it.snapshot_id
                     AND f.instrument = it.instrument
                     AND f.signal_date = it.signal_date
                    LEFT JOIN liq_trend_ranks lt
                      ON f.snapshot_id = lt.snapshot_id
                     AND f.instrument = lt.instrument
                     AND f.signal_date = lt.signal_date
                    LEFT JOIN momentum_ranks m
                      ON f.snapshot_id = m.snapshot_id
                     AND f.instrument = m.instrument
                     AND f.signal_date = m.signal_date
                    LEFT JOIN upside_share_ranks us
                      ON f.snapshot_id = us.snapshot_id
                     AND f.instrument = us.instrument
                     AND f.signal_date = us.signal_date
                )
                SELECT
                    snapshot_id,
                    instrument,
                    signal_date,
                    CAST({sql_quote(CANDIDATE_SCHEME_ID)} AS VARCHAR) AS candidate_scheme_id,
                    CASE
                        WHEN ranking_eligible_D0 AND score_component_count >= {args.min_feature_count}
                        THEN ({score_sum_expr}) / CAST(score_component_count AS DOUBLE)
                        ELSE CAST(NULL AS DOUBLE)
                    END AS model_score_D0,
                    score_component_count,
                    pv_beta_rank,
                    intraday_trend_rank,
                    liq_trend_rank,
                    momentum_rank,
                    upside_share_rank
                FROM score_frame
            ) TO {sql_path(score_output)} (FORMAT PARQUET)
            """
        )

        audit_counts = con.execute(
            f"""
            SELECT
                COUNT(*) AS total_rows,
                SUM(CASE WHEN ranking_eligible_D0 THEN 1 ELSE 0 END) AS ranking_eligible_rows,
                SUM(CASE WHEN model_score_D0 IS NOT NULL THEN 1 ELSE 0 END) AS scored_rows,
                SUM(CASE WHEN ranking_eligible_D0 AND model_score_D0 IS NULL THEN 1 ELSE 0 END) AS eligible_unscored_rows,
                SUM(CASE WHEN score_component_count >= {args.min_feature_count} THEN 1 ELSE 0 END) AS min_feature_ready_rows,
                SUM(CASE WHEN pv_beta_rank IS NOT NULL THEN 1 ELSE 0 END) AS pv_beta_rank_rows,
                SUM(CASE WHEN intraday_trend_rank IS NOT NULL THEN 1 ELSE 0 END) AS intraday_trend_rows,
                SUM(CASE WHEN liq_trend_rank IS NOT NULL THEN 1 ELSE 0 END) AS liq_trend_rows,
                SUM(CASE WHEN momentum_rank IS NOT NULL THEN 1 ELSE 0 END) AS momentum_rows,
                SUM(CASE WHEN upside_share_rank IS NOT NULL THEN 1 ELSE 0 END) AS upside_share_rows
            FROM (
                SELECT
                    p.ranking_eligible_D0,
                    s.model_score_D0,
                    s.score_component_count,
                    s.pv_beta_rank,
                    s.intraday_trend_rank,
                    s.liq_trend_rank,
                    s.momentum_rank,
                    s.upside_share_rank
                FROM read_parquet({sql_path(score_output)}) s
                INNER JOIN project_sample_panel p
                  ON s.snapshot_id = p.snapshot_id
                 AND s.instrument = p.instrument
                 AND s.signal_date = p.signal_date
            )
            """
        ).fetchone()
    finally:
        con.close()

    audit = {
        "run_id": args.run_id,
        "snapshot_id": snapshot_id,
        "candidate_scheme_id": CANDIDATE_SCHEME_ID,
        "score_file": score_output.name,
        "min_feature_count": args.min_feature_count,
        "features": FEATURE_NAMES,
        "summary_counts": {
            "total_rows": int(audit_counts[0] or 0),
            "ranking_eligible_rows": int(audit_counts[1] or 0),
            "scored_rows": int(audit_counts[2] or 0),
            "eligible_unscored_rows": int(audit_counts[3] or 0),
            "min_feature_ready_rows": int(audit_counts[4] or 0),
            "pv_beta_rank_rows": int(audit_counts[5] or 0),
            "intraday_trend_rows": int(audit_counts[6] or 0),
            "liq_trend_rows": int(audit_counts[7] or 0),
            "momentum_rows": int(audit_counts[8] or 0),
            "upside_share_rows": int(audit_counts[9] or 0),
        },
        "notes": [
            "Confirmatory baseline v1: 5 non-redundant signals equally weighted after cross-sectional percentile ranking.",
            "All features use D0-and-earlier market data from serving.vw_bars_daily.",
            "Snapshot: warehouse_20260429_trainval_20211231 (train+valid only, test set excluded).",
        ],
    }
    write_json(audit_output, audit)


if __name__ == "__main__":
    main()
