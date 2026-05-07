#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Multi-signal IC-weighted composite.

Signals: p98, cord30, vsumd60, corr30
Pairwise correlations: all < 0.42, most < 0.20 → excellent for additive combination.

Schemes:
  1. multi_ic_weighted_v1    — w ∝ IC (p98=0.33, cord30=0.24, corr30=0.23, vsumd60=0.20)
  2. multi_unique_weighted_v1— w ∝ IC × (1 − avg_pairwise_corr) → penalizes redundancy
  3. multi_equal_weight_v1   — w = 1/4 each
  4. multi_top2_ew_v1        — p98 + cord30 only (best IC + best full-chain)
  5. multi_top3_ew_v1        — p98 + cord30 + vsumd60 (best full-chain performers)
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import duckdb

ROOT = Path("/Users/wy/MiscProject/multi_factor")
ARTIFACTS_RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
LABEL_RUN = "project_panels_research_trainval_20211231_20260429"

TRAIN_END = "20181231"
VALID_START = "20190101"
VALID_END = "20211231"

# Pairwise correlations (pre-computed)
PAIRWISE_CORR = {
    ("p98", "cord30"): 0.1105, ("p98", "vsumd60"): 0.2615,
    ("p98", "corr30"): 0.0655, ("cord30", "vsumd60"): 0.1692,
    ("cord30", "corr30"): 0.4225, ("vsumd60", "corr30"): 0.1240,
}

SIGNAL_SPECS = [
    {
        "name": "p98",
        "path": ARTIFACTS_RUN_STATE_DIR / "confirmatory_reversal_p98_trainval_20260506" / "model_scores_D0.parquet",
        "scheme": "reversal_tail_exclude_p98_v1",
        "ic": 0.046045,
    },
    {
        "name": "cord30",
        "path": ARTIFACTS_RUN_STATE_DIR / "confirmatory_cord30_trainval_20260429" / "model_scores_D0.parquet",
        "scheme": "price_volume_single_signal_alpha158_cord30_v1",
        "ic": 0.032511,
    },
    {
        "name": "vsumd60",
        "path": ARTIFACTS_RUN_STATE_DIR / "confirmatory_vsumd60_trainval_20260429" / "model_scores_D0.parquet",
        "scheme": "price_volume_single_signal_alpha158_vsumd60_v1",
        "ic": 0.027709,
    },
    {
        "name": "corr30",
        "path": ARTIFACTS_RUN_STATE_DIR / "confirmatory_corr30_trainval_20260430" / "model_scores_D0.parquet",
        "scheme": "price_volume_single_signal_alpha158_corr30_v1",
        "ic": 0.031348,
    },
]


def sql_quote(v):
    return "'" + str(v).replace("'", "''") + "'"


def sql_path(p):
    return sql_quote(Path(p).resolve().as_posix())


