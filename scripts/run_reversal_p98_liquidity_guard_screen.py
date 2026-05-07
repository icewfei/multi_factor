#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Cheap liquidity-guard screen for the p98 reversal baseline.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
OUT_DIR = ROOT / "artifacts" / "fixed_test" / "reversal_p98_liquidity_guard_screen"

RUN_ID = "confirmatory_reversal_p98_trainval_20260506"
PANEL_RUN_ID = "project_panels_research_trainval_20211231_20260429"
THRESHOLDS = [0.55, 0.60, 0.65, 0.70]


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

    scores_path = RUN_STATE_DIR / RUN_ID / "model_scores_D0.parquet"
    label_path = RUN_STATE_DIR / PANEL_RUN_ID / "project_label_panel.parquet"

    con = duckdb.connect()
    try:
        con.execute(f"CREATE OR REPLACE VIEW scores AS SELECT * FROM read_parquet({sql_path(scores_path)})")
        con.execute(f"CREATE OR REPLACE VIEW labels AS SELECT * FROM read_parquet({sql_path(label_path)})")
        con.execute(
            """
            CREATE OR REPLACE VIEW base AS
            SELECT
                s.snapshot_id,
                s.instrument,
                s.signal_date,
                s.model_score_D0,
                s.liquidity_rank,
                l.label_5d_next_open_close AS oracle_label
            FROM scores s
            JOIN labels l
              ON s.snapshot_id = l.snapshot_id
             AND s.instrument = l.instrument
             AND s.signal_date = l.signal_date
            WHERE s.model_score_D0 IS NOT NULL
              AND s.liquidity_rank IS NOT NULL
              AND l.label_5d_next_open_close IS NOT NULL
            """
        )

        results = []
        for threshold in THRESHOLDS:
            con.execute("DROP VIEW IF EXISTS screened")
            con.execute(
                f"""
                CREATE OR REPLACE VIEW screened AS
                SELECT *
                FROM base
                WHERE liquidity_rank >= {threshold:.2f}
                """
            )

            daily_ic_rows = con.execute(
                """
                WITH daily AS (
                    SELECT
                        signal_date,
                        CORR(model_score_D0, oracle_label) AS daily_ic
                    FROM screened
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
                        ROW_NUMBER() OVER (
                            PARTITION BY signal_date
                            ORDER BY model_score_D0 DESC, instrument ASC
                        ) AS rank_desc,
                        ROW_NUMBER() OVER (
                            PARTITION BY signal_date
                            ORDER BY model_score_D0 ASC, instrument ASC
                        ) AS rank_asc
                    FROM screened
                )
                SELECT
                    AVG(CASE WHEN rank_desc <= 10 THEN oracle_label END) AS top10_avg_label,
                    AVG(CASE WHEN rank_asc <= 10 THEN oracle_label END) AS bot10_avg_label,
                    AVG(CASE WHEN rank_desc <= 10 THEN liquidity_rank END) AS top10_avg_liquidity_rank,
                    AVG(CASE WHEN rank_desc <= 10 THEN 1.0 ELSE 0.0 END) AS top10_share,
                    COUNT(*) AS total_rows
                FROM ranked_day
                """
            ).fetchone()

            coverage = con.execute(
                """
                SELECT AVG(cnt) AS avg_daily_rows
                FROM (
                    SELECT signal_date, COUNT(*) AS cnt
                    FROM screened
                    GROUP BY signal_date
                )
                """
            ).fetchone()

            results.append(
                {
                    "liquidity_threshold": threshold,
                    "median_daily_ic": median(daily_ics),
                    "mean_daily_ic": (sum(daily_ics) / len(daily_ics)) if daily_ics else None,
                    "n_days": len(daily_ics),
                    "top10_avg_label": float(summary[0]) if summary[0] is not None else None,
                    "bot10_avg_label": float(summary[1]) if summary[1] is not None else None,
                    "top10_bot10_spread": (
                        float(summary[0] - summary[1]) if summary[0] is not None and summary[1] is not None else None
                    ),
                    "top10_avg_liquidity_rank": float(summary[2]) if summary[2] is not None else None,
                    "avg_daily_rows": float(coverage[0]) if coverage[0] is not None else None,
                }
            )

        preferred = max(
            (
                row for row in results
                if row["median_daily_ic"] is not None
                and row["top10_bot10_spread"] is not None
                and row["top10_avg_liquidity_rank"] is not None
                and row["avg_daily_rows"] is not None
                and row["median_daily_ic"] >= 0.043
                and row["top10_bot10_spread"] >= 0.009
                and row["avg_daily_rows"] >= 400
            ),
            key=lambda row: (row["top10_avg_liquidity_rank"], row["top10_bot10_spread"]),
            default=None,
        )

        payload = {
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "results": results,
            "preferred_followup": preferred,
        }
    finally:
        con.close()

    json_path = OUT_DIR / "liquidity_guard_screen_20260506.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Reversal P98 Liquidity-Guard Screen",
        "",
        f"- generated_at: {payload['generated_at']}",
        "",
        "| threshold | median_IC | mean_IC | Top10 | Bot10 | Spread | Top10 avg liq_rank | avg_daily_rows |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in results:
        lines.append(
            "| "
            f"{row['liquidity_threshold']:.2f} | "
            f"{row['median_daily_ic']:.6f} | "
            f"{row['mean_daily_ic']:.6f} | "
            f"{row['top10_avg_label']:.6f} | "
            f"{row['bot10_avg_label']:.6f} | "
            f"{row['top10_bot10_spread']:.6f} | "
            f"{row['top10_avg_liquidity_rank']:.6f} | "
            f"{row['avg_daily_rows']:.2f} |"
        )
    lines.extend(["", "## Preferred follow-up", ""])
    if preferred is None:
        lines.append("- none")
    else:
        lines.append(
            f"- threshold = {preferred['liquidity_threshold']:.2f}, "
            f"median_IC = {preferred['median_daily_ic']:.6f}, "
            f"spread = {preferred['top10_bot10_spread']:.6f}, "
            f"top10_avg_liquidity_rank = {preferred['top10_avg_liquidity_rank']:.6f}, "
            f"avg_daily_rows = {preferred['avg_daily_rows']:.2f}"
        )

    md_path = OUT_DIR / "liquidity_guard_screen_20260506.md"
    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    print(f"JSON: {json_path}")
    print(f"MD:   {md_path}")


if __name__ == "__main__":
    main()
