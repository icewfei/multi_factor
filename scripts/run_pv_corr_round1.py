#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Run pv-corr family engineering round 1: compute cord ensemble and delta features,
then measure IC against oracle label. Strictly follows preregistration.

Candidates: pv_corr_ensemble_v1, pv_corr_delta_v1
Baseline: alpha158_cord30 (price_volume_single_signal_alpha158_cord30_v1)
"""

from __future__ import annotations

import json
import random
from datetime import datetime
from pathlib import Path

import duckdb

ROOT = Path("/Users/wy/MiscProject/multi_factor")
ARTIFACTS_RUN_STATE = ROOT / "artifacts" / "run_state"
ARTIFACTS_FIXED = ROOT / "artifacts" / "fixed_test"
REGISTRY = ROOT / "artifacts" / "research_registry"

# --- Config from preregistration ---
SNAPSHOT_ID = "warehouse_20260429_trainval_20211231"
SNAPSHOT_PATH = Path("/Users/wy/MiscProject/tushare_data/parquet_duckdb/data/snapshots/warehouse_20260429_trainval_20211231")
WAREHOUSE_DB = SNAPSHOT_PATH / "duckdb" / "warehouse.duckdb"
BASE_RUN = ARTIFACTS_RUN_STATE / "confirmatory_baseline_v1_trainval_20260429"
BASELINE_CORD30_RUN = ARTIFACTS_RUN_STATE / "confirmatory_cord30_trainval_20260429"

N_BOOTSTRAP = 10_000
SEED = 42

# Oracle label column
LABEL_COL = "label_5d_next_open_close"


def sql_quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def sql_path(p: Path) -> str:
    return sql_quote(p.resolve().as_posix())


def bootstrap_ci(values: list[float], n_bootstrap: int = N_BOOTSTRAP, seed: int = SEED) -> dict:
    rng = random.Random(seed)
    n = len(values)
    if n == 0:
        return {"median_lo": None, "median_hi": None, "mean_lo": None, "mean_hi": None}
    meds: list[float] = []
    means: list[float] = []
    for _ in range(n_bootstrap):
        sample = [values[rng.randint(0, n - 1)] for _ in range(n)]
        sample.sort()
        m = len(sample)
        med = sample[m // 2] if m % 2 == 1 else (sample[m // 2 - 1] + sample[m // 2]) / 2.0
        meds.append(med)
        means.append(sum(sample) / m)
    meds.sort()
    means.sort()
    lo = int(n_bootstrap * 0.025)
    hi = int(n_bootstrap * 0.975)
    return {"median_lo": meds[lo], "median_hi": meds[hi], "mean_lo": means[lo], "mean_hi": means[hi]}


def compute_ic_metrics(daily_ic_series: list[float]) -> dict:
    """Compute IC summary + bootstrap CI from daily IC list."""
    n = len(daily_ic_series)
    if n == 0:
        return {
            "full_sample_corr": None, "mean_daily_ic": None, "median_daily_ic": None,
            "std_daily_ic": None, "n_days": 0, "positive_daily_share": None,
            "median_ci_low": None, "median_ci_high": None,
            "mean_ci_low": None, "mean_ci_high": None,
        }
    s = sorted(daily_ic_series)
    mid = n // 2
    med = s[mid] if n % 2 == 1 else (s[mid - 1] + s[mid]) / 2.0
    avg = sum(daily_ic_series) / n
    var = sum((x - avg) ** 2 for x in daily_ic_series) / (n - 1)
    std = var ** 0.5
    pos = sum(1 for x in daily_ic_series if x > 0) / n
    ci = bootstrap_ci(daily_ic_series)
    return {
        "full_sample_corr": None,  # filled later
        "mean_daily_ic": avg,
        "median_daily_ic": med,
        "std_daily_ic": std,
        "n_days": n,
        "positive_daily_share": pos,
        "median_ci_low": ci["median_lo"],
        "median_ci_high": ci["median_hi"],
        "mean_ci_low": ci["mean_lo"],
        "mean_ci_high": ci["mean_hi"],
    }


def main() -> None:
    if not WAREHOUSE_DB.exists():
        raise FileNotFoundError(f"Warehouse DB not found: {WAREHOUSE_DB}")

    label_path = BASE_RUN / "project_label_panel.parquet"
    sample_path = BASE_RUN / "project_sample_panel.parquet"
    cord30_score_path = BASELINE_CORD30_RUN / "model_scores_D0.parquet"
    for p in (label_path, sample_path, cord30_score_path):
        if not p.exists():
            raise FileNotFoundError(f"Missing: {p}")

    con = duckdb.connect()

    try:
        # ── Attach warehouse and load panels ──
        con.execute(f"ATTACH {sql_path(WAREHOUSE_DB)} AS wh (READ_ONLY)")
        con.execute(f"CREATE OR REPLACE VIEW labels AS SELECT * FROM read_parquet({sql_path(label_path)})")
        con.execute(f"CREATE OR REPLACE VIEW samples AS SELECT * FROM read_parquet({sql_path(sample_path)})")
        con.execute(f"CREATE OR REPLACE VIEW cord30_score AS SELECT * FROM read_parquet({sql_path(cord30_score_path)})")

        # ── Build cord features from bar data ──
        con.execute(f"""
            CREATE OR REPLACE VIEW bar_enriched AS
            SELECT
                b.trade_date,
                b.ts_code AS instrument,
                b.adj_close,
                b.vol,
                b.adj_close / NULLIF(LAG(b.adj_close, 1) OVER (
                    PARTITION BY b.ts_code ORDER BY b.trade_date
                ), 0.0) AS close_rel1,
                LN(b.vol / NULLIF(LAG(b.vol, 1) OVER (
                    PARTITION BY b.ts_code ORDER BY b.trade_date
                ), 0.0) + 1.0) AS log_volume_rel1
            FROM wh.serving.vw_bars_daily b
            WHERE b.snapshot_id = {sql_quote(SNAPSHOT_ID)}
        """)

        # Compute cord at 4 windows, guarded by STDDEV > epsilon
        eps = 2e-05
        con.execute(f"""
            CREATE OR REPLACE VIEW bar_cord AS
            SELECT
                instrument,
                trade_date AS signal_date,
                CASE WHEN COALESCE(STDDEV_SAMP(close_rel1) OVER w10, 0.0) > {eps}
                      AND COALESCE(STDDEV_SAMP(log_volume_rel1) OVER w10, 0.0) > {eps}
                     THEN CORR(close_rel1, log_volume_rel1) OVER w10 END AS cord_10d,
                CASE WHEN COALESCE(STDDEV_SAMP(close_rel1) OVER w20, 0.0) > {eps}
                      AND COALESCE(STDDEV_SAMP(log_volume_rel1) OVER w20, 0.0) > {eps}
                     THEN CORR(close_rel1, log_volume_rel1) OVER w20 END AS cord_20d,
                CASE WHEN COALESCE(STDDEV_SAMP(close_rel1) OVER w30, 0.0) > {eps}
                      AND COALESCE(STDDEV_SAMP(log_volume_rel1) OVER w30, 0.0) > {eps}
                     THEN CORR(close_rel1, log_volume_rel1) OVER w30 END AS cord_30d,
                CASE WHEN COALESCE(STDDEV_SAMP(close_rel1) OVER w60, 0.0) > {eps}
                      AND COALESCE(STDDEV_SAMP(log_volume_rel1) OVER w60, 0.0) > {eps}
                     THEN CORR(close_rel1, log_volume_rel1) OVER w60 END AS cord_60d
            FROM bar_enriched
            WINDOW
                w10 AS (PARTITION BY instrument ORDER BY trade_date ROWS BETWEEN 9  PRECEDING AND CURRENT ROW),
                w20 AS (PARTITION BY instrument ORDER BY trade_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW),
                w30 AS (PARTITION BY instrument ORDER BY trade_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW),
                w60 AS (PARTITION BY instrument ORDER BY trade_date ROWS BETWEEN 59 PRECEDING AND CURRENT ROW)
        """)

        # ── Join to sample panel, rank-normalize, create candidates ──
        con.execute("""
            CREATE OR REPLACE VIEW feature_frame AS
            SELECT
                s.snapshot_id,
                s.instrument,
                s.signal_date,
                s.ranking_eligible_D0,
                c.cord_10d,
                c.cord_20d,
                c.cord_30d,
                c.cord_60d
            FROM samples s
            LEFT JOIN bar_cord c
              ON s.instrument = c.instrument
             AND s.signal_date = c.signal_date
        """)

        # Rank-normalize each cord window cross-sectionally.
        # Use ORDER BY cord DESC: lower cord → higher rank → higher score.
        # This matches the confirmatory cord30 pipeline convention (ranking_direction DESC),
        # which produces positive IC with oracle label.
        con.execute("""
            CREATE OR REPLACE VIEW ranked_features AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                ranking_eligible_D0,
                cord_10d, cord_20d, cord_30d, cord_60d,
                PERCENT_RANK() OVER (PARTITION BY signal_date ORDER BY cord_10d DESC)  AS cord_rank_10d,
                PERCENT_RANK() OVER (PARTITION BY signal_date ORDER BY cord_20d DESC)  AS cord_rank_20d,
                PERCENT_RANK() OVER (PARTITION BY signal_date ORDER BY cord_30d DESC)  AS cord_rank_30d,
                PERCENT_RANK() OVER (PARTITION BY signal_date ORDER BY cord_60d DESC)  AS cord_rank_60d
            FROM feature_frame
            WHERE ranking_eligible_D0
        """)

        # Create candidate scores
        con.execute("""
            CREATE OR REPLACE VIEW candidate_scores AS
            SELECT
                snapshot_id, instrument, signal_date,
                ranking_eligible_D0,
                -- A: ensemble
                (COALESCE(cord_rank_10d, 0.5) + COALESCE(cord_rank_30d, 0.5) + COALESCE(cord_rank_60d, 0.5)) / 3.0 AS pv_corr_ensemble_v1,
                -- B: delta
                (COALESCE(cord_rank_10d - cord_rank_30d, 0.0) + COALESCE(cord_rank_20d - cord_rank_60d, 0.0)) / 2.0 AS pv_corr_delta_v1,
                -- raw cord_30d rank for reference
                cord_rank_30d AS cord30_rank_raw
            FROM ranked_features
        """)

        # ── IC computation function ──
        candidate_names = ["pv_corr_ensemble_v1", "pv_corr_delta_v1"]

        results: dict[str, dict] = {}

        for cand in candidate_names:
            print(f"\n=== Computing IC for {cand} ===")

            # Full-sample IC
            full_ic = con.execute(f"""
                SELECT CORR(c.{cand}, l.{LABEL_COL})
                FROM candidate_scores c
                LEFT JOIN labels l
                  ON c.snapshot_id = l.snapshot_id
                 AND c.instrument = l.instrument
                 AND c.signal_date = l.signal_date
                WHERE c.{cand} IS NOT NULL
                  AND l.{LABEL_COL} IS NOT NULL
            """).fetchone()[0]

            # Daily IC series
            daily_rows = con.execute(f"""
                WITH daily AS (
                    SELECT
                        c.signal_date,
                        CORR(c.{cand}, l.{LABEL_COL}) AS daily_ic
                    FROM candidate_scores c
                    LEFT JOIN labels l
                      ON c.snapshot_id = l.snapshot_id
                     AND c.instrument = l.instrument
                     AND c.signal_date = l.signal_date
                    WHERE c.{cand} IS NOT NULL
                      AND l.{LABEL_COL} IS NOT NULL
                    GROUP BY c.signal_date
                    HAVING COUNT(*) >= 20
                )
                SELECT daily_ic FROM daily ORDER BY signal_date
            """).fetchall()

            daily_ics = [float(r[0]) for r in daily_rows if r[0] is not None]
            daily_ics = [x for x in daily_ics if not (x != x)]  # filter NaN
            metrics = compute_ic_metrics(daily_ics)
            metrics["full_sample_corr"] = float(full_ic) if full_ic is not None else None

            # Top10-Bot10 label spread
            top_bot = con.execute(f"""
                WITH ranked AS (
                    SELECT
                        c.signal_date,
                        l.{LABEL_COL},
                        ROW_NUMBER() OVER (PARTITION BY c.signal_date ORDER BY c.{cand} DESC, c.instrument ASC) AS rn_desc,
                        ROW_NUMBER() OVER (PARTITION BY c.signal_date ORDER BY c.{cand} ASC, c.instrument ASC) AS rn_asc
                    FROM candidate_scores c
                    LEFT JOIN labels l
                      ON c.snapshot_id = l.snapshot_id
                     AND c.instrument = l.instrument
                     AND c.signal_date = l.signal_date
                    WHERE c.{cand} IS NOT NULL AND l.{LABEL_COL} IS NOT NULL
                )
                SELECT
                    AVG(CASE WHEN rn_desc <= 10 THEN {LABEL_COL} END) AS top10,
                    AVG(CASE WHEN rn_asc <= 10 THEN {LABEL_COL} END) AS bot10
                FROM ranked
            """).fetchone()

            t10 = float(top_bot[0]) if top_bot[0] is not None else None
            tbot = float(top_bot[1]) if top_bot[1] is not None else None

            metrics["top10_bot10_spread"] = (t10 - tbot) if t10 is not None and tbot is not None else None
            metrics["top10_avg_label"] = t10
            metrics["bottom10_avg_label"] = tbot

            # Decile monotonicity
            deciles = con.execute(f"""
                WITH ranked AS (
                    SELECT
                        c.signal_date,
                        l.{LABEL_COL},
                        NTILE(10) OVER (PARTITION BY c.signal_date ORDER BY c.{cand} DESC, c.instrument ASC) AS bucket
                    FROM candidate_scores c
                    LEFT JOIN labels l
                      ON c.snapshot_id = l.snapshot_id
                     AND c.instrument = l.instrument
                     AND c.signal_date = l.signal_date
                    WHERE c.{cand} IS NOT NULL AND l.{LABEL_COL} IS NOT NULL
                )
                SELECT bucket, AVG({LABEL_COL}) FROM ranked GROUP BY bucket ORDER BY bucket
            """).fetchall()
            metrics["decile_labels"] = {str(int(b)): float(v) if v is not None else None for b, v in deciles}

            results[cand] = metrics
            print(f"  Full IC: {metrics['full_sample_corr']:.6f}")
            print(f"  Mean daily IC: {metrics['mean_daily_ic']:.6f}")
            print(f"  Median daily IC: {metrics['median_daily_ic']:.6f}")
            print(f"  CI: [{metrics['median_ci_low']:.6f}, {metrics['median_ci_high']:.6f}]")
            print(f"  Top10-Bot10 spread: {metrics['top10_bot10_spread']:.6f}")
            print(f"  N days: {metrics['n_days']}")

        # ── Baseline: cord30 from existing confirmatory run ──
        print("\n=== Computing baseline cord30 IC ===")
        # cord30 baseline from confirmatory run via model_score_D0 column
        con.execute(f"""
            CREATE OR REPLACE VIEW baseline_cord30 AS
            SELECT
                s.snapshot_id,
                s.instrument,
                s.signal_date,
                s.ranking_eligible_D0,
                c.model_score_D0 AS cord30_score
            FROM samples s
            LEFT JOIN cord30_score c
              ON s.snapshot_id = c.snapshot_id
             AND s.instrument = c.instrument
             AND s.signal_date = c.signal_date
            WHERE c.candidate_scheme_id = 'price_volume_single_signal_alpha158_cord30_v1'
        """)

        daily_baseline = con.execute(f"""
            WITH daily AS (
                SELECT
                    b.signal_date,
                    CORR(b.cord30_score, l.{LABEL_COL}) AS daily_ic
                FROM baseline_cord30 b
                LEFT JOIN labels l
                  ON b.snapshot_id = l.snapshot_id
                 AND b.instrument = l.instrument
                 AND b.signal_date = l.signal_date
                WHERE b.ranking_eligible_D0
                  AND b.cord30_score IS NOT NULL
                  AND l.{LABEL_COL} IS NOT NULL
                GROUP BY b.signal_date
                HAVING COUNT(*) >= 20
            )
            SELECT daily_ic FROM daily ORDER BY signal_date
        """).fetchall()

        baseline_daily = [float(r[0]) for r in daily_baseline if r[0] is not None]
        baseline_daily = [x for x in baseline_daily if not (x != x)]  # filter NaN
        baseline_metrics = compute_ic_metrics(baseline_daily)

        full_baseline = con.execute(f"""
            SELECT CORR(b.cord30_score, l.{LABEL_COL})
            FROM baseline_cord30 b
            LEFT JOIN labels l
              ON b.snapshot_id = l.snapshot_id
             AND b.instrument = l.instrument
             AND b.signal_date = l.signal_date
            WHERE b.ranking_eligible_D0
              AND b.cord30_score IS NOT NULL
              AND l.{LABEL_COL} IS NOT NULL
        """).fetchone()[0]
        baseline_metrics["full_sample_corr"] = float(full_baseline) if full_baseline is not None else None

        print(f"  cord30 Full IC: {baseline_metrics['full_sample_corr']:.6f}")
        print(f"  cord30 Mean daily IC: {baseline_metrics['mean_daily_ic']:.6f}")
        print(f"  cord30 Median daily IC: {baseline_metrics['median_daily_ic']:.6f}")
        print(f"  cord30 CI: [{baseline_metrics['median_ci_low']:.6f}, {baseline_metrics['median_ci_high']:.6f}]")

        # ── Compute deltas vs baseline ──
        for cand in candidate_names:
            delta = (results[cand]["median_daily_ic"] or 0) - (baseline_metrics["median_daily_ic"] or 0)
            results[cand]["median_ic_delta_vs_cord30"] = delta

            # Tier checks
            med = results[cand]["median_daily_ic"]
            ci_lo = results[cand]["median_ci_low"]
            ci_hi = results[cand]["median_ci_high"]
            tier1 = (med is not None and ci_lo is not None and ci_hi is not None
                     and med >= 0.040 and ci_lo > 0)
            tier2 = delta is not None and delta >= 0.005
            results[cand]["tier1_pass"] = tier1
            results[cand]["tier2_pass"] = tier2
            print(f"\n  {cand}: Tier1={'PASS' if tier1 else 'FAIL'}, Tier2={'PASS' if tier2 else 'FAIL'} (delta={delta:+.6f})")

    finally:
        con.close()

    # ── Write output ──
    as_of_date = datetime.now().strftime("%Y%m%d")
    round_dir = ARTIFACTS_FIXED / "pv_corr_round1"
    round_dir.mkdir(parents=True, exist_ok=True)

    output = {
        "as_of_date": as_of_date,
        "research_round_id": "rr_exploratory_pv_corr_family_engineering_20260502",
        "baseline": {
            "candidate_scheme_id": "price_volume_single_signal_alpha158_cord30_v1",
            "median_daily_ic": baseline_metrics["median_daily_ic"],
            "median_ci_low": baseline_metrics["median_ci_low"],
            "median_ci_high": baseline_metrics["median_ci_high"],
            "mean_daily_ic": baseline_metrics["mean_daily_ic"],
            "n_days": baseline_metrics["n_days"],
        },
        "candidates": {
            cand: {
                "full_sample_corr": results[cand]["full_sample_corr"],
                "mean_daily_ic": results[cand]["mean_daily_ic"],
                "median_daily_ic": results[cand]["median_daily_ic"],
                "std_daily_ic": results[cand]["std_daily_ic"],
                "n_days": results[cand]["n_days"],
                "positive_daily_share": results[cand]["positive_daily_share"],
                "median_ci_low": results[cand]["median_ci_low"],
                "median_ci_high": results[cand]["median_ci_high"],
                "mean_ci_low": results[cand]["mean_ci_low"],
                "mean_ci_high": results[cand]["mean_ci_high"],
                "median_ic_delta_vs_cord30": results[cand]["median_ic_delta_vs_cord30"],
                "top10_bot10_spread": results[cand]["top10_bot10_spread"],
                "top10_avg_label": results[cand]["top10_avg_label"],
                "bottom10_avg_label": results[cand]["bottom10_avg_label"],
                "decile_labels": results[cand]["decile_labels"],
                "tier1_pass": results[cand]["tier1_pass"],
                "tier2_pass": results[cand]["tier2_pass"],
            }
            for cand in candidate_names
        },
        "success_rules": {
            "tier_1": "median_daily_ic >= 0.040 AND 95% CI excludes zero",
            "tier_2": "median_ic_delta_vs_cord30 >= +0.005",
        },
    }

    # Family verdict
    any_tier1_tier2 = any(r["tier1_pass"] and r["tier2_pass"] for r in results.values())
    any_pass = any(r["tier1_pass"] or r["tier2_pass"] for r in results.values())
    if any_tier1_tier2:
        verdict = "continue pv-corr feature engineering"
    else:
        verdict = "pv-corr family near saturation; reopen data acquisition discussion"
    output["family_verdict"] = verdict

    json_path = round_dir / f"pv_corr_round1_results_{as_of_date}.json"
    json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # ── Markdown report ──
    md = [
        f"# pv-corr Family Engineering Round 1 — Results ({as_of_date})",
        "",
        "## Baseline: alpha158_cord30",
        f"- Median daily IC: {baseline_metrics['median_daily_ic']:.6f}",
        f"- 95% CI: [{baseline_metrics['median_ci_low']:.6f}, {baseline_metrics['median_ci_high']:.6f}]",
        f"- Mean daily IC: {baseline_metrics['mean_daily_ic']:.6f}",
        f"- N days: {baseline_metrics['n_days']}",
        "",
        "## Candidate Results",
        "",
        "| Candidate | Full IC | Mean Daily IC | Median Daily IC [95% CI] | Std | N Days | Median Δ vs cord30 | Top10-Bot10 Spread | Tier 1 | Tier 2 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]

    for cand in candidate_names:
        r = results[cand]
        full = f"{r['full_sample_corr']:.6f}" if r['full_sample_corr'] is not None else "null"
        mean_ = f"{r['mean_daily_ic']:.6f}" if r['mean_daily_ic'] is not None else "null"
        med = f"{r['median_daily_ic']:.6f}" if r['median_daily_ic'] is not None else "null"
        ci = f"[{r['median_ci_low']:.6f}, {r['median_ci_high']:.6f}]" if r['median_ci_low'] is not None else "null"
        std = f"{r['std_daily_ic']:.6f}" if r['std_daily_ic'] is not None else "null"
        delta = f"{r['median_ic_delta_vs_cord30']:+.6f}" if r['median_ic_delta_vs_cord30'] is not None else "null"
        spread = f"{r['top10_bot10_spread']:.6f}" if r['top10_bot10_spread'] is not None else "null"
        t1 = "PASS" if r['tier1_pass'] else "FAIL"
        t2 = "PASS" if r['tier2_pass'] else "FAIL"
        md.append(f"| {cand} | {full} | {mean_} | {med} {ci} | {std} | {r['n_days']} | {delta} | {spread} | **{t1}** | **{t2}** |")

    md.extend([
        "",
        "## Decile Monotonicity",
        "",
        "| Candidate | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ])
    for cand in candidate_names:
        dec = results[cand]["decile_labels"]
        buckets = sorted(dec.keys(), key=int)
        vals = " | ".join(f"{dec[b]:.6f}" if dec[b] is not None else "null" for b in buckets)
        md.append(f"| {cand} | {vals} |")

    md.extend([
        "",
        "## Success Criteria",
        "",
        "| Rule | Definition |",
        "|---|---|",
        "| Tier 1 | median daily IC >= 0.040, 95% CI excludes zero |",
        "| Tier 2 | median IC delta >= +0.005 over alpha158_cord30 |",
        "",
        "## Family Verdict",
        "",
        f"**{verdict}**",
        "",
        f"Generated: {as_of_date}",
    ])

    md_path = round_dir / f"pv_corr_round1_results_{as_of_date}.md"
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"Family Verdict: {verdict}")
    print(f"JSON: {json_path}")
    print(f"MD:   {md_path}")


if __name__ == "__main__":
    main()