def compute_ic(con, score_path, scheme_id, label_path, date_start=None, date_end=None):
    date_filter = ""
    if date_start and date_end:
        date_filter = f" AND s.signal_date BETWEEN {sql_quote(date_start)} AND {sql_quote(date_end)}"
    elif date_start:
        date_filter = f" AND s.signal_date >= {sql_quote(date_start)}"
    elif date_end:
        date_filter = f" AND s.signal_date <= {sql_quote(date_end)}"
    rows = con.execute(
        f"""
        WITH j AS (
            SELECT s.signal_date, s.model_score_D0 AS score_val,
                   l.label_5d_next_open_close AS oracle_label
            FROM read_parquet({sql_path(score_path)}) s
            JOIN read_parquet({sql_path(label_path)}) l
              ON s.instrument = l.instrument AND s.signal_date = l.signal_date
            WHERE s.candidate_scheme_id = {sql_quote(scheme_id)}
              AND s.model_score_D0 IS NOT NULL
              AND l.label_5d_next_open_close IS NOT NULL{date_filter}
        )
        SELECT signal_date, CORR(score_val, oracle_label) AS ic
        FROM j GROUP BY signal_date HAVING COUNT(*) >= 20
        """
    ).fetchall()
    ic_series = [float(r[1]) for r in rows if r[1] is not None]
    if not ic_series: return None
    n = len(ic_series); srt = sorted(ic_series)
    med = srt[n // 2] if n % 2 else (srt[n // 2 - 1] + srt[n // 2]) / 2.0
    return {"n_days": n, "median_ic": med}


def main():
    label_path = ARTIFACTS_RUN_STATE_DIR / LABEL_RUN / "project_label_panel.parquet"
    sample_path = ARTIFACTS_RUN_STATE_DIR / LABEL_RUN / "project_sample_panel.parquet"

    run_dir = ARTIFACTS_RUN_STATE_DIR / "exploratory_multi_signal_composite_v1"
    run_dir.mkdir(parents=True, exist_ok=True)
    for f in ["project_label_panel.parquet", "project_sample_panel.parquet"]:
        dst = run_dir / f
        if not dst.exists():
            dst.symlink_to(ARTIFACTS_RUN_STATE_DIR / LABEL_RUN / f)

    # Compute avg_pairwise_corr per signal
    avg_corr = {}
    for sig in SIGNAL_SPECS:
        name = sig["name"]
        corrs = []
        for (a, b), c in PAIRWISE_CORR.items():
            if a == name: corrs.append(c)
            if b == name: corrs.append(c)
        avg_corr[name] = sum(corrs) / len(corrs) if corrs else 0.0

    # IC weights
    total_ic = sum(s["ic"] for s in SIGNAL_SPECS)
    ic_weights = {s["name"]: s["ic"] / total_ic for s in SIGNAL_SPECS}

    # IC × uniqueness weights: IC * (1 - avg_corr)
    unique_scores = {s["name"]: s["ic"] * (1.0 - avg_corr[s["name"]]) for s in SIGNAL_SPECS}
    total_unique = sum(unique_scores.values())
    unique_weights = {n: v / total_unique for n, v in unique_scores.items()}

    print("Weights:")
    for s in SIGNAL_SPECS:
        n = s["name"]
        print(f"  {n}: IC={s['ic']:.4f}, avg_corr={avg_corr[n]:.3f}, "
              f"ic_w={ic_weights[n]:.3f}, unique_w={unique_weights[n]:.3f}")

    con = duckdb.connect()
    try:
        # Load all signals
        for sig in SIGNAL_SPECS:
            con.execute(
                f"CREATE OR REPLACE VIEW v_{sig['name']} AS "
                f"SELECT instrument, signal_date, model_score_D0 AS s_{sig['name']} "
                f"FROM read_parquet({sql_path(sig['path'])}) "
                f"WHERE candidate_scheme_id = {sql_quote(sig['scheme'])} "
                f"AND model_score_D0 IS NOT NULL"
            )

        # Build union of composites
        composites = {
            "multi_ic_weighted_v1": ic_weights,
            "multi_unique_weighted_v1": unique_weights,
            "multi_equal_weight_v1": {s["name"]: 0.25 for s in SIGNAL_SPECS},
            "multi_top2_ew_v1": {"p98": 0.5, "cord30": 0.5},
            "multi_top3_ew_v1": {"p98": 1/3, "cord30": 1/3, "vsumd60": 1/3},
        }

        union_parts = []
        for scheme_id, weights in composites.items():
            active = [s["name"] for s in SIGNAL_SPECS if s["name"] in weights]
            first = active[0]

            # Build FROM + LEFT JOINs
            from_clause = f"FROM v_{first}"
            for other in active[1:]:
                from_clause += (
                    f"\nLEFT JOIN v_{other} ON v_{first}.instrument = v_{other}.instrument "
                    f"AND v_{first}.signal_date = v_{other}.signal_date"
                )

            # Build weighted sum
            score_terms = [
                f"{weights[name]:.6f} * COALESCE(v_{name}.s_{name}, 0.0)"
                for name in active
            ]
            score_sum = " + ".join(score_terms)
            n_signals = len(active)

            union_parts.append(
                f"""
                SELECT CAST(NULL AS BIGINT) AS snapshot_id,
                    v_{first}.instrument, v_{first}.signal_date,
                    CAST({sql_quote(scheme_id)} AS VARCHAR) AS candidate_scheme_id,
                    ({score_sum}) AS model_score_D0,
                    {n_signals} AS score_component_count
                {from_clause}
                """
            )

        score_output = run_dir / "model_scores_D0_multi.parquet"
        con.execute(f"COPY ({' UNION ALL '.join(union_parts)}) TO {sql_path(score_output)} (FORMAT PARQUET)")

        # Diagnostic
        print(f"\n{'='*90}")
        print(f"{'Scheme':<30} {'Full IC':>10} {'Train IC':>10} {'Valid IC':>10} {'Valid-Train':>12}")
        print(f"{'-'*90}")

        p98_full = compute_ic(con, SIGNAL_SPECS[0]["path"], SIGNAL_SPECS[0]["scheme"], label_path)
        p98_train = compute_ic(con, SIGNAL_SPECS[0]["path"], SIGNAL_SPECS[0]["scheme"], label_path, date_end=TRAIN_END)
        p98_valid = compute_ic(con, SIGNAL_SPECS[0]["path"], SIGNAL_SPECS[0]["scheme"], label_path, date_start=VALID_START, date_end=VALID_END)
        pf = p98_full["median_ic"] if p98_full else 0
        pt = p98_train["median_ic"] if p98_train else 0
        pv = p98_valid["median_ic"] if p98_valid else 0
        print(f"{'p98 (baseline)':<30} {pf:>10.6f} {pt:>10.6f} {pv:>10.6f} {pv-pt:>+12.6f}")

        best_s, best_v = None, -99
        for sid in composites:
            full = compute_ic(con, score_output, sid, label_path)
            train = compute_ic(con, score_output, sid, label_path, date_end=TRAIN_END)
            valid = compute_ic(con, score_output, sid, label_path, date_start=VALID_START, date_end=VALID_END)
            if full is None: continue
            f_ic = full["median_ic"]; t_ic = train["median_ic"] if train else 0; v_ic = valid["median_ic"] if valid else 0
            print(f"{sid:<30} {f_ic:>10.6f} {t_ic:>10.6f} {v_ic:>10.6f} {v_ic-t_ic:>+12.6f}")
            if v_ic > best_v:
                best_v = v_ic; best_s = sid

        if best_s:
            print(f"\n  Best valid: {best_s} (IC={best_v:.6f})")

    finally:
        con.close()

    print(f"\nDone. Scores: {score_output}")


if __name__ == "__main__":
    main()
