#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Build a minimal dual-signal Alpha158 head-extraction family model_scores_D0.parquet
under an explicit run-input contract.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

from alpha158_canonical_common import FEATURE_META, build_feature_views, load_manifest
from single_signal_batch_common import sql_path, sql_quote


ROOT = Path("/Users/wy/MiscProject/multi_factor")
CONTRACTS_DIR = ROOT / "contracts"
RUN_STATE_DIR = ROOT / "artifacts" / "run_state"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build dual-signal Alpha158 head-extraction family scores."
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--candidate-scheme-id",
        required=True,
        help="Candidate scheme id, e.g. alpha158_corr30_cord30_dual_signal_family_v1",
    )
    parser.add_argument(
        "--feature-names",
        default="CORR30,CORD30",
        help="Comma-separated exact Alpha158 feature names. Defaults to CORR30,CORD30",
    )
    parser.add_argument("--input-dir", default=None)
    parser.add_argument(
        "--run-input-contract",
        default=None,
        help="Optional explicit run input contract JSON path. Defaults to contracts/run_input_contract.current.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dir = Path(args.input_dir) if args.input_dir else (RUN_STATE_DIR / args.run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    sample_panel = run_dir / "project_sample_panel.parquet"
    if not sample_panel.exists():
        raise FileNotFoundError(f"Required input file not found: {sample_panel}")

    run_input_contract_path = (
        Path(args.run_input_contract)
        if args.run_input_contract
        else (CONTRACTS_DIR / "run_input_contract.current.json")
    )
    run_input = load_json(run_input_contract_path)
    snapshot_id = run_input["snapshot_id"]
    source_db_path = Path(run_input["source_root"]["snapshot_path"]) / "duckdb" / "warehouse.duckdb"
    if not source_db_path.exists():
        raise FileNotFoundError(f"Shared warehouse DB not found: {source_db_path}")

    feature_names = [item.strip().upper() for item in args.feature_names.split(",") if item.strip()]
    if len(feature_names) != 2:
        raise ValueError("This builder currently supports exactly two feature names.")

    manifest = load_manifest()
    feature_lookup = {row["qlib_feature_name"]: row for row in manifest["feature_catalog"]}
    feature_batch: list[dict] = []
    for feature_name in feature_names:
        if feature_name not in feature_lookup:
            raise ValueError(f"Unknown Alpha158 feature name: {feature_name}")
        if feature_name not in FEATURE_META:
            raise ValueError(f"Missing feature metadata for Alpha158 feature: {feature_name}")
        feature_batch.append({**feature_lookup[feature_name], **FEATURE_META[feature_name]})

    candidate_scheme_id = args.candidate_scheme_id
    score_path = run_dir / "model_scores_D0.parquet"
    audit_path = run_dir / "model_scores_D0_audit.json"

    con = duckdb.connect()
    try:
        build_feature_views(
            con=con,
            sample_panel=sample_panel,
            source_db_path=source_db_path,
            snapshot_id=snapshot_id,
            feature_batch=feature_batch,
        )

        feature_1_field = feature_batch[0]["canonical_project_field"]
        feature_2_field = feature_batch[1]["canonical_project_field"]
        feature_1_name = feature_names[0]
        feature_2_name = feature_names[1]
        feature_1_direction = feature_batch[0]["ranking_direction"].upper()
        feature_2_direction = feature_batch[1]["ranking_direction"].upper()

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
            f"""
            COPY (
                WITH ranked AS (
                    SELECT
                        snapshot_id,
                        instrument,
                        signal_date,
                        ranking_eligible_D0,
                        {feature_1_field} AS {feature_1_field},
                        {feature_2_field} AS {feature_2_field},
                        PERCENT_RANK() OVER (
                            PARTITION BY snapshot_id, signal_date
                            ORDER BY {feature_1_field} {feature_1_direction}, instrument ASC
                        ) AS rank_{feature_1_field},
                        PERCENT_RANK() OVER (
                            PARTITION BY snapshot_id, signal_date
                            ORDER BY {feature_2_field} {feature_2_direction}, instrument ASC
                        ) AS rank_{feature_2_field}
                    FROM feature_frame
                    WHERE ranking_eligible_D0
                      AND {feature_1_field} IS NOT NULL
                      AND {feature_2_field} IS NOT NULL
                )
                SELECT
                    p.snapshot_id,
                    p.instrument,
                    p.signal_date,
                    CAST({sql_quote(candidate_scheme_id)} AS VARCHAR) AS candidate_scheme_id,
                    CASE
                        WHEN p.ranking_eligible_D0
                         AND r.rank_{feature_1_field} IS NOT NULL
                         AND r.rank_{feature_2_field} IS NOT NULL
                        THEN (r.rank_{feature_1_field} + r.rank_{feature_2_field}) / 2.0
                        ELSE CAST(NULL AS DOUBLE)
                    END AS model_score_D0,
                    l.liquidity_rank,
                    CASE
                        WHEN r.rank_{feature_1_field} IS NOT NULL AND r.rank_{feature_2_field} IS NOT NULL
                        THEN 2 ELSE 0
                    END AS score_component_count,
                    r.{feature_1_field} AS raw_signal_value_{feature_1_field},
                    r.{feature_2_field} AS raw_signal_value_{feature_2_field},
                    r.rank_{feature_1_field} AS rank_component_{feature_1_field},
                    r.rank_{feature_2_field} AS rank_component_{feature_2_field}
                FROM project_sample_panel p
                LEFT JOIN ranked r
                  ON p.snapshot_id = r.snapshot_id
                 AND p.instrument = r.instrument
                 AND p.signal_date = r.signal_date
                LEFT JOIN liquidity_ranks l
                  ON p.snapshot_id = l.snapshot_id
                 AND p.instrument = l.instrument
                 AND p.signal_date = l.signal_date
            ) TO {sql_path(score_path)} (FORMAT PARQUET)
            """
        )

        audit_row = con.execute(
            f"""
            SELECT
                COUNT(*) AS total_rows,
                SUM(CASE WHEN p.ranking_eligible_D0 THEN 1 ELSE 0 END) AS ranking_eligible_rows,
                SUM(CASE WHEN s.model_score_D0 IS NOT NULL THEN 1 ELSE 0 END) AS scored_rows,
                SUM(CASE WHEN p.ranking_eligible_D0 AND s.model_score_D0 IS NULL THEN 1 ELSE 0 END) AS eligible_unscored_rows,
                AVG(s.model_score_D0) AS avg_score,
                MIN(s.model_score_D0) AS min_score,
                MAX(s.model_score_D0) AS max_score
            FROM read_parquet({sql_path(score_path)}) s
            INNER JOIN project_sample_panel p
              ON s.snapshot_id = p.snapshot_id
             AND s.instrument = p.instrument
             AND s.signal_date = p.signal_date
            """
        ).fetchone()
        audit = {
            "candidate_scheme_id": candidate_scheme_id,
            "feature_names": feature_names,
            "feature_fields": [feature_1_field, feature_2_field],
            "ranking_directions": [feature_1_direction, feature_2_direction],
            "score_builder": "build_alpha158_head_extraction_dual_signal_family_scores.py",
            "summary_counts": {
                "total_rows": int(audit_row[0] or 0),
                "ranking_eligible_rows": int(audit_row[1] or 0),
                "scored_rows": int(audit_row[2] or 0),
                "eligible_unscored_rows": int(audit_row[3] or 0),
            },
            "score_distribution": {
                "avg_score": float(audit_row[4]) if audit_row[4] is not None else None,
                "min_score": float(audit_row[5]) if audit_row[5] is not None else None,
                "max_score": float(audit_row[6]) if audit_row[6] is not None else None,
            },
            "notes": [
                "Dual-signal Alpha158 head-extraction family score file.",
                f"Exactly two raw signals are ranked and averaged: {feature_1_name}, {feature_2_name}.",
                "Null scores are preserved for audit and no imputation is used.",
            ],
        }
        audit_path.write_text(
            json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    finally:
        con.close()


if __name__ == "__main__":
    main()
