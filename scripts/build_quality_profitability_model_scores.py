#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Build a reproducible quality/profitability model_scores_D0.parquet from PIT fundamentals.

This is the minimal v12 builder. It:
- reads the project-owned sample panel
- reads shared snapshot `fina_indicator_pit.parquet`
- uses an as-of PIT join on `pit_available_date <= signal_date`
- ranks a fixed quality/profitability feature set cross-sectionally on each signal_date
- writes `model_scores_D0.parquet` into the run directory

The score uses only D0-and-earlier PIT data.

Field discipline:
- `roe_dt`, `roa_yearly`, `q_roe`, `q_dt_roe` are treated as percentage-style
  profitability ratios where higher is better.
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
DEFAULT_CANDIDATE_SCHEME_ID = "quality_profitability_v12_core"
RESEARCH_ROUND_REGISTRY = RESEARCH_REGISTRY_DIR / "research_round_registry.jsonl"
DEFAULT_FEATURE_PRESET = "quality_profitability_v12_core"
FEATURE_PRESETS = {
    "quality_profitability_v12_core": [
        ("roe_dt_raw", "roe_dt_rank"),
        ("roa_yearly_raw", "roa_yearly_rank"),
        ("q_roe_raw", "q_roe_rank"),
        ("q_dt_roe_raw", "q_dt_roe_rank"),
    ],
    "single_roe_dt": [
        ("roe_dt_raw", "roe_dt_rank"),
    ],
    "single_roa_yearly": [
        ("roa_yearly_raw", "roa_yearly_rank"),
    ],
    "roe_dt_plus_roa_yearly": [
        ("roe_dt_raw", "roe_dt_rank"),
        ("roa_yearly_raw", "roa_yearly_rank"),
    ],
}


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


