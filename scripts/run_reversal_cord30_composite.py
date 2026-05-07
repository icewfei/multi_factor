#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Reversal + Cord30 minimal composite: p98 tail-handled reversal + cord30 equal-weight rank composite.
Single candidate, strictly per preregistration rr_exploratory_reversal_cord30_composite_20260502.
"""

from __future__ import annotations

import json
import random
from datetime import datetime
from pathlib import Path

import duckdb

ROOT = Path("/Users/wy/MiscProject/multi_factor")
BASE_RUN = ROOT / "artifacts" / "run_state" / "confirmatory_baseline_v1_trainval_20260429"
REVERSAL_RUN = ROOT / "artifacts" / "run_state" / "exploratory_cross_horizon_c1_reversal_only"
CORD30_RUN = ROOT / "artifacts" / "run_state" / "confirmatory_cord30_trainval_20260429"
OUT_DIR = ROOT / "artifacts" / "fixed_test" / "reversal_cord30_composite"

N_BOOTSTRAP = 10_000
SEED = 42
LABEL = "label_5d_next_open_close"

PRIMARY_IC = 0.0459
PRIMARY_SPREAD = 0.0049
CORD30_IC = 0.0325
CORD30_SPREAD = 0.0098


def sql_quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def sql_path(p: Path) -> str:
    return sql_quote(p.resolve().as_posix())


def bootstrap_ci(values: list[float]) -> dict:
    rng = random.Random(SEED)
    n = len(values)
    if n == 0:
        return {"med_lo": None, "med_hi": None, "mean_lo": None, "mean_hi": None}
    meds, means = [], []
    for _ in range(N_BOOTSTRAP):
        s = [values[rng.randint(0, n - 1)] for _ in range(n)]
        s.sort()
        m = len(s)
        med = s[m // 2] if m % 2 == 1 else (s[m // 2 - 1] + s[m // 2]) / 2.0
        meds.append(med)
        means.append(sum(s) / m)
    meds.sort()
    means.sort()
    lo = int(N_BOOTSTRAP * 0.025)
    hi = int(N_BOOTSTRAP * 0.975)
    return {"med_lo": meds[lo], "med_hi": meds[hi], "mean_lo": means[lo], "mean_hi": means[hi]}


def compute_metrics(con, view_name: str) -> dict:
    full_ic = con.execute(f"SELECT CORR(score, oracle_label) FROM {view_name}").fetchone()[0]

    daily_rows = con.execute(f"""
        SELECT signal_date, CORR(score, oracle_label) AS daily_ic
        FROM {view_name}
        GROUP BY signal_date HAVING COUNT(*) >= 20
        ORDER BY signal_date
    """).fetchall()

    d = [float(r[1]) for r in daily_rows if r[1] is not None]
    d = [x for x in d if not (x != x)]
    n = len(d)
    s = sorted(d)
    mid = n // 2
    med = s[mid] if n % 2 == 1 else (s[mid - 1] + s[mid]) / 2.0
    avg = sum(d) / n
    var = sum((x - avg) ** 2 for x in d) / (n - 1)
    std = var ** 0.5
    pos = sum(1 for x in d if x > 0) / n
    ci = bootstrap_ci(d)

    tb = con.execute(f"""
        WITH ranked AS (
            SELECT oracle_label,
                ROW_NUMBER() OVER (PARTITION BY signal_date ORDER BY score DESC, instrument ASC) AS rn_d,
                ROW_NUMBER() OVER (PARTITION BY signal_date ORDER BY score ASC, instrument ASC) AS rn_a
            FROM {view_name}
        )
        SELECT AVG(CASE WHEN rn_d <= 10 THEN oracle_label END),
               AVG(CASE WHEN rn_a <= 10 THEN oracle_label END)
        FROM ranked
    """).fetchone()
    t10 = float(tb[0]) if tb[0] is not None else None
    b10 = float(tb[1]) if tb[1] is not None else None

    dec = con.execute(f"""
        WITH ranked AS (
            SELECT oracle_label,
                NTILE(10) OVER (PARTITION BY signal_date ORDER BY score DESC, instrument ASC) AS bucket
            FROM {view_name}
        )
        SELECT bucket, AVG(oracle_label) FROM ranked GROUP BY bucket ORDER BY bucket
    """).fetchall()
    decile_map = {str(int(b)): float(v) if v is not None else None for b, v in dec}

    return {
        "full_sample_corr": float(full_ic) if full_ic is not None else None,
        "mean_daily_ic": avg,
        "median_daily_ic": med,
        "std_daily_ic": std,
        "n_days": n,
        "positive_daily_share": pos,
        "median_ci_low": ci["med_lo"],
        "median_ci_high": ci["med_hi"],
        "mean_ci_low": ci["mean_lo"],
        "mean_ci_high": ci["mean_hi"],
        "top10_avg_label": t10,
        "bottom10_avg_label": b10,
        "top10_bot10_spread": (t10 - b10) if t10 is not None and b10 is not None else None,
        "decile_labels": decile_map,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    label_path = BASE_RUN / "project_label_panel.parquet"
    sample_path = BASE_RUN / "project_sample_panel.parquet"
    rev_path = REVERSAL_RUN / "model_scores_D0.parquet"
    cord30_path = CORD30_RUN / "model_scores_D0.parquet"
    for p in (label_path, sample_path, rev_path, cord30_path):
        if not p.exists():
            raise FileNotFoundError(f"Missing: {p}")

    con = duckdb.connect()
    try:
        # ── Load panels ──
        con.execute(f"CREATE VIEW labels AS SELECT * FROM read_parquet({sql_path(label_path)})")
        con.execute(f"CREATE VIEW samples AS SELECT * FROM read_parquet({sql_path(sample_path)})")
        con.execute(f"CREATE VIEW rev AS SELECT * FROM read_parquet({sql_path(rev_path)})")
        con.execute(f"CREATE VIEW cord30_scores AS SELECT * FROM read_parquet({sql_path(cord30_path)})")

        # ── p98 tail-handled reversal (from tail-handling round) ──
        con.execute(f"""
            CREATE OR REPLACE VIEW nr_raw AS
            SELECT
                s.instrument, s.signal_date,
                -1.0 * r.model_score_D0 AS nr_score,
                l.{LABEL} AS oracle_label
            FROM samples s
            LEFT JOIN rev r ON s.snapshot_id=r.snapshot_id AND s.instrument=r.instrument AND s.signal_date=r.signal_date
            LEFT JOIN labels l ON s.snapshot_id=l.snapshot_id AND s.instrument=l.instrument AND s.signal_date=l.signal_date
            WHERE s.ranking_eligible_D0 AND r.model_score_D0 IS NOT NULL AND l.{LABEL} IS NOT NULL
        """)

        con.execute("""
            CREATE OR REPLACE VIEW nr_daily_p98 AS
            SELECT signal_date,
                PERCENTILE_CONT(0.98) WITHIN GROUP (ORDER BY nr_score) AS p98
            FROM nr_raw GROUP BY signal_date
        """)

        con.execute("""
            CREATE OR REPLACE VIEW nr_p98 AS
            SELECT n.instrument, n.signal_date, n.nr_score, n.oracle_label
            FROM nr_raw n
            JOIN nr_daily_p98 p ON n.signal_date = p.signal_date
            WHERE n.nr_score < p.p98
        """)

        # ── Cord30 scores ──
        con.execute(f"""
            CREATE OR REPLACE VIEW cord30_base AS
            SELECT
                s.instrument, s.signal_date,
                c.model_score_D0 AS cord30_score,
                l.{LABEL} AS oracle_label
            FROM samples s
            LEFT JOIN cord30_scores c
              ON s.snapshot_id=c.snapshot_id AND s.instrument=c.instrument AND s.signal_date=c.signal_date
              AND c.candidate_scheme_id='price_volume_single_signal_alpha158_cord30_v1'
            LEFT JOIN labels l
              ON s.snapshot_id=l.snapshot_id AND s.instrument=l.instrument AND s.signal_date=l.signal_date
            WHERE s.ranking_eligible_D0 AND c.model_score_D0 IS NOT NULL AND l.{LABEL} IS NOT NULL
        """)

        # ── Composite: equal-weight rank average ──
        con.execute("""
            CREATE OR REPLACE VIEW composite_base AS
            SELECT
                n.instrument,
                n.signal_date,
                n.oracle_label,
                PERCENT_RANK() OVER (PARTITION BY n.signal_date ORDER BY n.nr_score ASC) AS rev_rank,
                PERCENT_RANK() OVER (PARTITION BY n.signal_date ORDER BY c.cord30_score ASC) AS cord30_rank
            FROM nr_p98 n
            JOIN cord30_base c
              ON n.instrument = c.instrument AND n.signal_date = c.signal_date
        """)

        con.execute("""
            CREATE OR REPLACE VIEW composite_score AS
            SELECT
                instrument, signal_date, oracle_label,
                0.5 * rev_rank + 0.5 * cord30_rank AS score
            FROM composite_base
        """)

        # ── Also compute standalone baselines for direct comparison ──
        con.execute("""
            CREATE OR REPLACE VIEW nr_p98_standalone AS
            SELECT instrument, signal_date, oracle_label,
                PERCENT_RANK() OVER (PARTITION BY signal_date ORDER BY nr_score ASC) AS score
            FROM nr_p98
        """)

        con.execute("""
            CREATE OR REPLACE VIEW cord30_standalone AS
            SELECT instrument, signal_date, oracle_label,
                PERCENT_RANK() OVER (PARTITION BY signal_date ORDER BY cord30_score ASC) AS score
            FROM cord30_base
        """)

        # ── Compute metrics ──
        print("=== Computing metrics ===")
        m_composite = compute_metrics(con, "composite_score")
        m_p98 = compute_metrics(con, "nr_p98_standalone")
        m_cord30 = compute_metrics(con, "cord30_standalone")

        # ── Cross-signal rank correlation ──
        cross_corr = con.execute("""
            SELECT CORR(rev_rank, cord30_rank) FROM composite_base
        """).fetchone()[0]
        print(f"  Cross-signal rank correlation (reversal vs cord30): {cross_corr:.4f}")

    finally:
        con.close()

    # ── Evaluate ──
    ic_pass_040 = m_composite["median_daily_ic"] is not None and m_composite["median_daily_ic"] >= 0.040
    ic_pass_p98 = m_composite["median_daily_ic"] is not None and m_composite["median_daily_ic"] > PRIMARY_IC
    top10_pass = m_composite["top10_avg_label"] is not None and m_composite["top10_avg_label"] > 0
    spread_pass = m_composite["top10_bot10_spread"] is not None and m_composite["top10_bot10_spread"] > PRIMARY_SPREAD
    all_pass = ic_pass_040 and ic_pass_p98 and top10_pass and spread_pass

    # ── Print ──
    print(f"\n{'='*70}")
    print(f"  Candidate: reversal_p98_cord30_ew_v1")
    print(f"{'='*70}")
    print(f"  Cross-signal rank corr:  {cross_corr:.4f}")
    print(f"  Full IC:                {m_composite['full_sample_corr']:.6f}")
    print(f"  Mean Daily IC:          {m_composite['mean_daily_ic']:.6f}  [{m_composite['mean_ci_low']:.6f}, {m_composite['mean_ci_high']:.6f}]")
    print(f"  Median Daily IC:        {m_composite['median_daily_ic']:.6f}  [{m_composite['median_ci_low']:.6f}, {m_composite['median_ci_high']:.6f}]")
    print(f"  Std Daily IC:           {m_composite['std_daily_ic']:.6f}")
    print(f"  N days:                 {m_composite['n_days']}")
    print(f"  Pos share:              {m_composite['positive_daily_share']:.4f}")
    print(f"  Top10 avg label:        {m_composite['top10_avg_label']:+.6f}")
    print(f"  Bot10 avg label:        {m_composite['bottom10_avg_label']:+.6f}")
    print(f"  Top10-Bot10 spread:     {m_composite['top10_bot10_spread']:+.6f}")
    print(f"  ---")
    print(f"  IC >= 0.040:            {'PASS' if ic_pass_040 else 'FAIL'} ({m_composite['median_daily_ic']:.4f})")
    print(f"  IC > p98 (0.0459):      {'PASS' if ic_pass_p98 else 'FAIL'} ({m_composite['median_daily_ic']:.4f} vs {PRIMARY_IC})")
    print(f"  Top10 > 0:              {'PASS' if top10_pass else 'FAIL'} ({m_composite['top10_avg_label']:+.5f})")
    print(f"  Spread > p98 (0.0049):  {'PASS' if spread_pass else 'FAIL'} ({m_composite['top10_bot10_spread']:+.5f} vs {PRIMARY_SPREAD})")
    print(f"  >>> OVERALL:            {'PASS' if all_pass else 'FAIL'} <<<")

    print(f"\n{'='*70}")
    print(f"  Baseline comparison")
    print(f"{'='*70}")
    for name, m, is_primary in [("p98 reversal (primary)", m_p98, True), ("cord30 (secondary)", m_cord30, False)]:
        tag = " ← PRIMARY" if is_primary else " (aspirational)"
        print(f"  {name}{tag}:")
        print(f"    IC={m['median_daily_ic']:.4f} [{m['median_ci_low']:.4f}, {m['median_ci_high']:.4f}]")
        print(f"    Top10={m['top10_avg_label']:+.5f}  spread={m['top10_bot10_spread']:+.5f}")

    print(f"\n{'='*70}")
    print(f"  Decile Monotonicity (D1=highest score)")
    print(f"{'='*70}")
    for name, m in [("composite", m_composite), ("p98_reversal", m_p98), ("cord30", m_cord30)]:
        dec = m["decile_labels"]
        buckets = sorted(dec.keys(), key=int)
        vals = "  ".join(f"D{b}:{dec[b]:+.5f}" for b in buckets)
        print(f"  {name:20s} {vals}")

    # ── Delta table ──
    print(f"\n{'='*70}")
    print(f"  Delta vs p98 reversal (primary baseline)")
    print(f"{'='*70}")
    ic_delta = (m_composite["median_daily_ic"] or 0) - (m_p98["median_daily_ic"] or 0)
    spread_delta = (m_composite["top10_bot10_spread"] or 0) - (m_p98["top10_bot10_spread"] or 0)
    top10_delta = (m_composite["top10_avg_label"] or 0) - (m_p98["top10_avg_label"] or 0)
    print(f"  Δ IC:      {ic_delta:+.6f}")
    print(f"  Δ spread:  {spread_delta:+.6f}")
    print(f"  Δ Top10:   {top10_delta:+.6f}")

    # ── Verdict ──
    print(f"\n{'='*70}")
    if all_pass:
        print(f"  VERDICT: PASS — composite exceeds p98 reversal on both IC and spread")
        print(f"  Next: composite as new baseline")
    else:
        reasons = []
        if not ic_pass_p98:
            reasons.append(f"IC ({m_composite['median_daily_ic']:.4f}) does not exceed p98 ({PRIMARY_IC})")
        if not spread_pass:
            reasons.append(f"spread ({m_composite['top10_bot10_spread']:+.5f}) does not exceed p98 ({PRIMARY_SPREAD})")
        print(f"  VERDICT: FAIL — {'; '.join(reasons)}")
        print(f"  Next: p98 reversal remains standalone baseline")

    # ── Write JSON ──
    as_of_date = datetime.now().strftime("%Y%m%d")
    output = {
        "as_of_date": as_of_date,
        "research_round_id": "rr_exploratory_reversal_cord30_composite_20260502",
        "cross_signal_rank_corr": float(cross_corr) if cross_corr is not None else None,
        "primary_baseline": {
            "name": "p98 tail-handled reversal",
            "median_daily_ic": m_p98["median_daily_ic"],
            "median_ci": [m_p98["median_ci_low"], m_p98["median_ci_high"]],
            "top10_avg_label": m_p98["top10_avg_label"],
            "top10_bot10_spread": m_p98["top10_bot10_spread"],
            "target_ic": PRIMARY_IC,
            "target_spread": PRIMARY_SPREAD,
        },
        "secondary_reference": {
            "name": "cord30",
            "median_daily_ic": m_cord30["median_daily_ic"],
            "median_ci": [m_cord30["median_ci_low"], m_cord30["median_ci_high"]],
            "top10_avg_label": m_cord30["top10_avg_label"],
            "top10_bot10_spread": m_cord30["top10_bot10_spread"],
            "aspirational_spread": CORD30_SPREAD,
        },
        "candidate": {
            "candidate_scheme_id": "reversal_p98_cord30_ew_v1",
            "metrics": m_composite,
            "deltas_vs_primary": {
                "delta_median_ic": ic_delta,
                "delta_spread": spread_delta,
                "delta_top10_label": top10_delta,
            },
            "evaluation": {
                "ic_ge_0040": ic_pass_040,
                "ic_gt_p98": ic_pass_p98,
                "top10_gt_0": top10_pass,
                "spread_gt_p98": spread_pass,
                "all_pass": all_pass,
            },
        },
        "verdict": "pass" if all_pass else "fail",
    }
    json_path = OUT_DIR / f"reversal_cord30_composite_results_{as_of_date}.json"
    json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nJSON: {json_path}")


if __name__ == "__main__":
    main()
