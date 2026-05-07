#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Build a reproducible model_scores_D0.parquet for project-owned run state.

Supported presets:
- baseline_v1:
  - 5-day short-term reversal: lower recent return ranks higher
  - 60-to-5 day momentum: stronger medium-term momentum ranks higher
  - 20-day realized volatility: lower volatility ranks higher
  - 20-day liquidity proxy: higher average log amount ranks higher
- baseline_drop_liquidity_v2:
  - same as baseline_v1 but removes the liquidity component
- baseline_reversal_momentum_v3:
  - keeps only reversal and medium-term momentum
- baseline_momentum_v4:
  - keeps only medium-term momentum
- single_signal_intraday_trend_bias:
  - intraday trend bias (DESC): stronger intraday drift ranks higher
- intraday_trend_bias_upside_share_2sig:
  - intraday trend bias + upside range share
- intraday_full_microstructure_3sig:
  - intraday trend bias + upside range share + intraday reversal asymmetry
- single_signal_intraday_trend_bias_volume_gated:
  - intraday trend bias with volume gate (amount > 20d median)

The score uses only D0-and-earlier market data from the shared source.

Unit discipline:
- `amount` from `serving.vw_bars_daily` follows Tushare Pro `daily.amount` and is in
  thousand CNY, not CNY.
