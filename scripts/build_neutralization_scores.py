#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Factor neutralization experiment.

Compare:
  1. pr_rev_raw_v1          — reversal_5d PERCENT_RANK, no neutralization (baseline)
  2. pr_rev_size_neut_v1    — reversal_5d PR → residualize log(total_mv) → re-rank
  3. pr_rev_ind_neut_v1     — reversal_5d PR → residualize industry L1 → re-rank
  4. pr_rev_size_ind_neut_v1— reversal_5d PR → residualize both → re-rank
  5. p98_size_neut_v1       — p98 tail-excluded + size neutralized intermediate
  6. p98_ind_neut_v1        — p98 tail-excluded + industry neutralized intermediate

Method:
  - Size: pr_score - (REGR_SLOPE * log_mkt_cap + REGR_INTERCEPT), per signal_date
  - Industry: pr_score - AVG(pr_score) OVER (PARTITION BY signal_date, l1_code)
  - After neutralization: PERCENT_RANK residual → [0,1] score

All operations cross-sectional within signal_date → PIT-safe.
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

    run_dir = ARTIFACTS_RUN_STATE_DIR / "exploratory_neutralization_v1"
    run_dir.mkdir(parents=True, exist_ok=True)
    for fname in ["project_label_panel.parquet", "project_sample_panel.parquet"]:
        src = ARTIFACTS_RUN_STATE_DIR / LABEL_RUN / fname
        dst = run_dir / fname
        if not dst.exists():
            dst.symlink_to(src)

    con = duckdb.connect()
    try:
        con.execute(f"ATTACH {sql_path(source_db_path)} AS warehouse_db (READ_ONLY)")

        # ---- Step 1: Build base data ----
        # reversal_5d PERCENT_RANK + log(total_mv) + industry L1
        con.execute(
            f"""
            CREATE OR REPLACE VIEW base_data AS
            WITH bars AS (
                SELECT ts_code AS instrument, trade_date AS signal_date,
                       adj_close, LN(NULLIF(total_mv, 0)) AS log_mkt_cap
                FROM warehouse_db.serving.vw_bars_daily
                WHERE snapshot_id = {sql_quote(snapshot_id)}
            ),
            features AS (
                SELECT instrument, signal_date, log_mkt_cap,
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
            ),
            ranked AS (
                SELECT w.*, p.ranking_eligible_D0,
                    PERCENT_RANK() OVER (
                        PARTITION BY w.signal_date
                        ORDER BY w.reversal_5d_raw ASC, w.instrument ASC
                    ) AS pr_rev_raw,
                    PERCENT_RANK() OVER (
                        PARTITION BY w.signal_date
                        ORDER BY w.reversal_5d_raw DESC, w.instrument ASC
                    ) AS pr_mom_raw
                FROM with_ind w
                JOIN read_parquet({sql_path(sample_path)}) p
                  ON w.instrument = p.instrument AND w.signal_date = p.signal_date
                WHERE w.reversal_5d_raw IS NOT NULL
            )
            SELECT * FROM ranked
            """
        )

        # ---- Step 2: Neutralize ----
        # Size neutralization: residualize pr_rev_raw on log_mkt_cap
        con.execute(
            """
            CREATE OR REPLACE VIEW size_neut AS
            SELECT signal_date, instrument, ranking_eligible_D0, pr_rev_raw, pr_mom_raw,
                pr_rev_raw - (
                    REGR_SLOPE(pr_rev_raw, log_mkt_cap) OVER (
                        PARTITION BY signal_date
                    ) * log_mkt_cap
                    + REGR_INTERCEPT(pr_rev_raw, log_mkt_cap) OVER (
                        PARTITION BY signal_date
                    )
                ) AS pr_rev_size_neut,
                pr_mom_raw - (
                    REGR_SLOPE(pr_mom_raw, log_mkt_cap) OVER (
                        PARTITION BY signal_date
                    ) * log_mkt_cap
                    + REGR_INTERCEPT(pr_mom_raw, log_mkt_cap) OVER (
                        PARTITION BY signal_date
                    )
                ) AS pr_mom_size_neut,
                log_mkt_cap
            FROM base_data
            WHERE log_mkt_cap IS NOT NULL AND pr_rev_raw IS NOT NULL
            """
        )

        # Industry neutralization: subtract industry mean
        con.execute(
            """
            CREATE OR REPLACE VIEW ind_neut AS
            SELECT signal_date, instrument, ranking_eligible_D0, pr_rev_raw, pr_mom_raw,
                pr_rev_raw - AVG(pr_rev_raw) OVER (
                    PARTITION BY signal_date, l1_code
                ) AS pr_rev_ind_neut,
                pr_mom_raw - AVG(pr_mom_raw) OVER (
                    PARTITION BY signal_date, l1_code
                ) AS pr_mom_ind_neut,
                l1_code
            FROM base_data
            WHERE l1_code IS NOT NULL AND pr_rev_raw IS NOT NULL
            """
        )

        # Both: size first, then industry
        con.execute(
            """
            CREATE OR REPLACE VIEW both_neut AS
            WITH size_done AS (
                SELECT s.signal_date, s.instrument, s.ranking_eligible_d0,
                    s.pr_rev_raw, s.pr_mom_raw,
                    s.pr_rev_size_neut, s.pr_mom_size_neut,
                    s.log_mkt_cap,
                    b.l1_code
                FROM size_neut s
                JOIN (SELECT DISTINCT instrument, signal_date, l1_code FROM base_data) b
                  ON s.instrument = b.instrument AND s.signal_date = b.signal_date
            ),
            ind_done AS (
                SELECT *,
                    pr_rev_size_neut - AVG(pr_rev_size_neut) OVER (
                        PARTITION BY signal_date, l1_code
                    ) AS pr_rev_both_neut,
                    pr_mom_size_neut - AVG(pr_mom_size_neut) OVER (
                        PARTITION BY signal_date, l1_code
                    ) AS pr_mom_both_neut
                FROM size_done
            )
            SELECT * FROM ind_done
            """
        )

        # ---- Step 3: Build final PERCENT_RANK scores ----
        union_parts = []

        # 1. Raw reversal (no neutralization) — baseline
        union_parts.append(
            """
            SELECT CAST(NULL AS BIGINT) AS snapshot_id, instrument, signal_date,
                CAST('pr_rev_raw_v1' AS VARCHAR) AS candidate_scheme_id,
                pr_rev_raw AS model_score_D0, 1 AS score_component_count
            FROM base_data WHERE ranking_eligible_D0 AND pr_rev_raw IS NOT NULL
            """
        )

        # 2. Size neutralized reversal
        union_parts.append(
            """
            SELECT CAST(NULL AS BIGINT) AS snapshot_id, instrument, signal_date,
                CAST('pr_rev_size_neut_v1' AS VARCHAR) AS candidate_scheme_id,
                PERCENT_RANK() OVER (PARTITION BY signal_date
                    ORDER BY pr_rev_size_neut ASC, instrument ASC
                ) AS model_score_D0, 1 AS score_component_count
            FROM size_neut WHERE ranking_eligible_D0 AND pr_rev_size_neut IS NOT NULL
            """
        )

        # 3. Industry neutralized reversal
        union_parts.append(
            """
            SELECT CAST(NULL AS BIGINT) AS snapshot_id, instrument, signal_date,
                CAST('pr_rev_ind_neut_v1' AS VARCHAR) AS candidate_scheme_id,
                PERCENT_RANK() OVER (PARTITION BY signal_date
                    ORDER BY pr_rev_ind_neut ASC, instrument ASC
                ) AS model_score_D0, 1 AS score_component_count
            FROM ind_neut WHERE ranking_eligible_D0 AND pr_rev_ind_neut IS NOT NULL
            """
        )

        # 4. Size + industry neutralized reversal
        union_parts.append(
            """
            SELECT CAST(NULL AS BIGINT) AS snapshot_id, instrument, signal_date,
                CAST('pr_rev_size_ind_neut_v1' AS VARCHAR) AS candidate_scheme_id,
                PERCENT_RANK() OVER (PARTITION BY signal_date
                    ORDER BY pr_rev_both_neut ASC, instrument ASC
                ) AS model_score_D0, 1 AS score_component_count
            FROM both_neut WHERE ranking_eligible_D0 AND pr_rev_both_neut IS NOT NULL
            """
        )

        # 5. Size neutralized MOMENTUM direction (to compare with p98)
        union_parts.append(
            """
            SELECT CAST(NULL AS BIGINT) AS snapshot_id, instrument, signal_date,
                CAST('pr_mom_size_neut_v1' AS VARCHAR) AS candidate_scheme_id,
                PERCENT_RANK() OVER (PARTITION BY signal_date
                    ORDER BY pr_mom_size_neut ASC, instrument ASC
                ) AS model_score_D0, 1 AS score_component_count
            FROM size_neut WHERE ranking_eligible_D0 AND pr_mom_size_neut IS NOT NULL
            """
        )

        # 6. Industry neutralized momentum
        union_parts.append(
            """
            SELECT CAST(NULL AS BIGINT) AS snapshot_id, instrument, signal_date,
                CAST('pr_mom_ind_neut_v1' AS VARCHAR) AS candidate_scheme_id,
                PERCENT_RANK() OVER (PARTITION BY signal_date
                    ORDER BY pr_mom_ind_neut ASC, instrument ASC
                ) AS model_score_D0, 1 AS score_component_count
            FROM ind_neut WHERE ranking_eligible_D0 AND pr_mom_ind_neut IS NOT NULL
            """
        )

        # 7. Size + industry neutralized momentum
        union_parts.append(
            """
            SELECT CAST(NULL AS BIGINT) AS snapshot_id, instrument, signal_date,
                CAST('pr_mom_size_ind_neut_v1' AS VARCHAR) AS candidate_scheme_id,
                PERCENT_RANK() OVER (PARTITION BY signal_date
                    ORDER BY pr_mom_both_neut ASC, instrument ASC
                ) AS model_score_D0, 1 AS score_component_count
            FROM both_neut WHERE ranking_eligible_D0 AND pr_mom_both_neut IS NOT NULL
            """
        )

        # 8. Raw momentum (p98 direction, no neutralization)
        union_parts.append(
            """
            SELECT CAST(NULL AS BIGINT) AS snapshot_id, instrument, signal_date,
                CAST('pr_mom_raw_v1' AS VARCHAR) AS candidate_scheme_id,
                pr_mom_raw AS model_score_D0, 1 AS score_component_count
            FROM base_data WHERE ranking_eligible_D0 AND pr_mom_raw IS NOT NULL
            """
        )

        score_output = run_dir / "model_scores_D0_neut.parquet"
        union_sql = " UNION ALL ".join(union_parts)
        con.execute(f"COPY ({union_sql}) TO {sql_path(score_output)} (FORMAT PARQUET)")

        # ---- Step 4: Diagnostic ----
        # Load p98 for comparison
        all_schemes = [
            "pr_rev_raw_v1",
            "pr_rev_size_neut_v1",
            "pr_rev_ind_neut_v1",
            "pr_rev_size_ind_neut_v1",
            "pr_mom_raw_v1",
            "pr_mom_size_neut_v1",
            "pr_mom_ind_neut_v1",
            "pr_mom_size_ind_neut_v1",
        ]

        print("=" * 100)
        print(f"{'Scheme':<32} {'Full IC':>10} {'Train IC':>10} {'Valid IC':>10} {'Valid-Train':>12}")
        print("-" * 100)

        # p98
        p98_full = compute_ic(con, P98_SCORE_PATH, P98_SCHEME_ID, label_path)
        p98_train = compute_ic(con, P98_SCORE_PATH, P98_SCHEME_ID, label_path, date_end=TRAIN_END)
        p98_valid = compute_ic(con, P98_SCORE_PATH, P98_SCHEME_ID, label_path,
                                date_start=VALID_START, date_end=VALID_END)
        p98_f = p98_full["median_ic"] if p98_full else 0
        p98_t = p98_train["median_ic"] if p98_train else 0
        p98_v = p98_valid["median_ic"] if p98_valid else 0
        print(f"{'p98 (baseline)':<32} {p98_f:>10.6f} {p98_t:>10.6f} {p98_v:>10.6f} {p98_v-p98_t:>+12.6f}")

        best_scheme = None
        best_valid_ic = -99

        for sid in all_schemes:
            full = compute_ic(con, score_output, sid, label_path)
            train = compute_ic(con, score_output, sid, label_path, date_end=TRAIN_END)
            valid = compute_ic(con, score_output, sid, label_path,
                               date_start=VALID_START, date_end=VALID_END)
            if full is None:
                continue

            f_ic = full["median_ic"]
            t_ic = train["median_ic"] if train else 0
            v_ic = valid["median_ic"] if valid else 0

            print(f"{sid:<32} {f_ic:>10.6f} {t_ic:>10.6f} {v_ic:>10.6f} {v_ic-t_ic:>+12.6f}")

            if v_ic > best_valid_ic:
                best_valid_ic = v_ic
                best_scheme = {"scheme_id": sid, "full_ic": f_ic, "train_ic": t_ic, "valid_ic": v_ic}

        if best_scheme:
            vs_p98 = best_scheme["valid_ic"] - p98_v
            print(f"\n  Best valid: {best_scheme['scheme_id']} (IC={best_scheme['valid_ic']:.6f}, vs p98: {vs_p98:+.6f})")

        # Also compute the size exposure of p98 vs neutralized
        print("\n=== Size Exposure (CORR with log_mkt_cap, full period) ===")
        p98_exposure = con.execute(
            f"""
            WITH j AS (
                SELECT p.model_score_D0 AS score, b.log_mkt_cap
                FROM read_parquet({sql_path(P98_SCORE_PATH)}) p
                JOIN base_data b ON p.instrument = b.instrument AND p.signal_date = b.signal_date
                WHERE p.candidate_scheme_id = {sql_quote(P98_SCHEME_ID)}
                  AND p.model_score_D0 IS NOT NULL AND b.log_mkt_cap IS NOT NULL
            )
            SELECT CORR(score, log_mkt_cap) FROM j
            """
        ).fetchone()[0]
        print(f"  p98 score vs log_mkt_cap: {p98_exposure:+.6f}")

        for sid in ["pr_rev_raw_v1", "pr_rev_size_neut_v1"]:
            exp = con.execute(
                f"""
                WITH j AS (
                    SELECT s.model_score_D0 AS score, b.log_mkt_cap
                    FROM read_parquet({sql_path(score_output)}) s
                    JOIN base_data b ON s.instrument = b.instrument AND s.signal_date = b.signal_date
                    WHERE s.candidate_scheme_id = {sql_quote(sid)}
                      AND s.model_score_D0 IS NOT NULL AND b.log_mkt_cap IS NOT NULL
                )
                SELECT CORR(score, log_mkt_cap) FROM j
                """
            ).fetchone()[0]
            print(f"  {sid} vs log_mkt_cap: {exp:+.6f}")

    finally:
        con.close()

    print(f"\nDone. Scores: {score_output}")


if __name__ == "__main__":
    main()
