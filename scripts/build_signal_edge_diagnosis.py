#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Build a generic signal-edge diagnosis report for one model_scores_D0.parquet file.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
ARTIFACTS_RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
RESEARCH_REGISTRY_DIR = ROOT / "artifacts" / "research_registry"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build signal-edge diagnosis report.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--candidate-scheme-id", required=True)
    parser.add_argument("--research-round-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--input-dir", default=None)
    return parser.parse_args()


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_path(path: Path) -> str:
    return sql_quote(path.resolve().as_posix())


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    run_dir = Path(args.input_dir) if args.input_dir else (ARTIFACTS_RUN_STATE_DIR / args.run_id)
    score_path = run_dir / "model_scores_D0.parquet"
    sample_path = run_dir / "project_sample_panel.parquet"
    label_path = run_dir / "project_label_panel.parquet"
    for path in (score_path, sample_path, label_path):
        if not path.exists():
            raise FileNotFoundError(f"Required input file not found: {path}")

    round_dir = RESEARCH_REGISTRY_DIR / "research_rounds" / args.research_round_id
    round_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{args.candidate_scheme_id}_signal_edge_diagnosis_{args.as_of_date}"
    json_output = round_dir / f"{stem}.json"
    md_output = round_dir / f"{stem}.md"

    con = duckdb.connect()
    try:
        con.execute(f"CREATE OR REPLACE VIEW score_input AS SELECT * FROM read_parquet({sql_path(score_path)})")
        con.execute(f"CREATE OR REPLACE VIEW sample_input AS SELECT * FROM read_parquet({sql_path(sample_path)})")
        con.execute(f"CREATE OR REPLACE VIEW label_input AS SELECT * FROM read_parquet({sql_path(label_path)})")
        con.execute(
            """
            CREATE OR REPLACE VIEW diag_base AS
            SELECT
                p.snapshot_id,
                p.instrument,
                p.signal_date,
                p.ranking_eligible_D0,
                s.model_score_D0,
                l.label_5d_next_open_close AS forward_label
            FROM sample_input p
            LEFT JOIN score_input s
              ON p.snapshot_id = s.snapshot_id
             AND p.instrument = s.instrument
             AND p.signal_date = s.signal_date
            LEFT JOIN label_input l
              ON p.snapshot_id = l.snapshot_id
             AND p.instrument = l.instrument
             AND p.signal_date = l.signal_date
            """
        )

        coverage = con.execute(
            """
            SELECT
                SUM(CASE WHEN ranking_eligible_D0 THEN 1 ELSE 0 END) AS ranking_eligible_rows,
                SUM(CASE WHEN ranking_eligible_D0 AND model_score_D0 IS NULL THEN 1 ELSE 0 END) AS null_score_rows,
                SUM(CASE WHEN ranking_eligible_D0 AND model_score_D0 IS NOT NULL AND forward_label IS NOT NULL THEN 1 ELSE 0 END) AS scored_with_label_rows
            FROM diag_base
            """
        ).fetchone()

        ic = con.execute(
            """
            SELECT CORR(model_score_D0, forward_label)
            FROM diag_base
            WHERE ranking_eligible_D0
              AND model_score_D0 IS NOT NULL
              AND forward_label IS NOT NULL
            """
        ).fetchone()[0]

        daily = con.execute(
            """
            WITH daily_ic AS (
                SELECT
                    signal_date,
                    CORR(model_score_D0, forward_label) AS daily_ic
                FROM diag_base
                WHERE ranking_eligible_D0
                  AND model_score_D0 IS NOT NULL
                  AND forward_label IS NOT NULL
                GROUP BY signal_date
                HAVING COUNT(*) >= 20
            )
            SELECT
                AVG(daily_ic),
                MEDIAN(daily_ic),
                AVG(CASE WHEN daily_ic > 0 THEN 1.0 ELSE 0.0 END)
            FROM daily_ic
            """
        ).fetchone()

        deciles = con.execute(
            """
            WITH ranked AS (
                SELECT
                    signal_date,
                    forward_label,
                    NTILE(10) OVER (
                        PARTITION BY signal_date
                        ORDER BY model_score_D0 DESC, instrument ASC
                    ) AS decile_bucket
                FROM diag_base
                WHERE ranking_eligible_D0
                  AND model_score_D0 IS NOT NULL
                  AND forward_label IS NOT NULL
            )
            SELECT decile_bucket, AVG(forward_label) AS avg_label
            FROM ranked
            GROUP BY decile_bucket
            ORDER BY decile_bucket
            """
        ).fetchall()

        top_slice = con.execute(
            """
            WITH ranked AS (
                SELECT
                    signal_date,
                    instrument,
                    forward_label,
                    ROW_NUMBER() OVER (
                        PARTITION BY signal_date
                        ORDER BY model_score_D0 DESC, instrument ASC
                    ) AS rank_desc,
                    ROW_NUMBER() OVER (
                        PARTITION BY signal_date
                        ORDER BY model_score_D0 ASC, instrument ASC
                    ) AS rank_asc
                FROM diag_base
                WHERE ranking_eligible_D0
                  AND model_score_D0 IS NOT NULL
                  AND forward_label IS NOT NULL
            )
            SELECT
                AVG(CASE WHEN rank_desc <= 10 THEN forward_label END),
                AVG(CASE WHEN rank_desc BETWEEN 11 AND 20 THEN forward_label END),
                AVG(CASE WHEN rank_asc <= 10 THEN forward_label END)
            FROM ranked
            """
        ).fetchone()

        gap = con.execute(
            """
            WITH ranked AS (
                SELECT
                    signal_date,
                    instrument,
                    model_score_D0,
                    ROW_NUMBER() OVER (
                        PARTITION BY signal_date
                        ORDER BY model_score_D0 DESC, instrument ASC
                    ) AS rank_desc
                FROM diag_base
                WHERE ranking_eligible_D0
                  AND model_score_D0 IS NOT NULL
            ),
            gaps AS (
                SELECT
                    signal_date,
                    MAX(CASE WHEN rank_desc = 10 THEN model_score_D0 END) AS score_rank10,
                    MAX(CASE WHEN rank_desc = 11 THEN model_score_D0 END) AS score_rank11
                FROM ranked
                GROUP BY signal_date
            )
            SELECT
                AVG(score_rank10 - score_rank11),
                MEDIAN(score_rank10 - score_rank11),
                COUNT(*) FILTER (WHERE score_rank10 IS NOT NULL AND score_rank11 IS NOT NULL),
                COUNT(*) FILTER (WHERE score_rank10 IS NOT NULL AND score_rank11 IS NOT NULL AND ABS(score_rank10 - score_rank11) < 0.005),
                COUNT(*) FILTER (WHERE score_rank10 IS NOT NULL AND score_rank11 IS NOT NULL AND ABS(score_rank10 - score_rank11) < 0.001)
            FROM gaps
            """
        ).fetchone()
    finally:
        con.close()

    ranking_eligible_rows = int(coverage[0] or 0)
    null_score_rows = int(coverage[1] or 0)
    scored_with_label_rows = int(coverage[2] or 0)
    null_score_share = (null_score_rows / ranking_eligible_rows) if ranking_eligible_rows else None
    decile_payload = {str(int(bucket)): (float(v) if v is not None else None) for bucket, v in deciles}
    top10 = float(top_slice[0]) if top_slice[0] is not None else None
    rank11_20 = float(top_slice[1]) if top_slice[1] is not None else None
    bottom10 = float(top_slice[2]) if top_slice[2] is not None else None

    payload = {
        "candidate_scheme_id": args.candidate_scheme_id,
        "research_round_id": args.research_round_id,
        "as_of_date": args.as_of_date,
        "coverage": {
            "ranking_eligible_rows": ranking_eligible_rows,
            "null_score_rows": null_score_rows,
            "null_score_share": null_score_share,
            "scored_with_label_rows": scored_with_label_rows,
        },
        "ic_readout": {
            "full_sample_corr_ic": float(ic) if ic is not None else None,
            "avg_daily_ic": float(daily[0]) if daily[0] is not None else None,
            "median_daily_ic": float(daily[1]) if daily[1] is not None else None,
            "positive_daily_ic_share": float(daily[2]) if daily[2] is not None else None,
        },
        "decile_monotonicity": decile_payload,
        "top_slice_readout": {
            "avg_label_top10": top10,
            "avg_label_rank11_20": rank11_20,
            "avg_label_bottom10": bottom10,
            "top10_minus_rank11_20": (top10 - rank11_20) if top10 is not None and rank11_20 is not None else None,
            "top10_minus_bottom10": (top10 - bottom10) if top10 is not None and bottom10 is not None else None,
        },
        "cutoff_gap": {
            "avg_rank10_11_score_gap": float(gap[0]) if gap[0] is not None else None,
            "median_rank10_11_score_gap": float(gap[1]) if gap[1] is not None else None,
            "days_with_both_ranks": int(gap[2] or 0),
            "days_gap_lt_0_005": int(gap[3] or 0),
            "days_gap_lt_0_001": int(gap[4] or 0),
        },
    }
    write_json(json_output, payload)

    lines = [
        f"# {args.title} ({args.as_of_date})",
        "",
        f"Candidate: `{args.candidate_scheme_id}`",
        f"Research round: `{args.research_round_id}`",
        "",
        "## 1. Coverage",
        f"- `ranking_eligible_rows = {ranking_eligible_rows}`",
        f"- `null_score_rows = {null_score_rows}`",
        f"- `null_score_share = {null_score_share:.5f}`" if null_score_share is not None else "- `null_score_share = null`",
        f"- `scored_with_label_rows = {scored_with_label_rows}`",
        "",
        "## 2. IC Readout",
        f"- Full-sample correlation IC: `{payload['ic_readout']['full_sample_corr_ic']:.6f}`" if payload["ic_readout"]["full_sample_corr_ic"] is not None else "- Full-sample correlation IC: `null`",
        f"- Average daily IC: `{payload['ic_readout']['avg_daily_ic']:.6f}`" if payload["ic_readout"]["avg_daily_ic"] is not None else "- Average daily IC: `null`",
        f"- Median daily IC: `{payload['ic_readout']['median_daily_ic']:.6f}`" if payload["ic_readout"]["median_daily_ic"] is not None else "- Median daily IC: `null`",
        f"- Positive daily IC share: `{payload['ic_readout']['positive_daily_ic_share']:.5f}`" if payload["ic_readout"]["positive_daily_ic_share"] is not None else "- Positive daily IC share: `null`",
        "",
        "## 3. Decile Monotonicity",
        "Average forward label by score decile (descending):",
    ]
    for bucket in sorted(decile_payload.keys(), key=int):
        val = decile_payload[bucket]
        lines.append(f"- Decile {bucket}: `{val:.6f}`" if val is not None else f"- Decile {bucket}: `null`")
    lines.extend(
        [
            "",
            "## 4. Why `TopK=10` Still Matters",
            f"- Average label, top 10 names: `{top10:.6f}`" if top10 is not None else "- Average label, top 10 names: `null`",
            f"- Average label, rank 11-20: `{rank11_20:.6f}`" if rank11_20 is not None else "- Average label, rank 11-20: `null`",
            f"- Average label, bottom 10: `{bottom10:.6f}`" if bottom10 is not None else "- Average label, bottom 10: `null`",
            f"- `top10 - rank11_20 = {payload['top_slice_readout']['top10_minus_rank11_20']:.6f}`" if payload["top_slice_readout"]["top10_minus_rank11_20"] is not None else "- `top10 - rank11_20 = null`",
            f"- `top10 - bottom10 = {payload['top_slice_readout']['top10_minus_bottom10']:.6f}`" if payload["top_slice_readout"]["top10_minus_bottom10"] is not None else "- `top10 - bottom10 = null`",
            "",
            "## 5. Cutoff Gap Around Rank 10/11",
            f"- Average score gap `rank10 - rank11`: `{payload['cutoff_gap']['avg_rank10_11_score_gap']:.6f}`" if payload["cutoff_gap"]["avg_rank10_11_score_gap"] is not None else "- Average score gap `rank10 - rank11`: `null`",
            f"- Median score gap `rank10 - rank11`: `{payload['cutoff_gap']['median_rank10_11_score_gap']:.6f}`" if payload["cutoff_gap"]["median_rank10_11_score_gap"] is not None else "- Median score gap `rank10 - rank11`: `null`",
            f"- Days with both ranks present: `{payload['cutoff_gap']['days_with_both_ranks']}`",
            f"- Days with `|gap| < 0.005`: `{payload['cutoff_gap']['days_gap_lt_0_005']}`",
            f"- Days with `|gap| < 0.001`: `{payload['cutoff_gap']['days_gap_lt_0_001']}`",
            "",
        ]
    )
    md_output.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
