#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Build a reproducible price/volume multisignal model_scores_D0.parquet.

This is the minimal v13 builder. It:
- reads the project-owned sample panel
- derives a fixed price/volume feature set from shared bars data
- ranks the features cross-sectionally on each signal_date
- writes `model_scores_D0.parquet` into the run directory

The score uses only D0-and-earlier market data.

Field discipline:
- `amount` from `serving.vw_bars_daily` is in thousand CNY.
- `liquidity_rank` must always mean "higher liquidity -> higher rank".
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
CONTRACTS_DIR = ROOT / "contracts"
ARTIFACTS_RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
RESEARCH_REGISTRY_DIR = ROOT / "artifacts" / "research_registry"
CANDIDATE_SCHEME_REGISTRY = RESEARCH_REGISTRY_DIR / "candidate_scheme_registry.jsonl"
DEFAULT_CANDIDATE_SCHEME_ID = "price_volume_multisignal_v13_core"
EXPECTED_AMOUNT_UNIT = "thousand_cny"
FEATURE_SET = [
    ("reversal_5d_raw", "reversal_rank"),
    ("momentum_60_5_raw", "momentum_rank"),
    ("volatility_20d_raw", "lowvol_rank"),
    ("liquidity_20d_raw", "liquidity_rank"),
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def ensure_registered_candidate(candidate_scheme_id: str) -> None:
    rows = load_jsonl(CANDIDATE_SCHEME_REGISTRY)
    if not any(row.get("candidate_scheme_id") == candidate_scheme_id for row in rows):
        raise ValueError(
            "candidate_scheme_id must be registered before score production: "
            f"{candidate_scheme_id}"
        )


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_path(path: Path) -> str:
    return sql_quote(path.resolve().as_posix())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build price/volume multisignal model_scores_D0.parquet."
    )
    parser.add_argument("--run-id", required=True, help="Project-side run identifier.")
    parser.add_argument(
        "--input-dir",
        default=None,
        help="Optional run-state directory. Defaults to artifacts/run_state/<run_id>/",
    )
    parser.add_argument(
        "--candidate-scheme-id",
        default=DEFAULT_CANDIDATE_SCHEME_ID,
        help="Candidate scheme identifier written into the score file.",
    )
    parser.add_argument(
        "--min-feature-count",
        type=int,
        default=3,
        help="Minimum number of available feature ranks required to emit a score.",
    )
    return parser.parse_args()


def resolve_run_dir(run_id: str, input_dir: str | None) -> Path:
    run_dir = Path(input_dir) if input_dir else (ARTIFACTS_RUN_STATE_DIR / run_id)
    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")
    return run_dir


