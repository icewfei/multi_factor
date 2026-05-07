#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Cheap partner screen for p98 reversal + one positive-pass partner.
Compares cord30, corr30, imxd5 under the same diagnostic composite recipe.
"""

from __future__ import annotations

import json
import random
from datetime import datetime
from pathlib import Path

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
OUT_DIR = ROOT / "artifacts" / "fixed_test" / "reversal_partner_screen"
BASE_PANELS = RUN_STATE_DIR / "project_panels_research_trainval_20211231_20260429"

P98_SCORE_PATH = RUN_STATE_DIR / "confirmatory_reversal_p98_trainval_20260506" / "model_scores_D0.parquet"
PARTNERS = {
    "cord30": (
        RUN_STATE_DIR / "confirmatory_cord30_trainval_20260429" / "model_scores_D0.parquet",
        "price_volume_single_signal_alpha158_cord30_v1",
    ),
    "corr30": (
        RUN_STATE_DIR / "confirmatory_corr30_trainval_20260430" / "model_scores_D0.parquet",
        "price_volume_single_signal_alpha158_corr30_v1",
    ),
    "imxd5": (
        RUN_STATE_DIR / "confirmatory_imxd5_trainval_20260429" / "model_scores_D0.parquet",
        "price_volume_single_signal_alpha158_imxd5_v1",
    ),
}
LABEL = "label_5d_next_open_close"
N_BOOTSTRAP = 10000
SEED = 42


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
            f"CREATE OR REPLACE VIEW p98_scores AS SELECT * FROM read_parquet({sql_path(P98_SCORE_PATH)})"
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW p98_base AS
            SELECT
                p.snapshot_id,
                p.instrument,
                p.signal_date,
                p.model_score_D0 AS p98_score,
                p.liquidity_rank,
                l.{LABEL} AS oracle_label
            FROM p98_scores p
            LEFT JOIN labels l
              ON p.snapshot_id = l.snapshot_id
             AND p.instrument = l.instrument
             AND p.signal_date = l.signal_date
            WHERE p.model_score_D0 IS NOT NULL
              AND l.{LABEL} IS NOT NULL
        """
        )

        rows = []
        for partner_name, (path, scheme_id) in PARTNERS.items():
            con.execute(
                f"CREATE OR REPLACE VIEW partner_scores AS SELECT * FROM read_parquet({sql_path(path)})"
            )
            con.execute(
                f"""
                CREATE OR REPLACE VIEW partner_base AS
                SELECT
                    snapshot_id,
                    instrument,
                    signal_date,
                    model_score_D0 AS partner_score
                FROM partner_scores
                WHERE candidate_scheme_id = {sql_quote(scheme_id)}
                  AND model_score_D0 IS NOT NULL
            """
            )
            con.execute(
                """
                CREATE OR REPLACE VIEW combo_base AS
                SELECT
                    p.snapshot_id,
                    p.instrument,
                    p.signal_date,
                    p.oracle_label,
                    p.liquidity_rank,
                    p.p98_score,
                    b.partner_score,
                    PERCENT_RANK() OVER (
                        PARTITION BY p.snapshot_id, p.signal_date
                        ORDER BY p.p98_score ASC, p.instrument ASC
                    ) AS p98_rank,
                    PERCENT_RANK() OVER (
                        PARTITION BY p.snapshot_id, p.signal_date
                        ORDER BY b.partner_score ASC, p.instrument ASC
                    ) AS partner_rank
                FROM p98_base p
                JOIN partner_base b
                  ON p.snapshot_id = b.snapshot_id
                 AND p.instrument = b.instrument
                 AND p.signal_date = b.signal_date
            """
            )
            con.execute(
                """
                CREATE OR REPLACE VIEW combo_score AS
                SELECT
                    snapshot_id,
                    instrument,
                    signal_date,
                    oracle_label,
                    liquidity_rank,
                    p98_rank,
                    partner_rank,
                    0.5 * p98_rank + 0.5 * partner_rank AS score
                FROM combo_base
            """
            )

            daily = con.execute(
                """
                WITH daily_ic AS (
                    SELECT signal_date, CORR(score, oracle_label) AS ic
                    FROM combo_score
                    GROUP BY signal_date
                    HAVING COUNT(*) >= 20
                )
                SELECT ic FROM daily_ic ORDER BY signal_date
            """
            ).fetchall()
            ic_series = [float(r[0]) for r in daily if r[0] is not None]
            ic_series = [x for x in ic_series if not (x != x)]
            s = sorted(ic_series)
            n = len(s)
            med = s[n // 2] if n % 2 == 1 else (s[n // 2 - 1] + s[n // 2]) / 2.0
            ci_lo, ci_hi = bootstrap_ci(ic_series)

            summary = con.execute(
                """
                WITH ranked AS (
                    SELECT
                        signal_date,
                        instrument,
                        score,
                        oracle_label,
                        liquidity_rank,
                        ROW_NUMBER() OVER (PARTITION BY signal_date ORDER BY score DESC, instrument ASC) AS rn_desc,
                        ROW_NUMBER() OVER (PARTITION BY signal_date ORDER BY score ASC, instrument ASC) AS rn_asc
                    FROM combo_score
                )
                SELECT
                    AVG(CASE WHEN rn_desc <= 10 THEN oracle_label END),
                    AVG(CASE WHEN rn_asc <= 10 THEN oracle_label END),
                    AVG(CASE WHEN rn_desc <= 10 THEN liquidity_rank END),
                    MEDIAN(CASE WHEN rn_desc <= 10 THEN liquidity_rank END),
                    (SELECT CORR(p98_rank, partner_rank) FROM combo_base)
                FROM ranked
            """
            ).fetchone()

            rows.append(
                {
                    "partner": partner_name,
                    "partner_scheme_id": scheme_id,
                    "median_daily_ic": med,
                    "median_daily_ic_ci_low": ci_lo,
                    "median_daily_ic_ci_high": ci_hi,
                    "top10_avg_label": float(summary[0]),
                    "bottom10_avg_label": float(summary[1]),
                    "top10_bot10_spread": float(summary[0] - summary[1]),
                    "top10_avg_liquidity_rank": float(summary[2]),
                    "top10_median_liquidity_rank": float(summary[3]),
                    "cross_signal_rank_corr": float(summary[4]),
                }
            )
    finally:
        con.close()

    payload = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "screen_results": rows,
    }
    json_path = OUT_DIR / "reversal_partner_screen_20260506.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Reversal Partner Screen",
        "",
        "| Partner | Median IC | 95% CI | Top10 | Spread | Top10 avg liq rank | Cross-rank corr |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['partner']} | {row['median_daily_ic']:.6f} | "
            f"[{row['median_daily_ic_ci_low']:.6f}, {row['median_daily_ic_ci_high']:.6f}] | "
            f"{row['top10_avg_label']:+.6f} | {row['top10_bot10_spread']:+.6f} | "
            f"{row['top10_avg_liquidity_rank']:.6f} | {row['cross_signal_rank_corr']:.6f} |"
        )
    md_path = OUT_DIR / "reversal_partner_screen_20260506.md"
    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    print(f"JSON: {json_path}")
    print(f"MD:   {md_path}")


if __name__ == "__main__":
    main()
