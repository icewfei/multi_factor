#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Build model_scores_D0.parquet for the p98 tail-handled reversal baseline and the
reversal+cord30 equal-weight composite under the frozen trainval panels.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
REVERSAL_SOURCE = RUN_STATE_DIR / "exploratory_cross_horizon_c1_reversal_only" / "model_scores_D0.parquet"
CORD30_SOURCE = RUN_STATE_DIR / "confirmatory_cord30_trainval_20260429" / "model_scores_D0.parquet"
CORR30_SOURCE = RUN_STATE_DIR / "confirmatory_corr30_trainval_20260430" / "model_scores_D0.parquet"

P98_BASELINE_ID = "reversal_tail_exclude_p98_v1"
P98_TOP12_ID = "reversal_tail_exclude_p98_top12_v1"
COMPOSITE_ID = "reversal_p98_cord30_ew_v1"
LIQGUARD60_ID = "reversal_p98_cord30_liqguard60_v1"
CORR30_COMPOSITE_ID = "reversal_p98_corr30_ew_v1"
CORD30_W10_ID = "reversal_p98_cord30_w10_v1"
IRASYM_W20_ID = "reversal_p98_intraday_reversal_asymmetry_w20_v1"
CORD30_CANDIDATE_ID = "price_volume_single_signal_alpha158_cord30_v1"
CORR30_CANDIDATE_ID = "price_volume_single_signal_alpha158_corr30_v1"

