#!/opt/anaconda3/envs/quant_trade/bin/python
"""Diagnostic for v2 direction-corrected overnight/intraday scores + selected v1 schemes for comparison."""

from __future__ import annotations

import json
import random
import sys
from datetime import datetime
from pathlib import Path

import duckdb

ROOT = Path("/Users/wy/MiscProject/multi_factor")
ARTIFACTS_RUN_STATE = ROOT / "artifacts" / "run_state"
OUTPUT_DIR = ROOT / "artifacts" / "fixed_test" / "overnight_intraday_diagnostic"

RUN_ID = "exploratory_overnight_intraday_decomposition_v1"
P98_RUN_ID = "confirmatory_reversal_p98_trainval_20260506"
P98_SCHEME_ID = "reversal_tail_exclude_p98_v1"
LABEL_RUN = "project_panels_research_trainval_20211231_20260429"

N_BOOTSTRAP = 10000
SEED = 42

V2_SCHEMES = [
    "intraday_mom_5d_v1",
    "overnight_mom_5d_v1",
    "intraday_mom_20d_v1",
    "overnight_mom_20d_v1",
    "intraday_p98_ew_v2",
    "overnight_p98_ew_v2",
    "p98_overnight_supplement_v2",
    "overnight_intraday_mom_ew_v2",
    "intraday80_overnight20_mom_v2",
]

V1_SCHEMES_COMPARE = [
    "overnight_rev_5d_v1",
    "intraday_rev_5d_v1",
]


def sql_quote(v):
    return "'" + str(v).replace("'", "''") + "'"


def sql_path(p):
    return sql_quote(Path(p).resolve().as_posix())


