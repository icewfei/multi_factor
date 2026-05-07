#!/opt/anaconda3/envs/quant_trade/bin/python
"""
V2: Parametric power transforms on PERCENT_RANK scores.

Approach:
  1. For each feature, compute PERCENT_RANK → x ∈ [0,1]
  2. Apply f(x) = x^alpha (power transform) with various alpha values
  3. For each alpha, compute IC on TRAINING data only
  4. Select best alpha per feature by IC magnitude
  5. Apply best-alpha transform to all dates

This is smoother and more parametric than discrete decile bucketing.

Also adds: two-sided tail exclusion for reversal (generalizing p98).
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

TRAIN_START = "20100101"
TRAIN_END = "20181231"

ALPHAS = [0.125, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 8.0]

# Features to transform — focus on the ones with strongest raw signal
FEATURES = [
    "reversal_5d",
    "momentum_60_5",
    "intraday_trend_bias_20d",
    "liquidity_trend_20_60",
    "upside_range_share_20d",
    "intraday_reversal_asymmetry_20d",
]

FEATURE_EXPRS = {
    "reversal_5d": "(adj_close / LAG(adj_close, 5) OVER w - 1.0)",
    "momentum_60_5": "(LAG(adj_close, 5) OVER w / LAG(adj_close, 60) OVER w - 1.0)",
    "intraday_trend_bias_20d": (
        "AVG(CASE WHEN adj_open > 0 THEN adj_close / adj_open - 1.0 ELSE NULL END) OVER w20"
    ),
    "liquidity_trend_20_60": (
        "AVG(LN(GREATEST(amount, 0.0) + 1.0)) OVER w20 "
        "- AVG(LN(GREATEST(amount, 0.0) + 1.0)) OVER w60"
    ),
    "upside_range_share_20d": (
        "CASE WHEN SUM(CASE WHEN adj_close > 0 THEN (adj_high - adj_low) / adj_close ELSE 0.0 END) "
        "OVER w20 > 0 "
        "THEN SUM(CASE WHEN pct_chg / 100.0 > 0 AND adj_close > 0 "
        "THEN (adj_high - adj_low) / adj_close ELSE 0.0 END) OVER w20 "
        "/ SUM(CASE WHEN adj_close > 0 THEN (adj_high - adj_low) / adj_close ELSE 0.0 END) "
        "OVER w20 ELSE NULL END"
    ),
    "intraday_reversal_asymmetry_20d": (
        "AVG(CASE WHEN (adj_close / adj_open - 1.0) < 0 AND adj_high > adj_low "
        "THEN (adj_close - adj_low) / (adj_high - adj_low) ELSE NULL END) OVER w20 "
        "- AVG(CASE WHEN (adj_close / adj_open - 1.0) > 0 AND adj_high > adj_low "
        "THEN (adj_high - adj_close) / (adj_high - adj_low) ELSE NULL END) OVER w20"
    ),
}


def sql_quote(v):
    return "'" + str(v).replace("'", "''") + "'"


def sql_path(p):
    return sql_quote(Path(p).resolve().as_posix())


def write_json(path, payload):
    Path(path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


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

    run_dir = ARTIFACTS_RUN_STATE_DIR / "exploratory_power_transform_v1"
    run_dir.mkdir(parents=True, exist_ok=True)

    for fname in ["project_label_panel.parquet", "project_sample_panel.parquet"]:
        src = ARTIFACTS_RUN_STATE_DIR / LABEL_RUN / fname
        dst = run_dir / fname
        if not dst.exists():
            dst.symlink_to(src)

    con = duckdb.connect()
    try:
        con.execute(f"ATTACH {sql_path(source_db_path)} AS warehouse_db (READ_ONLY)")

        # ---- Step 1: Build features + PERCENT_RANK ----
        feature_expr_list = ",\n".join(
            f"    {expr} AS {name}_raw" for name, expr in FEATURE_EXPRS.items()
        )

        con.execute(
            f"""
            CREATE OR REPLACE VIEW bar_features AS
            WITH bars AS (
                SELECT ts_code AS instrument, trade_date AS signal_date,
                       adj_open, adj_high, adj_low, adj_close, amount, pct_chg
                FROM warehouse_db.serving.vw_bars_daily
                WHERE snapshot_id = {sql_quote(snapshot_id)}
            )
            SELECT instrument, signal_date,
{feature_expr_list}
            FROM bars
            WINDOW
                w AS (PARTITION BY instrument ORDER BY signal_date),
                w20 AS (PARTITION BY instrument ORDER BY signal_date
                        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW),
                w60 AS (PARTITION BY instrument ORDER BY signal_date
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW)
            """
        )

        con.execute(
            f"""
            CREATE OR REPLACE VIEW feature_ranks AS
            SELECT
                f.instrument,
                f.signal_date,
                p.ranking_eligible_D0,
                {', '.join(
                    f'PERCENT_RANK() OVER (PARTITION BY f.signal_date ORDER BY f.{name}_raw ASC, f.instrument ASC) AS pr_{name}'
                    for name in FEATURES
                )}
            FROM bar_features f
            JOIN read_parquet({sql_path(sample_path)}) p
              ON f.instrument = p.instrument AND f.signal_date = p.signal_date
            """
        )

        # ---- Step 2: For each feature + alpha, compute IC on TRAINING data ----
        con.execute(
            f"""
            CREATE OR REPLACE VIEW train_ranks AS
            SELECT r.*, l.label_5d_next_open_close AS oracle_label
            FROM feature_ranks r
            JOIN read_parquet({sql_path(label_path)}) l
              ON r.instrument = l.instrument AND r.signal_date = l.signal_date
            WHERE r.signal_date BETWEEN {sql_quote(TRAIN_START)} AND {sql_quote(TRAIN_END)}
              AND r.ranking_eligible_D0
              AND l.label_5d_next_open_close IS NOT NULL
            """
        )

        best_alphas = {}
        alpha_tuning = []

        for feature_name in FEATURES:
            pr_col = f"pr_{feature_name}"
            best_alpha = 1.0
            best_ic = 0.0

            for alpha in ALPHAS:
                rows = con.execute(
                    f"""
                    WITH scored AS (
                        SELECT signal_date,
                            POWER(NULLIF({pr_col}, 0.0), {alpha}) AS power_score,
                            oracle_label
                        FROM train_ranks
                        WHERE {pr_col} IS NOT NULL AND {pr_col} > 0
                    )
                    SELECT signal_date, CORR(power_score, oracle_label) AS ic
                    FROM scored
                    GROUP BY signal_date HAVING COUNT(*) >= 20
                    """
                ).fetchall()

                ic_series = [float(r[1]) for r in rows if r[1] is not None]
                if not ic_series:
                    continue

                n = len(ic_series)
                srt = sorted(ic_series)
                med_ic = srt[n // 2] if n % 2 else (srt[n // 2 - 1] + srt[n // 2]) / 2.0

                if abs(med_ic) > abs(best_ic):
                    best_ic = med_ic
                    best_alpha = alpha

            best_alphas[feature_name] = {"alpha": best_alpha, "train_ic": best_ic}
            alpha_tuning.append({
                "feature": feature_name,
                "best_alpha": best_alpha,
                "best_train_ic": best_ic,
            })
            print(f"  {feature_name}: best_alpha={best_alpha}, train_IC={best_ic:+.6f}")

        write_json(run_dir / "best_alphas.json", {
            "tuned_on": f"training {TRAIN_START}-{TRAIN_END}",
            "alphas_tested": ALPHAS,
            "best_alphas": best_alphas,
            "tuning_results": alpha_tuning,
        })

        # ---- Step 3: Build final scores ----
        union_parts = []

        # Single-feature power transform schemes
        for feature_name in FEATURES:
            alpha = best_alphas[feature_name]["alpha"]
            pr_col = f"pr_{feature_name}"
            scheme_id = f"power_{feature_name}_v1"

            union_parts.append(
                f"""
                SELECT
                    CAST(NULL AS BIGINT) AS snapshot_id,
                    instrument,
                    signal_date,
                    CAST({sql_quote(scheme_id)} AS VARCHAR) AS candidate_scheme_id,
                    POWER(NULLIF({pr_col}, 0.0), {alpha}) AS model_score_D0,
                    1 AS score_component_count
                FROM feature_ranks
                WHERE ranking_eligible_D0 AND {pr_col} IS NOT NULL AND {pr_col} > 0
                """
            )

        # Two-sided tail exclusion: p98's approach generalized
        # reversal_tail_exclude_both_v1: exclude BOTH bottom 2% and top 2% of reversal
        con.execute(
            """
            CREATE OR REPLACE VIEW rev_both_scores AS
            WITH nr AS (
                SELECT
                    instrument,
                    signal_date,
                    ranking_eligible_D0,
                    -1.0 * pr_reversal_5d AS nr_score
                FROM feature_ranks
                WHERE ranking_eligible_D0 AND pr_reversal_5d IS NOT NULL
            ),
            daily_pct AS (
                SELECT signal_date,
                    PERCENTILE_CONT(0.02) WITHIN GROUP (ORDER BY nr_score) AS p02,
                    PERCENTILE_CONT(0.98) WITHIN GROUP (ORDER BY nr_score) AS p98
                FROM nr GROUP BY signal_date
            ),
            filtered AS (
                SELECT n.instrument, n.signal_date, n.nr_score
                FROM nr n JOIN daily_pct p ON n.signal_date = p.signal_date
                WHERE n.nr_score > p.p02 AND n.nr_score < p.p98
            )
            SELECT
                CAST(NULL AS BIGINT) AS snapshot_id,
                instrument,
                signal_date,
                CAST('reversal_tail_exclude_both_v1' AS VARCHAR) AS candidate_scheme_id,
                PERCENT_RANK() OVER (
                    PARTITION BY signal_date
                    ORDER BY nr_score ASC, instrument ASC
                ) AS model_score_D0,
                1 AS score_component_count
            FROM filtered
            """
        )
        union_parts.append("SELECT * FROM rev_both_scores")

        # Power-transformed p98 composite
        rev_alpha = best_alphas["reversal_5d"]["alpha"]
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

        union_parts.append(
            f"""
            SELECT
                CAST(NULL AS BIGINT) AS snapshot_id,
                a.instrument,
                a.signal_date,
                CAST('power_rev_p98_ew_v1' AS VARCHAR) AS candidate_scheme_id,
                0.5 * COALESCE(POWER(NULLIF(a.pr_reversal_5d, 0.0), {rev_alpha}), 0.0)
                    + 0.5 * COALESCE(p.p98_score, 0.0) AS model_score_D0,
                2 AS score_component_count
            FROM feature_ranks a
            LEFT JOIN p98_scores p
              ON a.instrument = p.instrument AND a.signal_date = p.signal_date
            WHERE a.ranking_eligible_D0
              AND a.pr_reversal_5d IS NOT NULL AND a.pr_reversal_5d > 0
            """
        )

        union_sql = " UNION ALL ".join(union_parts)
        score_output = run_dir / "model_scores_D0_power.parquet"
        con.execute(f"COPY ({union_sql}) TO {sql_path(score_output)} (FORMAT PARQUET)")

        # ---- Step 4: Compute IC for each scheme ----
        print("\n=== Power Transform IC Summary ===")
        print(f"  p98 baseline: IC = 0.046045")

        all_schemes = (
            [f"power_{fn}_v1" for fn in FEATURES]
            + ["reversal_tail_exclude_both_v1", "power_rev_p98_ew_v1"]
        )

        best_result = None
        for scheme_id in all_schemes:
            # Check if scheme has any rows
            count = con.execute(
                f"""
                SELECT COUNT(*) FROM read_parquet({sql_path(score_output)})
                WHERE candidate_scheme_id = {sql_quote(scheme_id)}
                """
            ).fetchone()
            if not count or count[0] == 0:
                continue

            rows = con.execute(
                f"""
                WITH joined AS (
                    SELECT s.signal_date, s.model_score_D0 AS score_val,
                           l.label_5d_next_open_close AS oracle_label
                    FROM read_parquet({sql_path(score_output)}) s
                    JOIN read_parquet({sql_path(label_path)}) l
                      ON s.instrument = l.instrument AND s.signal_date = l.signal_date
                    WHERE s.candidate_scheme_id = {sql_quote(scheme_id)}
                      AND s.model_score_D0 IS NOT NULL
                      AND l.label_5d_next_open_close IS NOT NULL
                )
                SELECT signal_date, CORR(score_val, oracle_label) AS ic
                FROM joined GROUP BY signal_date HAVING COUNT(*) >= 20
                """
            ).fetchall()

            ic_series = [float(r[1]) for r in rows if r[1] is not None]
            if not ic_series:
                continue

            n = len(ic_series)
            srt = sorted(ic_series)
            med = srt[n // 2] if n % 2 else (srt[n // 2 - 1] + srt[n // 2]) / 2.0

            print(f"  {scheme_id:<45} IC = {med:+.6f}  (n={n})")

            if best_result is None or abs(med) > abs(best_result["ic"]):
                best_result = {"scheme": scheme_id, "ic": med}

        if best_result:
            print(f"\n  Best: {best_result['scheme']} (IC = {best_result['ic']:+.6f})")
            vs_p98 = abs(best_result["ic"]) - 0.046045
            print(f"  vs p98: delta = {vs_p98:+.6f}")

        write_json(run_dir / "power_transform_diagnostic.json", {
            "as_of": datetime.now().strftime("%Y%m%d"),
            "p98_baseline_ic": 0.046045,
            "best_alphas": best_alphas,
            "best_scheme": best_result,
        })

    finally:
        con.close()

    print(f"\nDone. Scores: {score_output}")


if __name__ == "__main__":
    main()
