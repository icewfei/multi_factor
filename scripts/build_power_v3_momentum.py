#!/opt/anaconda3/envs/quant_trade/bin/python
"""
V3: Direction-corrected power transform (momentum direction, like p98).

Key finding from v2: POWER(PR_ASC(reversal_5d), 4.0) has IC = -0.0516 (reversal direction).
Invert to momentum direction → should give IC +0.0516, beating p98 (0.046).

Candidates:
  1. power_mom_rev_5d_v1  — POWER(PR_DESC(reversal_5d), 4.0), momentum direction
  2. power_mom_rev_5d_v2  — alpha=3.0 variant (slightly less aggressive)
  3. power_mom_rev_5d_v3  — alpha=5.0 variant (slightly more aggressive)
  4. power_mom_rev_p98_ew — power_mom_rev + p98, equal weight

Also runs full IC diagnostic split by train/validation to check overfitting.
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
    Path(path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def compute_ic_series(con, score_path, scheme_id, label_path, date_start=None, date_end=None):
    """Compute daily IC series for a scheme, optionally filtered by date range."""
    date_filter = ""
    if date_start and date_end:
        date_filter = (
            f" AND s.signal_date BETWEEN {sql_quote(date_start)} AND {sql_quote(date_end)}"
        )
    elif date_start:
        date_filter = f" AND s.signal_date >= {sql_quote(date_start)}"

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
              AND l.label_5d_next_open_close IS NOT NULL
              {date_filter}
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
    avg = sum(ic_series) / n
    return {"n_days": n, "median_ic": med, "mean_ic": avg, "series": ic_series}


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

    run_dir = ARTIFACTS_RUN_STATE_DIR / "exploratory_power_transform_v3"
    run_dir.mkdir(parents=True, exist_ok=True)

    for fname in ["project_label_panel.parquet", "project_sample_panel.parquet"]:
        src = ARTIFACTS_RUN_STATE_DIR / LABEL_RUN / fname
        dst = run_dir / fname
        if not dst.exists():
            dst.symlink_to(src)

    con = duckdb.connect()
    try:
        con.execute(f"ATTACH {sql_path(source_db_path)} AS warehouse_db (READ_ONLY)")

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
                    ORDER BY f.reversal_5d_raw DESC, f.instrument ASC
                ) AS pr_mom,    -- momentum direction (high = went up)
                PERCENT_RANK() OVER (
                    PARTITION BY f.signal_date
                    ORDER BY f.reversal_5d_raw ASC, f.instrument ASC
                ) AS pr_rev      -- reversal direction (high = went down)
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
            SELECT snapshot_id, instrument, signal_date,
                   model_score_D0 AS p98_score
            FROM read_parquet({sql_path(P98_SCORE_PATH)})
            WHERE candidate_scheme_id = {sql_quote(P98_SCHEME_ID)}
              AND model_score_D0 IS NOT NULL
            """
        )

        # Build scores with alpha variants
        schemes = {
            "power_mom_rev_5d_v1": ("pr_mom", 4.0),
            "power_mom_rev_5d_v2": ("pr_mom", 3.0),
            "power_mom_rev_5d_v3": ("pr_mom", 5.0),
            "power_mom_rev_5d_v4": ("pr_mom", 2.0),
        }

        union_parts = []
        for scheme_id, (pr_col, alpha) in schemes.items():
            union_parts.append(
                f"""
                SELECT CAST(NULL AS BIGINT) AS snapshot_id, instrument, signal_date,
                    CAST({sql_quote(scheme_id)} AS VARCHAR) AS candidate_scheme_id,
                    POWER(NULLIF({pr_col}, 0.0), {alpha}) AS model_score_D0,
                    1 AS score_component_count
                FROM feature_ranks
                WHERE ranking_eligible_D0 AND {pr_col} IS NOT NULL AND {pr_col} > 0
                """
            )

        # Composite: power_mom_rev + p98 (50/50)
        union_parts.append(
            """
            SELECT CAST(NULL AS BIGINT) AS snapshot_id, a.instrument, a.signal_date,
                CAST('power_mom_rev_p98_ew_v1' AS VARCHAR) AS candidate_scheme_id,
                0.5 * COALESCE(POWER(NULLIF(a.pr_mom, 0.0), 4.0), 0.0)
                    + 0.5 * COALESCE(p.p98_score, 0.0) AS model_score_D0,
                2 AS score_component_count
            FROM feature_ranks a
            LEFT JOIN p98_scores p
              ON a.instrument = p.instrument AND a.signal_date = p.signal_date
            WHERE a.ranking_eligible_D0 AND a.pr_mom IS NOT NULL AND a.pr_mom > 0
            """
        )

        score_output = run_dir / "model_scores_D0_power_v3.parquet"
        union_sql = " UNION ALL ".join(union_parts)
        con.execute(f"COPY ({union_sql}) TO {sql_path(score_output)} (FORMAT PARQUET)")

        # Diagnostic: IC split by train/validation
        print("=" * 80)
        print(f"{'Scheme':<32} {'Full IC':>10} {'Train IC':>10} {'Valid IC':>10} {'Train→Valid':>14}")
        print("-" * 80)

        p98_full = compute_ic_series(con, P98_SCORE_PATH, P98_SCHEME_ID, label_path)
        p98_train = compute_ic_series(con, P98_SCORE_PATH, P98_SCHEME_ID, label_path,
                                       date_end=TRAIN_END)
        p98_valid = compute_ic_series(con, P98_SCORE_PATH, P98_SCHEME_ID, label_path,
                                       date_start=VALID_START, date_end=VALID_END)
        p98_full_ic = p98_full["median_ic"] if p98_full else 0
        p98_train_ic = p98_train["median_ic"] if p98_train else 0
        p98_valid_ic = p98_valid["median_ic"] if p98_valid else 0
        print(f"{'p98 (baseline)':<32} {p98_full_ic:>10.6f} {p98_train_ic:>10.6f} "
              f"{p98_valid_ic:>10.6f} {p98_valid_ic - p98_train_ic:>+13.6f}")

        all_schemes = list(schemes.keys()) + ["power_mom_rev_p98_ew_v1"]
        best_scheme = None
        best_valid_ic = 0

        for scheme_id in all_schemes:
            full = compute_ic_series(con, score_output, scheme_id, label_path)
            train = compute_ic_series(con, score_output, scheme_id, label_path,
                                       date_end=TRAIN_END)
            valid = compute_ic_series(con, score_output, scheme_id, label_path,
                                       date_start=VALID_START, date_end=VALID_END)

            if full is None:
                continue

            f_ic = full["median_ic"]
            t_ic = train["median_ic"] if train else 0
            v_ic = valid["median_ic"] if valid else 0

            decay = v_ic - t_ic  # positive = improved from train to valid
            print(f"{scheme_id:<32} {f_ic:>10.6f} {t_ic:>10.6f} {v_ic:>10.6f} {decay:>+13.6f}")

            if v_ic > best_valid_ic:
                best_valid_ic = v_ic
                best_scheme = {"scheme_id": scheme_id, "full_ic": f_ic, "train_ic": t_ic, "valid_ic": v_ic}

        if best_scheme:
            print(f"\n  Best on validation: {best_scheme['scheme_id']} "
                  f"(valid IC = {best_scheme['valid_ic']:.6f})")
            print(f"  vs p98 valid IC: delta = {best_scheme['valid_ic'] - p98_valid_ic:+.6f}")

        write_json(run_dir / "power_v3_diagnostic.json", {
            "as_of": datetime.now().strftime("%Y%m%d"),
            "p98": {"full": p98_full_ic, "train": p98_train_ic, "valid": p98_valid_ic},
            "best_scheme": best_scheme,
        })

    finally:
        con.close()

    print(f"\nDone. Scores: {score_output}")


if __name__ == "__main__":
    main()
