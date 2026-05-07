#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Run the full round-5 single-signal discovery batch under the frozen v18 contract.

This script:
1. reuses a shared project-panel directory,
2. materializes one model_scores_D0.parquet per candidate,
3. runs signal-edge diagnosis,
4. updates the candidate and round registries,
5. writes a phase summary with the batch-level decision.
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from single_signal_batch_common import CandidateSpec, materialize_ranked_single_signal, run_single_signal_batch, sql_path, sql_quote


ROOT = Path("/Users/wy/MiscProject/multi_factor")
RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
REGISTRY_DIR = ROOT / "artifacts" / "research_registry"
ROUND_ID = "rr_price_volume_single_signal_discovery_v18_round5_20260425"
AS_OF_DATE = "20260425"
BASE_RUN_ID = "signaldiag_rr_price_volume_single_signal_discovery_v18_round4_20260423_base"
BASE_RUN_DIR = RUN_STATE_DIR / BASE_RUN_ID
ROUND_DIR = REGISTRY_DIR / "research_rounds" / ROUND_ID
CANDIDATE_REGISTRY_PATH = REGISTRY_DIR / "candidate_scheme_registry.jsonl"
ROUND_REGISTRY_PATH = REGISTRY_DIR / "research_round_registry.jsonl"
BUILD_DIAGNOSIS_SCRIPT = ROOT / "scripts" / "build_signal_edge_diagnosis.py"
SCORE_BUILDER_NAME = "run_round5_single_signal_batch.py"


CANDIDATES: list[CandidateSpec] = [
    CandidateSpec(
        "price_volume_single_signal_signed_amount_imbalance_20d_v1",
        "signed_amount_imbalance_20d_raw",
        "DESC",
        "signals whose recent traded amount is more concentrated on positive-return days may capture a cleaner flow-imbalance edge than existing momentum and liquidity-trend keepers",
    ),
    CandidateSpec(
        "price_volume_single_signal_turnover_acceleration_5_20_v1",
        "turnover_acceleration_5_20_raw",
        "DESC",
        "signals experiencing a recent turnover acceleration versus their own 20-day baseline may reveal a more actionable trading-activity shock than amount-level surges alone",
    ),
    CandidateSpec(
        "price_volume_single_signal_volume_price_synchronicity_20d_v1",
        "volume_price_synchronicity_20d_raw",
        "DESC",
        "signals with stronger positive synchronicity between price change and amount change may encode cleaner price-volume confirmation than direct breakout overlays",
    ),
    CandidateSpec(
        "price_volume_single_signal_trend_efficiency_60d_v1",
        "trend_efficiency_60d_raw",
        "DESC",
        "signals that travel more efficiently over a 60-day path may provide a slower and more stable trend-quality edge than short-horizon efficiency or consistency variants",
    ),
    CandidateSpec(
        "price_volume_single_signal_range_compression_10_40_v1",
        "range_compression_10_40_raw",
        "ASC",
        "signals with lower recent trading-range pressure relative to a 40-day baseline may capture a pre-expansion structural state that is distinct from raw volatility level",
    ),
    CandidateSpec(
        "price_volume_single_signal_breakout_failure_pressure_20d_v1",
        "breakout_failure_pressure_20d_raw",
        "ASC",
        "signals with less recent failed-breakout pressure may offer a cleaner structural filter after the direct breakout-confirmation family substitution failed",
    ),
    CandidateSpec(
        "price_volume_single_signal_downside_gap_recovery_10d_v1",
        "downside_gap_recovery_10d_raw",
        "DESC",
        "signals that recover more effectively from recent downside gaps may encode a more useful resilience edge than standard short-horizon reversal variants",
    ),
    CandidateSpec(
        "price_volume_single_signal_up_amount_persistence_20d_v1",
        "up_amount_persistence_20d_raw",
        "DESC",
        "signals whose amount expansion persists on up days may provide a discrete volume-confirmation edge that is cleaner than direct amount-shock promotion",
    ),
    CandidateSpec(
        "price_volume_single_signal_turnover_stability_20d_v1",
        "turnover_stability_20d_raw",
        "ASC",
        "signals with more stable recent turnover may reveal a cleaner participation-quality dimension than turnover surges or raw liquidity levels",
    ),
    CandidateSpec(
        "price_volume_single_signal_intraday_recovery_skew_20d_v1",
        "intraday_recovery_skew_20d_raw",
        "DESC",
        "signals that show stronger intraday recovery especially on weaker days may encode a structural resilience signal distinct from close-location or simple path metrics",
    ),
]


