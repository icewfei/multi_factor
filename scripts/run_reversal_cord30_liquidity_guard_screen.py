#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Cheap diagnostic screen for adding a liquidity-rank guard to the
reversal_p98_cord30 composite before opening a new full-chain round.
"""

from __future__ import annotations

import json
import random
from datetime import datetime
from pathlib import Path

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
FIXED_TEST_DIR = ROOT / "artifacts" / "fixed_test"
OUT_DIR = ROOT / "artifacts" / "fixed_test" / "reversal_cord30_liquidity_guard_screen"

BASE_PANELS = RUN_STATE_DIR / "project_panels_research_trainval_20211231_20260429"
SCORE_PATH = RUN_STATE_DIR / "confirmatory_reversal_p98_cord30_trainval_20260506" / "model_scores_D0.parquet"

LABEL = "label_5d_next_open_close"
SEED = 42
N_BOOTSTRAP = 10000
THRESHOLDS = [0.55, 0.60, 0.65, 0.70]


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_path(path: Path) -> str:
    return sql_quote(path.resolve().as_posix())


def bootstrap_ci(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    rng = random.Random(SEED)
    n = len(values)
    medians = []
    for _ in range(N_BOOTSTRAP):
        sample = [values[rng.randint(0, n - 1)] for _ in range(n)]
        sample.sort()
        m = len(sample)
        medians.append(sample[m // 2] if m % 2 == 1 else (sample[m // 2 - 1] + sample[m // 2]) / 2.0)
    medians.sort()
    lo = int(N_BOOTSTRAP * 0.025)
    hi = int(N_BOOTSTRAP * 0.975)
    return medians[lo], medians[hi]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    try:
        con.execute(
            f"CREATE OR REPLACE VIEW labels AS SELECT * FROM read_parquet({sql_path(BASE_PANELS / 'project_label_panel.parquet')})"
        )
        con.execute(
            f"CREATE OR REPLACE VIEW scores AS SELECT * FROM read_parquet({sql_path(SCORE_PATH)})"
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW base AS
            SELECT
                s.snapshot_id,
                s.instrument,
                s.signal_date,
                s.model_score_D0 AS score,
                s.liquidity_rank,
                l.{LABEL} AS oracle_label
            FROM scores s
            LEFT JOIN labels l
              ON s.snapshot_id = l.snapshot_id
             AND s.instrument = l.instrument
             AND s.signal_date = l.signal_date
            WHERE s.model_score_D0 IS NOT NULL
              AND l.{LABEL} IS NOT NULL
        """
        )

        result_rows = []
        for threshold in [None] + THRESHOLDS:
            if threshold is None:
                filter_clause = "TRUE"
                name = "no_guard"
            else:
                filter_clause = f"liquidity_rank >= {threshold}"
                name = f"liq_ge_{threshold:.2f}"

            daily = con.execute(
                f"""
                WITH filtered AS (
                    SELECT * FROM base WHERE {filter_clause}
                ),
                daily_ic AS (
                    SELECT signal_date, CORR(score, oracle_label) AS daily_ic
                    FROM filtered
                    GROUP BY signal_date
                    HAVING COUNT(*) >= 20
                )
                SELECT daily_ic FROM daily_ic ORDER BY signal_date
            """
            ).fetchall()
            ic_series = [float(r[0]) for r in daily if r[0] is not None]
            ic_series = [x for x in ic_series if not (x != x)]
            ic_sorted = sorted(ic_series)
            n = len(ic_sorted)
            med = ic_sorted[n // 2] if n % 2 == 1 else (ic_sorted[n // 2 - 1] + ic_sorted[n // 2]) / 2.0
            ci_lo, ci_hi = bootstrap_ci(ic_series)

            summary = con.execute(
                f"""
                WITH filtered AS (
                    SELECT * FROM base WHERE {filter_clause}
                ),
                ranked AS (
                    SELECT
                        signal_date,
                        instrument,
                        score,
                        oracle_label,
                        liquidity_rank,
                        ROW_NUMBER() OVER (PARTITION BY signal_date ORDER BY score DESC, instrument ASC) AS rn_desc,
                        ROW_NUMBER() OVER (PARTITION BY signal_date ORDER BY score ASC, instrument ASC) AS rn_asc
                    FROM filtered
                )
                SELECT
                    AVG(CASE WHEN rn_desc <= 10 THEN oracle_label END) AS top10_label,
                    AVG(CASE WHEN rn_asc <= 10 THEN oracle_label END) AS bot10_label,
                    AVG(CASE WHEN rn_desc <= 10 THEN liquidity_rank END) AS top10_avg_liq_rank,
                    MEDIAN(CASE WHEN rn_desc <= 10 THEN liquidity_rank END) AS top10_med_liq_rank,
                    AVG(CASE WHEN rn_desc <= 10 THEN 1.0 ELSE 0.0 END) AS top10_row_share
                FROM ranked
            """
            ).fetchone()

            eligible = con.execute(
                f"SELECT AVG(cnt) FROM (SELECT signal_date, COUNT(*) AS cnt FROM base WHERE {filter_clause} GROUP BY signal_date)"
            ).fetchone()[0]

            result_rows.append(
                {
                    "screen_id": name,
                    "liquidity_rank_threshold": threshold,
                    "median_daily_ic": med,
                    "median_daily_ic_ci_low": ci_lo,
                    "median_daily_ic_ci_high": ci_hi,
                    "top10_avg_label": float(summary[0]),
                    "bottom10_avg_label": float(summary[1]),
                    "top10_bot10_spread": float(summary[0] - summary[1]),
                    "top10_avg_liquidity_rank": float(summary[2]),
                    "top10_median_liquidity_rank": float(summary[3]),
                    "avg_eligible_names_per_day": float(eligible),
                    "n_days": n,
                }
            )
    finally:
        con.close()

    payload = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_score_run_id": "confirmatory_reversal_p98_cord30_trainval_20260506",
        "screen_results": result_rows,
    }

    json_path = OUT_DIR / "liquidity_guard_screen_20260506.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Reversal + Cord30 Liquidity Guard Screen",
        "",
        "| Screen | Median IC | 95% CI | Top10 | Spread | Top10 avg liq rank | Avg eligible/day |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in result_rows:
        lines.append(
            f"| {row['screen_id']} | {row['median_daily_ic']:.6f} | "
            f"[{row['median_daily_ic_ci_low']:.6f}, {row['median_daily_ic_ci_high']:.6f}] | "
            f"{row['top10_avg_label']:+.6f} | {row['top10_bot10_spread']:+.6f} | "
            f"{row['top10_avg_liquidity_rank']:.6f} | {row['avg_eligible_names_per_day']:.1f} |"
        )
    md_path = OUT_DIR / "liquidity_guard_screen_20260506.md"
    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    print(f"JSON: {json_path}")
    print(f"MD:   {md_path}")


if __name__ == "__main__":
    main()