def ensure_registered_candidate(candidate_scheme_id: str, research_round_id: str | None = None) -> dict | None:
    rows = load_jsonl(CANDIDATE_SCHEME_REGISTRY)
    if not any(row.get("candidate_scheme_id") == candidate_scheme_id for row in rows):
        raise ValueError(
            "candidate_scheme_id must be registered before score production: "
            f"{candidate_scheme_id}"
        )
    if research_round_id is not None:
        round_rows = load_jsonl(RESEARCH_ROUND_REGISTRY)
        if not any(row.get("research_round_id") == research_round_id for row in round_rows):
            raise ValueError(
                f"research_round_id is not registered: {research_round_id}"
            )
    return {"candidate_scheme_id": candidate_scheme_id, "research_round_id": research_round_id}


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_path(path: Path) -> str:
    return sql_quote(path.resolve().as_posix())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build quality/profitability model_scores_D0.parquet."
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
        help="Minimum number of available quality/profitability ranks required to emit a score.",
    )
    parser.add_argument(
        "--run-input-contract",
        default=None,
        help="Optional explicit run input contract JSON path. Defaults to contracts/run_input_contract.current.json",
    )
    parser.add_argument(
        "--feature-preset",
        default=DEFAULT_FEATURE_PRESET,
        choices=sorted(FEATURE_PRESETS.keys()),
        help="Named quality/profitability feature preset.",
    )
    parser.add_argument(
        "--research-round-id",
        default=None,
        help="Optional research round identifier for registry validation.",
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
    selected_features = FEATURE_PRESETS[args.feature_preset]
    if args.min_feature_count > len(selected_features):
        raise ValueError("--min-feature-count cannot exceed the number of score components.")
    ensure_registered_candidate(args.candidate_scheme_id, args.research_round_id)

    run_dir = resolve_run_dir(args.run_id, args.input_dir)
    sample_panel = require_input(run_dir / "project_sample_panel.parquet")

    run_input_contract_path = Path(args.run_input_contract) if args.run_input_contract else (
        CONTRACTS_DIR / "run_input_contract.current.json"
    )
    run_input = load_json(run_input_contract_path)
    snapshot_id = run_input["snapshot_id"]
    snapshot_path = Path(run_input["source_root"]["snapshot_path"])
    fundamental_pit_path = snapshot_path / "warehouse" / "fundamental" / "fina_indicator_pit.parquet"
    if not fundamental_pit_path.exists():
        raise FileNotFoundError(f"Shared PIT parquet not found: {fundamental_pit_path}")

    score_output = run_dir / "model_scores_D0.parquet"
    audit_output = run_dir / "model_scores_D0_audit.json"

    con = duckdb.connect()
    try:
        con.execute(
            f"""
            CREATE OR REPLACE VIEW project_sample_panel AS
            SELECT * FROM read_parquet({sql_path(sample_panel)})
            """
        )
        winsor_param = 5.0
        con.execute(
            f"""
            CREATE OR REPLACE VIEW pit_source_raw AS
            SELECT
                snapshot_id,
                ts_code AS instrument,
                ann_date,
                end_date,
                pit_available_date,
                CAST(roe_dt AS DOUBLE) AS roe_dt_raw,
                CAST(roa_yearly AS DOUBLE) AS roa_yearly_raw,
                CAST(q_roe AS DOUBLE) AS q_roe_raw,
                CAST(q_dt_roe AS DOUBLE) AS q_dt_roe_raw
            FROM read_parquet({sql_path(fundamental_pit_path)})
            WHERE snapshot_id = {sql_quote(snapshot_id)}
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW pit_source_deduped AS
            WITH numbered AS (
                SELECT *,
                    ROW_NUMBER() OVER (
                        PARTITION BY instrument, pit_available_date
                        ORDER BY end_date DESC
                    ) AS rn
                FROM pit_source_raw
            )
            SELECT * EXCLUDE (rn)
            FROM numbered
            WHERE rn = 1
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW pit_source_winsorized AS
            WITH raw AS (
                SELECT * FROM pit_source_deduped
            ),
            daily_stats AS (
                SELECT
                    r.pit_available_date AS signal_date,
                    MEDIAN(r.roe_dt_raw) AS med_roe,
                    MEDIAN(r.roa_yearly_raw) AS med_roa,
                    MEDIAN(r.q_roe_raw) AS med_q_roe,
                    MEDIAN(r.q_dt_roe_raw) AS med_q_dt,
                    MAD(r.roe_dt_raw) AS mad_roe,
                    MAD(r.roa_yearly_raw) AS mad_roa,
                    MAD(r.q_roe_raw) AS mad_q_roe,
                    MAD(r.q_dt_roe_raw) AS mad_q_dt
                FROM raw r
                GROUP BY r.pit_available_date
            )
            SELECT
                r.snapshot_id,
                r.instrument,
                r.ann_date,
                r.end_date,
                r.pit_available_date,
                CASE
                    WHEN d.mad_roe IS NOT NULL AND d.mad_roe > 0
                    THEN d.med_roe + LEAST(GREATEST(r.roe_dt_raw - d.med_roe, -{winsor_param} * d.mad_roe), {winsor_param} * d.mad_roe)
                    ELSE r.roe_dt_raw
                END AS roe_dt_raw,
                CASE
                    WHEN d.mad_roa IS NOT NULL AND d.mad_roa > 0
                    THEN d.med_roa + LEAST(GREATEST(r.roa_yearly_raw - d.med_roa, -{winsor_param} * d.mad_roa), {winsor_param} * d.mad_roa)
                    ELSE r.roa_yearly_raw
                END AS roa_yearly_raw,
                CASE
                    WHEN d.mad_q_roe IS NOT NULL AND d.mad_q_roe > 0
                    THEN d.med_q_roe + LEAST(GREATEST(r.q_roe_raw - d.med_q_roe, -{winsor_param} * d.mad_q_roe), {winsor_param} * d.mad_q_roe)
                    ELSE r.q_roe_raw
                END AS q_roe_raw,
                CASE
                    WHEN d.mad_q_dt IS NOT NULL AND d.mad_q_dt > 0
                    THEN d.med_q_dt + LEAST(GREATEST(r.q_dt_roe_raw - d.med_q_dt, -{winsor_param} * d.mad_q_dt), {winsor_param} * d.mad_q_dt)
                    ELSE r.q_dt_roe_raw
                END AS q_dt_roe_raw
            FROM raw r
            LEFT JOIN daily_stats d
                ON r.pit_available_date = d.signal_date
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
                f.ann_date,
                f.end_date,
                f.pit_available_date,
                f.roe_dt_raw,
                f.roa_yearly_raw,
                f.q_roe_raw,
                f.q_dt_roe_raw
            FROM project_sample_panel p
            ASOF LEFT JOIN pit_source_winsorized f
              ON p.instrument = f.instrument
             AND p.signal_date >= f.pit_available_date
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW roe_dt_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY roe_dt_raw DESC, instrument ASC
                ) AS roe_dt_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND roe_dt_raw IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW roa_yearly_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY roa_yearly_raw DESC, instrument ASC
                ) AS roa_yearly_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND roa_yearly_raw IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW q_roe_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY q_roe_raw DESC, instrument ASC
                ) AS q_roe_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND q_roe_raw IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW q_dt_roe_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY q_dt_roe_raw DESC, instrument ASC
                ) AS q_dt_roe_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND q_dt_roe_raw IS NOT NULL
            """
        )

        component_count_expr = " + ".join(
            f"CASE WHEN {rank_col} IS NOT NULL THEN 1 ELSE 0 END" for _, rank_col in selected_features
        )
        score_sum_expr = " + ".join(f"COALESCE({rank_col}, 0.0)" for _, rank_col in selected_features)

        con.execute(
            f"""
            COPY (
                WITH score_frame AS (
                    SELECT
                        f.snapshot_id,
                        f.instrument,
                        f.signal_date,
                        f.ranking_eligible_D0,
                        f.ann_date,
                        f.end_date,
                        f.pit_available_date,
                        f.roe_dt_raw,
                        f.roa_yearly_raw,
                        f.q_roe_raw,
                        f.q_dt_roe_raw,
                        r1.roe_dt_rank,
                        r2.roa_yearly_rank,
                        r3.q_roe_rank,
                        r4.q_dt_roe_rank,
                        ({component_count_expr}) AS score_component_count
                    FROM feature_frame f
                    LEFT JOIN roe_dt_ranks r1
                      ON f.snapshot_id = r1.snapshot_id
                     AND f.instrument = r1.instrument
                     AND f.signal_date = r1.signal_date
                    LEFT JOIN roa_yearly_ranks r2
                      ON f.snapshot_id = r2.snapshot_id
                     AND f.instrument = r2.instrument
                     AND f.signal_date = r2.signal_date
                    LEFT JOIN q_roe_ranks r3
                      ON f.snapshot_id = r3.snapshot_id
                     AND f.instrument = r3.instrument
                     AND f.signal_date = r3.signal_date
                    LEFT JOIN q_dt_roe_ranks r4
                      ON f.snapshot_id = r4.snapshot_id
                     AND f.instrument = r4.instrument
                     AND f.signal_date = r4.signal_date
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
                    ann_date,
                    end_date,
                    pit_available_date,
                    roe_dt_raw,
                    roa_yearly_raw,
                    q_roe_raw,
                    q_dt_roe_raw,
                    roe_dt_rank,
                    roa_yearly_rank,
                    q_roe_rank,
                    q_dt_roe_rank
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
                SUM(CASE WHEN roe_dt_rank IS NOT NULL THEN 1 ELSE 0 END) AS roe_dt_rank_rows,
                SUM(CASE WHEN roa_yearly_rank IS NOT NULL THEN 1 ELSE 0 END) AS roa_yearly_rank_rows,
                SUM(CASE WHEN q_roe_rank IS NOT NULL THEN 1 ELSE 0 END) AS q_roe_rank_rows,
                SUM(CASE WHEN q_dt_roe_rank IS NOT NULL THEN 1 ELSE 0 END) AS q_dt_roe_rank_rows,
                SUM(CASE WHEN pit_available_date IS NOT NULL THEN 1 ELSE 0 END) AS pit_joined_rows
            FROM (
                SELECT
                    p.ranking_eligible_D0,
                    s.model_score_D0,
                    s.score_component_count,
                    s.roe_dt_rank,
                    s.roa_yearly_rank,
                    s.q_roe_rank,
                    s.q_dt_roe_rank,
                    s.pit_available_date
                FROM read_parquet({sql_path(score_output)}) s
                INNER JOIN project_sample_panel p
                  ON s.snapshot_id = p.snapshot_id
                 AND s.instrument = p.instrument
                 AND s.signal_date = p.signal_date
            )
            """
        ).fetchone()
        asof_span = con.execute(
            f"""
            SELECT
                MIN(pit_available_date) AS min_pit_available_date,
                MAX(pit_available_date) AS max_pit_available_date
            FROM read_parquet({sql_path(score_output)})
            WHERE pit_available_date IS NOT NULL
            """
        ).fetchone()
    finally:
        con.close()

    audit = {
        "run_id": args.run_id,
        "snapshot_id": snapshot_id,
        "candidate_scheme_id": args.candidate_scheme_id,
        "research_round_id": args.research_round_id,
        "feature_preset": args.feature_preset,
        "score_file": score_output.name,
        "min_feature_count": args.min_feature_count,
        "feature_family": "quality_profitability_core_v1",
        "baseline_features": [feature_name for feature_name, _ in selected_features],
        "source_table": str(fundamental_pit_path),
        "summary_counts": {
            "total_rows": int(audit_counts[0] or 0),
            "ranking_eligible_rows": int(audit_counts[1] or 0),
            "scored_rows": int(audit_counts[2] or 0),
            "eligible_unscored_rows": int(audit_counts[3] or 0),
            "min_feature_ready_rows": int(audit_counts[4] or 0),
            "roe_dt_rank_rows": int(audit_counts[5] or 0),
            "roa_yearly_rank_rows": int(audit_counts[6] or 0),
            "q_roe_rank_rows": int(audit_counts[7] or 0),
            "q_dt_roe_rank_rows": int(audit_counts[8] or 0),
            "pit_joined_rows": int(audit_counts[9] or 0),
        },
        "pit_asof_span": {
            "min_pit_available_date": asof_span[0],
            "max_pit_available_date": asof_span[1],
        },
        "notes": [
            "This minimal v12 builder uses a PIT as-of join on pit_available_date <= signal_date.",
            "All four features are profitability-style percentage ratios where higher is better.",
            "The initial v12 implementation uses only fields that are physically present in fina_indicator_pit.parquet.",
        ],
    }
    write_json(audit_output, audit)


if __name__ == "__main__":
    main()
