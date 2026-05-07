#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Cheap screen over reversal + cord30 composite weights.

Goal:
- keep the partner family fixed (cord30 only)
- vary only the mixing weight
- measure whether lighter partner weights preserve useful top-slice behavior
  while reducing the liquidity drag seen in the 50/50 line
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
OUT_DIR = ROOT / "artifacts" / "fixed_test" / "reversal_cord30_weight_screen"

PANEL_RUN_ID = "project_panels_research_trainval_20211231_20260429"
REVERSAL_RUN_ID = "exploratory_cross_horizon_c1_reversal_only"
CORD30_RUN_ID = "confirmatory_cord30_trainval_20260429"
CORD30_CANDIDATE_ID = "price_volume_single_signal_alpha158_cord30_v1"

WEIGHTS = [0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_path(path: Path) -> str:
    return sql_quote(path.resolve().as_posix())


def median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    sample_path = RUN_STATE_DIR / PANEL_RUN_ID / "project_sample_panel.parquet"
    label_path = RUN_STATE_DIR / PANEL_RUN_ID / "project_label_panel.parquet"
    reversal_path = RUN_STATE_DIR / REVERSAL_RUN_ID / "model_scores_D0.parquet"
    cord30_path = RUN_STATE_DIR / CORD30_RUN_ID / "model_scores_D0.parquet"

    con = duckdb.connect()
    try:
        con.execute(f"CREATE OR REPLACE VIEW sample_panel AS SELECT * FROM read_parquet({sql_path(sample_path)})")
        con.execute(f"CREATE OR REPLACE VIEW label_panel AS SELECT * FROM read_parquet({sql_path(label_path)})")
        con.execute(f"CREATE OR REPLACE VIEW reversal_scores AS SELECT * FROM read_parquet({sql_path(reversal_path)})")
        con.execute(f"CREATE OR REPLACE VIEW cord30_scores AS SELECT * FROM read_parquet({sql_path(cord30_path)})")

        con.execute(
            """
            CREATE OR REPLACE VIEW nr_raw AS
            SELECT
                s.snapshot_id,
                s.instrument,
                s.signal_date,
                -1.0 * r.model_score_D0 AS nr_score,
                r.liquidity_rank
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
        con.execute(
            f"""
            CREATE OR REPLACE VIEW cord30_base AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                model_score_D0 AS cord30_score
            FROM cord30_scores
            WHERE candidate_scheme_id = {sql_quote(CORD30_CANDIDATE_ID)}
              AND model_score_D0 IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW joined AS
            SELECT
                n.snapshot_id,
                n.instrument,
                n.signal_date,
                n.nr_score,
                n.liquidity_rank,
                c.cord30_score,
                l.label_5d_next_open_close AS oracle_label
            FROM nr_p98 n
            JOIN cord30_base c
              ON n.snapshot_id = c.snapshot_id
             AND n.instrument = c.instrument
             AND n.signal_date = c.signal_date
            JOIN label_panel l
              ON n.snapshot_id = l.snapshot_id
             AND n.instrument = l.instrument
             AND n.signal_date = l.signal_date
            WHERE l.label_5d_next_open_close IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW ranked AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                liquidity_rank,
                oracle_label,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY nr_score ASC, instrument ASC
                ) AS rev_rank,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY cord30_score ASC, instrument ASC
                ) AS cord30_rank
            FROM joined
            """
        )

        results = []
        for cord30_weight in WEIGHTS:
            reversal_weight = 1.0 - cord30_weight
            con.execute("DROP VIEW IF EXISTS weighted_scores")
            con.execute(
                f"""
                CREATE OR REPLACE VIEW weighted_scores AS
                SELECT
                    snapshot_id,
                    instrument,
                    signal_date,
                    liquidity_rank,
                    oracle_label,
                    rev_rank,
                    cord30_rank,
                    ({reversal_weight:.6f} * rev_rank) + ({cord30_weight:.6f} * cord30_rank) AS score
                FROM ranked
                """
            )

            daily_ic_rows = con.execute(
                """
                WITH daily AS (
                    SELECT
                        signal_date,
                        CORR(score, oracle_label) AS daily_ic
                    FROM weighted_scores
                    GROUP BY signal_date
                    HAVING COUNT(*) >= 20
                )
                SELECT daily_ic
                FROM daily
                ORDER BY signal_date
                """
            ).fetchall()
            daily_ics = [float(row[0]) for row in daily_ic_rows if row[0] is not None]

            summary = con.execute(
                """
                WITH ranked_day AS (
                    SELECT
                        signal_date,
                        instrument,
                        liquidity_rank,
                        oracle_label,
                        score,
                        rev_rank,
                        cord30_rank,
                        ROW_NUMBER() OVER (
                            PARTITION BY signal_date
                            ORDER BY score DESC, instrument ASC
                        ) AS rank_desc,
                        ROW_NUMBER() OVER (
                            PARTITION BY signal_date
                            ORDER BY score ASC, instrument ASC
                        ) AS rank_asc
                    FROM weighted_scores
                )
                SELECT
                    AVG(CASE WHEN rank_desc <= 10 THEN oracle_label END) AS top10_avg_label,
                    AVG(CASE WHEN rank_asc <= 10 THEN oracle_label END) AS bot10_avg_label,
                    AVG(CASE WHEN rank_desc <= 10 THEN liquidity_rank END) AS top10_avg_liquidity_rank,
                    AVG(CASE WHEN rank_desc <= 10 THEN rev_rank END) AS top10_avg_rev_rank,
                    AVG(CASE WHEN rank_desc <= 10 THEN cord30_rank END) AS top10_avg_cord30_rank
                FROM ranked_day
                """
            ).fetchone()

            results.append(
                {
                    "cord30_weight": cord30_weight,
                    "reversal_weight": reversal_weight,
                    "median_daily_ic": median(daily_ics),
                    "mean_daily_ic": (sum(daily_ics) / len(daily_ics)) if daily_ics else None,
                    "n_days": len(daily_ics),
                    "top10_avg_label": float(summary[0]) if summary[0] is not None else None,
                    "bot10_avg_label": float(summary[1]) if summary[1] is not None else None,
                    "top10_bot10_spread": (
                        float(summary[0] - summary[1]) if summary[0] is not None and summary[1] is not None else None
                    ),
                    "top10_avg_liquidity_rank": float(summary[2]) if summary[2] is not None else None,
                    "top10_avg_rev_rank": float(summary[3]) if summary[3] is not None else None,
                    "top10_avg_cord30_rank": float(summary[4]) if summary[4] is not None else None,
                }
            )

        baseline_50 = next(row for row in results if abs(row["cord30_weight"] - 0.50) < 1e-9)
        candidates = [
            row for row in results
            if row["top10_avg_liquidity_rank"] is not None
            and row["top10_bot10_spread"] is not None
            and row["median_daily_ic"] is not None
            and row["cord30_weight"] < 0.50
            and row["top10_avg_liquidity_rank"] > baseline_50["top10_avg_liquidity_rank"]
            and row["top10_bot10_spread"] >= baseline_50["top10_bot10_spread"] * 0.75
            and row["median_daily_ic"] >= 0.045
        ]
        preferred = max(candidates, key=lambda row: (row["top10_avg_liquidity_rank"], row["top10_bot10_spread"])) if candidates else None

        payload = {
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "weights": results,
            "reference_50_50": baseline_50,
            "preferred_followup": preferred,
        }
    finally:
        con.close()

    json_path = OUT_DIR / "weight_screen_20260506.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Reversal + Cord30 Weight Screen",
        "",
        f"- generated_at: {payload['generated_at']}",
        "",
        "| cord30_weight | median_IC | mean_IC | Top10 | Bot10 | Spread | Top10 avg liq_rank |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in results:
        lines.append(
            "| "
            f"{row['cord30_weight']:.2f} | "
            f"{row['median_daily_ic']:.6f} | "
            f"{row['mean_daily_ic']:.6f} | "
            f"{row['top10_avg_label']:.6f} | "
            f"{row['bot10_avg_label']:.6f} | "
            f"{row['top10_bot10_spread']:.6f} | "
            f"{row['top10_avg_liquidity_rank']:.6f} |"
        )
    lines.extend(["", "## Preferred follow-up", ""])
    if preferred is None:
        lines.append("- none")
    else:
        lines.append(
            f"- cord30_weight = {preferred['cord30_weight']:.2f}, "
            f"median_IC = {preferred['median_daily_ic']:.6f}, "
            f"spread = {preferred['top10_bot10_spread']:.6f}, "
            f"top10_avg_liquidity_rank = {preferred['top10_avg_liquidity_rank']:.6f}"
        )

    md_path = OUT_DIR / "weight_screen_20260506.md"
    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    print(f"JSON: {json_path}")
    print(f"MD:   {md_path}")


if __name__ == "__main__":
    main()
