#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Phase A: Decile-based non-linear feature transformation.

Core idea:
  p98's tail exclusion is a special case: one segment gets weight 0, rest equal weight.
  Generalize to: learn the optimal bucket→expected_return mapping from training oracle labels.

Method:
  1. On TRAINING data only (2010-2018), for each feature:
     - Per day, split stocks into 10 deciles by feature value
     - Compute average oracle label (5d forward return) per decile
     - Average across all training days → 10 learned bucket scores
  2. On ANY date: map feature value → bucket → learned score → PERCENT_RANK

Features tested (14 raw features from daily bars):
  reversal_5d, momentum_60_5, momentum_120_20, momentum_250_20, momentum_20_5,
  intraday_trend_bias_20d, upside_range_share_20d, intraday_reversal_asymmetry_20d,
  liquidity_trend_20_60, liquidity_trend_60_120, volatility_20d, volatility_60d,
  trend_consistency_20d, trend_consistency_60d

Candidate schemes:
  1. decile_reversal_5d_v1        — decile-mapped reversal_5d (compare with p98)
  2. decile_momentum_60_5_v1      — decile-mapped momentum
  3. decile_intraday_bias_v1      — decile-mapped intraday trend bias
  4. decile_liquidity_trend_v1    — decile-mapped liquidity_trend_20_60
  5. decile_composite_top3_ew_v1  — equal-weight of top-3 decile features by IC
  6. decile_p98_ew_v1             — p98 + best decile feature, equal weight

Outputs:
  - model_scores_D0_decile.parquet — all candidate scores
  - decile_bucket_scores.json      — learned bucket mappings (for audit)
  - non_linearity_diagnostic.json  — full diagnostic report
