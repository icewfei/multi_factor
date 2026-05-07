#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Industry-neutralized reversal + p98 tail exclusion (combo experiment).

Pipeline:
  1. reversal_5d → PERCENT_RANK ASC → pr_rev
  2. Industry neutralize: pr_rev - AVG(pr_rev) OVER (PARTITION BY signal_date, l1_code)
  3. Negate: nr = -1.0 * pr_ind_neut  (momentum direction, like p98)
  4. Tail exclude: nr < daily p98(nr)
  5. PERCENT_RANK nr ASC → model_score

Compares: p98, ind_neut only, ind_neut+tail combo, raw reverse+tail (p98 equivalent no industry).

Single-dimension change: adds industry neutralization to p98 preprocessing. Nothing else changes.
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

    run_dir = ARTIFACTS_RUN_STATE_DIR / "exploratory_neut_tail_combo_v1"
    run_dir.mkdir(parents=True, exist_ok=True)
    for f in ["project_label_panel.parquet", "project_sample_panel.parquet"]:
        dst = run_dir / f
        if not dst.exists():
            dst.symlink_to(ARTIFACTS_RUN_STATE_DIR / LABEL_RUN / f)

    con = duckdb.connect()
    try:
        con.execute(f"ATTACH {sql_path(source_db_path)} AS warehouse_db (READ_ONLY)")

        # Build base data: reversal raw, PERCENT_RANK, industry
        con.execute(
            f"""
            CREATE OR REPLACE VIEW base_data AS
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
            ),
            industry AS (
                SELECT ts_code AS instrument, l1_code,
                       CAST(in_date AS INTEGER) AS in_date_int,
                       CAST(NULLIF(out_date, '') AS INTEGER) AS out_date_int
                FROM warehouse_db.serving.vw_industry_membership_interval
                WHERE snapshot_id = {sql_quote(snapshot_id)}
            ),
            with_ind AS (
                SELECT f.*, i.l1_code
                FROM features f
                LEFT JOIN industry i
                  ON f.instrument = i.instrument
                 AND CAST(f.signal_date AS INTEGER) >= i.in_date_int
                 AND (i.out_date_int IS NULL OR CAST(f.signal_date AS INTEGER) < i.out_date_int)
            )
            SELECT w.*, p.ranking_eligible_D0,
                PERCENT_RANK() OVER (
                    PARTITION BY w.signal_date
                    ORDER BY w.reversal_5d_raw ASC, w.instrument ASC
                ) AS pr_rev
            FROM with_ind w
            JOIN read_parquet({sql_path(sample_path)}) p
              ON w.instrument = p.instrument AND w.signal_date = p.signal_date
            WHERE w.reversal_5d_raw IS NOT NULL
            """
        )

        # Industry neutralize pr_rev
        con.execute(
            """
            CREATE OR REPLACE VIEW ind_neut AS
            SELECT *, pr_rev - AVG(pr_rev) OVER (
                PARTITION BY signal_date, l1_code
            ) AS pr_rev_ind_neut
            FROM base_data
            WHERE l1_code IS NOT NULL AND pr_rev IS NOT NULL
            """
        )

        # p98-style tail exclusion on negated neutralized score
        # negate → nr = -pr_rev_ind_neut, high nr = stocks that went DOWN (reversal)
        # exclude top 2% of nr → exclude extreme DOWN stocks
        # rank ASC on nr → high rank = low nr = stocks that went UP (momentum)
        con.execute(
            """
            CREATE OR REPLACE VIEW nr_ind AS
            SELECT instrument, signal_date, ranking_eligible_D0,
                   -1.0 * pr_rev_ind_neut AS nr_ind_score,
                   pr_rev_ind_neut, l1_code
            FROM ind_neut
            WHERE ranking_eligible_D0 AND pr_rev_ind_neut IS NOT NULL
            """
        )

        # Also build the same for non-neutralized (pr_rev → tail exclude) for fair comparison
        con.execute(
            """
            CREATE OR REPLACE VIEW nr_raw AS
            SELECT instrument, signal_date, ranking_eligible_D0,
                   -1.0 * pr_rev AS nr_raw_score,
                   pr_rev
            FROM base_data
            WHERE ranking_eligible_D0 AND pr_rev IS NOT NULL
            """
        )

        # Build scores with tail exclusion — build each as a separate view, then UNION from views
        # Scheme 1: Industry neutralized + tail exclusion
        con.execute(
            """
            CREATE OR REPLACE VIEW score_ind_neut_tail AS
            WITH daily_p98 AS (
                SELECT signal_date,
                    PERCENTILE_CONT(0.98) WITHIN GROUP (ORDER BY nr_ind_score) AS p98
                FROM nr_ind GROUP BY signal_date
            ),
            filtered AS (
                SELECT n.instrument, n.signal_date, n.nr_ind_score
                FROM nr_ind n JOIN daily_p98 p ON n.signal_date = p.signal_date
                WHERE n.nr_ind_score < p.p98
            )
            SELECT instrument, signal_date,
                CAST('ind_neut_tail_p98_v1' AS VARCHAR) AS candidate_scheme_id,
                PERCENT_RANK() OVER (
                    PARTITION BY signal_date
                    ORDER BY nr_ind_score ASC, instrument ASC
                ) AS model_score_D0,
                1 AS score_component_count
            FROM filtered
            """
        )

        # Scheme 2: No neutralization + tail exclusion (PR-based p98 equivalent)
        con.execute(
            """
            CREATE OR REPLACE VIEW score_raw_tail AS
            WITH daily_p98 AS (
                SELECT signal_date,
                    PERCENTILE_CONT(0.98) WITHIN GROUP (ORDER BY nr_raw_score) AS p98
                FROM nr_raw GROUP BY signal_date
            ),
            filtered AS (
                SELECT n.instrument, n.signal_date, n.nr_raw_score
                FROM nr_raw n JOIN daily_p98 p ON n.signal_date = p.signal_date
                WHERE n.nr_raw_score < p.p98
            )
            SELECT instrument, signal_date,
                CAST('raw_tail_p98_v1' AS VARCHAR) AS candidate_scheme_id,
                PERCENT_RANK() OVER (
                    PARTITION BY signal_date
                    ORDER BY nr_raw_score ASC, instrument ASC
                ) AS model_score_D0,
                1 AS score_component_count
            FROM filtered
            """
        )

        # Scheme 3: Industry neutralized only (no tail)
        con.execute(
            """
            CREATE OR REPLACE VIEW score_ind_neut_only AS
            SELECT instrument, signal_date,
                CAST('ind_neut_only_v1' AS VARCHAR) AS candidate_scheme_id,
                PERCENT_RANK() OVER (
                    PARTITION BY signal_date
                    ORDER BY pr_rev_ind_neut ASC, instrument ASC
                ) AS model_score_D0,
                1 AS score_component_count
            FROM nr_ind WHERE ranking_eligible_D0 AND pr_rev_ind_neut IS NOT NULL
            """
        )

        score_output = run_dir / "model_scores_D0_combo.parquet"
        con.execute(f"""
            COPY (
                SELECT CAST(NULL AS BIGINT) AS snapshot_id, * FROM score_ind_neut_tail
                UNION ALL
                SELECT CAST(NULL AS BIGINT) AS snapshot_id, * FROM score_raw_tail
                UNION ALL
                SELECT CAST(NULL AS BIGINT) AS snapshot_id, * FROM score_ind_neut_only
            ) TO {sql_path(score_output)} (FORMAT PARQUET)
        """)

        # Diagnostic
        print(f"{'='*90}")
        print(f"{'Scheme':<32} {'Full IC':>10} {'Train IC':>10} {'Valid IC':>10} {'Valid-Train':>12}")
        print(f"{'-'*90}")

        p98_full = compute_ic(con, P98_SCORE_PATH, P98_SCHEME_ID, label_path)
        p98_train = compute_ic(con, P98_SCORE_PATH, P98_SCHEME_ID, label_path, date_end=TRAIN_END)
        p98_valid = compute_ic(con, P98_SCORE_PATH, P98_SCHEME_ID, label_path,
                                date_start=VALID_START, date_end=VALID_END)
        p_f, p_t, p_v = (p98_full["median_ic"] if p98_full else 0,
                         p98_train["median_ic"] if p98_train else 0,
                         p98_valid["median_ic"] if p98_valid else 0)
        print(f"{'p98 (baseline)':<32} {p_f:>10.6f} {p_t:>10.6f} {p_v:>10.6f} {p_v-p_t:>+12.6f}")

        for sid in ["ind_neut_tail_p98_v1", "raw_tail_p98_v1", "ind_neut_only_v1"]:
            full = compute_ic(con, score_output, sid, label_path)
            train = compute_ic(con, score_output, sid, label_path, date_end=TRAIN_END)
            valid = compute_ic(con, score_output, sid, label_path,
                               date_start=VALID_START, date_end=VALID_END)
            if full is None:
                continue
            print(f"{sid:<32} {full['median_ic']:>10.6f} "
                  f"{train['median_ic'] if train else 0:>10.6f} "
                  f"{valid['median_ic'] if valid else 0:>10.6f} "
                  f"{(valid['median_ic'] if valid else 0) - (train['median_ic'] if train else 0):>+12.6f}")

    finally:
        con.close()

    print(f"\nDone. Scores: {score_output}")


if __name__ == "__main__":
    main()