def build_feature_views(
    con: duckdb.DuckDBPyConnection,
    sample_panel: Path,
    source_db_path: Path,
    snapshot_id: str,
) -> None:
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
                turnover_rate,
                pct_chg / 100.0 AS pct_ret
            FROM warehouse_db.serving.vw_bars_daily
            WHERE snapshot_id = {sql_quote(snapshot_id)}
        ),
        daily AS (
            SELECT
                instrument,
                signal_date,
                adj_open,
                adj_high,
                adj_low,
                adj_close,
                amount,
                turnover_rate,
                pct_ret,
                LN(GREATEST(amount, 0.0) + 1.0) AS log_amount,
                LN(GREATEST(turnover_rate, 0.0) + 1.0) AS log_turnover,
                LAG(adj_close, 1) OVER w AS prev_adj_close,
                LAG(LN(GREATEST(amount, 0.0) + 1.0), 1) OVER w AS prev_log_amount,
                CASE
                    WHEN pct_ret > 0 THEN amount
                    WHEN pct_ret < 0 THEN -amount
                    ELSE 0.0
                END AS signed_amount_daily,
                CASE
                    WHEN pct_ret > 0 AND amount > AVG(amount) OVER w20
                    THEN 1.0
                    ELSE 0.0
                END AS up_amount_persistence_daily,
                CASE
                    WHEN GREATEST(adj_high - adj_low, 1e-12) > 0
                    THEN (adj_close - adj_open) / GREATEST(adj_high - adj_low, 1e-12)
                    ELSE NULL
                END AS intraday_recovery_daily,
                CASE
                    WHEN pct_ret < 0 THEN 2.0 ELSE 1.0
                END AS intraday_recovery_weight,
                CASE
                    WHEN adj_close > 0
                    THEN (adj_high - adj_low) / adj_close
                    ELSE NULL
                END AS daily_range_ratio,
                CASE
                    WHEN LAG(adj_close, 20) OVER w IS NOT NULL
                         AND LAG(adj_close, 20) OVER w > 0
                         AND SUM(ABS(pct_ret)) OVER w60 > 0
                    THEN (adj_close / LAG(adj_close, 20) OVER w - 1.0) / SUM(ABS(pct_ret)) OVER w60
                    ELSE NULL
                END AS trend_efficiency_60d_point,
                CASE
                    WHEN MAX(adj_close) OVER w20_prev IS NOT NULL
                         AND adj_high >= MAX(adj_close) OVER w20_prev
                         AND adj_close < MAX(adj_close) OVER w20_prev
                         AND MAX(adj_close) OVER w20_prev > 0
                    THEN (MAX(adj_close) OVER w20_prev - adj_close) / MAX(adj_close) OVER w20_prev
                    ELSE 0.0
                END AS breakout_failure_pressure_daily,
                CASE
                    WHEN LAG(adj_close, 1) OVER w IS NOT NULL
                         AND adj_open < LAG(adj_close, 1) OVER w
                    THEN (adj_close - adj_open) / GREATEST(LAG(adj_close, 1) OVER w - adj_open, 1e-12)
                    ELSE NULL
                END AS downside_gap_recovery_daily
            FROM bars
            WINDOW
                w AS (PARTITION BY instrument ORDER BY signal_date),
                w20 AS (
                    PARTITION BY instrument
                    ORDER BY signal_date
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                ),
                w20_prev AS (
                    PARTITION BY instrument
                    ORDER BY signal_date
                    ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING
                ),
                w60 AS (
                    PARTITION BY instrument
                    ORDER BY signal_date
                    ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                )
        )
        SELECT
            instrument,
            signal_date,
            CASE
                WHEN SUM(amount) OVER w20 > 0
                THEN SUM(signed_amount_daily) OVER w20 / SUM(amount) OVER w20
                ELSE NULL
            END AS signed_amount_imbalance_20d_raw,
            AVG(log_turnover) OVER w5 - AVG(log_turnover) OVER w20 AS turnover_acceleration_5_20_raw,
            CORR(pct_ret, log_amount - prev_log_amount) OVER w20 AS volume_price_synchronicity_20d_raw,
            AVG(trend_efficiency_60d_point) OVER w5 AS trend_efficiency_60d_raw,
            CASE
                WHEN AVG(daily_range_ratio) OVER w40 > 0
                THEN AVG(daily_range_ratio) OVER w10 / AVG(daily_range_ratio) OVER w40
                ELSE NULL
            END AS range_compression_10_40_raw,
            AVG(breakout_failure_pressure_daily) OVER w20 AS breakout_failure_pressure_20d_raw,
            AVG(downside_gap_recovery_daily) OVER w10 AS downside_gap_recovery_10d_raw,
            AVG(up_amount_persistence_daily) OVER w20 AS up_amount_persistence_20d_raw,
            STDDEV_SAMP(log_turnover) OVER w20 AS turnover_stability_20d_raw,
            CASE
                WHEN SUM(intraday_recovery_weight) OVER w20 > 0
                THEN SUM(intraday_recovery_daily * intraday_recovery_weight) OVER w20
                     / SUM(intraday_recovery_weight) OVER w20
                ELSE NULL
            END AS intraday_recovery_skew_20d_raw
        FROM daily
        WINDOW
            w5 AS (
                PARTITION BY instrument
                ORDER BY signal_date
                ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
            ),
            w10 AS (
                PARTITION BY instrument
                ORDER BY signal_date
                ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
            ),
            w20 AS (
                PARTITION BY instrument
                ORDER BY signal_date
                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
            ),
            w40 AS (
                PARTITION BY instrument
                ORDER BY signal_date
                ROWS BETWEEN 39 PRECEDING AND CURRENT ROW
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
            b.signed_amount_imbalance_20d_raw,
            b.turnover_acceleration_5_20_raw,
            b.volume_price_synchronicity_20d_raw,
            b.trend_efficiency_60d_raw,
            b.range_compression_10_40_raw,
            b.breakout_failure_pressure_20d_raw,
            b.downside_gap_recovery_10d_raw,
            b.up_amount_persistence_20d_raw,
            b.turnover_stability_20d_raw,
            b.intraday_recovery_skew_20d_raw
        FROM project_sample_panel p
        LEFT JOIN bar_features b
          ON p.instrument = b.instrument
         AND p.signal_date = b.signal_date
        """
    )


def materialize_single_signal(con: duckdb.DuckDBPyConnection, spec: CandidateSpec, run_dir: Path) -> dict:
    return materialize_ranked_single_signal(
        con=con,
        spec=spec,
        run_dir=run_dir,
        score_builder_name=SCORE_BUILDER_NAME,
    )


def main() -> None:
    run_single_signal_batch(
        round_id=ROUND_ID,
        as_of_date=AS_OF_DATE,
        round_label="Round-5",
        base_run_dir=BASE_RUN_DIR,
        round_dir=ROUND_DIR,
        candidate_registry_path=CANDIDATE_REGISTRY_PATH,
        round_registry_path=ROUND_REGISTRY_PATH,
        build_diagnosis_script=BUILD_DIAGNOSIS_SCRIPT,
        score_builder_name=SCORE_BUILDER_NAME,
        candidates=CANDIDATES,
        build_feature_views_fn=build_feature_views,
        materialize_single_signal_fn=materialize_single_signal,
        status_question=(
            "Within the frozen v18 operational contract, does this new atomic "
            "price-volume signal show genuinely positive and head-usable cross-sectional edge "
            "without relying on any family-level composition or portfolio-rule changes?"
        ),
        positive_reason=(
            "Round 5 produced at least one new clean positive keeper, which is enough new information "
            "to reopen family construction with a disciplined one-step composition or screening test."
        ),
        zero_reason=(
            "Round 5 produced zero new clean positive keepers, so the next step should remain "
            "single-signal discovery rather than another family remix."
        ),
        summary_intro=(
            "This round evaluated ten new atomic price-volume signals under the frozen "
            "`price_volume_v18_refresh_hysteresis` operational contract."
        ),
        round_note_prefix="Round 5 batch completed under the frozen v18 operational contract.",
    )


if __name__ == "__main__":
    main()
