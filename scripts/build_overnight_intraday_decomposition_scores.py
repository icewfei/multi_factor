#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Build overnight/intraday return decomposition features and model scores.

Features:
  1. overnight_rev_5d_raw  — cumulative overnight return over 5 days
  2. intraday_rev_5d_raw   — cumulative intraday return over 5 days
  3. overnight_rev_20d_raw — cumulative overnight return over 20 days
  4. intraday_rev_20d_raw  — cumulative intraday return over 20 days
  5. overnight_vol_20d_raw — 20d overnight return volatility (gap instability)
  6. overnight_intraday_ratio_20d_raw — overnight / (|overnight| + |intraday|)

Candidate schemes (all exploratory):
  - overnight_rev_5d_v1        — pure overnight reversal, rank ASC
  - intraday_rev_5d_v1         — pure intraday reversal, rank ASC
  - overnight_rev_20d_v1       — longer-window overnight reversal
  - intraday_rev_20d_v1        — longer-window intraday reversal
  - overnight_p98_ew_v1        — overnight_rev_5d + p98, equal weight
  - intraday_p98_ew_v1         — intraday_rev_5d + p98, equal weight
  - overnight_intraday_ew_v1   — overnight + intraday, equal weight
  - overnight_vol_5d_v1        — overnight gap volatility

All features use D0-and-earlier data only (PIT-safe).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

ROOT = Path("/Users/wy/MiscProject/multi_factor")
CONTRACTS_DIR = ROOT / "contracts"
ARTIFACTS_RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
P98_SCORE_PATH = (
    ARTIFACTS_RUN_STATE_DIR
    / "confirmatory_reversal_p98_trainval_20260506"
    / "model_scores_D0.parquet"
)
P98_SCHEME_ID = "reversal_tail_exclude_p98_v1"

CANDIDATE_SCHEMES = {
    "overnight_rev_5d_v1": {
        "feature": "overnight_rev_5d_raw",
        "rank_order": "ASC",
        "rank_name": "overnight_rev_5d_rank",
        "description": "Overnight return reversal over 5 days",
    },
    "intraday_rev_5d_v1": {
        "feature": "intraday_rev_5d_raw",
        "rank_order": "ASC",
        "rank_name": "intraday_rev_5d_rank",
        "description": "Intraday return reversal over 5 days",
    },
    "overnight_rev_20d_v1": {
        "feature": "overnight_rev_20d_raw",
        "rank_order": "ASC",
        "rank_name": "overnight_rev_20d_rank",
        "description": "Overnight return reversal over 20 days",
    },
    "intraday_rev_20d_v1": {
        "feature": "intraday_rev_20d_raw",
        "rank_order": "ASC",
        "rank_name": "intraday_rev_20d_rank",
        "description": "Intraday return reversal over 20 days",
    },
    "overnight_vol_5d_v1": {
        "feature": "overnight_vol_20d_raw",
        "rank_order": "DESC",
        "rank_name": "overnight_vol_20d_rank",
        "description": "Overnight gap volatility — higher vol = more reversal potential",
    },
    "overnight_intraday_divergence_v1": {
        "feature": "overnight_intraday_ratio_20d_raw",
        "rank_order": "ASC",
        "rank_name": "oi_ratio_20d_rank",
        "description": "Ratio of overnight to total return — divergence signal",
    },
}

