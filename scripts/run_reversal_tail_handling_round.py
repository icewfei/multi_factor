#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Reversal tail-handling round: exclude top 1% / 2% of negated reversal raw scores
per signal_date, re-rank, measure IC and TopK label direction.
Strictly follows preregistration rr_exploratory_reversal_tail_handling_20260502.
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
OUT_DIR = ROOT / "artifacts" / "fixed_test" / "reversal_tail_handling"

N_BOOTSTRAP = 10_000
SEED = 42
LABEL = "label_5d_next_open_close"


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


def compute_metrics(con, view_name: str, label: str) -> dict:
    """Compute IC + TopK metrics for a candidate score view."""

    full_ic = con.execute(f"SELECT CORR(score, oracle_label) FROM {view_name}").fetchone()[0]

    daily_rows = con.execute(f"""
        SELECT signal_date, CORR(score, oracle_label) AS daily_ic
        FROM {view_name}
        GROUP BY signal_date HAVING COUNT(*) >= 20
        ORDER BY signal_date
    """).fetchall()

    d = [float(r[1]) for r in daily_rows if r[1] is not None]
    d = [x for x in d if not (x != x)]  # filter NaN
    n = len(d)
    s = sorted(d)
    mid = n // 2
    med = s[mid] if n % 2 == 1 else (s[mid - 1] + s[mid]) / 2.0
    avg = sum(d) / n
    var = sum((x - avg) ** 2 for x in d) / (n - 1)
    std = var ** 0.5
    pos = sum(1 for x in d if x > 0) / n
    ci = bootstrap_ci(d)

    # Top10 / Bot10 labels
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
    t10 = float(tb[0]) if tb[0] is not None else None
    b10 = float(tb[1]) if tb[1] is not None else None

    # Deciles
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
        con.execute(f"CREATE VIEW cord30 AS SELECT * FROM read_parquet({sql_path(cord30_path)})")

        # ── Negated reversal base view ──
        con.execute(f"""
            CREATE OR REPLACE VIEW nr_raw AS
            SELECT
                s.instrument,
                s.signal_date,
                -1.0 * r.model_score_D0 AS nr_score,
                l.{LABEL} AS oracle_label
            FROM samples s
            LEFT JOIN rev r
              ON s.snapshot_id = r.snapshot_id AND s.instrument = r.instrument AND s.signal_date = r.signal_date
            LEFT JOIN labels l
              ON s.snapshot_id = l.snapshot_id AND s.instrument = l.instrument AND s.signal_date = l.signal_date
            WHERE s.ranking_eligible_D0
              AND r.model_score_D0 IS NOT NULL
              AND l.{LABEL} IS NOT NULL
        """)

        # ── Daily percentiles ──
        con.execute("""
            CREATE OR REPLACE VIEW nr_daily_pct AS
            SELECT
                signal_date,
                PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY nr_score) AS p99,
                PERCENTILE_CONT(0.98) WITHIN GROUP (ORDER BY nr_score) AS p98
            FROM nr_raw
            GROUP BY signal_date
        """)

        # ── Candidate A: exclude top 1% (p99) ──
        con.execute("""
            CREATE OR REPLACE VIEW nr_p99 AS
            SELECT
                n.instrument, n.signal_date,
                n.nr_score AS score,
                n.oracle_label
            FROM nr_raw n
            JOIN nr_daily_pct p ON n.signal_date = p.signal_date
            WHERE n.nr_score < p.p99
        """)
        print("=== Candidate A: reversal_tail_exclude_p99_v1 ===")
        metrics_p99 = compute_metrics(con, "nr_p99", LABEL)

        # ── Candidate B: exclude top 2% (p98) ──
        con.execute("""
            CREATE OR REPLACE VIEW nr_p98 AS
            SELECT
                n.instrument, n.signal_date,
                n.nr_score AS score,
                n.oracle_label
            FROM nr_raw n
            JOIN nr_daily_pct p ON n.signal_date = p.signal_date
            WHERE n.nr_score < p.p98
        """)
        print("=== Candidate B: reversal_tail_exclude_p98_v1 ===")
        metrics_p98 = compute_metrics(con, "nr_p98", LABEL)

        # ── Baseline: raw negated reversal (no handling) ──
        con.execute("""
            CREATE OR REPLACE VIEW nr_baseline AS
            SELECT instrument, signal_date, nr_score AS score, oracle_label FROM nr_raw
        """)
        print("=== Baseline: raw negated reversal ===")
        metrics_raw = compute_metrics(con, "nr_baseline", LABEL)

        # ── Secondary baseline: cord30 ──
        con.execute(f"""
            CREATE OR REPLACE VIEW cord30_base AS
            SELECT
                s.instrument, s.signal_date,
                c.model_score_D0 AS score,
                l.{LABEL} AS oracle_label
            FROM samples s
            LEFT JOIN cord30 c
              ON s.snapshot_id = c.snapshot_id AND s.instrument = c.instrument AND s.signal_date = c.signal_date
              AND c.candidate_scheme_id = 'price_volume_single_signal_alpha158_cord30_v1'
            LEFT JOIN labels l
              ON s.snapshot_id = l.snapshot_id AND s.instrument = l.instrument AND s.signal_date = l.signal_date
            WHERE s.ranking_eligible_D0
              AND c.model_score_D0 IS NOT NULL
              AND l.{LABEL} IS NOT NULL
        """)
        print("=== Secondary ref: cord30 ===")
        metrics_cord30 = compute_metrics(con, "cord30_base", LABEL)

    finally:
        con.close()

    # ── Evaluate success criteria ──
    def evaluate(name: str, m: dict) -> dict:
        learn_ic = (m["median_daily_ic"] is not None and m["median_daily_ic"] >= 0.040)
        learn_ci = (m["median_ci_low"] is not None and m["median_ci_low"] > 0)
        pipe_t10 = (m["top10_avg_label"] is not None and m["top10_avg_label"] > 0)
        pipe_spread = (m["top10_bot10_spread"] is not None and m["top10_bot10_spread"] > 0.003)
        all_pass = learn_ic and learn_ci and pipe_t10 and pipe_spread
        return {
            "learnability_ic_ge_040": learn_ic,
            "learnability_ci_excludes_zero": learn_ci,
            "pipeline_top10_gt_0": pipe_t10,
            "pipeline_spread_gt_0003": pipe_spread,
            "all_pass": all_pass,
        }

    eval_p99 = evaluate("p99", metrics_p99)
    eval_p98 = evaluate("p98", metrics_p98)

    # ── Print results ──
    for label, m, ev in [("reversal_tail_exclude_p99_v1", metrics_p99, eval_p99),
                          ("reversal_tail_exclude_p98_v1", metrics_p98, eval_p98)]:
        print(f"\n{'='*60}")
        print(f"  {label}")
        print(f"{'='*60}")
        print(f"  Full IC:           {m['full_sample_corr']:.6f}")
        print(f"  Mean Daily IC:     {m['mean_daily_ic']:.6f}  [{m['mean_ci_low']:.6f}, {m['mean_ci_high']:.6f}]")
        print(f"  Median Daily IC:   {m['median_daily_ic']:.6f}  [{m['median_ci_low']:.6f}, {m['median_ci_high']:.6f}]")
        print(f"  Std Daily IC:      {m['std_daily_ic']:.6f}")
        print(f"  N days:            {m['n_days']}")
        print(f"  Pos share:         {m['positive_daily_share']:.4f}")
        print(f"  Top10 avg label:   {m['top10_avg_label']:+.6f}")
        print(f"  Bot10 avg label:   {m['bottom10_avg_label']:+.6f}")
        print(f"  Top10-Bot10 spread:{m['top10_bot10_spread']:+.6f}")
        print(f"  ---")
        print(f"  Learnability:")
        print(f"    IC >= 0.040:     {'PASS' if ev['learnability_ic_ge_040'] else 'FAIL'} ({m['median_daily_ic']:.4f})")
        print(f"    CI excl zero:    {'PASS' if ev['learnability_ci_excludes_zero'] else 'FAIL'}")
        print(f"  Pipeline:")
        print(f"    Top10 label > 0: {'PASS' if ev['pipeline_top10_gt_0'] else 'FAIL'} ({m['top10_avg_label']:+.5f})")
        print(f"    Spread > 0.003:  {'PASS' if ev['pipeline_spread_gt_0003'] else 'FAIL'} ({m['top10_bot10_spread']:+.5f})")
        print(f"  >>> OVERALL:       {'PASS' if ev['all_pass'] else 'FAIL'} <<<")

    # Baseline comparison
    print(f"\n{'='*60}")
    print(f"  Baseline comparison")
    print(f"{'='*60}")
    for label, m in [("raw negated reversal", metrics_raw), ("cord30", metrics_cord30)]:
        print(f"  {label}: IC={m['median_daily_ic']:.4f}  Top10={m['top10_avg_label']:+.5f}  spread={m['top10_bot10_spread']:+.5f}")

    # Decile table
    print(f"\n{'='*60}")
    print(f"  Decile Monotonicity")
    print(f"{'='*60}")
    buckets = sorted(metrics_p99["decile_labels"].keys(), key=int)
    header = f"  {'Candidate':40s}" + "".join(f"  D{b:2s}  " for b in buckets)
    print(header)
    for name, m in [("p99", metrics_p99), ("p98", metrics_p98), ("raw", metrics_raw), ("cord30", metrics_cord30)]:
        dec = m["decile_labels"]
        vals = "".join(f" {dec[b]:+.5f}" if dec[b] is not None else "   null " for b in buckets)
        print(f"  {name:40s}{vals}")

    # ── Verdict ──
    print(f"\n{'='*60}")
    if eval_p99["all_pass"] and eval_p98["all_pass"]:
        best = "p98" if metrics_p98["top10_bot10_spread"] > metrics_p99["top10_bot10_spread"] else "p99"
        print(f"  Round verdict: BOTH PASS. Preferred: {best} (higher spread)")
        decision = "reversal tail handling validated"
    elif eval_p99["all_pass"]:
        print(f"  Round verdict: p99 PASS, p98 FAIL. Preferred: p99")
        decision = "reversal tail handling validated"
    elif eval_p98["all_pass"]:
        print(f"  Round verdict: p98 PASS, p99 FAIL. Preferred: p98")
        decision = "reversal tail handling validated"
    else:
        print(f"  Round verdict: NEITHER PASS")
        decision = "simple tail handling insufficient"
    print(f"  Decision: {decision}")

    # ── Write outputs ──
    as_of_date = datetime.now().strftime("%Y%m%d")
    output = {
        "as_of_date": as_of_date,
        "research_round_id": "rr_exploratory_reversal_tail_handling_20260502",
        "baselines": {
            "raw_negated_reversal": {k: metrics_raw[k] for k in ["median_daily_ic", "median_ci_low", "median_ci_high", "top10_avg_label", "top10_bot10_spread"]},
            "cord30": {k: metrics_cord30[k] for k in ["median_daily_ic", "median_ci_low", "median_ci_high", "top10_avg_label", "top10_bot10_spread"]},
        },
        "candidates": {
            "reversal_tail_exclude_p99_v1": {"metrics": metrics_p99, "evaluation": eval_p99},
            "reversal_tail_exclude_p98_v1": {"metrics": metrics_p98, "evaluation": eval_p98},
        },
        "success_rules": {
            "learnability": ["median_daily_ic >= 0.040", "bootstrap 95% CI excludes zero"],
            "pipeline_compatibility": ["top10_avg_label > 0", "top10_bot10_spread > 0.003"],
        },
        "round_verdict": decision,
    }
    json_path = OUT_DIR / f"reversal_tail_handling_results_{as_of_date}.json"
    json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nJSON: {json_path}")


if __name__ == "__main__":
    main()
