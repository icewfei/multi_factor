#!/opt/anaconda3/envs/quant_trade/bin/python
"""
V4: Correctly inverted power transform.

v2 found: POWER(PR_ASC(reversal), alpha) has IC = -0.052 (reversal direction).
To use in TopK (selects highest score), need IC to be positive.
Correct inversion: score = 1.0 - POWER(PR_ASC(reversal), alpha).
  → IC should flip sign: +0.052

v3 was WRONG: used POWER(PR_DESC, alpha) = POWER(1-PR_ASC, alpha) ≠ 1 - POWER(PR_ASC, alpha).

Candidates:
  power_inv_rev_alpha3:  1.0 - POWER(PR_ASC, 3.0)
  power_inv_rev_alpha4:  1.0 - POWER(PR_ASC, 4.0)  ← expected best
  power_inv_rev_alpha5:  1.0 - POWER(PR_ASC, 5.0)

Also: split IC by train (2010-2018) vs validation (2019-2021).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import duckdb

ROOT = Path("/Users/wy/MiscProject/multi_factor")
CONTRACTS_DIR = ROOT / "contracts"
ARTIFACTS_RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
P98_SCORE_PATH = (
    ARTIFACTS_RUN_STATE_DIR
    / "confirmatory_reversal_p98_trainval_20260506"
    / "model_scores_D0.parquet"
)
P98_SCHEME_ID = "reversal_tail_exclude_p98_v1"
LABEL_RUN = "project_panels_research_trainval_20211231_20260429"

TRAIN_END = "20181231"
VALID_START = "20190101"
VALID_END = "20211231"


def sql_quote(v):
    return "'" + str(v).replace("'", "''") + "'"


def sql_path(p):
    return sql_quote(Path(p).resolve().as_posix())


def write_json(path, payload):
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
        WITH joined AS (
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
        FROM joined GROUP BY signal_date HAVING COUNT(*) >= 20
        """
    ).fetchall()

    ic_series = [float(r[1]) for r in rows if r[1] is not None]
    if not ic_series:
        return None

    n = len(ic_series)
    srt = sorted(ic_series)
    med = srt[n // 2] if n % 2 else (srt[n // 2 - 1] + srt[n // 2]) / 2.0
    return {"n_days": n, "median_ic": med}


def main():
    run_input = json.loads(
        (CONTRACTS_DIR / "run_input_contract.research_trainval_20211231.json").read_text("utf-8")
    )
    snapshot_id = run_input["snapshot_id"]
    source_db_path = (
        Path(run_input["source_root"]["snapshot_path"]) / "duckdb" / "warehouse.duckdb"
    )

    label_path = ARTIFACTS_RUN_STATE_DIR / LABEL_RUN / "project_label_panel.parquet"
    sample_path = ARTIFACTS_RUN_STATE_DIR / LABEL_RUN / "project_sample_panel.parquet"

    run_dir = ARTIFACTS_RUN_STATE_DIR / "exploratory_power_transform_v4"
    run_dir.mkdir(parents=True, exist_ok=True)

    for fname in ["project_label_panel.parquet", "project_sample_panel.parquet"]:
        src = ARTIFACTS_RUN_STATE_DIR / LABEL_RUN / fname
        dst = run_dir / fname
        if not dst.exists():
            dst.symlink_to(src)

    con = duckdb.connect()
    try:
        con.execute(f"ATTACH {sql_path(source_db_path)} AS warehouse_db (READ_ONLY)")

        # Build features + PR_ASC (reversal direction)
        con.execute(
            f"""
            CREATE OR REPLACE VIEW feature_ranks AS
            WITH bars AS (
                SELECT ts_code AS instrument, trade_date AS signal_date, adj_close
                FROM warehouse_db.serving.vw_bars_daily
                WHERE snapshot_id = {sql_quote(snapshot_id)}
            ),
            features AS (
                SELECT instrument, signal_date,
                    (adj_close / LAG(adj_close, 5) OVER w - 1.0) AS reversal_5d_raw
                FROM bars
                WINDOW w AS (PARTITION BY instrument ORDER BY signal_date)
            )
            SELECT f.instrument, f.signal_date, p.ranking_eligible_D0,
                PERCENT_RANK() OVER (
                    PARTITION BY f.signal_date
                    ORDER BY f.reversal_5d_raw ASC, f.instrument ASC
                ) AS pr_rev
            FROM features f
            JOIN read_parquet({sql_path(sample_path)}) p
              ON f.instrument = p.instrument AND f.signal_date = p.signal_date
            WHERE f.reversal_5d_raw IS NOT NULL
            """
        )

        # Load p98
        con.execute(
            f"""
            CREATE OR REPLACE VIEW p98_scores AS
            SELECT instrument, signal_date, model_score_D0 AS p98_score
            FROM read_parquet({sql_path(P98_SCORE_PATH)})
            WHERE candidate_scheme_id = {sql_quote(P98_SCHEME_ID)}
              AND model_score_D0 IS NOT NULL
            """
        )

        # Build scores: 1.0 - POWER(PR_ASC, alpha)
        alphas = [2.0, 3.0, 4.0, 5.0, 6.0]

        union_parts = []
        for alpha in alphas:
            alpha_int = int(alpha) if alpha == int(alpha) else alpha
            scheme_id = f"power_inv_rev_a{alpha_int}_v1"
            union_parts.append(
                f"""
                SELECT CAST(NULL AS BIGINT) AS snapshot_id, instrument, signal_date,
                    CAST({sql_quote(scheme_id)} AS VARCHAR) AS candidate_scheme_id,
                    1.0 - POWER(NULLIF(pr_rev, 0.0), {alpha}) AS model_score_D0,
                    1 AS score_component_count
                FROM feature_ranks
                WHERE ranking_eligible_D0 AND pr_rev IS NOT NULL AND pr_rev > 0
                """
            )

        # Composite with p98 (power_inv_rev + p98 at 50/50)
        for alpha in [3.0, 4.0]:
            alpha_int = int(alpha) if alpha == int(alpha) else alpha
            scheme_id = f"power_inv_rev_a{alpha_int}_p98_ew_v1"
            union_parts.append(
                f"""
                SELECT CAST(NULL AS BIGINT) AS snapshot_id, a.instrument, a.signal_date,
                    CAST({sql_quote(scheme_id)} AS VARCHAR) AS candidate_scheme_id,
                    0.5 * (1.0 - POWER(NULLIF(a.pr_rev, 0.0), {alpha}))
                        + 0.5 * COALESCE(p.p98_score, 0.0) AS model_score_D0,
                    2 AS score_component_count
                FROM feature_ranks a
                LEFT JOIN p98_scores p
                  ON a.instrument = p.instrument AND a.signal_date = p.signal_date
                WHERE a.ranking_eligible_D0 AND a.pr_rev IS NOT NULL AND a.pr_rev > 0
                """
            )

        score_output = run_dir / "model_scores_D0_power_v4.parquet"
        union_sql = " UNION ALL ".join(union_parts)
        con.execute(f"COPY ({union_sql}) TO {sql_path(score_output)} (FORMAT PARQUET)")

        # Diagnostic
        print("=" * 80)
        print(f"{'Scheme':<35} {'n_full':>6} {'Full IC':>10} {'n_train':>6} {'Train IC':>10} {'n_valid':>6} {'Valid IC':>10}")
        print("-" * 80)

        # p98
        p98_full = compute_ic(con, P98_SCORE_PATH, P98_SCHEME_ID, label_path)
        p98_train = compute_ic(con, P98_SCORE_PATH, P98_SCHEME_ID, label_path, date_end=TRAIN_END)
        p98_valid = compute_ic(con, P98_SCORE_PATH, P98_SCHEME_ID, label_path,
                                date_start=VALID_START, date_end=VALID_END)
        nf = p98_full["n_days"] if p98_full else 0
        nt = p98_train["n_days"] if p98_train else 0
        nv = p98_valid["n_days"] if p98_valid else 0
        print(f"{'p98 (baseline)':<35} {nf:>6} {p98_full['median_ic']:>10.6f} "
              f"{nt:>6} {p98_train['median_ic']:>10.6f} "
              f"{nv:>6} {p98_valid['median_ic']:>10.6f}")

        all_schemes = (
            [f"power_inv_rev_a{int(a)}_v1" for a in alphas]
            + [f"power_inv_rev_a{int(a)}_p98_ew_v1" for a in [3.0, 4.0]]
        )

        best = None
        for scheme_id in all_schemes:
            full = compute_ic(con, score_output, scheme_id, label_path)
            train = compute_ic(con, score_output, scheme_id, label_path, date_end=TRAIN_END)
            valid = compute_ic(con, score_output, scheme_id, label_path,
                                date_start=VALID_START, date_end=VALID_END)

            if full is None:
                continue

            nf = full["n_days"]
            nt = train["n_days"] if train else 0
            nv = valid["n_days"] if valid else 0
            f_ic = full["median_ic"]
            t_ic = train["median_ic"] if train else 0
            v_ic = valid["median_ic"] if valid else 0

            print(f"{scheme_id:<35} {nf:>6} {f_ic:>10.6f} {nt:>6} {t_ic:>10.6f} {nv:>6} {v_ic:>10.6f}")

            if best is None or v_ic > best["valid_ic"]:
                best = {"scheme_id": scheme_id, "full_ic": f_ic, "train_ic": t_ic, "valid_ic": v_ic}

        if best:
            print(f"\n  Best valid: {best['scheme_id']} (IC = {best['valid_ic']:.6f})")
            vs_p98 = best["valid_ic"] - (p98_valid["median_ic"] if p98_valid else 0)
            print(f"  vs p98 valid: {vs_p98:+.6f}")

        write_json(run_dir / "power_v4_diagnostic.json", {
            "as_of": datetime.now().strftime("%Y%m%d"),
            "p98": {"full": p98_full, "train": p98_train, "valid": p98_valid},
            "best": best,
        })

    finally:
        con.close()

    print(f"\nDone. Scores: {score_output}")


if __name__ == "__main__":
    main()