COMPOSITE_SCHEMES = {
    "overnight_p98_ew_v1": {
        "primary_scheme": "overnight_rev_5d_v1",
        "partner": "p98",
        "weight_primary": 0.5,
        "weight_partner": 0.5,
        "description": "Overnight reversal + p98 reversal, equal weight",
    },
    "intraday_p98_ew_v1": {
        "primary_scheme": "intraday_rev_5d_v1",
        "partner": "p98",
        "weight_primary": 0.5,
        "weight_partner": 0.5,
        "description": "Intraday reversal + p98 reversal, equal weight",
    },
    "overnight_intraday_ew_v1": {
        "primary_scheme": "overnight_rev_5d_v1",
        "partner_scheme": "intraday_rev_5d_v1",
        "partner": "intraday",
        "weight_primary": 0.5,
        "weight_partner": 0.5,
        "description": "Overnight reversal + Intraday reversal, equal weight",
    },
    "overnight70_p98_30_v1": {
        "primary_scheme": "overnight_rev_5d_v1",
        "partner": "p98",
        "weight_primary": 0.7,
        "weight_partner": 0.3,
        "description": "Overnight reversal 70% + p98 30%",
    },
    "intraday70_p98_30_v1": {
        "primary_scheme": "intraday_rev_5d_v1",
        "partner": "p98",
        "weight_primary": 0.7,
        "weight_partner": 0.3,
        "description": "Intraday reversal 70% + p98 30%",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build overnight/intraday decomposition model scores."
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--input-dir", default=None)
    return parser.parse_args()


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_path(path: Path) -> str:
    return sql_quote(path.resolve().as_posix())


def write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    args = parse_args()

    run_dir = Path(args.input_dir) if args.input_dir else (ARTIFACTS_RUN_STATE_DIR / args.run_id)
    sample_panel = run_dir / "project_sample_panel.parquet"
    if not sample_panel.exists():
        raise FileNotFoundError(f"Required input file not found: {sample_panel}")

    run_input = json.loads(
        (CONTRACTS_DIR / "run_input_contract.research_trainval_20211231.json").read_text("utf-8")
    )
    snapshot_id = run_input["snapshot_id"]
    source_db_path = (
        Path(run_input["source_root"]["snapshot_path"]) / "duckdb" / "warehouse.duckdb"
    )
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

        # Build overnight/intraday features from bars
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
                    CASE
                        WHEN LAG(adj_close, 1) OVER w_instr > 0 AND adj_open > 0
                        THEN adj_open / LAG(adj_close, 1) OVER w_instr - 1.0
                        ELSE NULL
                    END AS overnight_ret,
                    CASE
                        WHEN adj_open > 0
                        THEN adj_close / adj_open - 1.0
                        ELSE NULL
                    END AS intraday_ret
                FROM warehouse_db.serving.vw_bars_daily
                WHERE snapshot_id = {sql_quote(snapshot_id)}
                WINDOW w_instr AS (PARTITION BY ts_code ORDER BY trade_date)
            )
            SELECT
                instrument,
                signal_date,
                SUM(overnight_ret) OVER w5 AS overnight_rev_5d_raw,
                SUM(intraday_ret) OVER w5 AS intraday_rev_5d_raw,
                SUM(overnight_ret) OVER w20 AS overnight_rev_20d_raw,
                SUM(intraday_ret) OVER w20 AS intraday_rev_20d_raw,
                STDDEV_SAMP(overnight_ret) OVER w20 AS overnight_vol_20d_raw,
                CASE
                    WHEN AVG(ABS(overnight_ret) + ABS(intraday_ret)) OVER w20 > 1e-12
                    THEN AVG(overnight_ret) OVER w20
                         / AVG(ABS(overnight_ret) + ABS(intraday_ret)) OVER w20
                    ELSE NULL
                END AS overnight_intraday_ratio_20d_raw,
                AVG(overnight_ret) OVER w5 AS overnight_avg_5d_raw,
                AVG(intraday_ret) OVER w5 AS intraday_avg_5d_raw
            FROM bars
            WINDOW
                w5 AS (
                    PARTITION BY instrument
                    ORDER BY signal_date
                    ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
                ),
                w20 AS (
                    PARTITION BY instrument
                    ORDER BY signal_date
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
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
                f.overnight_rev_5d_raw,
                f.intraday_rev_5d_raw,
                f.overnight_rev_20d_raw,
                f.intraday_rev_20d_raw,
                f.overnight_vol_20d_raw,
                f.overnight_intraday_ratio_20d_raw,
                f.overnight_avg_5d_raw,
                f.intraday_avg_5d_raw
            FROM project_sample_panel p
            LEFT JOIN bar_features f
              ON p.instrument = f.instrument
             AND p.signal_date = f.signal_date
            """
        )

        # Build ranks for each single-signal scheme
        rank_views = {}
        for scheme_id, spec in CANDIDATE_SCHEMES.items():
            feature_col = spec["feature"]
            rank_name = spec["rank_name"]
            order_clause = f"{feature_col} {spec['rank_order']}, instrument ASC"
            rank_views[scheme_id] = rank_name

            con.execute(
                f"""
                CREATE OR REPLACE VIEW rank_{scheme_id} AS
                SELECT
                    snapshot_id,
                    instrument,
                    signal_date,
                    PERCENT_RANK() OVER (
                        PARTITION BY snapshot_id, signal_date
                        ORDER BY {order_clause}
                    ) AS {rank_name}
                FROM feature_frame
                WHERE ranking_eligible_D0 AND {feature_col} IS NOT NULL
                """
            )

        # Load p98 scores for composites
        con.execute(
            f"""
            CREATE OR REPLACE VIEW p98_scores AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                model_score_D0 AS p98_rank
            FROM read_parquet({sql_path(P98_SCORE_PATH)})
            WHERE candidate_scheme_id = {sql_quote(P98_SCHEME_ID)}
              AND model_score_D0 IS NOT NULL
            """
        )

        # Also load intraday rank for intraday composites
        intraday_rank_view = rank_views["intraday_rev_5d_v1"]

        # Build all scores in one output
        union_parts = []

        # Single-signal schemes
        for scheme_id, spec in CANDIDATE_SCHEMES.items():
            rank_name = spec["rank_name"]
            union_parts.append(f"""
                SELECT
                    f.snapshot_id,
                    f.instrument,
                    f.signal_date,
                    CAST({sql_quote(scheme_id)} AS VARCHAR) AS candidate_scheme_id,
                    r.{rank_name} AS model_score_D0,
                    1 AS score_component_count,
                    NULL AS overnight_component,
                    NULL AS intraday_component,
                    NULL AS p98_component
                FROM feature_frame f
                LEFT JOIN rank_{scheme_id} r
                  ON f.snapshot_id = r.snapshot_id
                 AND f.instrument = r.instrument
                 AND f.signal_date = r.signal_date
                WHERE f.ranking_eligible_D0
                  AND r.{rank_name} IS NOT NULL
            """)

        # Composite schemes
        for scheme_id, spec in COMPOSITE_SCHEMES.items():
            primary_scheme = spec["primary_scheme"]
            primary_rank = rank_views[primary_scheme]
            w1 = spec["weight_primary"]
            w2 = spec["weight_partner"]

            if spec["partner"] == "p98":
                union_parts.append(f"""
                    SELECT
                        f.snapshot_id,
                        f.instrument,
                        f.signal_date,
                        CAST({sql_quote(scheme_id)} AS VARCHAR) AS candidate_scheme_id,
                        ({w1:.6f} * COALESCE(r1.{primary_rank}, 0.0))
                            + ({w2:.6f} * COALESCE(r2.p98_rank, 0.0)) AS model_score_D0,
                        CASE
                            WHEN r1.{primary_rank} IS NOT NULL AND r2.p98_rank IS NOT NULL THEN 2
                            ELSE 1
                        END AS score_component_count,
                        r1.{primary_rank} AS overnight_component,
                        NULL AS intraday_component,
                        r2.p98_rank AS p98_component
                    FROM feature_frame f
                    LEFT JOIN rank_{primary_scheme} r1
                      ON f.snapshot_id = r1.snapshot_id
                     AND f.instrument = r1.instrument
                     AND f.signal_date = r1.signal_date
                    LEFT JOIN p98_scores r2
                      ON f.snapshot_id = r2.snapshot_id
                     AND f.instrument = r2.instrument
                     AND f.signal_date = r2.signal_date
                    WHERE f.ranking_eligible_D0
                """)
            elif spec["partner"] == "intraday":
                partner_scheme = spec["partner_scheme"]
                partner_rank = rank_views[partner_scheme]
                union_parts.append(f"""
                    SELECT
                        f.snapshot_id,
                        f.instrument,
                        f.signal_date,
                        CAST({sql_quote(scheme_id)} AS VARCHAR) AS candidate_scheme_id,
                        ({w1:.6f} * COALESCE(r1.{primary_rank}, 0.0))
                            + ({w2:.6f} * COALESCE(r2.{partner_rank}, 0.0)) AS model_score_D0,
                        CASE
                            WHEN r1.{primary_rank} IS NOT NULL AND r2.{partner_rank} IS NOT NULL THEN 2
                            ELSE 1
                        END AS score_component_count,
                        r1.{primary_rank} AS overnight_component,
                        r2.{partner_rank} AS intraday_component,
                        NULL AS p98_component
                    FROM feature_frame f
                    LEFT JOIN rank_{primary_scheme} r1
                      ON f.snapshot_id = r1.snapshot_id
                     AND f.instrument = r1.instrument
                     AND f.signal_date = r1.signal_date
                    LEFT JOIN rank_{partner_scheme} r2
                      ON f.snapshot_id = r2.snapshot_id
                     AND f.instrument = r2.instrument
                     AND f.signal_date = r2.signal_date
                    WHERE f.ranking_eligible_D0
                """)

        union_sql = " UNION ALL ".join(union_parts)

        con.execute(
            f"""
            COPY (
                {union_sql}
            ) TO {sql_path(score_output)} (FORMAT PARQUET)
            """
        )

        # Audit
        summary_rows = []
        all_scheme_ids = list(CANDIDATE_SCHEMES.keys()) + list(COMPOSITE_SCHEMES.keys())
        for scheme_id in all_scheme_ids:
            row = con.execute(
                f"""
                SELECT
                    COUNT(*) AS scored_rows,
                    AVG(model_score_D0) AS avg_score,
                    MIN(model_score_D0) AS min_score,
                    MAX(model_score_D0) AS max_score,
                    AVG(CAST(score_component_count AS DOUBLE)) AS avg_components
                FROM read_parquet({sql_path(score_output)})
                WHERE candidate_scheme_id = {sql_quote(scheme_id)}
                """
            ).fetchone()
            summary_rows.append(
                {
                    "candidate_scheme_id": scheme_id,
                    "scored_rows": int(row[0] or 0),
                    "avg_score": float(row[1]) if row[1] is not None else None,
                    "min_score": float(row[2]) if row[2] is not None else None,
                    "max_score": float(row[3]) if row[3] is not None else None,
                    "avg_components": float(row[4]) if row[4] is not None else None,
                }
            )

        total_rows = con.execute(
            f"""
            SELECT COUNT(*) FROM read_parquet({sql_path(score_output)})
            """
        ).fetchone()

        audit = {
            "run_id": args.run_id,
            "snapshot_id": snapshot_id,
            "score_builder": "build_overnight_intraday_decomposition_scores.py",
            "p98_reference": str(P98_SCORE_PATH),
            "candidate_schemes": {
                "single_signal": list(CANDIDATE_SCHEMES.keys()),
                "composite": list(COMPOSITE_SCHEMES.keys()),
            },
            "total_output_rows": int(total_rows[0] or 0),
            "per_scheme_summary": summary_rows,
            "feature_definitions": {
                "overnight_ret": "adj_open / LAG(adj_close, 1) - 1",
                "intraday_ret": "adj_close / adj_open - 1",
                "overnight_rev_5d": "SUM(overnight_ret) OVER 5d",
                "intraday_rev_5d": "SUM(intraday_ret) OVER 5d",
                "overnight_rev_20d": "SUM(overnight_ret) OVER 20d",
                "intraday_rev_20d": "SUM(intraday_ret) OVER 20d",
                "overnight_vol_20d": "STDDEV(overnight_ret) OVER 20d",
                "overnight_intraday_ratio_20d": "AVG(overnight) / AVG(|overnight| + |intraday|) OVER 20d",
            },
            "pit_compliance": "All features use D0-and-earlier data only. LAG references prior trading days within instrument partition.",
        }
        write_json(audit_output, audit)

    finally:
        con.close()


if __name__ == "__main__":
    main()
