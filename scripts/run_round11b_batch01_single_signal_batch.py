#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Run round11b batch01 (serial-only whitelist batch) under the frozen v18 contract.
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
ROUND_ID = "rr_price_volume_single_signal_discovery_v18_round11b_batch01_20260428"
AS_OF_DATE = "20260428"
BASE_RUN_ID = "signaldiag_rr_price_volume_single_signal_discovery_v18_round4_20260423_base"
BASE_RUN_DIR = RUN_STATE_DIR / BASE_RUN_ID
ROUND_DIR = REGISTRY_DIR / "research_rounds" / ROUND_ID
CANDIDATE_REGISTRY_PATH = REGISTRY_DIR / "candidate_scheme_registry.jsonl"
ROUND_REGISTRY_PATH = REGISTRY_DIR / "research_round_registry.jsonl"
BUILD_DIAGNOSIS_SCRIPT = ROOT / "scripts" / "build_signal_edge_diagnosis.py"
SCORE_BUILDER_NAME = "run_round11b_batch01_single_signal_batch.py"


CANDIDATES: list[CandidateSpec] = [
    CandidateSpec("price_volume_single_signal_price_volume_beta_20d_v1", "price_volume_beta_20d_raw", "DESC", "rolling price-volume slope sensitivity"),
    CandidateSpec("price_volume_single_signal_price_volume_rank_corr_20d_v1", "price_volume_rank_corr_20d_raw", "DESC", "rank-style return-volume dependence proxy"),
    CandidateSpec("price_volume_single_signal_turnover_entropy_20d_v1", "turnover_entropy_20d_raw", "DESC", "turnover distribution diversity"),
    CandidateSpec("price_volume_single_signal_candle_body_efficiency_20d_v1", "candle_body_efficiency_20d_raw", "DESC", "body-to-range directional efficiency"),
    CandidateSpec("price_volume_single_signal_upper_lower_shadow_asymmetry_20d_v1", "upper_lower_shadow_asymmetry_20d_raw", "ASC", "upper-vs-lower shadow imbalance"),
    CandidateSpec("price_volume_single_signal_gap_to_range_ratio_20d_v1", "gap_to_range_ratio_20d_raw", "ASC", "gap dislocation normalized by intraday range"),
    CandidateSpec("price_volume_single_signal_close_position_stability_20d_v1", "close_position_stability_20d_raw", "DESC", "stability of close location in daily bar"),
    CandidateSpec("price_volume_single_signal_rolling_vwap_distance_20d_v1", "rolling_vwap_distance_20d_raw", "ASC", "distance to rolling VWAP anchor"),
    CandidateSpec("price_volume_single_signal_downside_range_convexity_20d_v1", "downside_range_convexity_20d_raw", "ASC", "downside range nonlinearity"),
    CandidateSpec("price_volume_single_signal_updown_volume_balance_persistence_20d_v1", "updown_volume_balance_persistence_20d_raw", "DESC", "persistence of up/down flow balance"),
    CandidateSpec("price_volume_single_signal_intraday_path_curvature_20d_v1", "intraday_path_curvature_20d_raw", "ASC", "intraday path roughness proxy"),
    CandidateSpec("price_volume_single_signal_liquidity_shock_recovery_ratio_20d_v1", "liquidity_shock_recovery_ratio_20d_raw", "DESC", "post-shock liquidity recovery"),
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
                COALESCE(turnover_rate, 0.0) AS turnover_rate,
                pct_ret,
                LN(GREATEST(amount, 0.0) + 1.0) AS log_amount,
                LN(GREATEST(COALESCE(turnover_rate, 0.0), 0.0) + 1.0) AS log_turnover,
                LAG(LN(GREATEST(amount, 0.0) + 1.0), 1) OVER w AS prev_log_amount,
                LAG(adj_close, 1) OVER w AS prev_close
            FROM bars
            WINDOW w AS (PARTITION BY instrument ORDER BY signal_date)
        ),
        enriched AS (
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
                log_amount,
                prev_log_amount,
                (log_amount - prev_log_amount) AS dlog_amount,
                CASE
                    WHEN adj_high > adj_low
                    THEN ABS(adj_close - adj_open) / GREATEST(adj_high - adj_low, 1e-12)
                    ELSE NULL
                END AS candle_body_eff_daily,
                CASE
                    WHEN adj_high > adj_low
                    THEN (adj_high - GREATEST(adj_open, adj_close)) / GREATEST(adj_high - adj_low, 1e-12)
                    ELSE NULL
                END AS upper_shadow_daily,
                CASE
                    WHEN adj_high > adj_low
                    THEN (LEAST(adj_open, adj_close) - adj_low) / GREATEST(adj_high - adj_low, 1e-12)
                    ELSE NULL
                END AS lower_shadow_daily,
                CASE
                    WHEN adj_high > adj_low
                    THEN (adj_close - adj_low) / GREATEST(adj_high - adj_low, 1e-12)
                    ELSE NULL
                END AS close_loc_daily,
                CASE
                    WHEN adj_close > 0
                    THEN (adj_high - adj_low) / adj_close
                    ELSE NULL
                END AS range_ratio_daily,
                CASE
                    WHEN prev_close > 0
                    THEN adj_open / prev_close - 1.0
                    ELSE NULL
                END AS gap_ret,
                CASE
                    WHEN adj_open > 0
                    THEN (adj_close - adj_open) / adj_open
                    ELSE NULL
                END AS intraday_ret,
                CASE
                    WHEN pct_ret > 0 THEN 1.0
                    WHEN pct_ret < 0 THEN -1.0
                    ELSE 0.0
                END AS signed_flow_ratio_daily,
                CASE
                    WHEN adj_high > adj_low AND pct_ret < 0
                    THEN (adj_open - adj_low) / GREATEST(adj_high - adj_low, 1e-12)
                    ELSE 0.0
                END AS downside_range_pressure_daily
            FROM daily
        ),
        with_anchors AS (
            SELECT
                *,
                CASE
                    WHEN SUM(amount) OVER w20 > 0
                    THEN SUM(adj_close * amount) OVER w20 / SUM(amount) OVER w20
                    ELSE NULL
                END AS rolling_vwap20,
                AVG(log_amount) OVER w20 AS avg_log_amount20,
                LAG(signed_flow_ratio_daily, 1) OVER (
                    PARTITION BY instrument
                    ORDER BY signal_date
                ) AS prev_signed_flow_ratio
            FROM enriched
            WINDOW
                w AS (PARTITION BY instrument ORDER BY signal_date),
                w20 AS (
                    PARTITION BY instrument
                    ORDER BY signal_date
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                )
        ),
        with_shock AS (
            SELECT
                *,
                ABS(log_amount - avg_log_amount20) AS abs_shock,
                LAG(ABS(log_amount - avg_log_amount20), 1) OVER (
                    PARTITION BY instrument
                    ORDER BY signal_date
                ) AS prev_abs_shock
            FROM with_anchors
        ),
        with_turnover_share AS (
            SELECT
                *,
                CASE
                    WHEN SUM(GREATEST(turnover_rate, 0.0)) OVER w20 > 0
                    THEN GREATEST(turnover_rate, 0.0) / SUM(GREATEST(turnover_rate, 0.0)) OVER w20
                    ELSE NULL
                END AS turnover_share20
            FROM with_shock
            WINDOW
                w20 AS (
                    PARTITION BY instrument
                    ORDER BY signal_date
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                )
        )
        SELECT
            instrument,
            signal_date,
            CASE
                WHEN VAR_SAMP(dlog_amount) OVER w20 > 1e-12
                THEN COVAR_SAMP(pct_ret, dlog_amount) OVER w20 / VAR_SAMP(dlog_amount) OVER w20
                ELSE NULL
            END AS price_volume_beta_20d_raw,
            CORR(SIGN(pct_ret), SIGN(dlog_amount)) OVER w20 AS price_volume_rank_corr_20d_raw,
            1.0 - SUM(POWER(turnover_share20, 2)) OVER w20 AS turnover_entropy_20d_raw,
            AVG(candle_body_eff_daily) OVER w20 AS candle_body_efficiency_20d_raw,
            AVG(upper_shadow_daily - lower_shadow_daily) OVER w20 AS upper_lower_shadow_asymmetry_20d_raw,
            AVG(
                CASE
                    WHEN range_ratio_daily > 1e-12 AND gap_ret IS NOT NULL
                    THEN ABS(gap_ret) / range_ratio_daily
                    ELSE NULL
                END
            ) OVER w20 AS gap_to_range_ratio_20d_raw,
            -STDDEV_SAMP(close_loc_daily) OVER w20 AS close_position_stability_20d_raw,
            AVG(
                CASE
                    WHEN rolling_vwap20 > 1e-12
                    THEN ABS(adj_close - rolling_vwap20) / rolling_vwap20
                    ELSE NULL
                END
            ) OVER w20 AS rolling_vwap_distance_20d_raw,
            CASE
                WHEN AVG(downside_range_pressure_daily) OVER w20 > 1e-12
                THEN AVG(POWER(downside_range_pressure_daily, 2)) OVER w20
                     / AVG(downside_range_pressure_daily) OVER w20
                ELSE NULL
            END AS downside_range_convexity_20d_raw,
            CORR(
                signed_flow_ratio_daily,
                prev_signed_flow_ratio
            ) OVER w20 AS updown_volume_balance_persistence_20d_raw,
            AVG(
                CASE
                    WHEN range_ratio_daily IS NOT NULL AND intraday_ret IS NOT NULL
                    THEN GREATEST(range_ratio_daily - ABS(intraday_ret), 0.0)
                    ELSE NULL
                END
            ) OVER w20 AS intraday_path_curvature_20d_raw,
            AVG(
                CASE
                    WHEN prev_abs_shock IS NOT NULL AND prev_abs_shock > 1e-12
                    THEN (prev_abs_shock - abs_shock) / prev_abs_shock
                    ELSE NULL
                END
            ) OVER w20 AS liquidity_shock_recovery_ratio_20d_raw
        FROM with_turnover_share
        WINDOW
            w20 AS (
                PARTITION BY instrument
                ORDER BY signal_date
                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
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
            b.price_volume_beta_20d_raw,
            b.price_volume_rank_corr_20d_raw,
            b.turnover_entropy_20d_raw,
            b.candle_body_efficiency_20d_raw,
            b.upper_lower_shadow_asymmetry_20d_raw,
            b.gap_to_range_ratio_20d_raw,
            b.close_position_stability_20d_raw,
            b.rolling_vwap_distance_20d_raw,
            b.downside_range_convexity_20d_raw,
            b.updown_volume_balance_persistence_20d_raw,
            b.intraday_path_curvature_20d_raw,
            b.liquidity_shock_recovery_ratio_20d_raw
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
        round_label="Round-11b-Batch01",
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
            "Within round11b serial-only whitelist execution, does this full158 candidate show positive and head-usable "
            "signal-edge under frozen v18 contract?"
        ),
        positive_reason=(
            "Batch01 produced at least one clean positive keeper and can proceed to composability-screening intake after serial batch completion policy."
        ),
        zero_reason=(
            "Batch01 produced zero clean positive keepers; continue serial-only full158 discovery batches and do not reopen family construction."
        ),
        summary_intro=(
            "This batch is the first serial executable tranche inside round11b full158 governance under frozen "
            "`price_volume_v18_refresh_hysteresis` contract."
        ),
        round_note_prefix="Round11b batch01 serial run completed under whitelist-only governance.",
    )


if __name__ == "__main__":
    main()