"""

from __future__ import annotations

import json
import random
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

N_BOOTSTRAP = 10000
BOOTSTRAP_SEED = 42

FEATURE_SPECS = {
    "reversal_5d": {
        "expr": "(adj_close / LAG(adj_close, 5) OVER w - 1.0)",
        "description": "5-day reversal",
        "expected_shape": "left-tail reversal, right-tail momentum",
    },
    "momentum_20_5": {
        "expr": "(LAG(adj_close, 5) OVER w / LAG(adj_close, 20) OVER w - 1.0)",
        "description": "20-day lookback, 5-day skip momentum",
    },
    "momentum_60_5": {
        "expr": "(LAG(adj_close, 5) OVER w / LAG(adj_close, 60) OVER w - 1.0)",
        "description": "60-day lookback, 5-day skip momentum",
    },
    "momentum_120_20": {
        "expr": "(LAG(adj_close, 20) OVER w / LAG(adj_close, 120) OVER w - 1.0)",
        "description": "120-day lookback momentum",
    },
    "momentum_250_20": {
        "expr": "(LAG(adj_close, 20) OVER w / LAG(adj_close, 250) OVER w - 1.0)",
        "description": "250-day lookback momentum",
    },
    "intraday_trend_bias_20d": {
        "expr": "AVG(CASE WHEN adj_open > 0 THEN adj_close / adj_open - 1.0 ELSE NULL END) OVER w20",
        "description": "20-day average intraday return",
    },
    "upside_range_share_20d": {
        "expr": (
            "CASE WHEN SUM(CASE WHEN adj_close > 0 THEN (adj_high - adj_low) / adj_close ELSE 0.0 END) "
            "OVER w20 > 0 "
            "THEN SUM(CASE WHEN pct_chg / 100.0 > 0 AND adj_close > 0 "
            "THEN (adj_high - adj_low) / adj_close ELSE 0.0 END) OVER w20 "
            "/ SUM(CASE WHEN adj_close > 0 THEN (adj_high - adj_low) / adj_close ELSE 0.0 END) "
            "OVER w20 ELSE NULL END"
        ),
        "description": "Upside range share of total range",
    },
    "intraday_reversal_asymmetry_20d": {
        "expr": (
            "AVG(CASE WHEN (adj_close / adj_open - 1.0) < 0 AND adj_high > adj_low "
            "THEN (adj_close - adj_low) / (adj_high - adj_low) ELSE NULL END) OVER w20 "
            "- AVG(CASE WHEN (adj_close / adj_open - 1.0) > 0 AND adj_high > adj_low "
            "THEN (adj_high - adj_close) / (adj_high - adj_low) ELSE NULL END) OVER w20"
        ),
        "description": "Asymmetry of intraday reversal: down-day recovery minus up-day fade",
    },
    "liquidity_trend_20_60": {
        "expr": (
            "AVG(LN(GREATEST(amount, 0.0) + 1.0)) OVER w20 "
            "- AVG(LN(GREATEST(amount, 0.0) + 1.0)) OVER w60"
        ),
        "description": "Short-term minus medium-term log amount",
    },
    "liquidity_trend_60_120": {
        "expr": (
            "AVG(LN(GREATEST(amount, 0.0) + 1.0)) OVER w60 "
            "- AVG(LN(GREATEST(amount, 0.0) + 1.0)) OVER w120"
        ),
        "description": "Medium-term minus long-term log amount",
    },
    "volatility_20d": {
        "expr": "STDDEV_SAMP(pct_chg / 100.0) OVER w20",
        "description": "20-day return volatility",
    },
    "volatility_60d": {
        "expr": "STDDEV_SAMP(pct_chg / 100.0) OVER w60",
        "description": "60-day return volatility",
    },
    "trend_consistency_20d": {
        "expr": "AVG(CASE WHEN pct_chg / 100.0 > 0 THEN 1.0 ELSE 0.0 END) OVER w20",
        "description": "Fraction of up days in 20-day window",
    },
    "trend_consistency_60d": {
        "expr": "AVG(CASE WHEN pct_chg / 100.0 > 0 THEN 1.0 ELSE 0.0 END) OVER w60",
        "description": "Fraction of up days in 60-day window",
    },
}


def sql_quote(v: str) -> str:
    return "'" + v.replace("'", "''") + "'"


def sql_path(p: Path) -> str:
    return sql_quote(p.resolve().as_posix())


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    run_input = json.loads(
        (CONTRACTS_DIR / "run_input_contract.research_trainval_20211231.json").read_text("utf-8")
    )
    snapshot_id = run_input["snapshot_id"]
    source_db_path = (
        Path(run_input["source_root"]["snapshot_path"]) / "duckdb" / "warehouse.duckdb"
    )
    if not source_db_path.exists():
        raise FileNotFoundError(f"Shared warehouse DB not found: {source_db_path}")

    label_path = ARTIFACTS_RUN_STATE_DIR / LABEL_RUN / "project_label_panel.parquet"
    sample_path = ARTIFACTS_RUN_STATE_DIR / LABEL_RUN / "project_sample_panel.parquet"

    run_dir = ARTIFACTS_RUN_STATE_DIR / "exploratory_decile_nonlinear_v1"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Symlink panels
    for fname in ["project_label_panel.parquet", "project_sample_panel.parquet"]:
        src = ARTIFACTS_RUN_STATE_DIR / LABEL_RUN / fname
        dst = run_dir / fname
        if not dst.exists():
            dst.symlink_to(src)

    score_output = run_dir / "model_scores_D0_decile.parquet"
    bucket_scores_output = run_dir / "decile_bucket_scores.json"
    diagnostic_output = run_dir / "non_linearity_diagnostic.json"

    con = duckdb.connect()
    try:
        con.execute(f"ATTACH {sql_path(source_db_path)} AS warehouse_db (READ_ONLY)")

        # ---- Step 1: Build raw features on the full trainval period ----
        feature_exprs = ",\n".join(
            f"    {expr} AS {name}_raw"
            for name, spec in FEATURE_SPECS.items()
            for expr in [spec["expr"]]
        )

        con.execute(
            f"""
            CREATE OR REPLACE VIEW bar_features AS
            WITH bars AS (
                SELECT
                    ts_code AS instrument,
                    trade_date AS signal_date,
                    adj_open,
                    adj_high,
                    adj_low,
                    adj_close,
                    amount,
                    pct_chg
                FROM warehouse_db.serving.vw_bars_daily
                WHERE snapshot_id = {sql_quote(snapshot_id)}
            )
            SELECT
                instrument,
                signal_date,
{feature_exprs}
            FROM bars
            WINDOW
                w AS (PARTITION BY instrument ORDER BY signal_date),
                w20 AS (
                    PARTITION BY instrument
                    ORDER BY signal_date
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                ),
                w60 AS (
                    PARTITION BY instrument
                    ORDER BY signal_date
                    ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                ),
                w120 AS (
                    PARTITION BY instrument
                    ORDER BY signal_date
                    ROWS BETWEEN 119 PRECEDING AND CURRENT ROW
                )
            """
        )

        # Join with labels
        con.execute(
            f"""
            CREATE OR REPLACE VIEW diag_data AS
            SELECT
                b.instrument,
                b.signal_date,
                b.*,
                l.label_5d_next_open_close AS oracle_label
            FROM bar_features b
            LEFT JOIN read_parquet({sql_path(label_path)}) l
              ON b.instrument = l.instrument
             AND b.signal_date = l.signal_date
            WHERE b.signal_date BETWEEN {sql_quote(TRAIN_START)} AND {sql_quote(TRAIN_END)}
              AND l.label_5d_next_open_close IS NOT NULL
            """
        )

        # ---- Step 2: Learn decile bucket scores from TRAINING data ----
        bucket_scores = {}
        non_linearity_report = []

        for feature_name in FEATURE_SPECS:
            col = f"{feature_name}_raw"

            # Per-decile oracle label on training data
            rows = con.execute(
                f"""
                WITH ranked AS (
                    SELECT
                        signal_date,
                        oracle_label,
                        NTILE(10) OVER (
                            PARTITION BY signal_date
                            ORDER BY {col}, instrument ASC
                        ) AS bucket
                    FROM diag_data
                    WHERE {col} IS NOT NULL
                )
                SELECT
                    bucket,
                    AVG(oracle_label) AS avg_label,
                    STDDEV_SAMP(oracle_label) AS std_label,
                    COUNT(*) AS n_samples
                FROM ranked
                GROUP BY bucket
                ORDER BY bucket
                """
            ).fetchall()

            if not rows:
                continue

            bucket_map = {}
            for row in rows:
                b = int(row[0])
                bucket_map[str(b)] = {
                    "avg_oracle_label": float(row[1]) if row[1] is not None else 0.0,
                    "std": float(row[2]) if row[2] is not None else None,
                    "n_samples": int(row[3]),
                }
            bucket_scores[feature_name] = bucket_map

            # Measure non-linearity: stdev of bucket means vs range
            means = [v["avg_oracle_label"] for v in bucket_map.values()]
            label_range = max(means) - min(means)
            label_std = (
                (sum((m - sum(means) / len(means)) ** 2 for m in means) / (len(means) - 1))
                ** 0.5
            )
            non_linearity_report.append({
                "feature": feature_name,
                "bucket_means": means,
                "label_range": label_range,
                "label_std": label_std,
                "monotonic": all(
                    means[i] <= means[i + 1] for i in range(len(means) - 1)
                ) or all(
                    means[i] >= means[i + 1] for i in range(len(means) - 1)
                ),
                "best_bucket": int(max(bucket_map.keys(), key=lambda k: bucket_map[k]["avg_oracle_label"])),
                "worst_bucket": int(min(bucket_map.keys(), key=lambda k: bucket_map[k]["avg_oracle_label"])),
            })

        write_json(bucket_scores_output, {
            "learned_from": f"training data {TRAIN_START} to {TRAIN_END}",
            "method": "NTILE(10) per signal_date, average oracle label per bucket",
            "bucket_scores": bucket_scores,
        })

        # ---- Step 3: Apply bucket mapping to ALL dates, build PERCENT_RANK scores ----
        con.execute(
            f"""
            CREATE OR REPLACE VIEW all_features AS
            SELECT
                b.instrument,
                b.signal_date,
                b.*,
                sp.ranking_eligible_D0
            FROM bar_features b
            LEFT JOIN read_parquet({sql_path(sample_path)}) sp
              ON b.instrument = sp.instrument
             AND b.signal_date = sp.signal_date
            """
        )

        # Create mapped feature views
        mapped_features = {}
        for feature_name in FEATURE_SPECS:
            col = f"{feature_name}_raw"
            scores = bucket_scores.get(feature_name, {})
            if not scores:
                continue

            # Build a CASE expression for bucket mapping
            case_parts = []
            for i in range(1, 11):
                s = scores[str(i)]["avg_oracle_label"]
                case_parts.append(f"WHEN ntile_ranked.bucket = {i} THEN {s:.10f}")

            case_expr = "CASE " + " ".join(case_parts) + " END"

            con.execute(
                f"""
                CREATE OR REPLACE VIEW mapped_{feature_name} AS
                WITH ntile_ranked AS (
                    SELECT
                        instrument,
                        signal_date,
                        ranking_eligible_D0,
                        {col},
                        NTILE(10) OVER (
                            PARTITION BY signal_date
                            ORDER BY {col}, instrument ASC
                        ) AS bucket
                    FROM all_features
                    WHERE {col} IS NOT NULL
                )
                SELECT
                    instrument,
                    signal_date,
                    ranking_eligible_D0,
                    {case_expr} AS bucket_score
                FROM ntile_ranked
                """
            )
            mapped_features[feature_name] = f"mapped_{feature_name}"

        # ---- Step 4: Build final model scores ----
        # Load p98 for composite
        con.execute(
            f"""
            CREATE OR REPLACE VIEW p98_scores AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                model_score_D0 AS p98_rank
            FROM read_parquet({sql_path(P98_SCORE_PATH)})
            WHERE candidate_scheme_id = {sql_quote(P98_SCHEME_ID)}
              AND model_score_D0 IS NOT NULL
            """
        )

        union_parts = []

        # Single-feature decile schemes
        best_3 = sorted(non_linearity_report, key=lambda x: abs(x["label_range"]), reverse=True)[:3]
        best_feature_names = {r["feature"] for r in best_3}
        print(f"Top 3 features by non-linearity (label_range):")
        for r in best_3:
            print(f"  {r['feature']}: range={r['label_range']:.6f}, "
                  f"monotonic={r['monotonic']}, best_bucket={r['best_bucket']}")

        for feature_name in mapped_features:
            scheme_id = f"decile_{feature_name}_v1"
            union_parts.append(
                f"""
                SELECT
                    CAST(NULL AS BIGINT) AS snapshot_id,
                    m.instrument,
                    m.signal_date,
                    CAST({sql_quote(scheme_id)} AS VARCHAR) AS candidate_scheme_id,
                    PERCENT_RANK() OVER (
                        PARTITION BY m.signal_date
                        ORDER BY m.bucket_score ASC, m.instrument ASC
                    ) AS model_score_D0,
                    1 AS score_component_count,
                    CAST(NULL AS DOUBLE) AS component_a,
                    CAST(NULL AS DOUBLE) AS component_b
                FROM {mapped_features[feature_name]} m
                WHERE m.ranking_eligible_D0 AND m.bucket_score IS NOT NULL
                """
            )

        # Composite: equal-weight of top 3 decile features
        top3_scheme = "decile_composite_top3_ew_v1"
        top3_names = [r["feature"] for r in best_3 if r["feature"] in mapped_features]
        if len(top3_names) >= 2:
            joins = "\n".join(
                f"""LEFT JOIN (
                    SELECT instrument, signal_date,
                        PERCENT_RANK() OVER (
                            PARTITION BY signal_date
                            ORDER BY bucket_score ASC, instrument ASC
                        ) AS r_{fn}
                    FROM {mapped_features[fn]}
                    WHERE ranking_eligible_D0 AND bucket_score IS NOT NULL
                ) m_{fn} ON a.instrument = m_{fn}.instrument AND a.signal_date = m_{fn}.signal_date"""
                for fn in top3_names
            )
            score_sum = " + ".join(f"COALESCE(m_{fn}.r_{fn}, 0.0)" for fn in top3_names)
            n_feats = len(top3_names)

            union_parts.append(
                f"""
                SELECT
                    CAST(NULL AS BIGINT) AS snapshot_id,
                    a.instrument,
                    a.signal_date,
                    CAST({sql_quote(top3_scheme)} AS VARCHAR) AS candidate_scheme_id,
                    ({score_sum}) / CAST({n_feats} AS DOUBLE) AS model_score_D0,
                    {n_feats} AS score_component_count,
                    CAST(NULL AS DOUBLE) AS component_a,
                    CAST(NULL AS DOUBLE) AS component_b
                FROM all_features a
                {joins}
                WHERE a.ranking_eligible_D0
                """
            )

        # Composite: best decile + p98
        best_feature = best_3[0]["feature"] if best_3 else None
        if best_feature and best_feature in mapped_features:
            decile_p98_scheme = "decile_best_p98_ew_v1"
            union_parts.append(
                f"""
                SELECT
                    CAST(NULL AS BIGINT) AS snapshot_id,
                    a.instrument,
                    a.signal_date,
                    CAST({sql_quote(decile_p98_scheme)} AS VARCHAR) AS candidate_scheme_id,
                    0.5 * COALESCE(dr.rank_score, 0.0) + 0.5 * COALESCE(p.p98_rank, 0.0)
                        AS model_score_D0,
                    CASE WHEN dr.rank_score IS NOT NULL AND p.p98_rank IS NOT NULL THEN 2 ELSE 1 END
                        AS score_component_count,
                    dr.rank_score AS component_a,
                    p.p98_rank AS component_b
                FROM all_features a
                LEFT JOIN (
                    SELECT instrument, signal_date,
                        PERCENT_RANK() OVER (
                            PARTITION BY signal_date
                            ORDER BY bucket_score ASC, instrument ASC
                        ) AS rank_score
                    FROM {mapped_features[best_feature]}
                    WHERE ranking_eligible_D0 AND bucket_score IS NOT NULL
                ) dr ON a.instrument = dr.instrument AND a.signal_date = dr.signal_date
                LEFT JOIN p98_scores p
                    ON a.instrument = p.instrument AND a.signal_date = p.signal_date
                WHERE a.ranking_eligible_D0
                """
            )

        union_sql = " UNION ALL ".join(union_parts)
        con.execute(
            f"COPY ({union_sql}) TO {sql_path(score_output)} (FORMAT PARQUET)"
        )

        # ---- Step 5: Compute learnability diagnostic (IC) for each scheme ----
        all_scheme_ids = [
            f"decile_{fn}_v1" for fn in mapped_features
        ] + [top3_scheme]
        if best_feature and best_feature in mapped_features:
            all_scheme_ids.append(decile_p98_scheme)

        diagnostic_results = []

        for scheme_id in all_scheme_ids:
            con.execute(
                f"""
                CREATE OR REPLACE VIEW _diag AS
                SELECT
                    s.signal_date,
                    s.model_score_D0 AS score_val,
                    l.label_5d_next_open_close AS forward_label
                FROM read_parquet({sql_path(score_output)}) s
                JOIN read_parquet({sql_path(label_path)}) l
                  ON s.instrument = l.instrument AND s.signal_date = l.signal_date
                WHERE s.candidate_scheme_id = {sql_quote(scheme_id)}
                  AND s.model_score_D0 IS NOT NULL
                  AND l.label_5d_next_open_close IS NOT NULL
                """
            )

            rows = con.execute("""
                SELECT signal_date, CORR(score_val, forward_label) AS ic
                FROM _diag GROUP BY signal_date HAVING COUNT(*) >= 20
                ORDER BY signal_date
            """).fetchall()
            ic_series = [float(r[1]) for r in rows if r[1] is not None]
            con.execute("DROP VIEW IF EXISTS _diag")

            if not ic_series:
                continue

            n = len(ic_series)
            srt = sorted(ic_series)
            mid = n // 2
            med = srt[mid] if n % 2 else (srt[mid - 1] + srt[mid]) / 2.0
            avg = sum(ic_series) / n

            # Top10/Bot10 spread - compute via a simple query
            con.execute(
                f"""
                CREATE OR REPLACE VIEW _diag AS
                SELECT
                    s.signal_date,
                    s.model_score_D0 AS score_val,
                    l.label_5d_next_open_close AS forward_label
                FROM read_parquet({sql_path(score_output)}) s
                JOIN read_parquet({sql_path(label_path)}) l
                  ON s.instrument = l.instrument AND s.signal_date = l.signal_date
                WHERE s.candidate_scheme_id = {sql_quote(scheme_id)}
                  AND s.model_score_D0 IS NOT NULL
                  AND l.label_5d_next_open_close IS NOT NULL
                """
            )

            diagnostic_results.append({
                "scheme_id": scheme_id,
                "median_ic": med,
                "mean_ic": avg,
                "n_days": n,
            })

        # Print comparison
        print("\n=== Decile Non-Linear IC Summary ===")
        p98_ic = 0.046045
        print(f"  p98 baseline: IC = {p98_ic:.6f}")
        for d in sorted(diagnostic_results, key=lambda x: abs(x["median_ic"]), reverse=True):
            print(f"  {d['scheme_id']:<45} IC = {d['median_ic']:+.6f}  (n={d['n_days']})")

        # Find best
        best = max(diagnostic_results, key=lambda x: abs(x["median_ic"]))
        print(f"\n  Best non-linear: {best['scheme_id']} (IC = {best['median_ic']:+.6f})")

        # Save full report
        write_json(diagnostic_output, {
            "as_of": datetime.now().strftime("%Y%m%d"),
            "p98_baseline_ic": p98_ic,
            "top_features_by_nonlinearity": best_3,
            "non_linearity_report": non_linearity_report,
            "diagnostic_results": diagnostic_results,
            "best_scheme": best,
        })

    finally:
        con.close()

    print(f"\nOutputs:")
    print(f"  Scores: {score_output}")
    print(f"  Bucket scores: {bucket_scores_output}")
    print(f"  Diagnostic: {diagnostic_output}")


if __name__ == "__main__":
    main()
