#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Learnability diagnostic for overnight/intraday decomposition features.

Measures each candidate scheme against the oracle 5d forward label, compares
with p98 baseline, and computes pairwise rank correlation with p98.

Output:
  - diagnostic_report.json — full results
  - diagnostic_report.md — human-readable summary
"""

from __future__ import annotations

import json
import random
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

CANDIDATE_SCHEMES = [
    "overnight_rev_5d_v1",
    "intraday_rev_5d_v1",
    "overnight_rev_20d_v1",
    "intraday_rev_20d_v1",
    "overnight_vol_5d_v1",
    "overnight_intraday_divergence_v1",
    "overnight_p98_ew_v1",
    "intraday_p98_ew_v1",
    "overnight_intraday_ew_v1",
    "overnight70_p98_30_v1",
    "intraday70_p98_30_v1",
]


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_path(path: Path) -> str:
    return sql_quote(path.resolve().as_posix())


def bootstrap_ci(values: list[float], n_bootstrap=N_BOOTSTRAP, seed=SEED):
    rng = random.Random(seed)
    n = len(values)
    medians, means = [], []
    for _ in range(n_bootstrap):
        sample = [values[rng.randint(0, n - 1)] for _ in range(n)]
        sample.sort()
        m = len(sample)
        if m % 2 == 1:
            medians.append(sample[m // 2])
        else:
            medians.append((sample[m // 2 - 1] + sample[m // 2]) / 2.0)
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


def compute_ic(con, label_path, sample_path, score_path, candidate_scheme_id=None):
    """Compute rank-correlation diagnostics for one signal against oracle label."""
    con.execute(
        f"CREATE OR REPLACE VIEW _diag_labels AS SELECT * FROM read_parquet({sql_path(label_path)})"
    )
    con.execute(
        f"CREATE OR REPLACE VIEW _diag_samples AS SELECT * FROM read_parquet({sql_path(sample_path)})"
    )
    con.execute(
        f"CREATE OR REPLACE VIEW _diag_scores AS SELECT * FROM read_parquet({sql_path(score_path)})"
    )

    scheme_filter = ""
    if candidate_scheme_id is not None:
        scheme_filter = (
            f" AND s.candidate_scheme_id = {sql_quote(candidate_scheme_id)}"
        )

    con.execute(
        f"""
        CREATE OR REPLACE VIEW _diag_base AS
        SELECT
            p.snapshot_id,
            p.instrument,
            p.signal_date,
            p.ranking_eligible_D0,
            s.model_score_D0 AS score_val,
            l.label_5d_next_open_close AS forward_label
        FROM _diag_samples p
        LEFT JOIN _diag_scores s
          ON p.snapshot_id = s.snapshot_id
         AND p.instrument = s.instrument
         AND p.signal_date = s.signal_date{scheme_filter}
        LEFT JOIN _diag_labels l
          ON p.snapshot_id = l.snapshot_id
         AND p.instrument = l.instrument
         AND p.signal_date = l.signal_date
        """
    )

    # Coverage
    coverage = con.execute("""
        SELECT
            SUM(CASE WHEN ranking_eligible_D0 THEN 1 ELSE 0 END) AS eligible,
            SUM(CASE WHEN ranking_eligible_D0 AND score_val IS NOT NULL
                AND forward_label IS NOT NULL THEN 1 ELSE 0 END) AS scored
        FROM _diag_base
    """).fetchone()
    eligible = int(coverage[0] or 0)
    scored = int(coverage[1] or 0)

    # Daily IC series
    daily_rows = con.execute("""
        WITH daily_ic AS (
            SELECT
                signal_date,
                CORR(score_val, forward_label) AS daily_ic
            FROM _diag_base
            WHERE ranking_eligible_D0
              AND score_val IS NOT NULL
              AND forward_label IS NOT NULL
            GROUP BY signal_date
            HAVING COUNT(*) >= 20
        )
        SELECT daily_ic FROM daily_ic ORDER BY signal_date
    """).fetchall()
    daily_ic_series = [float(r[0]) for r in daily_rows if r[0] is not None]

    n = len(daily_ic_series)
    if n == 0:
        return {
            "coverage": {"eligible_rows": eligible, "scored_with_label_rows": scored},
            "ic": {
                "mean_daily_ic": None,
                "median_daily_ic": None,
                "std_daily_ic": None,
                "n_days": 0,
                "positive_daily_share": None,
                "median_daily_ic_95ci_low": None,
                "median_daily_ic_95ci_high": None,
            },
            "top_slice": None,
        }

    sorted_ic = sorted(daily_ic_series)
    mid = n // 2
    med_ic = sorted_ic[mid] if n % 2 == 1 else (sorted_ic[mid - 1] + sorted_ic[mid]) / 2.0
    avg_ic = sum(daily_ic_series) / n
    variance = sum((x - avg_ic) ** 2 for x in daily_ic_series) / (n - 1)
    std_ic = variance ** 0.5
    pos_share = sum(1 for x in daily_ic_series if x > 0) / n
    ci = bootstrap_ci(daily_ic_series)

    # Top-slice
    top_slice = con.execute("""
        WITH ranked AS (
            SELECT
                signal_date,
                forward_label,
                ROW_NUMBER() OVER (PARTITION BY signal_date ORDER BY score_val DESC, instrument ASC) AS rn_desc,
                ROW_NUMBER() OVER (PARTITION BY signal_date ORDER BY score_val ASC, instrument ASC) AS rn_asc
            FROM _diag_base
            WHERE ranking_eligible_D0 AND score_val IS NOT NULL AND forward_label IS NOT NULL
        )
        SELECT
            AVG(CASE WHEN rn_desc <= 10 THEN forward_label END) AS top10,
            AVG(CASE WHEN rn_asc <= 10 THEN forward_label END) AS bot10
        FROM ranked
    """).fetchone()

    t10 = float(top_slice[0]) if top_slice[0] is not None else None
    tbot = float(top_slice[1]) if top_slice[1] is not None else None

    # Decile labels
    deciles = con.execute("""
        WITH ranked AS (
            SELECT
                signal_date,
                forward_label,
                NTILE(10) OVER (PARTITION BY signal_date ORDER BY score_val DESC, instrument ASC) AS bucket
            FROM _diag_base
            WHERE ranking_eligible_D0 AND score_val IS NOT NULL AND forward_label IS NOT NULL
        )
        SELECT bucket, AVG(forward_label)
        FROM ranked
        GROUP BY bucket
        ORDER BY bucket
    """).fetchall()

    decile_map = {str(int(b)): float(v) if v is not None else None for b, v in deciles}

    for v in ("_diag_labels", "_diag_samples", "_diag_scores", "_diag_base"):
        con.execute(f"DROP VIEW IF EXISTS {v}")

    return {
        "coverage": {"eligible_rows": eligible, "scored_with_label_rows": scored},
        "ic": {
            "mean_daily_ic": avg_ic,
            "median_daily_ic": med_ic,
            "std_daily_ic": std_ic,
            "n_days": n,
            "positive_daily_share": pos_share,
            "median_daily_ic_95ci_low": ci["median_daily_ic_95ci_low"],
            "median_daily_ic_95ci_high": ci["median_daily_ic_95ci_high"],
        },
        "decile_labels": decile_map,
        "top_slice": {
            "top10_avg_label": t10,
            "bottom10_avg_label": tbot,
            "top10_minus_bottom10": (
                (t10 - tbot) if t10 is not None and tbot is not None else None
            ),
        },
    }


def compute_pairwise_corr(con, score_path, scheme_a, scheme_b, scheme_b_path, sample_path):
    """Compute daily pairwise rank correlation between two schemes (possibly in different parquet files)."""
    con.execute(
        f"CREATE OR REPLACE VIEW _pw_samples AS SELECT * FROM read_parquet({sql_path(sample_path)})"
    )
    con.execute(
        f"CREATE OR REPLACE VIEW _pw_scores_a AS SELECT * FROM read_parquet({sql_path(score_path)})"
    )
    con.execute(
        f"CREATE OR REPLACE VIEW _pw_scores_b AS SELECT * FROM read_parquet({sql_path(scheme_b_path)})"
    )

    con.execute(
        f"""
        CREATE OR REPLACE VIEW _pw_joined AS
        SELECT
            a.signal_date,
            a.model_score_D0 AS score_a,
            b.model_score_D0 AS score_b
        FROM _pw_scores_a a
        JOIN _pw_scores_b b
          ON a.snapshot_id = b.snapshot_id
         AND a.instrument = b.instrument
         AND a.signal_date = b.signal_date
        WHERE a.candidate_scheme_id = {sql_quote(scheme_a)}
          AND b.candidate_scheme_id = {sql_quote(scheme_b)}
          AND a.model_score_D0 IS NOT NULL
          AND b.model_score_D0 IS NOT NULL
        """
    )

    daily_corr_rows = con.execute("""
        SELECT signal_date, CORR(score_a, score_b) AS daily_corr
        FROM _pw_joined
        GROUP BY signal_date
        HAVING COUNT(*) >= 20
        ORDER BY signal_date
    """).fetchall()

    corr_series = [float(r[1]) for r in daily_corr_rows if r[1] is not None]
    if not corr_series:
        return None

    n = len(corr_series)
    sorted_c = sorted(corr_series)
    mid = n // 2
    med_corr = sorted_c[mid] if n % 2 == 1 else (sorted_c[mid - 1] + sorted_c[mid]) / 2.0

    for v in ("_pw_samples", "_pw_scores_a", "_pw_scores_b", "_pw_joined"):
        con.execute(f"DROP VIEW IF EXISTS {v}")

    return {"median_daily_corr": med_corr, "n_days": n}


def main():
    as_of_date = datetime.now().strftime("%Y%m%d")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    label_path = ARTIFACTS_RUN_STATE / LABEL_RUN / "project_label_panel.parquet"
    sample_path = ARTIFACTS_RUN_STATE / LABEL_RUN / "project_sample_panel.parquet"
    score_path = ARTIFACTS_RUN_STATE / RUN_ID / "model_scores_D0.parquet"
    p98_score_path = ARTIFACTS_RUN_STATE / P98_RUN_ID / "model_scores_D0.parquet"

    for p in (label_path, sample_path, score_path, p98_score_path):
        if not p.exists():
            raise FileNotFoundError(f"Missing: {p}")

    con = duckdb.connect()
    results = []

    try:
        # p98 baseline
        print("Computing p98 baseline IC...")
        p98_diag = compute_ic(
            con, label_path, sample_path, p98_score_path,
            candidate_scheme_id=P98_SCHEME_ID,
        )
        results.append({
            "name": "p98 (reversal baseline)",
            "scheme_id": P98_SCHEME_ID,
            "family": "baseline",
            "diagnostic": p98_diag,
        })
        p98_ic = p98_diag["ic"]["median_daily_ic"]
        print(f"  p98: median IC = {p98_ic:.6f}")

        # Overnight/intraday candidates
        for scheme_id in CANDIDATE_SCHEMES:
            print(f"Computing IC for {scheme_id}...")
            diag = compute_ic(
                con, label_path, sample_path, score_path,
                candidate_scheme_id=scheme_id,
            )
            ic_val = diag["ic"]["median_daily_ic"]
            top10 = diag["top_slice"]["top10_avg_label"] if diag["top_slice"] else None
            spread = diag["top_slice"]["top10_minus_bottom10"] if diag["top_slice"] else None

            # Pairwise correlation with p98
            corr_info = compute_pairwise_corr(
                con, score_path, scheme_id, P98_SCHEME_ID, p98_score_path, sample_path
            )
            median_corr = corr_info["median_daily_corr"] if corr_info else None

            results.append({
                "name": scheme_id,
                "scheme_id": scheme_id,
                "family": "overnight_intraday",
                "diagnostic": diag,
                "p98_pairwise_corr": corr_info,
            })
            print(f"  {scheme_id}: median IC = {ic_val:.6f}, "
                  f"top10={top10:.6f}, spread={spread:.6f}, "
                  f"corr_with_p98={median_corr:.4f}" if median_corr else "N/A")

        # Summary classification
        for r in results:
            if r["name"] == "p98 (reversal baseline)":
                r["classification"] = "baseline"
                continue
            diag = r["diagnostic"]
            med = diag["ic"]["median_daily_ic"]
            ci_lo = diag["ic"]["median_daily_ic_95ci_low"]
            ci_hi = diag["ic"]["median_daily_ic_95ci_high"]
            corr = r.get("p98_pairwise_corr", {}).get("median_daily_corr") if r.get("p98_pairwise_corr") else None

            if med is None:
                r["classification"] = "no_data"
            elif abs(med) > abs(p98_ic) and ci_lo is not None and ci_lo > 0:
                r["classification"] = "outperform_p98"
            elif abs(med) > 0.03 and ci_lo is not None and ci_lo > 0:
                r["classification"] = "positive_pass"
            elif abs(med) > 0.03:
                r["classification"] = "threshold_met_ci_issues"
            elif abs(med) > 0.01:
                r["classification"] = "marginal"
            else:
                r["classification"] = "below_threshold"

            if corr is not None and abs(corr) > 0.8:
                r["p98_overlap"] = "high"
            elif corr is not None and abs(corr) > 0.5:
                r["p98_overlap"] = "moderate"
            elif corr is not None:
                r["p98_overlap"] = "low"
            else:
                r["p98_overlap"] = "unknown"

    finally:
        con.close()

    # Build report
    report = {
        "as_of_date": as_of_date,
        "run_id": RUN_ID,
        "p98_median_ic": p98_ic,
        "candidates": results,
        "recommendations": [],
    }

    # Generate recommendations
    for r in results:
        if r["name"] == "p98 (reversal baseline)":
            continue
        cls = r.get("classification", "")
        overlap = r.get("p98_overlap", "")
        if cls == "outperform_p98":
            report["recommendations"].append(
                f"PROMOTE: {r['name']} outperforms p98 — run confirmatory fixed test"
            )
        elif cls == "positive_pass" and overlap == "low":
            report["recommendations"].append(
                f"CONSIDER: {r['name']} has positive IC with low p98 overlap — "
                f"candidate for composite with p98"
            )
        elif cls == "positive_pass" and overlap in ("moderate", "high"):
            report["recommendations"].append(
                f"WATCH: {r['name']} has positive IC but high overlap with p98 — "
                f"limited marginal value"
            )
        elif cls == "marginal":
            report["recommendations"].append(
                f"SKIP: {r['name']} — marginal IC, not worth full-chain"
            )

    # Write outputs
    json_path = OUTPUT_DIR / f"overnight_intraday_diagnostic_{as_of_date}.json"
    md_path = OUTPUT_DIR / f"overnight_intraday_diagnostic_{as_of_date}.md"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Markdown summary
    lines = [
        "# Overnight/Intraday Decomposition — Learnability Diagnostic",
        f"Generated: {as_of_date}",
        "",
        f"## p98 Baseline: median daily IC = {p98_ic:.6f}",
        "",
        "## Results",
        "",
        "| Scheme | Median IC [95% CI] | Top10 Label | Spread | Corr w/ p98 | Classification |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        diag = r["diagnostic"]
        ic = diag["ic"]
        med_s = f"{ic['median_daily_ic']:.6f}" if ic["median_daily_ic"] is not None else "N/A"
        ci_lo = ic["median_daily_ic_95ci_low"]
        ci_hi = ic["median_daily_ic_95ci_high"]
        ci_s = f"[{ci_lo:.6f}, {ci_hi:.6f}]" if ci_lo is not None else "N/A"
        ts = diag["top_slice"]
        t10_s = f"{ts['top10_avg_label']:.6f}" if ts and ts["top10_avg_label"] is not None else "N/A"
        spread_s = f"{ts['top10_minus_bottom10']:.6f}" if ts and ts["top10_minus_bottom10"] is not None else "N/A"
        corr = r.get("p98_pairwise_corr", {}) or {}
        corr_s = f"{corr.get('median_daily_corr', 0):.4f}" if corr.get('median_daily_corr') is not None else "N/A"
        cls = r.get("classification", "-")
        lines.append(f"| {r['name']} | {med_s} {ci_s} | {t10_s} | {spread_s} | {corr_s} | **{cls}** |")

    lines.extend([
        "",
        "## Recommendations",
        "",
    ])
    if report["recommendations"]:
        for rec in report["recommendations"]:
            lines.append(f"- {rec}")
    else:
        lines.append("- (none)")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\nDone. JSON: {json_path}, MD: {md_path}")
    print(f"\nKey findings:")
    for r in results:
        if r.get("classification") in ("outperform_p98", "positive_pass", "threshold_met_ci_issues"):
            ic = r["diagnostic"]["ic"]
            corr = r.get("p98_pairwise_corr", {}) or {}
            corr_val = corr.get("median_daily_corr", "N/A")
            print(f"  {r['name']}: IC={ic['median_daily_ic']:.6f}, corr_p98={corr_val}")


if __name__ == "__main__":
    main()