COMPOSITE_SPECS = {
    COMPOSITE_ID: {
        "partner_view": "cord30_scores",
        "partner_candidate_scheme_id": CORD30_CANDIDATE_ID,
        "partner_run_id": "confirmatory_cord30_trainval_20260429",
        "reversal_weight": 0.5,
        "partner_weight": 0.5,
    },
    LIQGUARD60_ID: {
        "partner_view": "cord30_scores",
        "partner_candidate_scheme_id": CORD30_CANDIDATE_ID,
        "partner_run_id": "confirmatory_cord30_trainval_20260429",
        "reversal_weight": 0.5,
        "partner_weight": 0.5,
    },
    CORR30_COMPOSITE_ID: {
        "partner_view": "corr30_scores",
        "partner_candidate_scheme_id": CORR30_CANDIDATE_ID,
        "partner_run_id": "confirmatory_corr30_trainval_20260430",
        "reversal_weight": 0.5,
        "partner_weight": 0.5,
    },
    CORD30_W10_ID: {
        "partner_view": "cord30_scores",
        "partner_candidate_scheme_id": CORD30_CANDIDATE_ID,
        "partner_run_id": "confirmatory_cord30_trainval_20260429",
        "reversal_weight": 0.9,
        "partner_weight": 0.1,
    },
    IRASYM_W20_ID: {
        "partner_source_kind": "internal_reversal",
        "internal_partner_col": "intraday_reversal_asymmetry_rank",
        "partner_run_id": "exploratory_cross_horizon_c1_reversal_only",
        "reversal_weight": 0.8,
        "partner_weight": 0.2,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build reversal tail/composite model scores.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--candidate-scheme-id", required=True)
    parser.add_argument("--input-dir", default=None)
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_path(path: Path) -> str:
    return sql_quote(path.resolve().as_posix())


def main() -> None:
    args = parse_args()
    if args.candidate_scheme_id not in {P98_BASELINE_ID, P98_TOP12_ID, *COMPOSITE_SPECS.keys()}:
        raise ValueError(f"Unsupported candidate_scheme_id: {args.candidate_scheme_id}")

    run_dir = Path(args.input_dir) if args.input_dir else (RUN_STATE_DIR / args.run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    sample_panel = run_dir / "project_sample_panel.parquet"
    if not sample_panel.exists():
        raise FileNotFoundError(f"Required input file not found: {sample_panel}")
    if not REVERSAL_SOURCE.exists():
        raise FileNotFoundError(f"Missing reversal source: {REVERSAL_SOURCE}")
    if not CORD30_SOURCE.exists():
        raise FileNotFoundError(f"Missing cord30 source: {CORD30_SOURCE}")
    if not CORR30_SOURCE.exists():
        raise FileNotFoundError(f"Missing corr30 source: {CORR30_SOURCE}")

    score_path = run_dir / "model_scores_D0.parquet"
    audit_path = run_dir / "model_scores_D0_audit.json"

    con = duckdb.connect()
    try:
        con.execute(
            f"CREATE OR REPLACE VIEW sample_panel AS SELECT * FROM read_parquet({sql_path(sample_panel)})"
        )
        con.execute(
            f"CREATE OR REPLACE VIEW reversal_scores AS SELECT * FROM read_parquet({sql_path(REVERSAL_SOURCE)})"
        )
        con.execute(
            f"CREATE OR REPLACE VIEW cord30_scores AS SELECT * FROM read_parquet({sql_path(CORD30_SOURCE)})"
        )
        con.execute(
            f"CREATE OR REPLACE VIEW corr30_scores AS SELECT * FROM read_parquet({sql_path(CORR30_SOURCE)})"
        )

        con.execute(
            """
            CREATE OR REPLACE VIEW nr_raw AS
            SELECT
                s.snapshot_id,
                s.instrument,
                s.signal_date,
                s.ranking_eligible_D0,
                -1.0 * r.model_score_D0 AS nr_score,
                r.liquidity_rank AS liquidity_rank
            FROM sample_panel s
            LEFT JOIN reversal_scores r
              ON s.snapshot_id = r.snapshot_id
             AND s.instrument = r.instrument
             AND s.signal_date = r.signal_date
            WHERE s.ranking_eligible_D0
              AND r.model_score_D0 IS NOT NULL
        """
        )

        con.execute(
            """
            CREATE OR REPLACE VIEW nr_daily_p98 AS
            SELECT
                snapshot_id,
                signal_date,
                PERCENTILE_CONT(0.98) WITHIN GROUP (ORDER BY nr_score) AS p98
            FROM nr_raw
            GROUP BY snapshot_id, signal_date
        """
        )

        con.execute(
            """
            CREATE OR REPLACE VIEW nr_p98 AS
            SELECT
                n.snapshot_id,
                n.instrument,
                n.signal_date,
                n.nr_score,
                n.liquidity_rank
            FROM nr_raw n
            JOIN nr_daily_p98 p
              ON n.snapshot_id = p.snapshot_id
             AND n.signal_date = p.signal_date
            WHERE n.nr_score < p.p98
        """
        )

        partner_score_col = "partner_score"

        con.execute(
            "CREATE OR REPLACE VIEW partner_base AS "
            "SELECT CAST(NULL AS BIGINT) AS snapshot_id, CAST(NULL AS VARCHAR) AS instrument, "
            "CAST(NULL AS VARCHAR) AS signal_date, CAST(NULL AS DOUBLE) AS partner_score "
            "WHERE FALSE"
        )

        if args.candidate_scheme_id in {P98_BASELINE_ID, P98_TOP12_ID}:
            build_sql = f"""
                COPY (
                    WITH ranked AS (
                        SELECT
                            snapshot_id,
                            instrument,
                            signal_date,
                            liquidity_rank,
                            PERCENT_RANK() OVER (
                                PARTITION BY snapshot_id, signal_date
                                ORDER BY nr_score ASC, instrument ASC
                            ) AS model_score_D0
                        FROM nr_p98
                    )
                    SELECT
                        s.snapshot_id,
                        s.instrument,
                        s.signal_date,
                        CAST({sql_quote(args.candidate_scheme_id)} AS VARCHAR) AS candidate_scheme_id,
                        r.model_score_D0,
                        r.liquidity_rank,
                        CASE WHEN r.model_score_D0 IS NOT NULL THEN 1 ELSE 0 END AS score_component_count,
                        CAST(NULL AS DOUBLE) AS raw_signal_value_cord30,
                        CAST(NULL AS DOUBLE) AS rank_component_cord30,
                        CAST(NULL AS DOUBLE) AS composite_component_count
                    FROM sample_panel s
                    LEFT JOIN ranked r
                      ON s.snapshot_id = r.snapshot_id
                     AND s.instrument = r.instrument
                     AND s.signal_date = r.signal_date
                ) TO {sql_path(score_path)} (FORMAT PARQUET)
            """
        else:
            composite_id = args.candidate_scheme_id
            spec = COMPOSITE_SPECS[composite_id]
            reversal_weight = spec["reversal_weight"]
            partner_weight = spec["partner_weight"]
            if spec.get("partner_source_kind") == "internal_reversal":
                internal_partner_col = spec["internal_partner_col"]
                con.execute(
                    f"""
                    CREATE OR REPLACE VIEW partner_base AS
                    SELECT
                        snapshot_id,
                        instrument,
                        signal_date,
                        {internal_partner_col} AS {partner_score_col}
                    FROM reversal_scores
                    WHERE {internal_partner_col} IS NOT NULL
                    """
                )
            else:
                partner_source_view = spec["partner_view"]
                partner_scheme_id = spec["partner_candidate_scheme_id"]
                con.execute(
                    f"""
                    CREATE OR REPLACE VIEW partner_base AS
                    SELECT
                        snapshot_id,
                        instrument,
                        signal_date,
                        model_score_D0 AS {partner_score_col}
                    FROM {partner_source_view}
                    WHERE candidate_scheme_id = {sql_quote(partner_scheme_id)}
                      AND model_score_D0 IS NOT NULL
                    """
                )
            build_sql = f"""
                COPY (
                    WITH joined AS (
                        SELECT
                            n.snapshot_id,
                            n.instrument,
                            n.signal_date,
                            n.liquidity_rank,
                            n.nr_score,
                            c.{partner_score_col}
                        FROM nr_p98 n
                        JOIN partner_base c
                          ON n.snapshot_id = c.snapshot_id
                         AND n.instrument = c.instrument
                         AND n.signal_date = c.signal_date
                    ),
                    ranked AS (
                        SELECT
                            snapshot_id,
                            instrument,
                            signal_date,
                            liquidity_rank,
                            nr_score,
                            {partner_score_col},
                            PERCENT_RANK() OVER (
                                PARTITION BY snapshot_id, signal_date
                                ORDER BY nr_score ASC, instrument ASC
                            ) AS rev_rank,
                            PERCENT_RANK() OVER (
                                PARTITION BY snapshot_id, signal_date
                                ORDER BY {partner_score_col} ASC, instrument ASC
                            ) AS partner_rank
                        FROM joined
                    )
                    SELECT
                        s.snapshot_id,
                        s.instrument,
                        s.signal_date,
                        CAST({sql_quote(composite_id)} AS VARCHAR) AS candidate_scheme_id,
                        ({reversal_weight:.6f} * r.rev_rank) + ({partner_weight:.6f} * r.partner_rank) AS model_score_D0,
                        r.liquidity_rank,
                        CASE
                            WHEN r.rev_rank IS NOT NULL AND r.partner_rank IS NOT NULL THEN 2
                            ELSE 0
                        END AS score_component_count,
                        r.{partner_score_col} AS raw_signal_value_cord30,
                        r.partner_rank AS rank_component_cord30,
                        r.rev_rank AS composite_component_count
                    FROM sample_panel s
                    LEFT JOIN ranked r
                      ON s.snapshot_id = r.snapshot_id
                     AND s.instrument = r.instrument
                     AND s.signal_date = r.signal_date
                ) TO {sql_path(score_path)} (FORMAT PARQUET)
            """

        con.execute(build_sql)

        audit_row = con.execute(
            f"""
            SELECT
                COUNT(*) AS total_rows,
                SUM(CASE WHEN ranking_eligible_D0 THEN 1 ELSE 0 END) AS eligible_rows,
                SUM(CASE WHEN model_score_D0 IS NOT NULL THEN 1 ELSE 0 END) AS scored_rows,
                AVG(model_score_D0) AS avg_score,
                MIN(model_score_D0) AS min_score,
                MAX(model_score_D0) AS max_score
            FROM (
                SELECT s.ranking_eligible_D0, m.model_score_D0
                FROM sample_panel s
                LEFT JOIN read_parquet({sql_path(score_path)}) m
                  ON s.snapshot_id = m.snapshot_id
                 AND s.instrument = m.instrument
                 AND s.signal_date = m.signal_date
            )
        """
        ).fetchone()

        audit = {
            "candidate_scheme_id": args.candidate_scheme_id,
            "score_builder": "build_reversal_tail_composite_model_scores.py",
            "source_runs": {
                "reversal_source_run_id": "exploratory_cross_horizon_c1_reversal_only",
                "partner_source_run_id": (
                    COMPOSITE_SPECS[args.candidate_scheme_id]["partner_run_id"]
                    if args.candidate_scheme_id in COMPOSITE_SPECS
                    else None
                )
            },
            "tail_handling_rule": "negate reversal score; exclude rows with raw negated score strictly above daily p98",
            "alias_of": (
                P98_BASELINE_ID
                if args.candidate_scheme_id == P98_TOP12_ID
                else None
            ),
            "composite_weights": (
                {
                    "reversal_weight": COMPOSITE_SPECS[args.candidate_scheme_id]["reversal_weight"],
                    "partner_weight": COMPOSITE_SPECS[args.candidate_scheme_id]["partner_weight"],
                }
                if args.candidate_scheme_id in COMPOSITE_SPECS
                else None
            ),
            "summary_counts": {
                "total_rows": int(audit_row[0] or 0),
                "ranking_eligible_rows": int(audit_row[1] or 0),
                "scored_rows": int(audit_row[2] or 0)
            },
            "score_distribution": {
                "avg_score": float(audit_row[3]) if audit_row[3] is not None else None,
                "min_score": float(audit_row[4]) if audit_row[4] is not None else None,
                "max_score": float(audit_row[5]) if audit_row[5] is not None else None
            }
        }
        audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    finally:
        con.close()


if __name__ == "__main__":
    main()