def bootstrap_ci(values, n_bootstrap=N_BOOTSTRAP, seed=SEED):
    rng = random.Random(seed)
    n = len(values)
    medians, means = [], []
    for _ in range(n_bootstrap):
        sample = [values[rng.randint(0, n - 1)] for _ in range(n)]
        sample.sort()
        m = len(sample)
        med = sample[m // 2] if m % 2 else (sample[m // 2 - 1] + sample[m // 2]) / 2.0
        medians.append(med)
        means.append(sum(sample) / m)
    medians.sort()
    means.sort()
    lo = int(n_bootstrap * 0.025)
    hi = int(n_bootstrap * 0.975)
    return {
        "median_daily_ic_95ci_low": medians[lo],
        "median_daily_ic_95ci_high": medians[hi],
        "mean_daily_ic_95ci_low": means[lo],
        "mean_daily_ic_95ci_high": means[hi],
    }


def compute_ic(con, label_path, sample_path, score_path, scheme_id=None):
    con.execute(f"CREATE OR REPLACE VIEW _lbl AS SELECT * FROM read_parquet({sql_path(label_path)})")
    con.execute(f"CREATE OR REPLACE VIEW _smp AS SELECT * FROM read_parquet({sql_path(sample_path)})")
    con.execute(f"CREATE OR REPLACE VIEW _scr AS SELECT * FROM read_parquet({sql_path(score_path)})")

    flt = f" AND s.candidate_scheme_id = {sql_quote(scheme_id)}" if scheme_id else ""

    con.execute(f"""
        CREATE OR REPLACE VIEW _d AS
        SELECT p.snapshot_id, p.instrument, p.signal_date, p.ranking_eligible_D0,
               s.model_score_D0 AS score_val,
               l.label_5d_next_open_close AS forward_label
        FROM _smp p
        LEFT JOIN _scr s ON p.snapshot_id = s.snapshot_id AND p.instrument = s.instrument
            AND p.signal_date = s.signal_date{flt}
        LEFT JOIN _lbl l ON p.snapshot_id = l.snapshot_id AND p.instrument = l.instrument
            AND p.signal_date = l.signal_date
    """)

    rows = con.execute("""
        WITH d AS (
            SELECT signal_date, CORR(score_val, forward_label) AS ic
            FROM _d WHERE ranking_eligible_D0 AND score_val IS NOT NULL
              AND forward_label IS NOT NULL
            GROUP BY signal_date HAVING COUNT(*) >= 20
        ) SELECT ic FROM d ORDER BY signal_date
    """).fetchall()
    ic_series = [float(r[0]) for r in rows if r[0] is not None]
    n = len(ic_series)
    if n == 0:
        for v in ("_lbl", "_smp", "_scr", "_d"):
            con.execute(f"DROP VIEW IF EXISTS {v}")
        return None

    srt = sorted(ic_series)
    mid = n // 2
    med = srt[mid] if n % 2 else (srt[mid - 1] + srt[mid]) / 2.0
    avg = sum(ic_series) / n
    std = (sum((x - avg)**2 for x in ic_series) / (n - 1)) ** 0.5
    pos = sum(1 for x in ic_series if x > 0) / n
    ci = bootstrap_ci(ic_series)

    ts = con.execute("""
        WITH r AS (
            SELECT signal_date, forward_label,
                ROW_NUMBER() OVER (PARTITION BY signal_date ORDER BY score_val DESC, instrument ASC) AS rd,
                ROW_NUMBER() OVER (PARTITION BY signal_date ORDER BY score_val ASC, instrument ASC) AS ra
            FROM _d WHERE ranking_eligible_D0 AND score_val IS NOT NULL AND forward_label IS NOT NULL
        )
        SELECT AVG(CASE WHEN rd <= 10 THEN forward_label END),
               AVG(CASE WHEN ra <= 10 THEN forward_label END)
        FROM r
    """).fetchone()

    for v in ("_lbl", "_smp", "_scr", "_d"):
        con.execute(f"DROP VIEW IF EXISTS {v}")

    t10 = float(ts[0]) if ts[0] is not None else None
    tbot = float(ts[1]) if ts[1] is not None else None

    return {
        "n_days": n,
        "mean_ic": avg,
        "median_ic": med,
        "std_ic": std,
        "pos_share": pos,
        "ci_lo": ci["median_daily_ic_95ci_low"],
        "ci_hi": ci["median_daily_ic_95ci_high"],
        "top10_label": t10,
        "bot10_label": tbot,
        "spread": (t10 - tbot) if t10 is not None and tbot is not None else None,
    }


def pairwise_corr(con, score_path_a, scheme_a, score_path_b, scheme_b, sample_path):
    con.execute(f"CREATE OR REPLACE VIEW _pw_smp AS SELECT * FROM read_parquet({sql_path(sample_path)})")
    con.execute(f"CREATE OR REPLACE VIEW _pw_a AS SELECT * FROM read_parquet({sql_path(score_path_a)})")
    con.execute(f"CREATE OR REPLACE VIEW _pw_b AS SELECT * FROM read_parquet({sql_path(score_path_b)})")
    con.execute(f"""
        CREATE OR REPLACE VIEW _pw_j AS
        SELECT a.signal_date, a.model_score_D0 AS sa, b.model_score_D0 AS sb
        FROM _pw_a a JOIN _pw_b b
          ON a.snapshot_id = b.snapshot_id AND a.instrument = b.instrument
         AND a.signal_date = b.signal_date
        WHERE a.candidate_scheme_id = {sql_quote(scheme_a)}
          AND b.candidate_scheme_id = {sql_quote(scheme_b)}
          AND a.model_score_D0 IS NOT NULL AND b.model_score_D0 IS NOT NULL
    """)
    rows = con.execute("""
        SELECT signal_date, CORR(sa, sb) FROM _pw_j
        GROUP BY signal_date HAVING COUNT(*) >= 20 ORDER BY signal_date
    """).fetchall()
    c_series = [float(r[1]) for r in rows if r[1] is not None]
    for v in ("_pw_smp", "_pw_a", "_pw_b", "_pw_j"):
        con.execute(f"DROP VIEW IF EXISTS {v}")
    if not c_series:
        return None
    n = len(c_series)
    srt = sorted(c_series)
    mid = n // 2
    return {"median_corr": srt[mid] if n % 2 else (srt[mid - 1] + srt[mid]) / 2.0, "n_days": n}


def main():
    as_of = datetime.now().strftime("%Y%m%d")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    label_path = ARTIFACTS_RUN_STATE / LABEL_RUN / "project_label_panel.parquet"
    sample_path = ARTIFACTS_RUN_STATE / LABEL_RUN / "project_sample_panel.parquet"
    v2_score_path = ARTIFACTS_RUN_STATE / RUN_ID / "model_scores_D0_v2.parquet"
    v1_score_path = ARTIFACTS_RUN_STATE / RUN_ID / "model_scores_D0.parquet"
    p98_score_path = ARTIFACTS_RUN_STATE / P98_RUN_ID / "model_scores_D0.parquet"

    for p in (label_path, sample_path, v2_score_path, p98_score_path):
        if not p.exists():
            raise FileNotFoundError(f"Missing: {p}")

    con = duckdb.connect()
    results = []

    try:
        # p98 baseline
        print("p98 baseline...", end=" ", flush=True)
        d = compute_ic(con, label_path, sample_path, p98_score_path, P98_SCHEME_ID)
        results.append({"name": "p98 (baseline)", "scheme": P98_SCHEME_ID, "family": "baseline", "diag": d})
        p98_ic = d["median_ic"] if d else 0
        print(f"IC={p98_ic:.6f}")

        # v1 comparison schemes
        for s in V1_SCHEMES_COMPARE:
            print(f"  {s} (v1)...", end=" ", flush=True)
            d = compute_ic(con, label_path, sample_path, v1_score_path, s)
            if d:
                c = pairwise_corr(con, v1_score_path, s, p98_score_path, P98_SCHEME_ID, sample_path)
                results.append({
                    "name": f"{s} (v1)", "scheme": s, "family": "v1_ref",
                    "diag": d, "p98_corr": c,
                })
                print(f"IC={d['median_ic']:.6f}, corr_p98={c['median_corr']:.4f}" if c else "N/A")
            else:
                print("NO DATA")

        # v2 schemes
        for s in V2_SCHEMES:
            print(f"  {s}...", end=" ", flush=True)
            d = compute_ic(con, label_path, sample_path, v2_score_path, s)
            if d:
                c = pairwise_corr(con, v2_score_path, s, p98_score_path, P98_SCHEME_ID, sample_path)
                results.append({
                    "name": s, "scheme": s, "family": "v2",
                    "diag": d, "p98_corr": c,
                })
                print(f"IC={d['median_ic']:.6f}, corr_p98={c['median_corr']:.4f}" if c else "N/A")
            else:
                print("NO DATA")

    finally:
        con.close()

    # Classify
    for r in results:
        if "baseline" in r.get("family", ""):
            r["classification"] = "baseline"
            continue
        d = r.get("diag")
        if d is None:
            r["classification"] = "no_data"
            continue
        med = d["median_ic"]
        ci_lo, ci_hi = d["ci_lo"], d["ci_hi"]
        corr = r.get("p98_corr", {}).get("median_corr") if r.get("p98_corr") else None

        if abs(med) > abs(p98_ic) and ci_lo and ci_hi and ci_lo > 0:
            r["classification"] = "OUTPERFORM_P98"
        elif abs(med) > 0.03 and ci_lo and ci_lo > 0:
            r["classification"] = "PASS"
        elif abs(med) > 0.03:
            r["classification"] = "THRESHOLD_CI_ISSUE"
        elif abs(med) > 0.01:
            r["classification"] = "MARGINAL"
        else:
            r["classification"] = "BELOW"

        if corr is not None:
            r["p98_overlap"] = "HIGH" if abs(corr) > 0.8 else ("MODERATE" if abs(corr) > 0.5 else "LOW")

    # Print summary table
    print("\n" + "=" * 120)
    print(f"{'Scheme':<42} {'Median IC':>10} {'95% CI':<24} {'Spread':>10} {'Corr p98':>10} {'Class':>20}")
    print("-" * 120)
    for r in sorted(results, key=lambda x: abs(x["diag"]["median_ic"]) if x.get("diag") else 0, reverse=True):
        d = r["diag"]
        if d is None:
            continue
        print(f"{r['name']:<42} {d['median_ic']:>10.6f} "
              f"[{d['ci_lo']:.6f}, {d['ci_hi']:.6f}]  "
              f"{d.get('spread', 0) or 0:>10.6f} "
              f"{r.get('p98_corr', {}).get('median_corr', 0) or 0:>10.4f} "
              f"{r.get('classification', ''):>20}")

    # Recommendations
    print("\n## Key Findings:")
    for r in results:
        if r.get("classification") in ("OUTPERFORM_P98", "PASS"):
            print(f"  ** {r['name']}: IC={r['diag']['median_ic']:.6f}, "
                  f"corr_p98={r.get('p98_corr', {}).get('median_corr', '?'):.4f} → PROMOTABLE")
        elif r.get("classification") == "THRESHOLD_CI_ISSUE":
            print(f"  ? {r['name']}: IC={r['diag']['median_ic']:.6f} "
                  f"(CI issue) → NEEDS DIAGNOSIS")

    # Find best non-baseline
    best = None
    for r in results:
        if r.get("family") == "baseline":
            continue
        d = r.get("diag")
        if d is None:
            continue
        if best is None or abs(d["median_ic"]) > abs(best["diag"]["median_ic"]):
            best = r
    if best and best.get("diag"):
        print(f"\n## Best non-p98: {best['name']} (IC={best['diag']['median_ic']:.6f})")
        print(f"  vs p98: IC delta = {abs(best['diag']['median_ic']) - abs(p98_ic):.6f}")

    # Write JSON
    report = {"as_of": as_of, "p98_ic": p98_ic, "results": results}
    json_path = OUTPUT_DIR / f"overnight_intraday_v2_diagnostic_{as_of}.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nJSON: {json_path}")


if __name__ == "__main__":
    main()