def require_input(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Required input file not found: {path}")
    return path


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    if args.min_feature_count <= 0:
        raise ValueError("--min-feature-count must be positive.")
    if args.min_feature_count > len(FEATURE_SET):
        raise ValueError("--min-feature-count cannot exceed the number of score components.")
    ensure_registered_candidate(args.candidate_scheme_id)

    run_dir = resolve_run_dir(args.run_id, args.input_dir)
    sample_panel = require_input(run_dir / "project_sample_panel.parquet")

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
                    amount,
                    pct_chg / 100.0 AS pct_ret
                FROM warehouse_db.serving.vw_bars_daily
                WHERE snapshot_id = {sql_quote(snapshot_id)}
            )
            SELECT
                instrument,
                signal_date,
                (adj_close / LAG(adj_close, 5) OVER w - 1.0) AS reversal_5d_raw,
                (LAG(adj_close, 5) OVER w / LAG(adj_close, 60) OVER w - 1.0) AS momentum_60_5_raw,
                STDDEV_SAMP(pct_ret) OVER w20 AS volatility_20d_raw,
                AVG(LN(GREATEST(amount, 0.0) + 1.0)) OVER w20 AS liquidity_20d_raw
            FROM bars
            WINDOW
                w AS (PARTITION BY instrument ORDER BY signal_date),
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
                f.reversal_5d_raw,
                f.momentum_60_5_raw,
                f.volatility_20d_raw,
                f.liquidity_20d_raw
            FROM project_sample_panel p
            LEFT JOIN bar_features f
              ON p.instrument = f.instrument
             AND p.signal_date = f.signal_date
            """
        )

        con.execute(
            """
            CREATE OR REPLACE VIEW reversal_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY reversal_5d_raw ASC, instrument ASC
                ) AS reversal_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND reversal_5d_raw IS NOT NULL
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
            CREATE OR REPLACE VIEW volatility_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY volatility_20d_raw ASC, instrument ASC
                ) AS lowvol_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND volatility_20d_raw IS NOT NULL
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

        component_count_expr = " + ".join(
            f"CASE WHEN {rank_col} IS NOT NULL THEN 1 ELSE 0 END" for _, rank_col in FEATURE_SET
        )
        score_sum_expr = " + ".join(f"COALESCE({rank_col}, 0.0)" for _, rank_col in FEATURE_SET)

        con.execute(
            f"""
            COPY (
                WITH score_frame AS (
                    SELECT
                        f.snapshot_id,
                        f.instrument,
                        f.signal_date,
                        f.ranking_eligible_D0,
                        f.reversal_5d_raw,
                        f.momentum_60_5_raw,
                        f.volatility_20d_raw,
                        f.liquidity_20d_raw,
                        r.reversal_rank,
                        m.momentum_rank,
                        v.lowvol_rank,
                        l.liquidity_rank,
                        ({component_count_expr}) AS score_component_count
                    FROM feature_frame f
                    LEFT JOIN reversal_ranks r
                      ON f.snapshot_id = r.snapshot_id
                     AND f.instrument = r.instrument
                     AND f.signal_date = r.signal_date
                    LEFT JOIN momentum_ranks m
                      ON f.snapshot_id = m.snapshot_id
                     AND f.instrument = m.instrument
                     AND f.signal_date = m.signal_date
                    LEFT JOIN volatility_ranks v
                      ON f.snapshot_id = v.snapshot_id
                     AND f.instrument = v.instrument
                     AND f.signal_date = v.signal_date
                    LEFT JOIN liquidity_ranks l
                      ON f.snapshot_id = l.snapshot_id
                     AND f.instrument = l.instrument
                     AND f.signal_date = l.signal_date
                )
                SELECT
                    snapshot_id,
                    instrument,
                    signal_date,
                    CAST({sql_quote(args.candidate_scheme_id)} AS VARCHAR) AS candidate_scheme_id,
                    CASE
                        WHEN ranking_eligible_D0 AND score_component_count >= {args.min_feature_count}
                        THEN ({score_sum_expr}) / score_component_count
                        ELSE CAST(NULL AS DOUBLE)
                    END AS model_score_D0,
                    score_component_count,
                    reversal_5d_raw,
                    momentum_60_5_raw,
                    volatility_20d_raw,
                    liquidity_20d_raw,
                    reversal_rank,
                    momentum_rank,
                    lowvol_rank,
                    liquidity_rank
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
                SUM(CASE WHEN reversal_rank IS NOT NULL THEN 1 ELSE 0 END) AS reversal_rank_rows,
                SUM(CASE WHEN momentum_rank IS NOT NULL THEN 1 ELSE 0 END) AS momentum_rank_rows,
                SUM(CASE WHEN lowvol_rank IS NOT NULL THEN 1 ELSE 0 END) AS lowvol_rank_rows,
                SUM(CASE WHEN liquidity_rank IS NOT NULL THEN 1 ELSE 0 END) AS liquidity_rank_rows
            FROM (
                SELECT
                    p.ranking_eligible_D0,
                    s.model_score_D0,
                    s.score_component_count,
                    s.reversal_rank,
                    s.momentum_rank,
                    s.lowvol_rank,
                    s.liquidity_rank
                FROM read_parquet({sql_path(score_output)}) s
                INNER JOIN project_sample_panel p
                  ON s.snapshot_id = p.snapshot_id
                 AND s.instrument = p.instrument
                 AND s.signal_date = p.signal_date
            )
            """
        ).fetchone()
        amount_sanity = con.execute(
            f"""
            SELECT
                MIN(liquidity_rank) AS min_liquidity_rank,
                MAX(liquidity_rank) AS max_liquidity_rank,
                AVG(liquidity_rank) AS avg_liquidity_rank
            FROM read_parquet({sql_path(score_output)})
            """
        ).fetchone()
    finally:
        con.close()

    audit = {
        "run_id": args.run_id,
        "snapshot_id": snapshot_id,
        "candidate_scheme_id": args.candidate_scheme_id,
        "score_file": score_output.name,
        "min_feature_count": args.min_feature_count,
        "feature_family": "price_volume_multisignal_core_v1",
        "baseline_features": [feature_name for feature_name, _ in FEATURE_SET],
        "summary_counts": {
            "total_rows": int(audit_counts[0] or 0),
            "ranking_eligible_rows": int(audit_counts[1] or 0),
            "scored_rows": int(audit_counts[2] or 0),
            "eligible_unscored_rows": int(audit_counts[3] or 0),
            "min_feature_ready_rows": int(audit_counts[4] or 0),
            "reversal_rank_rows": int(audit_counts[5] or 0),
            "momentum_rank_rows": int(audit_counts[6] or 0),
            "lowvol_rank_rows": int(audit_counts[7] or 0),
            "liquidity_rank_rows": int(audit_counts[8] or 0),
        },
        "notes": [
            "This minimal v13 builder uses only price/volume-derived market features from D0-and-earlier data.",
            "The score is the average of available cross-sectional percentile ranks when enough features are present.",
            "amount_unit_assumption = thousand CNY",
            "liquidity_rank_direction = higher liquidity -> higher rank",
        ],
        "unit_sanity": {
            "amount_unit_assumption": EXPECTED_AMOUNT_UNIT,
            "liquidity_rank_min": float(amount_sanity[0]) if amount_sanity[0] is not None else None,
            "liquidity_rank_max": float(amount_sanity[1]) if amount_sanity[1] is not None else None,
            "liquidity_rank_avg": float(amount_sanity[2]) if amount_sanity[2] is not None else None,
        },
    }
    write_json(audit_output, audit)


if __name__ == "__main__":
    main()
