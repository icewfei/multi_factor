#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Run the full round-6 single-signal discovery batch under the frozen v18 contract.

This round uses more standardized atomic price-volume signals inspired by
Alpha158-style feature construction, but every field is implemented directly
inside this project and does not depend on any neighboring qlib adapter.
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
ROUND_ID = "rr_price_volume_single_signal_discovery_v18_round6_alpha158_paper_20260425"
AS_OF_DATE = "20260425"
BASE_RUN_ID = "signaldiag_rr_price_volume_single_signal_discovery_v18_round4_20260423_base"
BASE_RUN_DIR = RUN_STATE_DIR / BASE_RUN_ID
ROUND_DIR = REGISTRY_DIR / "research_rounds" / ROUND_ID
CANDIDATE_REGISTRY_PATH = REGISTRY_DIR / "candidate_scheme_registry.jsonl"
ROUND_REGISTRY_PATH = REGISTRY_DIR / "research_round_registry.jsonl"
BUILD_DIAGNOSIS_SCRIPT = ROOT / "scripts" / "build_signal_edge_diagnosis.py"
SCORE_BUILDER_NAME = "run_round6_single_signal_batch.py"


CANDIDATES: list[CandidateSpec] = [
    CandidateSpec(
        "price_volume_single_signal_price_volume_corr_20d_v1",
        "price_volume_corr_20d_raw",
        "DESC",
        "a stronger positive 20-day correlation between daily return and change in traded amount may encode a standardized price-volume confirmation signal",
    ),
    CandidateSpec(
        "price_volume_single_signal_turnover_mean_reversion_gap_5_20_v1",
        "turnover_mean_reversion_gap_5_20_raw",
        "ASC",
        "a smaller short-vs-medium turnover deviation may capture cleaner participation normalization than simple turnover acceleration alone",
    ),
    CandidateSpec(
        "price_volume_single_signal_volume_momentum_5_20_v1",
        "volume_momentum_5_20_raw",
        "DESC",
        "a stronger recent amount momentum relative to a 20-day baseline may reveal standardized volume persistence",
    ),
    CandidateSpec(
        "price_volume_single_signal_close_to_high_ratio_20d_v1",
        "close_to_high_ratio_20d_raw",
        "DESC",
        "signals that persistently close nearer the top of the daily range may represent a standardized trend-quality signal",
    ),
    CandidateSpec(
        "price_volume_single_signal_upper_shadow_pressure_20d_v1",
        "upper_shadow_pressure_20d_raw",
        "ASC",
        "lower recent upper-shadow pressure may indicate less overhead supply and cleaner continuation structure",
    ),
    CandidateSpec(
        "price_volume_single_signal_path_efficiency_60d_v1",
        "path_efficiency_60d_raw",
        "DESC",
        "a more efficient 60-day path may provide a slower and more standardized trend-quality edge than broad momentum alone",
    ),
    CandidateSpec(
        "price_volume_single_signal_breakout_distance_20d_v1",
        "breakout_distance_20d_raw",
        "DESC",
        "signals trading closer to the recent 20-day breakout boundary may encode a standardized structural-position signal",
    ),
    CandidateSpec(
        "price_volume_single_signal_breakdown_distance_20d_v1",
        "breakdown_distance_20d_raw",
        "ASC",
        "signals trading farther from the recent 20-day breakdown boundary may encode downside-distance resilience",
    ),
    CandidateSpec(
        "price_volume_single_signal_range_compression_5_20_v1",
        "range_compression_5_20_raw",
        "ASC",
        "lower recent range expansion relative to a 20-day baseline may capture a standardized compression state distinct from level volatility",
    ),
    CandidateSpec(
        "price_volume_single_signal_downside_recovery_strength_10d_v1",
        "downside_recovery_strength_10d_raw",
        "DESC",
        "stronger recovery after recent weak opens or intraday downside pressure may encode a standardized resilience signal",
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
                    WHEN GREATEST(adj_high - adj_low, 1e-12) > 0
                    THEN (adj_close - adj_low) / GREATEST(adj_high - adj_low, 1e-12)
                    ELSE NULL
                END AS close_to_high_daily,
                CASE
                    WHEN GREATEST(adj_high - adj_low, 1e-12) > 0
                    THEN (adj_high - GREATEST(adj_open, adj_close)) / GREATEST(adj_high - adj_low, 1e-12)
                    ELSE NULL
                END AS upper_shadow_pressure_daily,
                CASE
                    WHEN adj_close > 0
                    THEN (adj_high - adj_low) / adj_close
                    ELSE NULL
                END AS daily_range_ratio,
                CASE
                    WHEN LAG(adj_close, 60) OVER w IS NOT NULL
                         AND LAG(adj_close, 60) OVER w > 0
                         AND SUM(ABS(pct_ret)) OVER w60 > 0
                    THEN ABS(adj_close / LAG(adj_close, 60) OVER w - 1.0) / SUM(ABS(pct_ret)) OVER w60
                    ELSE NULL
                END AS path_efficiency_60d_point,
                CASE
                    WHEN LAG(adj_close, 1) OVER w IS NOT NULL
                         AND (adj_open < LAG(adj_close, 1) OVER w OR pct_ret < 0)
                         AND GREATEST(adj_high - adj_low, 1e-12) > 0
                    THEN (adj_close - adj_low) / GREATEST(adj_high - adj_low, 1e-12)
                    ELSE NULL
                END AS downside_recovery_daily
            FROM bars
            WINDOW
                w AS (PARTITION BY instrument ORDER BY signal_date),
                w60 AS (
                    PARTITION BY instrument
                    ORDER BY signal_date
                    ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                )
        )
        SELECT
            instrument,
            signal_date,
            CORR(pct_ret, log_amount - prev_log_amount) OVER w20 AS price_volume_corr_20d_raw,
            AVG(log_turnover) OVER w5 - AVG(log_turnover) OVER w20 AS turnover_mean_reversion_gap_5_20_raw,
            AVG(log_amount) OVER w5 - AVG(log_amount) OVER w20 AS volume_momentum_5_20_raw,
            AVG(close_to_high_daily) OVER w20 AS close_to_high_ratio_20d_raw,
            AVG(upper_shadow_pressure_daily) OVER w20 AS upper_shadow_pressure_20d_raw,
            AVG(path_efficiency_60d_point) OVER w5 AS path_efficiency_60d_raw,
            CASE
                WHEN MAX(adj_close) OVER w20_prev > 0
                THEN adj_close / MAX(adj_close) OVER w20_prev
                ELSE NULL
            END AS breakout_distance_20d_raw,
            CASE
                WHEN adj_close > 0
                     AND MIN(adj_close) OVER w20_prev IS NOT NULL
                THEN MIN(adj_close) OVER w20_prev / adj_close
                ELSE NULL
            END AS breakdown_distance_20d_raw,
            CASE
                WHEN AVG(daily_range_ratio) OVER w20 > 0
                THEN AVG(daily_range_ratio) OVER w5 / AVG(daily_range_ratio) OVER w20
                ELSE NULL
            END AS range_compression_5_20_raw,
            AVG(downside_recovery_daily) OVER w10 AS downside_recovery_strength_10d_raw
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
            w20_prev AS (
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
            b.price_volume_corr_20d_raw,
            b.turnover_mean_reversion_gap_5_20_raw,
            b.volume_momentum_5_20_raw,
            b.close_to_high_ratio_20d_raw,
            b.upper_shadow_pressure_20d_raw,
            b.path_efficiency_60d_raw,
            b.breakout_distance_20d_raw,
            b.breakdown_distance_20d_raw,
            b.range_compression_5_20_raw,
            b.downside_recovery_strength_10d_raw
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
        round_label="Round-6",
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
            "Within the frozen v18 operational contract, does this more standardized atomic "
            "price-volume signal show genuinely positive and head-usable cross-sectional edge "
            "without relying on any family-level composition or portfolio-rule changes?"
        ),
        positive_reason=(
            "Round 6 produced at least one new clean positive keeper, which is enough new information "
            "to reopen family construction or composability screening with a disciplined next step."
        ),
        zero_reason=(
            "Round 6 produced zero new clean positive keepers, so the next step should remain atomic "
            "single-signal discovery rather than another family remix."
        ),
        summary_intro=(
            "This round evaluated ten more standardized atomic price-volume signals under the frozen "
            "`price_volume_v18_refresh_hysteresis` operational contract."
        ),
        round_note_prefix="Round 6 batch completed under the frozen v18 operational contract.",
    )


if __name__ == "__main__":
    main()
