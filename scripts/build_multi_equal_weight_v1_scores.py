#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Build a reproducible `multi_equal_weight_v1` model_scores_D0.parquet.

Contract:
- Uses the existing p98 score file as one fixed component.
- Recomputes Alpha158 `cord30` / `corr30` / `vsumd60` raw features from the
  shared trainval snapshot and converts each to a cross-sectional percentile
  rank on each signal_date.
- Applies the historical equal-weight composition rule:
    0.25 * p98
  + 0.25 * COALESCE(cord30, 0.0)
  + 0.25 * COALESCE(corr30, 0.0)
  + 0.25 * COALESCE(vsumd60, 0.0)

This builder is trainval-only and does not access frozen test data.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
CONTRACTS_DIR = ROOT / "contracts"

DEFAULT_P98_RUN_ID = "confirmatory_reversal_p98_trainval_20260506"
DEFAULT_P98_CANDIDATE_SCHEME_ID = "reversal_tail_exclude_p98_v1"
CANDIDATE_SCHEME_ID = "multi_equal_weight_v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build multi_equal_weight_v1 model scores.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--input-dir", default=None)
    parser.add_argument(
        "--run-input-contract",
        default=str(CONTRACTS_DIR / "run_input_contract.current.json"),
        help="Run input contract JSON. Defaults to current trainval contract.",
    )
    parser.add_argument(
        "--p98-score-path",
        default=str(RUN_STATE_DIR / DEFAULT_P98_RUN_ID / "model_scores_D0.parquet"),
        help="Path to the p98 component score parquet.",
    )
    parser.add_argument(
        "--p98-candidate-scheme-id",
        default=DEFAULT_P98_CANDIDATE_SCHEME_ID,
        help="candidate_scheme_id to read from the p98 score parquet.",
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


def require_path(path: Path, label: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Required {label} not found: {path}")
    return path


def main() -> None:
    args = parse_args()
    run_dir = Path(args.input_dir) if args.input_dir else (RUN_STATE_DIR / args.run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    sample_panel = require_path(run_dir / "project_sample_panel.parquet", "project_sample_panel")
    p98_score_path = require_path(Path(args.p98_score_path), "p98 score parquet")

    run_input = load_json(Path(args.run_input_contract))
    snapshot_id = str(run_input["snapshot_id"])
    source_db_path = Path(run_input["source_root"]["snapshot_path"]) / "duckdb" / "warehouse.duckdb"
    require_path(source_db_path, "shared warehouse DB")

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
            CREATE OR REPLACE VIEW p98_scores AS
            SELECT
                CAST(instrument AS VARCHAR) AS instrument,
                CAST(signal_date AS VARCHAR) AS signal_date,
                CAST(model_score_D0 AS DOUBLE) AS p98_score
            FROM read_parquet({sql_path(p98_score_path)})
            WHERE candidate_scheme_id = {sql_quote(args.p98_candidate_scheme_id)}
              AND model_score_D0 IS NOT NULL
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
                    amount,
                    vol,
                    pct_chg / 100.0 AS pct_ret
                FROM warehouse_db.serving.vw_bars_daily
                WHERE snapshot_id = {sql_quote(snapshot_id)}
            ),
            enriched AS (
                SELECT
                    instrument,
                    signal_date,
                    adj_close,
                    amount,
                    vol,
                    pct_ret,
                    LN(GREATEST(vol, 0.0) + 1.0) AS log_volume,
                    CASE
                        WHEN LAG(adj_close, 1) OVER (
                            PARTITION BY instrument ORDER BY signal_date
                        ) > 1e-12
                        THEN adj_close / LAG(adj_close, 1) OVER (
                            PARTITION BY instrument ORDER BY signal_date
                        )
                        ELSE NULL
                    END AS close_rel1,
                    CASE
                        WHEN LAG(vol, 1) OVER (
                            PARTITION BY instrument ORDER BY signal_date
                        ) > 1e-12
                        THEN LN(vol / LAG(vol, 1) OVER (
                            PARTITION BY instrument ORDER BY signal_date
                        ) + 1.0)
                        ELSE NULL
                    END AS log_volume_rel1,
                    GREATEST(
                        vol - LAG(vol, 1) OVER (
                            PARTITION BY instrument ORDER BY signal_date
                        ),
                        0.0
                    ) AS pos_vol_delta,
                    GREATEST(
                        LAG(vol, 1) OVER (
                            PARTITION BY instrument ORDER BY signal_date
                        ) - vol,
                        0.0
                    ) AS neg_vol_delta,
                    ABS(
                        vol - LAG(vol, 1) OVER (
                            PARTITION BY instrument ORDER BY signal_date
                        )
                    ) AS abs_vol_delta
                FROM bars
            )
            SELECT
                instrument,
                signal_date,
                CORR(close_rel1, log_volume_rel1) OVER w30 AS alpha158_cord30_raw,
                CORR(adj_close, log_volume) OVER w30 AS alpha158_corr30_raw,
                CASE
                    WHEN SUM(abs_vol_delta) OVER w60 > 0
                    THEN (
                        SUM(pos_vol_delta) OVER w60 - SUM(neg_vol_delta) OVER w60
                    ) / (SUM(abs_vol_delta) OVER w60 + 1e-12)
                    ELSE NULL
                END AS alpha158_vsumd60_raw
            FROM enriched
            WINDOW
                w30 AS (
                    PARTITION BY instrument
                    ORDER BY signal_date
                    ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
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
                b.alpha158_cord30_raw,
                b.alpha158_corr30_raw,
                b.alpha158_vsumd60_raw
            FROM project_sample_panel p
            LEFT JOIN bar_features b
              ON p.instrument = b.instrument
             AND p.signal_date = b.signal_date
            """
        )
        for field in ("cord30", "corr30", "vsumd60"):
            raw_field = f"alpha158_{field}_raw"
            con.execute(
                f"""
                CREATE OR REPLACE VIEW {field}_scores AS
                SELECT
                    snapshot_id,
                    instrument,
                    signal_date,
                    PERCENT_RANK() OVER (
                        PARTITION BY snapshot_id, signal_date
                        ORDER BY {raw_field} DESC, instrument ASC
                    ) AS {field}_score
                FROM feature_frame
                WHERE ranking_eligible_D0
                  AND {raw_field} IS NOT NULL
                """
            )

        con.execute(
            f"""
            COPY (
                SELECT
                    p.snapshot_id,
                    p.instrument,
                    p.signal_date,
                    CAST({sql_quote(CANDIDATE_SCHEME_ID)} AS VARCHAR) AS candidate_scheme_id,
                    (
                        0.25 * p98.p98_score
                      + 0.25 * COALESCE(cord30.cord30_score, 0.0)
                      + 0.25 * COALESCE(corr30.corr30_score, 0.0)
                      + 0.25 * COALESCE(vsumd60.vsumd60_score, 0.0)
                    ) AS model_score_D0,
                    4 AS score_component_count
                FROM p98_scores p98
                INNER JOIN project_sample_panel p
                  ON p98.instrument = p.instrument
                 AND p98.signal_date = p.signal_date
                LEFT JOIN cord30_scores cord30
                  ON p.snapshot_id = cord30.snapshot_id
                 AND p.instrument = cord30.instrument
                 AND p.signal_date = cord30.signal_date
                LEFT JOIN corr30_scores corr30
                  ON p.snapshot_id = corr30.snapshot_id
                 AND p.instrument = corr30.instrument
                 AND p.signal_date = corr30.signal_date
                LEFT JOIN vsumd60_scores vsumd60
                  ON p.snapshot_id = vsumd60.snapshot_id
                 AND p.instrument = vsumd60.instrument
                 AND p.signal_date = vsumd60.signal_date
            ) TO {sql_path(score_output)} (FORMAT PARQUET)
            """
        )

        audit_row = con.execute(
            f"""
            SELECT
                COUNT(*) AS total_rows,
                AVG(model_score_D0) AS avg_score,
                MIN(model_score_D0) AS min_score,
                MAX(model_score_D0) AS max_score,
                SUM(CASE WHEN model_score_D0 IS NULL THEN 1 ELSE 0 END) AS null_score_rows,
                SUM(CASE WHEN model_score_D0 IS NOT NULL AND NOT isfinite(model_score_D0) THEN 1 ELSE 0 END) AS nonfinite_score_rows
            FROM read_parquet({sql_path(score_output)})
            """
        ).fetchone()
        component_coverage = con.execute(
            """
            SELECT
                COUNT(*) AS anchor_rows,
                SUM(CASE WHEN cord30_score IS NOT NULL THEN 1 ELSE 0 END) AS cord30_rows,
                SUM(CASE WHEN corr30_score IS NOT NULL THEN 1 ELSE 0 END) AS corr30_rows,
                SUM(CASE WHEN vsumd60_score IS NOT NULL THEN 1 ELSE 0 END) AS vsumd60_rows
            FROM (
                SELECT
                    p98.instrument,
                    p98.signal_date,
                    cord30.cord30_score,
                    corr30.corr30_score,
                    vsumd60.vsumd60_score
                FROM p98_scores p98
                INNER JOIN project_sample_panel p
                  ON p98.instrument = p.instrument
                 AND p98.signal_date = p.signal_date
                LEFT JOIN cord30_scores cord30
                  ON p.snapshot_id = cord30.snapshot_id
                 AND p.instrument = cord30.instrument
                 AND p.signal_date = cord30.signal_date
                LEFT JOIN corr30_scores corr30
                  ON p.snapshot_id = corr30.snapshot_id
                 AND p.instrument = corr30.instrument
                 AND p.signal_date = corr30.signal_date
                LEFT JOIN vsumd60_scores vsumd60
                  ON p.snapshot_id = vsumd60.snapshot_id
                 AND p.instrument = vsumd60.instrument
                 AND p.signal_date = vsumd60.signal_date
            )
            """
        ).fetchone()

        audit_payload = {
            "candidate_scheme_id": CANDIDATE_SCHEME_ID,
            "score_builder": "build_multi_equal_weight_v1_scores.py",
            "component_contract": {
                "p98_candidate_scheme_id": args.p98_candidate_scheme_id,
                "alpha158_components": ["cord30", "corr30", "vsumd60"],
                "composition_rule": "0.25 * p98 + 0.25 * COALESCE(cord30,0) + 0.25 * COALESCE(corr30,0) + 0.25 * COALESCE(vsumd60,0)",
                "frozen_test_access": False,
            },
            "summary_counts": {
                "total_rows": int(audit_row[0] or 0),
                "anchor_p98_rows": int(component_coverage[0] or 0),
                "cord30_component_rows": int(component_coverage[1] or 0),
                "corr30_component_rows": int(component_coverage[2] or 0),
                "vsumd60_component_rows": int(component_coverage[3] or 0),
                "null_score_rows": int(audit_row[4] or 0),
                "nonfinite_score_rows": int(audit_row[5] or 0),
            },
            "score_distribution": {
                "avg_score": float(audit_row[1]) if audit_row[1] is not None else None,
                "min_score": float(audit_row[2]) if audit_row[2] is not None else None,
                "max_score": float(audit_row[3]) if audit_row[3] is not None else None,
            },
            "notes": [
                "Trainval-only local score build for same-contract portfolio comparison.",
                "Alpha158 component ranks are recomputed from the shared trainval warehouse.",
                "Missing component scores are carried as zero contribution by contract, not imputed downstream in portfolio.",
            ],
        }
        write_json(audit_output, audit_payload)
    finally:
        con.close()


if __name__ == "__main__":
    main()