- `liquidity_20d_raw` is therefore a log-liquidity proxy on the thousand-CNY scale.
- `liquidity_rank` must always mean "higher liquidity -> higher rank".
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
CONTRACTS_DIR = ROOT / "contracts"
ARTIFACTS_RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
RESEARCH_REGISTRY_DIR = ROOT / "artifacts" / "research_registry"
CANDIDATE_SCHEME_REGISTRY = RESEARCH_REGISTRY_DIR / "candidate_scheme_registry.jsonl"
DEFAULT_CANDIDATE_SCHEME_ID = "baseline_reversal_momentum_lowvol_liquidity_v1"
EXPECTED_AMOUNT_UNIT = "thousand_cny"
FEATURE_PRESETS = {
    "baseline_v1": [
        ("reversal_5d_raw", "reversal_rank"),
        ("momentum_60_5_raw", "momentum_rank"),
        ("volatility_20d_raw", "lowvol_rank"),
        ("liquidity_20d_raw", "liquidity_rank"),
    ],
    "baseline_drop_liquidity_v2": [
        ("reversal_5d_raw", "reversal_rank"),
        ("momentum_60_5_raw", "momentum_rank"),
        ("volatility_20d_raw", "lowvol_rank"),
    ],
    "baseline_reversal_momentum_v3": [
        ("reversal_5d_raw", "reversal_rank"),
        ("momentum_60_5_raw", "momentum_rank"),
    ],
    "baseline_momentum_v4": [
        ("momentum_60_5_raw", "momentum_rank"),
    ],
    "baseline_momentum_lowvol_v5": [
        ("momentum_60_5_raw", "momentum_rank"),
        ("volatility_20d_raw", "lowvol_rank"),
    ],
    "single_signal_momentum_60_5_v1": [
        ("momentum_60_5_raw", "momentum_rank"),
    ],
    "single_signal_reversal_5d_v1": [
        ("reversal_5d_raw", "reversal_rank"),
    ],
    "single_signal_reversal_5d_followthrough_v1": [
        ("reversal_5d_raw", "reversal_followthrough_rank"),
    ],
    "single_signal_volatility_20d_v1": [
        ("volatility_20d_raw", "lowvol_rank"),
    ],
    "single_signal_volatility_60d_v1": [
        ("volatility_60d_raw", "lowvol_60d_rank"),
    ],
    "single_signal_liquidity_20d_v1": [
        ("liquidity_20d_raw", "liquidity_rank"),
    ],
    "single_signal_liquidity_60d_v1": [
        ("liquidity_60d_raw", "liquidity_60d_rank"),
    ],
    "single_signal_liquidity_trend_60_120_v1": [
        ("liquidity_trend_60_120_raw", "liquidity_trend_60_120_rank"),
    ],
    "single_signal_trend_consistency_20d_v1": [
        ("trend_consistency_20d_raw", "trend_consistency_rank"),
    ],
    "single_signal_trend_consistency_60d_v1": [
        ("trend_consistency_60d_raw", "trend_consistency_60d_rank"),
    ],
    "single_signal_momentum_120_20_v1": [
        ("momentum_120_20_raw", "momentum_120_20_rank"),
    ],
    "single_signal_momentum_250_20_v1": [
        ("momentum_250_20_raw", "momentum_250_20_rank"),
    ],
    "single_signal_momentum_20_5_v1": [
        ("momentum_20_5_raw", "momentum_20_5_rank"),
    ],
    "single_signal_vol_regime_20_60_v1": [
        ("vol_regime_20_60_raw", "vol_regime_rank"),
    ],
    "single_signal_vol_regime_20_60_inverse_v1": [
        ("vol_regime_20_60_raw", "vol_regime_inverse_rank"),
    ],
    "single_signal_liquidity_trend_20_60_v1": [
        ("liquidity_trend_20_60_raw", "liquidity_trend_rank"),
    ],
    "price_volume_v15_trend_liquidity_improvement_core": [
        ("momentum_60_5_raw", "momentum_rank"),
        ("trend_consistency_20d_raw", "trend_consistency_rank"),
        ("liquidity_trend_20_60_raw", "liquidity_trend_rank"),
    ],
    "price_volume_v16_remove_trend_consistency": [
        ("momentum_60_5_raw", "momentum_rank"),
        ("liquidity_trend_20_60_raw", "liquidity_trend_rank"),
    ],
    "price_volume_v21_liquidity_trend_60_120_substitution": [
        ("momentum_60_5_raw", "momentum_rank"),
        ("liquidity_trend_60_120_raw", "liquidity_trend_60_120_rank"),
    ],
    "single_signal_intraday_trend_bias": [
        ("intraday_trend_bias_20d_raw", "intraday_trend_bias_rank"),
    ],
    "intraday_trend_bias_upside_share_2sig": [
        ("intraday_trend_bias_20d_raw", "intraday_trend_bias_rank"),
        ("upside_range_share_20d_raw", "upside_range_share_rank"),
    ],
    "intraday_full_microstructure_3sig": [
        ("intraday_trend_bias_20d_raw", "intraday_trend_bias_rank"),
        ("upside_range_share_20d_raw", "upside_range_share_rank"),
        ("intraday_reversal_asymmetry_20d_raw", "intraday_reversal_asymmetry_rank"),
    ],
    "single_signal_intraday_trend_bias_volume_gated": [
        ("intraday_trend_bias_20d_raw", "intraday_trend_bias_volume_gated_rank"),
    ],
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def ensure_registered_candidate(candidate_scheme_id: str) -> None:
    rows = load_jsonl(CANDIDATE_SCHEME_REGISTRY)
    if not any(row.get("candidate_scheme_id") == candidate_scheme_id for row in rows):
        raise ValueError(
            "candidate_scheme_id must be registered before score production: "
            f"{candidate_scheme_id}"
        )


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_path(path: Path) -> str:
    return sql_quote(path.resolve().as_posix())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build baseline model_scores_D0.parquet.")
    parser.add_argument("--run-id", required=True, help="Project-side run identifier.")
    parser.add_argument(
        "--input-dir",
        default=None,
        help="Optional run-state directory. Defaults to artifacts/run_state/<run_id>/",
    )
    parser.add_argument(
        "--candidate-scheme-id",
        default=DEFAULT_CANDIDATE_SCHEME_ID,
        help="Candidate scheme identifier written into the score file.",
    )
    parser.add_argument(
        "--min-feature-count",
        type=int,
        default=3,
        help="Minimum number of available baseline feature ranks required to emit a score.",
    )
    parser.add_argument(
        "--feature-preset",
        default="baseline_v1",
        choices=sorted(FEATURE_PRESETS.keys()),
        help="Named feature preset used to compose the score.",
    )
    parser.add_argument(
        "--run-input-contract",
        default=None,
        help="Optional explicit run input contract JSON path. Defaults to contracts/run_input_contract.current.json",
    )
    return parser.parse_args()


def resolve_run_dir(run_id: str, input_dir: str | None) -> Path:
    run_dir = Path(input_dir) if input_dir else (ARTIFACTS_RUN_STATE_DIR / run_id)
    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")
    return run_dir


def require_input(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Required input file not found: {path}")
    return path


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    if args.min_feature_count <= 0:
        raise ValueError("--min-feature-count must be positive.")
    selected_features = FEATURE_PRESETS[args.feature_preset]
    if args.min_feature_count > len(selected_features):
        raise ValueError(
            "--min-feature-count cannot exceed the number of selected score components "
            f"for preset {args.feature_preset}."
        )
    ensure_registered_candidate(args.candidate_scheme_id)

    run_dir = resolve_run_dir(args.run_id, args.input_dir)
    sample_panel = require_input(run_dir / "project_sample_panel.parquet")

    run_input_contract_path = Path(args.run_input_contract) if args.run_input_contract else (
        CONTRACTS_DIR / "run_input_contract.current.json"
    )
    run_input = load_json(run_input_contract_path)
    snapshot_id = run_input["snapshot_id"]
    source_db_path = Path(run_input["source_root"]["snapshot_path"]) / "duckdb" / "warehouse.duckdb"
    if not source_db_path.exists():
        raise FileNotFoundError(f"Shared warehouse DB not found: {source_db_path}")

    score_output = run_dir / "model_scores_D0.parquet"
    audit_output = run_dir / "model_scores_D0_audit.json"

    con = duckdb.connect()
    try:
        con.execute(f"ATTACH {sql_path(source_db_path)} AS warehouse_db (READ_ONLY)")
        con.execute(
            f"""
            CREATE OR REPLACE VIEW project_sample_panel AS
            SELECT * FROM read_parquet({sql_path(sample_panel)})
            """
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
                    pct_chg / 100.0 AS pct_ret,
                    CASE WHEN adj_open > 0 THEN adj_close / adj_open - 1.0 ELSE NULL END AS intraday_ret,
                    CASE WHEN adj_close > 0 THEN (adj_high - adj_low) / adj_close ELSE 0.0 END AS daily_range_ratio,
                    CASE WHEN pct_ret > 0 AND adj_close > 0 THEN (adj_high - adj_low) / adj_close ELSE 0.0 END AS upside_range_daily
                FROM warehouse_db.serving.vw_bars_daily
                WHERE snapshot_id = {sql_quote(snapshot_id)}
            )
            SELECT
                instrument,
                signal_date,
                (adj_close / LAG(adj_close, 5) OVER w - 1.0) AS reversal_5d_raw,
                (LAG(adj_close, 5) OVER w / LAG(adj_close, 20) OVER w - 1.0) AS momentum_20_5_raw,
                (LAG(adj_close, 5) OVER w / LAG(adj_close, 60) OVER w - 1.0) AS momentum_60_5_raw,
                (LAG(adj_close, 20) OVER w / LAG(adj_close, 120) OVER w - 1.0) AS momentum_120_20_raw,
                (LAG(adj_close, 20) OVER w / LAG(adj_close, 250) OVER w - 1.0) AS momentum_250_20_raw,
                STDDEV_SAMP(pct_ret) OVER w20 AS volatility_20d_raw,
                STDDEV_SAMP(pct_ret) OVER w60 AS volatility_60d_raw,
                -- `amount` is in thousand CNY. We keep the scale explicit here so any
                -- future unit change in the shared source must be handled deliberately.
                AVG(LN(GREATEST(amount, 0.0) + 1.0)) OVER w20 AS liquidity_20d_raw,
                AVG(LN(GREATEST(amount, 0.0) + 1.0)) OVER w60 AS liquidity_60d_raw,
                AVG(LN(GREATEST(amount, 0.0) + 1.0)) OVER w120 AS liquidity_120d_raw,
                AVG(CASE WHEN pct_ret > 0 THEN 1.0 ELSE 0.0 END) OVER w20 AS trend_consistency_20d_raw,
                AVG(CASE WHEN pct_ret > 0 THEN 1.0 ELSE 0.0 END) OVER w60 AS trend_consistency_60d_raw,
                AVG(intraday_ret) OVER w20 AS intraday_trend_bias_20d_raw,
                CASE
                    WHEN SUM(daily_range_ratio) OVER w20 > 0
                    THEN SUM(upside_range_daily) OVER w20 / SUM(daily_range_ratio) OVER w20
                    ELSE NULL
                END AS upside_range_share_20d_raw,
                AVG(CASE WHEN intraday_ret < 0 AND adj_high > adj_low
                    THEN (adj_close - adj_low) / (adj_high - adj_low) ELSE NULL END) OVER w20
                - AVG(CASE WHEN intraday_ret > 0 AND adj_high > adj_low
                    THEN (adj_high - adj_close) / (adj_high - adj_low) ELSE NULL END) OVER w20
                    AS intraday_reversal_asymmetry_20d_raw,
                MEDIAN(amount) OVER w20_excl_current AS median_amount_20d,
                amount
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
                ),
                w20_excl_current AS (
                    PARTITION BY instrument
                    ORDER BY signal_date
                    ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING
                )
            """
        )

        con.execute(
            """
            CREATE OR REPLACE VIEW feature_frame AS
            SELECT
                p.snapshot_id,
                p.instrument,
                p.signal_date,
                p.ranking_eligible_D0,
                f.reversal_5d_raw,
                f.momentum_20_5_raw,
                f.momentum_60_5_raw,
                f.momentum_120_20_raw,
                f.momentum_250_20_raw,
                f.volatility_20d_raw,
                f.volatility_60d_raw,
                f.liquidity_20d_raw,
                f.liquidity_60d_raw,
                f.liquidity_120d_raw,
                f.trend_consistency_20d_raw,
                f.trend_consistency_60d_raw,
                f.intraday_trend_bias_20d_raw,
                f.upside_range_share_20d_raw,
                f.intraday_reversal_asymmetry_20d_raw,
                f.amount,
                f.median_amount_20d,
                CASE
                    WHEN f.median_amount_20d IS NOT NULL AND f.median_amount_20d > 0
                    THEN CAST(f.amount AS DOUBLE) / f.median_amount_20d
                    ELSE NULL
                END AS volume_ratio_20d,
                CASE
                    WHEN f.volatility_20d_raw IS NOT NULL AND f.volatility_60d_raw IS NOT NULL
                         AND f.volatility_60d_raw > 0
                    THEN f.volatility_20d_raw / f.volatility_60d_raw
                    ELSE NULL
                END AS vol_regime_20_60_raw,
                CASE
                    WHEN f.liquidity_20d_raw IS NOT NULL AND f.liquidity_60d_raw IS NOT NULL
                    THEN f.liquidity_20d_raw - f.liquidity_60d_raw
                    ELSE NULL
                END AS liquidity_trend_20_60_raw,
                CASE
                    WHEN f.liquidity_60d_raw IS NOT NULL AND f.liquidity_120d_raw IS NOT NULL
                    THEN f.liquidity_60d_raw - f.liquidity_120d_raw
                    ELSE NULL
                END AS liquidity_trend_60_120_raw
            FROM project_sample_panel p
            LEFT JOIN bar_features f
                ON p.instrument = f.instrument
               AND p.signal_date = f.signal_date
            """
        )

        con.execute(
            """
            CREATE OR REPLACE VIEW reversal_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY reversal_5d_raw ASC, instrument ASC
                ) AS reversal_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND reversal_5d_raw IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW reversal_followthrough_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY reversal_5d_raw DESC, instrument ASC
                ) AS reversal_followthrough_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND reversal_5d_raw IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW momentum_20_5_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY momentum_20_5_raw DESC, instrument ASC
                ) AS momentum_20_5_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND momentum_20_5_raw IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW momentum_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY momentum_60_5_raw DESC, instrument ASC
                ) AS momentum_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND momentum_60_5_raw IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW volatility_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY volatility_20d_raw ASC, instrument ASC
                ) AS lowvol_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND volatility_20d_raw IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW volatility_60d_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY volatility_60d_raw ASC, instrument ASC
                ) AS lowvol_60d_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND volatility_60d_raw IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW liquidity_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    -- Higher liquidity must map to a higher rank. Ascending sort is
                    -- correct because `liquidity_20d_raw` is a monotone proxy on amount.
                    ORDER BY liquidity_20d_raw ASC, instrument ASC
                ) AS liquidity_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND liquidity_20d_raw IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW liquidity_60d_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    -- Higher liquidity must map to a higher rank. Ascending sort is
                    -- correct because `liquidity_60d_raw` is a monotone proxy on amount.
                    ORDER BY liquidity_60d_raw ASC, instrument ASC
                ) AS liquidity_60d_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND liquidity_60d_raw IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW trend_consistency_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY trend_consistency_20d_raw DESC, instrument ASC
                ) AS trend_consistency_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND trend_consistency_20d_raw IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW trend_consistency_60d_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY trend_consistency_60d_raw DESC, instrument ASC
                ) AS trend_consistency_60d_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND trend_consistency_60d_raw IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW momentum_120_20_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY momentum_120_20_raw DESC, instrument ASC
                ) AS momentum_120_20_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND momentum_120_20_raw IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW momentum_250_20_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY momentum_250_20_raw DESC, instrument ASC
                ) AS momentum_250_20_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND momentum_250_20_raw IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW vol_regime_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY vol_regime_20_60_raw ASC, instrument ASC
                ) AS vol_regime_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND vol_regime_20_60_raw IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW vol_regime_inverse_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY vol_regime_20_60_raw DESC, instrument ASC
                ) AS vol_regime_inverse_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND vol_regime_20_60_raw IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW liquidity_trend_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY liquidity_trend_20_60_raw DESC, instrument ASC
                ) AS liquidity_trend_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND liquidity_trend_20_60_raw IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW liquidity_trend_60_120_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY liquidity_trend_60_120_raw DESC, instrument ASC
                ) AS liquidity_trend_60_120_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND liquidity_trend_60_120_raw IS NOT NULL
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW intraday_trend_bias_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY intraday_trend_bias_20d_raw DESC, instrument ASC
                ) AS intraday_trend_bias_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND intraday_trend_bias_20d_raw IS NOT NULL
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW intraday_trend_bias_volume_gated_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY intraday_trend_bias_20d_raw DESC, instrument ASC
                ) AS intraday_trend_bias_volume_gated_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND intraday_trend_bias_20d_raw IS NOT NULL
              AND volume_ratio_20d > 1.0
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW upside_range_share_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY upside_range_share_20d_raw DESC, instrument ASC
                ) AS upside_range_share_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND upside_range_share_20d_raw IS NOT NULL
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW intraday_reversal_asymmetry_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY intraday_reversal_asymmetry_20d_raw DESC, instrument ASC
                ) AS intraday_reversal_asymmetry_rank
            FROM feature_frame
            WHERE ranking_eligible_D0
              AND intraday_reversal_asymmetry_20d_raw IS NOT NULL
            """
        )

        component_count_expr = " + ".join(
            f"CASE WHEN {rank_col} IS NOT NULL THEN 1 ELSE 0 END" for _, rank_col in selected_features
        )
        score_sum_expr = " + ".join(f"COALESCE({rank_col}, 0.0)" for _, rank_col in selected_features)

        con.execute(
            f"""
            COPY (
                WITH score_frame AS (
                    SELECT
                        f.snapshot_id,
                        f.instrument,
                        f.signal_date,
                        f.ranking_eligible_D0,
                        r.reversal_rank,
                        rf.reversal_followthrough_rank,
                        m205.momentum_20_5_rank,
                        m.momentum_rank,
                        m120.momentum_120_20_rank,
                        m250.momentum_250_20_rank,
                        v.lowvol_rank,
                        v60.lowvol_60d_rank,
                        l.liquidity_rank,
                        l60.liquidity_60d_rank,
                        tc.trend_consistency_rank,
                        tc60.trend_consistency_60d_rank,
                        vr.vol_regime_rank,
                        vri.vol_regime_inverse_rank,
                        lt.liquidity_trend_rank,
                        lt2.liquidity_trend_60_120_rank,
                        itb.intraday_trend_bias_rank,
                        itb_vg.intraday_trend_bias_volume_gated_rank,
                        usr.upside_range_share_rank,
                        ira.intraday_reversal_asymmetry_rank,
                        ({component_count_expr}) AS score_component_count
                    FROM feature_frame f
                    LEFT JOIN reversal_ranks r
                        ON f.snapshot_id = r.snapshot_id
                       AND f.instrument = r.instrument
                       AND f.signal_date = r.signal_date
                    LEFT JOIN reversal_followthrough_ranks rf
                        ON f.snapshot_id = rf.snapshot_id
                       AND f.instrument = rf.instrument
                       AND f.signal_date = rf.signal_date
                    LEFT JOIN momentum_ranks m
                        ON f.snapshot_id = m.snapshot_id
                       AND f.instrument = m.instrument
                       AND f.signal_date = m.signal_date
                    LEFT JOIN momentum_20_5_ranks m205
                        ON f.snapshot_id = m205.snapshot_id
                       AND f.instrument = m205.instrument
                       AND f.signal_date = m205.signal_date
                    LEFT JOIN volatility_ranks v
                        ON f.snapshot_id = v.snapshot_id
                       AND f.instrument = v.instrument
                       AND f.signal_date = v.signal_date
                    LEFT JOIN volatility_60d_ranks v60
                        ON f.snapshot_id = v60.snapshot_id
                       AND f.instrument = v60.instrument
                       AND f.signal_date = v60.signal_date
                    LEFT JOIN liquidity_ranks l
                        ON f.snapshot_id = l.snapshot_id
                       AND f.instrument = l.instrument
                       AND f.signal_date = l.signal_date
                    LEFT JOIN liquidity_60d_ranks l60
                        ON f.snapshot_id = l60.snapshot_id
                       AND f.instrument = l60.instrument
                       AND f.signal_date = l60.signal_date
                    LEFT JOIN trend_consistency_ranks tc
                        ON f.snapshot_id = tc.snapshot_id
                       AND f.instrument = tc.instrument
                       AND f.signal_date = tc.signal_date
                    LEFT JOIN trend_consistency_60d_ranks tc60
                        ON f.snapshot_id = tc60.snapshot_id
                       AND f.instrument = tc60.instrument
                       AND f.signal_date = tc60.signal_date
                    LEFT JOIN momentum_120_20_ranks m120
                        ON f.snapshot_id = m120.snapshot_id
                       AND f.instrument = m120.instrument
                       AND f.signal_date = m120.signal_date
                    LEFT JOIN momentum_250_20_ranks m250
                        ON f.snapshot_id = m250.snapshot_id
                       AND f.instrument = m250.instrument
                       AND f.signal_date = m250.signal_date
                    LEFT JOIN vol_regime_ranks vr
                        ON f.snapshot_id = vr.snapshot_id
                       AND f.instrument = vr.instrument
                       AND f.signal_date = vr.signal_date
                    LEFT JOIN vol_regime_inverse_ranks vri
                        ON f.snapshot_id = vri.snapshot_id
                       AND f.instrument = vri.instrument
                       AND f.signal_date = vri.signal_date
                    LEFT JOIN liquidity_trend_ranks lt
                        ON f.snapshot_id = lt.snapshot_id
                       AND f.instrument = lt.instrument
                       AND f.signal_date = lt.signal_date
                    LEFT JOIN liquidity_trend_60_120_ranks lt2
                        ON f.snapshot_id = lt2.snapshot_id
                       AND f.instrument = lt2.instrument
                       AND f.signal_date = lt2.signal_date
                    LEFT JOIN intraday_trend_bias_ranks itb
                        ON f.snapshot_id = itb.snapshot_id
                       AND f.instrument = itb.instrument
                       AND f.signal_date = itb.signal_date
                    LEFT JOIN intraday_trend_bias_volume_gated_ranks itb_vg
                        ON f.snapshot_id = itb_vg.snapshot_id
                       AND f.instrument = itb_vg.instrument
                       AND f.signal_date = itb_vg.signal_date
                    LEFT JOIN upside_range_share_ranks usr
                        ON f.snapshot_id = usr.snapshot_id
                       AND f.instrument = usr.instrument
                       AND f.signal_date = usr.signal_date
                    LEFT JOIN intraday_reversal_asymmetry_ranks ira
                        ON f.snapshot_id = ira.snapshot_id
                       AND f.instrument = ira.instrument
                       AND f.signal_date = ira.signal_date
                )
                SELECT
                    snapshot_id,
                    instrument,
                    signal_date,
                    CAST({sql_quote(args.candidate_scheme_id)} AS VARCHAR) AS candidate_scheme_id,
                    CASE
                        WHEN ranking_eligible_D0 AND score_component_count >= {args.min_feature_count}
                        THEN ({score_sum_expr}) / score_component_count
                        ELSE CAST(NULL AS DOUBLE)
                    END AS model_score_D0,
                    score_component_count,
                    reversal_rank,
                    reversal_followthrough_rank,
                    momentum_20_5_rank,
                    momentum_rank,
                    momentum_120_20_rank,
                    momentum_250_20_rank,
                    lowvol_rank,
                    lowvol_60d_rank,
                    liquidity_rank,
                    liquidity_60d_rank,
                    trend_consistency_rank,
                    trend_consistency_60d_rank,
                    vol_regime_rank,
                    vol_regime_inverse_rank,
                    liquidity_trend_rank,
                    liquidity_trend_60_120_rank,
                    intraday_trend_bias_rank,
                    intraday_trend_bias_volume_gated_rank,
                    upside_range_share_rank,
                    intraday_reversal_asymmetry_rank
                FROM score_frame
            ) TO {sql_path(score_output)} (FORMAT PARQUET)
            """
        )

        audit_counts = con.execute(
            f"""
            SELECT
                COUNT(*) AS total_rows,
                SUM(CASE WHEN ranking_eligible_D0 THEN 1 ELSE 0 END) AS ranking_eligible_rows,
                SUM(CASE WHEN model_score_D0 IS NOT NULL THEN 1 ELSE 0 END) AS scored_rows,
                SUM(CASE WHEN ranking_eligible_D0 AND model_score_D0 IS NULL THEN 1 ELSE 0 END) AS eligible_unscored_rows,
                SUM(CASE WHEN score_component_count >= {args.min_feature_count} THEN 1 ELSE 0 END) AS min_feature_ready_rows,
                SUM(CASE WHEN reversal_rank IS NOT NULL THEN 1 ELSE 0 END) AS reversal_rank_rows,
                SUM(CASE WHEN reversal_followthrough_rank IS NOT NULL THEN 1 ELSE 0 END) AS reversal_followthrough_rank_rows,
                SUM(CASE WHEN momentum_20_5_rank IS NOT NULL THEN 1 ELSE 0 END) AS momentum_20_5_rank_rows,
                SUM(CASE WHEN momentum_rank IS NOT NULL THEN 1 ELSE 0 END) AS momentum_rank_rows,
                SUM(CASE WHEN momentum_120_20_rank IS NOT NULL THEN 1 ELSE 0 END) AS momentum_120_20_rank_rows,
                SUM(CASE WHEN momentum_250_20_rank IS NOT NULL THEN 1 ELSE 0 END) AS momentum_250_20_rank_rows,
                SUM(CASE WHEN lowvol_rank IS NOT NULL THEN 1 ELSE 0 END) AS lowvol_rank_rows,
                SUM(CASE WHEN lowvol_60d_rank IS NOT NULL THEN 1 ELSE 0 END) AS lowvol_60d_rank_rows,
                SUM(CASE WHEN liquidity_rank IS NOT NULL THEN 1 ELSE 0 END) AS liquidity_rank_rows,
                SUM(CASE WHEN liquidity_60d_rank IS NOT NULL THEN 1 ELSE 0 END) AS liquidity_60d_rank_rows,
                SUM(CASE WHEN trend_consistency_rank IS NOT NULL THEN 1 ELSE 0 END) AS trend_consistency_rank_rows,
                SUM(CASE WHEN trend_consistency_60d_rank IS NOT NULL THEN 1 ELSE 0 END) AS trend_consistency_60d_rank_rows,
                SUM(CASE WHEN vol_regime_rank IS NOT NULL THEN 1 ELSE 0 END) AS vol_regime_rank_rows,
                SUM(CASE WHEN vol_regime_inverse_rank IS NOT NULL THEN 1 ELSE 0 END) AS vol_regime_inverse_rank_rows,
                SUM(CASE WHEN liquidity_trend_rank IS NOT NULL THEN 1 ELSE 0 END) AS liquidity_trend_rank_rows,
                SUM(CASE WHEN liquidity_trend_60_120_rank IS NOT NULL THEN 1 ELSE 0 END) AS liquidity_trend_60_120_rank_rows,
                SUM(CASE WHEN intraday_trend_bias_rank IS NOT NULL THEN 1 ELSE 0 END) AS intraday_trend_bias_rank_rows,
                SUM(CASE WHEN intraday_trend_bias_volume_gated_rank IS NOT NULL THEN 1 ELSE 0 END) AS intraday_trend_bias_volume_gated_rank_rows,
                SUM(CASE WHEN upside_range_share_rank IS NOT NULL THEN 1 ELSE 0 END) AS upside_range_share_rank_rows,
                SUM(CASE WHEN intraday_reversal_asymmetry_rank IS NOT NULL THEN 1 ELSE 0 END) AS intraday_reversal_asymmetry_rank_rows
            FROM (
                SELECT
                    p.ranking_eligible_D0,
                    s.model_score_D0,
                    s.score_component_count,
                    s.reversal_rank,
                    s.reversal_followthrough_rank,
                    s.momentum_20_5_rank,
                    s.momentum_rank,
                    s.momentum_120_20_rank,
                    s.momentum_250_20_rank,
                    s.lowvol_rank,
                    s.lowvol_60d_rank,
                    s.liquidity_rank,
                    s.liquidity_60d_rank,
                    s.trend_consistency_rank,
                    s.trend_consistency_60d_rank,
                    s.vol_regime_rank,
                    s.vol_regime_inverse_rank,
                    s.liquidity_trend_rank,
                    s.liquidity_trend_60_120_rank,
                    s.intraday_trend_bias_rank,
                    s.intraday_trend_bias_volume_gated_rank,
                    s.upside_range_share_rank,
                    s.intraday_reversal_asymmetry_rank
                FROM read_parquet({sql_path(score_output)}) s
                INNER JOIN project_sample_panel p
                    ON s.snapshot_id = p.snapshot_id
                   AND s.instrument = p.instrument
                   AND s.signal_date = p.signal_date
            )
            """
        ).fetchone()
        amount_sanity = con.execute(
            """
            SELECT
                MIN(liquidity_rank) AS min_liquidity_rank,
                MAX(liquidity_rank) AS max_liquidity_rank,
                AVG(liquidity_rank) AS avg_liquidity_rank
            FROM read_parquet(?)
            """,
            [score_output.as_posix()],
        ).fetchone()
    finally:
        con.close()

    audit = {
        "run_id": args.run_id,
        "snapshot_id": snapshot_id,
        "candidate_scheme_id": args.candidate_scheme_id,
        "feature_preset": args.feature_preset,
        "score_file": score_output.name,
        "min_feature_count": args.min_feature_count,
        "baseline_features": [feature_name for feature_name, _ in selected_features],
        "summary_counts": {
            "total_rows": int(audit_counts[0] or 0),
            "ranking_eligible_rows": int(audit_counts[1] or 0),
            "scored_rows": int(audit_counts[2] or 0),
            "eligible_unscored_rows": int(audit_counts[3] or 0),
            "min_feature_ready_rows": int(audit_counts[4] or 0),
            "reversal_rank_rows": int(audit_counts[5] or 0),
            "reversal_followthrough_rank_rows": int(audit_counts[6] or 0),
            "momentum_rank_rows": int(audit_counts[7] or 0),
            "momentum_120_20_rank_rows": int(audit_counts[8] or 0),
            "momentum_250_20_rank_rows": int(audit_counts[9] or 0),
            "lowvol_rank_rows": int(audit_counts[10] or 0),
            "lowvol_60d_rank_rows": int(audit_counts[11] or 0),
            "liquidity_rank_rows": int(audit_counts[12] or 0),
            "liquidity_60d_rank_rows": int(audit_counts[13] or 0),
            "trend_consistency_rank_rows": int(audit_counts[14] or 0),
            "trend_consistency_60d_rank_rows": int(audit_counts[15] or 0),
            "vol_regime_rank_rows": int(audit_counts[16] or 0),
            "vol_regime_inverse_rank_rows": int(audit_counts[17] or 0),
            "liquidity_trend_rank_rows": int(audit_counts[18] or 0),
            "liquidity_trend_60_120_rank_rows": int(audit_counts[19] or 0),
            "intraday_trend_bias_rank_rows": int(audit_counts[21] or 0),
            "intraday_trend_bias_volume_gated_rank_rows": int(audit_counts[22] or 0),
            "upside_range_share_rank_rows": int(audit_counts[23] or 0),
            "intraday_reversal_asymmetry_rank_rows": int(audit_counts[24] or 0),
        },
        "notes": [
            "This is a simple project-owned cross-sectional scorer for first end-to-end project runs.",
            "All features use D0-and-earlier market data only.",
            "The score is the average of available cross-sectional percentile ranks when enough features are present.",
            "amount_unit_assumption = thousand CNY",
            "liquidity_rank_direction = higher liquidity -> higher rank",
        ],
        "unit_sanity": {
            "amount_unit_assumption": EXPECTED_AMOUNT_UNIT,
            "liquidity_rank_min": float(amount_sanity[0]) if amount_sanity[0] is not None else None,
            "liquidity_rank_max": float(amount_sanity[1]) if amount_sanity[1] is not None else None,
            "liquidity_rank_avg": float(amount_sanity[2]) if amount_sanity[2] is not None else None,
        },
    }
    write_json(audit_output, audit)


if __name__ == "__main__":
    main()
