#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Cheap composability screen inside the reversal family.

Goal:
- start from the live p98 reversal construction
- test whether nearby same-run rank components offer a promising modifier path
- avoid opening a full round unless one candidate clearly improves the diagnostic profile
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
OUT_DIR = ROOT / "artifacts" / "fixed_test" / "reversal_family_composability_screen"

REVERSAL_RUN_ID = "exploratory_cross_horizon_c1_reversal_only"
PANEL_RUN_ID = "project_panels_research_trainval_20211231_20260429"

PARTNER_COLS = [
    "reversal_followthrough_rank",
    "intraday_reversal_asymmetry_rank",
    "upside_range_share_rank",
    "intraday_trend_bias_rank",
    "liquidity_trend_rank",
]
PARTNER_WEIGHTS = [0.10, 0.20]


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

    score_path = RUN_STATE_DIR / REVERSAL_RUN_ID / "model_scores_D0.parquet"
    label_path = RUN_STATE_DIR / PANEL_RUN_ID / "project_label_panel.parquet"
    sample_path = RUN_STATE_DIR / PANEL_RUN_ID / "project_sample_panel.parquet"

    con = duckdb.connect()
    try:
        con.execute(f"CREATE OR REPLACE VIEW reversal_scores AS SELECT * FROM read_parquet({sql_path(score_path)})")
        con.execute(f"CREATE OR REPLACE VIEW label_panel AS SELECT * FROM read_parquet({sql_path(label_path)})")
        con.execute(f"CREATE OR REPLACE VIEW sample_panel AS SELECT * FROM read_parquet({sql_path(sample_path)})")

        con.execute(
            """
            CREATE OR REPLACE VIEW nr_raw AS
            SELECT
                s.snapshot_id,
                s.instrument,
                s.signal_date,
                -1.0 * r.model_score_D0 AS nr_score,
                r.model_score_D0 AS raw_reversal_score,
                r.reversal_followthrough_rank,
                r.intraday_reversal_asymmetry_rank,
                r.upside_range_share_rank,
                r.intraday_trend_bias_rank,
                r.liquidity_trend_rank,
                r.liquidity_rank,
                l.label_5d_next_open_close AS oracle_label
            FROM sample_panel s
            JOIN reversal_scores r
              ON s.snapshot_id = r.snapshot_id
             AND s.instrument = r.instrument
             AND s.signal_date = r.signal_date
            JOIN label_panel l
              ON s.snapshot_id = l.snapshot_id
             AND s.instrument = l.instrument
             AND s.signal_date = l.signal_date
            WHERE s.ranking_eligible_D0
              AND r.model_score_D0 IS NOT NULL
              AND l.label_5d_next_open_close IS NOT NULL
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
                n.*
            FROM nr_raw n
            JOIN nr_daily_p98 p
              ON n.snapshot_id = p.snapshot_id
             AND n.signal_date = p.signal_date
            WHERE n.nr_score < p.p98
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW p98_ranked AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                liquidity_rank,
                oracle_label,
                reversal_followthrough_rank,
                intraday_reversal_asymmetry_rank,
                upside_range_share_rank,
                intraday_trend_bias_rank,
                liquidity_trend_rank,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY nr_score ASC, instrument ASC
                ) AS p98_reversal_rank
            FROM nr_p98
            """
        )

        def diagnostic_from_view(view_name: str, score_col: str) -> dict:
            daily_ic_rows = con.execute(
                f"""
                WITH daily AS (
                    SELECT
                        signal_date,
                        CORR({score_col}, oracle_label) AS daily_ic
                    FROM {view_name}
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
                f"""
                WITH ranked_day AS (
                    SELECT
                        signal_date,
                        instrument,
                        liquidity_rank,
                        oracle_label,
                        {score_col} AS score,
                        ROW_NUMBER() OVER (
                            PARTITION BY signal_date
                            ORDER BY {score_col} DESC, instrument ASC
                        ) AS rank_desc,
                        ROW_NUMBER() OVER (
                            PARTITION BY signal_date
                            ORDER BY {score_col} ASC, instrument ASC
                        ) AS rank_asc
                    FROM {view_name}
                    WHERE {score_col} IS NOT NULL
                )
                SELECT
                    AVG(CASE WHEN rank_desc <= 10 THEN oracle_label END) AS top10_avg_label,
                    AVG(CASE WHEN rank_asc <= 10 THEN oracle_label END) AS bot10_avg_label,
                    AVG(CASE WHEN rank_desc <= 10 THEN liquidity_rank END) AS top10_avg_liquidity_rank,
                    COUNT(*) AS scored_rows
                FROM ranked_day
                """
            ).fetchone()
            return {
                "median_daily_ic": median(daily_ics),
                "mean_daily_ic": (sum(daily_ics) / len(daily_ics)) if daily_ics else None,
                "n_days": len(daily_ics),
                "top10_avg_label": float(summary[0]) if summary[0] is not None else None,
                "bot10_avg_label": float(summary[1]) if summary[1] is not None else None,
                "top10_bot10_spread": (
                    float(summary[0] - summary[1]) if summary[0] is not None and summary[1] is not None else None
                ),
                "top10_avg_liquidity_rank": float(summary[2]) if summary[2] is not None else None,
                "scored_rows": int(summary[3]) if summary[3] is not None else 0,
            }

        baseline = diagnostic_from_view("p98_ranked", "p98_reversal_rank")

        partner_results = []
        for partner_col in PARTNER_COLS:
            partner_corr = con.execute(
                f"""
                WITH daily AS (
                    SELECT
                        signal_date,
                        CORR(p98_reversal_rank, {partner_col}) AS corr_daily
                    FROM p98_ranked
                    WHERE {partner_col} IS NOT NULL
                    GROUP BY signal_date
                    HAVING COUNT(*) >= 20
                )
                SELECT AVG(corr_daily), MEDIAN(corr_daily)
                FROM daily
                """
            ).fetchone()
            for partner_weight in PARTNER_WEIGHTS:
                reversal_weight = 1.0 - partner_weight
                view_name = f"screen_{partner_col}_{str(partner_weight).replace('.', 'p')}"
                con.execute(f"DROP VIEW IF EXISTS {view_name}")
                con.execute(
                    f"""
                    CREATE OR REPLACE VIEW {view_name} AS
                    SELECT
                        *,
                        ({reversal_weight:.6f} * p98_reversal_rank) + ({partner_weight:.6f} * {partner_col}) AS screen_score
                    FROM p98_ranked
                    WHERE {partner_col} IS NOT NULL
                    """
                )
                diag = diagnostic_from_view(view_name, "screen_score")
                diag["partner_col"] = partner_col
                diag["partner_weight"] = partner_weight
                diag["reversal_weight"] = reversal_weight
                diag["avg_daily_corr_with_p98"] = float(partner_corr[0]) if partner_corr[0] is not None else None
                diag["median_daily_corr_with_p98"] = float(partner_corr[1]) if partner_corr[1] is not None else None
                partner_results.append(diag)

        promising = [
            row
            for row in partner_results
            if row["median_daily_ic"] is not None
            and row["top10_bot10_spread"] is not None
            and row["top10_avg_liquidity_rank"] is not None
            and row["median_daily_ic"] >= (baseline["median_daily_ic"] - 0.0015)
            and row["top10_bot10_spread"] > baseline["top10_bot10_spread"]
            and row["top10_avg_liquidity_rank"] >= (baseline["top10_avg_liquidity_rank"] + 0.01)
        ]
        preferred = max(
            promising,
            key=lambda row: (row["top10_bot10_spread"], row["top10_avg_liquidity_rank"], row["median_daily_ic"]),
            default=None,
        )

        payload = {
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "baseline_p98": baseline,
            "screen_results": partner_results,
            "preferred_followup": preferred,
        }
    finally:
        con.close()

    json_path = OUT_DIR / "reversal_family_composability_screen_20260506.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Reversal Family Composability Screen",
        "",
        f"- generated_at: {payload['generated_at']}",
        "",
        "## Baseline p98",
        "",
        f"- median_daily_ic = {baseline['median_daily_ic']:.6f}",
        f"- mean_daily_ic = {baseline['mean_daily_ic']:.6f}",
        f"- top10_avg_label = {baseline['top10_avg_label']:.6f}",
        f"- top10_bot10_spread = {baseline['top10_bot10_spread']:.6f}",
        f"- top10_avg_liquidity_rank = {baseline['top10_avg_liquidity_rank']:.6f}",
        "",
        "## Candidates",
        "",
        "| partner | weight | median_IC | mean_IC | Top10 | Spread | Top10 avg liq_rank | avg corr with p98 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in partner_results:
        lines.append(
            "| "
            f"{row['partner_col']} | "
            f"{row['partner_weight']:.2f} | "
            f"{row['median_daily_ic']:.6f} | "
            f"{row['mean_daily_ic']:.6f} | "
            f"{row['top10_avg_label']:.6f} | "
            f"{row['top10_bot10_spread']:.6f} | "
            f"{row['top10_avg_liquidity_rank']:.6f} | "
            f"{row['avg_daily_corr_with_p98']:.6f} |"
        )
    lines.extend(["", "## Preferred follow-up", ""])
    if preferred is None:
        lines.append("- none")
    else:
        lines.append(
            f"- partner = {preferred['partner_col']}, "
            f"weight = {preferred['partner_weight']:.2f}, "
            f"median_IC = {preferred['median_daily_ic']:.6f}, "
            f"spread = {preferred['top10_bot10_spread']:.6f}, "
            f"top10_avg_liquidity_rank = {preferred['top10_avg_liquidity_rank']:.6f}"
        )

    md_path = OUT_DIR / "reversal_family_composability_screen_20260506.md"
    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    print(f"JSON: {json_path}")
    print(f"MD:   {md_path}")


if __name__ == "__main__":
    main()
