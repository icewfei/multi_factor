#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Reversal tail-failure minimal diagnosis. Read-only. 3 questions:
1. What stocks are in the Top10 tail?
2. How deep does the tail inversion go (Top10 vs Top20 vs Top50 vs D1)?
3. Can simple winsorization/exclusion restore TopK label direction?
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import duckdb

ROOT = Path("/Users/wy/MiscProject/multi_factor")
SNAPSHOT_ID = "warehouse_20260429_trainval_20211231"
SNAPSHOT_PATH = Path("/Users/wy/MiscProject/tushare_data/parquet_duckdb/data/snapshots/warehouse_20260429_trainval_20211231")
WAREHOUSE_DB = SNAPSHOT_PATH / "duckdb" / "warehouse.duckdb"
BASE_RUN = ROOT / "artifacts" / "run_state" / "confirmatory_baseline_v1_trainval_20260429"
REVERSAL_RUN = ROOT / "artifacts" / "run_state" / "exploratory_cross_horizon_c1_reversal_only"

LABEL = "label_5d_next_open_close"


def sql_quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def sql_path(p: Path) -> str:
    return sql_quote(p.resolve().as_posix())


def main() -> None:
    con = duckdb.connect()
    try:
        con.execute(f"ATTACH {sql_path(WAREHOUSE_DB)} AS wh (READ_ONLY)")
        con.execute(f"CREATE OR REPLACE VIEW labels AS SELECT * FROM read_parquet({sql_path(BASE_RUN / 'project_label_panel.parquet')})")
        con.execute(f"CREATE OR REPLACE VIEW samples AS SELECT * FROM read_parquet({sql_path(BASE_RUN / 'project_sample_panel.parquet')})")
        con.execute(f"CREATE OR REPLACE VIEW rev_scores AS SELECT * FROM read_parquet({sql_path(REVERSAL_RUN / 'model_scores_D0.parquet')})")

        # ── Base view: negated reversal score + oracle label ──
        con.execute(f"""
            CREATE OR REPLACE VIEW nr_base AS
            SELECT
                s.instrument,
                s.signal_date,
                s.ranking_eligible_D0,
                -1.0 * r.model_score_D0 AS nr_score,
                l.{LABEL} AS oracle_label
            FROM samples s
            LEFT JOIN rev_scores r
              ON s.snapshot_id = r.snapshot_id AND s.instrument = r.instrument AND s.signal_date = r.signal_date
            LEFT JOIN labels l
              ON s.snapshot_id = l.snapshot_id AND s.instrument = l.instrument AND s.signal_date = l.signal_date
            WHERE s.ranking_eligible_D0
              AND r.model_score_D0 IS NOT NULL
              AND l.{LABEL} IS NOT NULL
        """)

        # ═══════════════════════════════════════════
        # Q1: What stocks are in the Top10 tail?
        # ═══════════════════════════════════════════
        print("=" * 60)
        print("Q1: Tail stock characteristics")
        print("=" * 60)

        # Build daily bar stats (amount=size proxy, volume, volatility)
        con.execute(f"""
            CREATE OR REPLACE VIEW bar_stats AS
            SELECT
                b.trade_date,
                b.ts_code AS instrument,
                b.amount,
                b.vol,
                b.adj_close,
                b.pct_chg,
                -- 20d realized vol
                STDDEV_SAMP(b.pct_chg / 100.0) OVER (
                    PARTITION BY b.ts_code ORDER BY b.trade_date
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                ) AS vol_20d,
                -- 20d avg amount
                AVG(b.amount) OVER (
                    PARTITION BY b.ts_code ORDER BY b.trade_date
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                ) AS avg_amount_20d
            FROM wh.serving.vw_bars_daily b
            WHERE b.snapshot_id = {sql_quote(SNAPSHOT_ID)}
        """)

        # Identify daily Top10 by nr_score, join with bar stats
        con.execute("""
            CREATE OR REPLACE VIEW top10_stocks AS
            SELECT
                r.signal_date,
                r.instrument,
                r.nr_score,
                r.oracle_label,
                'top10' AS bucket
            FROM (
                SELECT *,
                    ROW_NUMBER() OVER (PARTITION BY signal_date ORDER BY nr_score DESC, instrument ASC) AS rn
                FROM nr_base
            ) r
            WHERE r.rn <= 10
        """)

        con.execute("""
            CREATE OR REPLACE VIEW other_stocks AS
            SELECT
                r.signal_date, r.instrument, r.nr_score, r.oracle_label, 'other' AS bucket
            FROM (
                SELECT *,
                    ROW_NUMBER() OVER (PARTITION BY signal_date ORDER BY nr_score DESC, instrument ASC) AS rn
                FROM nr_base
            ) r
            WHERE r.rn > 10
        """)

        # Join Top10 with bar stats
        q1_raw = con.execute("""
            WITH joined AS (
                SELECT
                    t.signal_date, t.instrument, t.nr_score, t.oracle_label, t.bucket,
                    COALESCE(b.amount, 0) AS amount,
                    COALESCE(b.avg_amount_20d, 0) AS avg_amount_20d,
                    COALESCE(b.vol_20d, 0) AS vol_20d,
                    ABS(COALESCE(b.pct_chg, 0)) AS abs_pct_chg
                FROM top10_stocks t
                LEFT JOIN bar_stats b
                  ON t.instrument = b.instrument AND t.signal_date = b.trade_date
            )
            SELECT
                AVG(oracle_label) AS avg_label,
                AVG(amount) AS avg_amount,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY amount) AS med_amount,
                AVG(avg_amount_20d) AS avg_amount_20d,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY avg_amount_20d) AS med_amount_20d,
                AVG(vol_20d) AS avg_vol_20d,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY vol_20d) AS med_vol_20d,
                AVG(abs_pct_chg) AS avg_abs_pct_chg,
                COUNT(*) AS n
            FROM joined
        """).fetchone()

        # Compare with non-Top10 (other 10 stocks: rank 11-20 for direct comparison)
        con.execute("""
            CREATE OR REPLACE VIEW rank11_20_stocks AS
            SELECT
                r.signal_date, r.instrument, r.nr_score, r.oracle_label, 'rank11_20' AS bucket
            FROM (
                SELECT *,
                    ROW_NUMBER() OVER (PARTITION BY signal_date ORDER BY nr_score DESC, instrument ASC) AS rn
                FROM nr_base
            ) r
            WHERE r.rn BETWEEN 11 AND 20
        """)

        q1_compare = con.execute("""
            WITH joined AS (
                SELECT
                    t.signal_date, t.instrument, t.nr_score, t.oracle_label, t.bucket,
                    COALESCE(b.amount, 0) AS amount,
                    COALESCE(b.avg_amount_20d, 0) AS avg_amount_20d,
                    COALESCE(b.vol_20d, 0) AS vol_20d
                FROM rank11_20_stocks t
                LEFT JOIN bar_stats b ON t.instrument = b.instrument AND t.signal_date = b.trade_date
            )
            SELECT
                AVG(oracle_label) AS avg_label,
                AVG(amount) AS avg_amount,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY amount) AS med_amount,
                AVG(vol_20d) AS avg_vol_20d,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY vol_20d) AS med_vol_20d,
                COUNT(*) AS n
            FROM joined
        """).fetchone()

        # Full-sample medians for reference
        q1_ref = con.execute("""
            SELECT
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY amount) AS med_amount,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY avg_amount_20d) AS med_amount_20d,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY vol_20d) AS med_vol_20d
            FROM bar_stats
            WHERE avg_amount_20d > 0
        """).fetchone()

        print(f"  Top10 stocks (n={q1_raw[8]}):")
        print(f"    avg oracle label = {q1_raw[0]:.5f}")
        print(f"    avg amount = {q1_raw[1]:.0f}  |  med amount = {q1_raw[2]:.0f}")
        print(f"    avg amount_20d = {q1_raw[3]:.0f}  |  med amount_20d = {q1_raw[4]:.0f}")
        print(f"    avg vol_20d = {q1_raw[5]:.4f}  |  med vol_20d = {q1_raw[6]:.4f}")
        print(f"    avg |pct_chg| = {q1_raw[7]:.4f}")
        print(f"  Rank 11-20 comparison (n={q1_compare[5]}):")
        print(f"    avg oracle label = {q1_compare[0]:.5f}")
        print(f"    avg amount = {q1_compare[1]:.0f}  |  med amount = {q1_compare[2]:.0f}")
        print(f"    avg vol_20d = {q1_compare[3]:.4f}  |  med vol_20d = {q1_compare[4]:.4f}")
        print(f"  Full-sample medians:")
        print(f"    med amount = {q1_ref[0]:.0f}  med amount_20d = {q1_ref[1]:.0f}  med vol_20d = {q1_ref[2]:.4f}")

        # Check by year
        print("\n  By year (Top10 avg oracle label):")
        years = con.execute("""
            SELECT
                LEFT(signal_date, 4) AS yr,
                AVG(oracle_label) AS avg_label,
                COUNT(*) AS n
            FROM top10_stocks
            GROUP BY yr ORDER BY yr
        """).fetchall()
        for yr, label, n in years:
            bar = "█" * max(0, min(20, int(abs(label) * 500))) if label < 0 else ""
            print(f"    {int(yr)}: avg_label={label:+.5f}  n={int(n)}  {bar}")

        # ═══════════════════════════════════════════
        # Q2: Tail depth — Top10 vs Top20 vs Top50 vs D1
        # ═══════════════════════════════════════════
        print("\n" + "=" * 60)
        print("Q2: Tail depth — where does inversion stop?")
        print("=" * 60)

        for k in [10, 20, 50, 100]:
            tb = con.execute(f"""
                WITH ranked AS (
                    SELECT oracle_label,
                        ROW_NUMBER() OVER (PARTITION BY signal_date ORDER BY nr_score DESC, instrument ASC) AS rn_d,
                        ROW_NUMBER() OVER (PARTITION BY signal_date ORDER BY nr_score ASC, instrument ASC) AS rn_a
                    FROM nr_base
                )
                SELECT
                    AVG(CASE WHEN rn_d <= {k} THEN oracle_label END) AS top_label,
                    AVG(CASE WHEN rn_a <= {k} THEN oracle_label END) AS bot_label
                FROM ranked
            """).fetchone()
            print(f"  Top{k}: avg_label={tb[0]:+.5f}  |  Bot{k}: avg_label={tb[1]:+.5f}  |  spread={tb[0]-tb[1]:+.5f}")

        # Decile 1 (top ~10% of stocks each day)
        d1 = con.execute("""
            WITH ranked AS (
                SELECT oracle_label,
                    NTILE(10) OVER (PARTITION BY signal_date ORDER BY nr_score DESC, instrument ASC) AS bucket
                FROM nr_base
            )
            SELECT AVG(oracle_label) FROM ranked WHERE bucket = 1
        """).fetchone()[0]
        print(f"  Decile 1 (top ~10%): avg_label={d1:+.5f}")

        # ═══════════════════════════════════════════
        # Q3: Simple tail handling — winsorize / exclude
        # ═══════════════════════════════════════════
        print("\n" + "=" * 60)
        print("Q3: Tail handling — winsorize / exclude extreme scores")
        print("=" * 60)

        # Original Top10 spread for reference
        orig = con.execute("""
            WITH ranked AS (
                SELECT oracle_label,
                    ROW_NUMBER() OVER (PARTITION BY signal_date ORDER BY nr_score DESC, instrument ASC) AS rn_d,
                    ROW_NUMBER() OVER (PARTITION BY signal_date ORDER BY nr_score ASC, instrument ASC) AS rn_a
                FROM nr_base
            )
            SELECT
                AVG(CASE WHEN rn_d <= 10 THEN oracle_label END),
                AVG(CASE WHEN rn_a <= 10 THEN oracle_label END)
            FROM ranked
        """).fetchone()
        print(f"  Original:      Top10={orig[0]:+.5f}  Bot10={orig[1]:+.5f}  spread={orig[0]-orig[1]:+.5f}")

        # Method 1: Winsorize — precompute daily percentile thresholds
        con.execute("""
            CREATE OR REPLACE VIEW nr_daily_pct AS
            SELECT
                signal_date,
                PERCENTILE_CONT(0.01) WITHIN GROUP (ORDER BY nr_score) AS p01,
                PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY nr_score) AS p99,
                PERCENTILE_CONT(0.98) WITHIN GROUP (ORDER BY nr_score) AS p98,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY nr_score) AS p95
            FROM nr_base
            GROUP BY signal_date
        """)

        con.execute("""
            CREATE OR REPLACE VIEW nr_winsor AS
            SELECT
                n.signal_date, n.instrument,
                CASE
                    WHEN n.nr_score < p.p01 THEN p.p01
                    WHEN n.nr_score > p.p99 THEN p.p99
                    ELSE n.nr_score
                END AS nr_score_winsor,
                n.oracle_label
            FROM nr_base n
            JOIN nr_daily_pct p ON n.signal_date = p.signal_date
        """)

        for method_name, join_clause, filter_clause in [
            ("winsor 1%/99%", "", "TRUE"),
            ("exclude top 1%", "JOIN nr_daily_pct p ON n.signal_date = p.signal_date", "n.nr_score < p.p99"),
            ("exclude top 2%", "JOIN nr_daily_pct p ON n.signal_date = p.signal_date", "n.nr_score < p.p98"),
            ("exclude top 5%", "JOIN nr_daily_pct p ON n.signal_date = p.signal_date", "n.nr_score < p.p95"),
        ]:
            view_name = "nr_" + method_name.replace("/", "_").replace(" ", "_").replace("%", "pct")
            con.execute(f"DROP VIEW IF EXISTS {view_name}")

            if method_name.startswith("winsor"):
                con.execute(f"""
                    CREATE OR REPLACE VIEW {view_name} AS
                    SELECT signal_date, instrument, nr_score_winsor AS score, oracle_label
                    FROM nr_winsor
                """)
            else:
                con.execute(f"""
                    CREATE OR REPLACE VIEW {view_name} AS
                    SELECT n.signal_date, n.instrument, n.nr_score AS score, n.oracle_label
                    FROM nr_base n
                    {join_clause}
                    WHERE {filter_clause}
                """)

            tb = con.execute(f"""
                WITH ranked AS (
                    SELECT oracle_label,
                        ROW_NUMBER() OVER (PARTITION BY signal_date ORDER BY score DESC, instrument ASC) AS rn_d,
                        ROW_NUMBER() OVER (PARTITION BY signal_date ORDER BY score ASC, instrument ASC) AS rn_a
                    FROM {view_name}
                )
                SELECT
                    AVG(CASE WHEN rn_d <= 10 THEN oracle_label END),
                    AVG(CASE WHEN rn_a <= 10 THEN oracle_label END)
                FROM ranked
            """).fetchone()

            ic = con.execute(f"""
                WITH daily AS (
                    SELECT signal_date, CORR(score, oracle_label) AS daily_ic
                    FROM {view_name}
                    GROUP BY signal_date HAVING COUNT(*) >= 20
                )
                SELECT MEDIAN(daily_ic) FROM daily
            """).fetchone()[0]

            spread = tb[0] - tb[1] if tb[0] is not None and tb[1] is not None else None
            spread_str = f"{spread:+.5f}" if spread is not None else "null"
            ic_str = f"{ic:.4f}" if ic is not None else "null"
            print(f"  {method_name:20s}: Top10={tb[0]:+.5f}  Bot10={tb[1]:+.5f}  spread={spread_str}  median_IC={ic_str}")

    finally:
        con.close()

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    main()
