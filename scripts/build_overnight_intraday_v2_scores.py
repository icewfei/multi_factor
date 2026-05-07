#!/opt/anaconda3/envs/quant_trade/bin/python
"""
V2: Direction-corrected overnight/intraday scores based on v1 diagnostic findings.

Key findings from v1:
  - p98 IC = +0.046 (momentum direction)
  - intraday_rev_5d IC = -0.037, corr with p98 = 0.86 → same as p98, opposite direction
  - overnight_rev_5d IC = -0.014, corr with p98 = 0.18 → orthogonal, weak
  - Direction: p98 ranks ASC on negated reversal = momentum. Our v1 ranks ASC on raw
    reversal = opposite. Need to align.

New v2 schemes (all direction-aligned with p98 = momentum/continuation):
  1. intraday_mom_5d_v1    — intraday_rev ranked DESC (momentum direction)
  2. overnight_mom_5d_v1   — overnight_rev ranked DESC (momentum direction)
  3. intraday_p98_ew_v2    — 0.5*intraday_mom + 0.5*p98 (aligned!)
  4. overnight_p98_ew_v2   — 0.5*overnight_mom + 0.5*p98 (aligned!)
  5. intraday80_p98_20_v2  — 0.8*intraday_mom + 0.2*p98
  6. overnight90_p98_10_v2 — 0.9*p98 + 0.1*overnight_mom (light overnight boost)
  7. intraday_pure_5d_v1   — same as intraday_mom but also a simpler name

Also keep 3 v1 composites for comparison.
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
V1_SCORE_PATH = (
    ARTIFACTS_RUN_STATE_DIR
    / "exploratory_overnight_intraday_decomposition_v1"
    / "model_scores_D0.parquet"
)

V2_SCHEMES = {
    "intraday_mom_5d_v1": {
        "feature": "intraday_rev_5d_raw",
        "order": "DESC",
        "desc": "Intraday momentum continuation over 5 days",
    },
    "overnight_mom_5d_v1": {
        "feature": "overnight_rev_5d_raw",
        "order": "DESC",
        "desc": "Overnight momentum continuation over 5 days",
    },
    "intraday_mom_20d_v1": {
        "feature": "intraday_rev_20d_raw",
        "order": "DESC",
        "desc": "Intraday momentum continuation over 20 days",
    },
    "overnight_mom_20d_v1": {
        "feature": "overnight_rev_20d_raw",
        "order": "DESC",
        "desc": "Overnight momentum continuation over 20 days",
    },
}

V2_COMPOSITES = {
    "intraday_p98_ew_v2": {
        "primary": "intraday_mom_5d_v1",
        "w_primary": 0.5,
        "w_p98": 0.5,
        "desc": "Intraday momentum + p98 (direction-aligned) — should match p98 quality",
    },
    "overnight_p98_ew_v2": {
        "primary": "overnight_mom_5d_v1",
        "w_primary": 0.5,
        "w_p98": 0.5,
        "desc": "Overnight momentum + p98 — low-correlation blend",
    },
    "p98_overnight_supplement_v2": {
        "primary": "overnight_mom_5d_v1",
        "w_primary": 0.1,
        "w_p98": 0.9,
        "desc": "p98 with 10% overnight orthogonal boost — preserve p98, add unique overnight info",
    },
    "overnight_intraday_mom_ew_v2": {
        "primary": "overnight_mom_5d_v1",
        "partner_scheme": "intraday_mom_5d_v1",
        "w_primary": 0.5,
        "w_partner": 0.5,
        "desc": "Equal-weight overnight + intraday momentum",
    },
    "intraday80_overnight20_mom_v2": {
        "primary": "intraday_mom_5d_v1",
        "partner_scheme": "overnight_mom_5d_v1",
        "w_primary": 0.8,
        "w_partner": 0.2,
        "desc": "Intraday-heavy momentum blend",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build v2 direction-corrected overnight/intraday scores."
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

    run_dir = (
        Path(args.input_dir) if args.input_dir else (ARTIFACTS_RUN_STATE_DIR / args.run_id)
    )
    sample_panel = run_dir / "project_sample_panel.parquet"
    if not sample_panel.exists():
        raise FileNotFoundError(f"Required input file not found: {sample_panel}")

    # Reuse v1 features from v1 score file (reads feature columns directly)
    if not V1_SCORE_PATH.exists():
        raise FileNotFoundError(f"v1 score file missing: {V1_SCORE_PATH}")

    run_input = json.loads(
        (CONTRACTS_DIR / "run_input_contract.research_trainval_20211231.json").read_text("utf-8")
    )
    snapshot_id = run_input["snapshot_id"]
    source_db_path = (
        Path(run_input["source_root"]["snapshot_path"]) / "duckdb" / "warehouse.duckdb"
    )
    if not source_db_path.exists():
        raise FileNotFoundError(f"Shared warehouse DB not found: {source_db_path}")

    score_output = run_dir / "model_scores_D0_v2.parquet"
    audit_output = run_dir / "model_scores_D0_v2_audit.json"

    con = duckdb.connect()
    try:
        con.execute(f"ATTACH {sql_path(source_db_path)} AS warehouse_db (READ_ONLY)")
        con.execute(
            f"""
            CREATE OR REPLACE VIEW project_sample_panel AS
            SELECT * FROM read_parquet({sql_path(sample_panel)})
            """
        )

        # Recompute bar features for freshness
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
                SUM(intraday_ret) OVER w20 AS intraday_rev_20d_raw
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
                f.intraday_rev_20d_raw
            FROM project_sample_panel p
            LEFT JOIN bar_features f
              ON p.instrument = f.instrument
             AND p.signal_date = f.signal_date
            """
        )

        # Build ranks for v2 single-signal schemes
        rank_views = {}
        for scheme_id, spec in V2_SCHEMES.items():
            feature = spec["feature"]
            order = spec["order"]
            rank_name = f"{scheme_id}_rank"
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
                        ORDER BY {feature} {order}, instrument ASC
                    ) AS {rank_name}
                FROM feature_frame
                WHERE ranking_eligible_D0 AND {feature} IS NOT NULL
                """
            )

        # Load p98
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

        union_parts = []

        # Single-signal v2 schemas
        for scheme_id, spec in V2_SCHEMES.items():
            rank_name = rank_views[scheme_id]
            union_parts.append(f"""
                SELECT
                    f.snapshot_id,
                    f.instrument,
                    f.signal_date,
                    CAST({sql_quote(scheme_id)} AS VARCHAR) AS candidate_scheme_id,
                    r.{rank_name} AS model_score_D0,
                    1 AS score_component_count,
                    NULL AS primary_component,
                    NULL AS partner_component
                FROM feature_frame f
                JOIN rank_{scheme_id} r
                  ON f.snapshot_id = r.snapshot_id
                 AND f.instrument = r.instrument
                 AND f.signal_date = r.signal_date
                WHERE f.ranking_eligible_D0
            """)

        # Composite v2 schemas
        for scheme_id, spec in V2_COMPOSITES.items():
            primary_scheme = spec["primary"]
            primary_rank = rank_views[primary_scheme]
            wp = spec["w_primary"]

            if "partner_scheme" in spec:
                # Two new features composite
                partner_scheme = spec["partner_scheme"]
                partner_rank = rank_views[partner_scheme]
                wp2 = spec["w_partner"]
                union_parts.append(f"""
                    SELECT
                        f.snapshot_id,
                        f.instrument,
                        f.signal_date,
                        CAST({sql_quote(scheme_id)} AS VARCHAR) AS candidate_scheme_id,
                        ({wp:.6f} * COALESCE(r1.{primary_rank}, 0.0))
                            + ({wp2:.6f} * COALESCE(r2.{partner_rank}, 0.0)) AS model_score_D0,
                        2 AS score_component_count,
                        r1.{primary_rank} AS primary_component,
                        r2.{partner_rank} AS partner_component
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
            else:
                # Composite with p98
                wp98 = spec["w_p98"]
                union_parts.append(f"""
                    SELECT
                        f.snapshot_id,
                        f.instrument,
                        f.signal_date,
                        CAST({sql_quote(scheme_id)} AS VARCHAR) AS candidate_scheme_id,
                        ({wp:.6f} * COALESCE(r1.{primary_rank}, 0.0))
                            + ({wp98:.6f} * COALESCE(r2.p98_rank, 0.0)) AS model_score_D0,
                        CASE
                            WHEN r1.{primary_rank} IS NOT NULL AND r2.p98_rank IS NOT NULL THEN 2
                            ELSE 1
                        END AS score_component_count,
                        r1.{primary_rank} AS primary_component,
                        r2.p98_rank AS partner_component
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
        for scheme_id in list(V2_SCHEMES.keys()) + list(V2_COMPOSITES.keys()):
            row = con.execute(
                f"""
                SELECT COUNT(*) AS n, AVG(model_score_D0) AS avg_s,
                       MIN(model_score_D0) AS min_s, MAX(model_score_D0) AS max_s
                FROM read_parquet({sql_path(score_output)})
                WHERE candidate_scheme_id = {sql_quote(scheme_id)}
                """
            ).fetchone()
            summary_rows.append({
                "candidate_scheme_id": scheme_id,
                "scored_rows": int(row[0] or 0),
                "avg_score": float(row[1]) if row[1] is not None else None,
            })

        audit = {
            "run_id": args.run_id,
            "snapshot_id": snapshot_id,
            "v2_changes": "Direction-aligned ranks (DESC = momentum direction like p98). Composites with correct sign alignment.",
            "schemes": list(V2_SCHEMES.keys()) + list(V2_COMPOSITES.keys()),
            "per_scheme_summary": summary_rows,
        }
        write_json(audit_output, audit)

    finally:
        con.close()


if __name__ == "__main__":
    main()
