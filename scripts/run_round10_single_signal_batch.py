#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Run the full round-10 whitelist-only single-signal discovery batch under the
frozen v18 contract.
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
ROUND_ID = "rr_price_volume_single_signal_discovery_v18_round10_alpha158_paper_whitelist_20260428"
AS_OF_DATE = "20260428"
BASE_RUN_ID = "signaldiag_rr_price_volume_single_signal_discovery_v18_round4_20260423_base"
BASE_RUN_DIR = RUN_STATE_DIR / BASE_RUN_ID
ROUND_DIR = REGISTRY_DIR / "research_rounds" / ROUND_ID
CANDIDATE_REGISTRY_PATH = REGISTRY_DIR / "candidate_scheme_registry.jsonl"
ROUND_REGISTRY_PATH = REGISTRY_DIR / "research_round_registry.jsonl"
BUILD_DIAGNOSIS_SCRIPT = ROOT / "scripts" / "build_signal_edge_diagnosis.py"
SCORE_BUILDER_NAME = "run_round10_single_signal_batch.py"


CANDIDATES: list[CandidateSpec] = [
    CandidateSpec(
        "price_volume_single_signal_amihud_illiquidity_20d_v1",
        "amihud_illiquidity_20d_raw",
        "ASC",
        "lower Amihud-style illiquidity indicates lower expected price impact per unit traded amount and potentially cleaner executable cross-sectional edge",
    ),
    CandidateSpec(
        "price_volume_single_signal_turnover_concentration_hhi_20d_v1",
        "turnover_concentration_hhi_20d_raw",
        "ASC",
        "lower turnover concentration implies more distributed participation across days and potentially more stable tradability quality",
    ),
    CandidateSpec(
        "price_volume_single_signal_close_to_vwap_bias_20d_v1",
        "close_to_vwap_bias_20d_raw",
        "DESC",
        "persistent close-above-vwap tendency may capture session-end demand quality beyond simple close-location within daily range",
    ),
    CandidateSpec(
        "price_volume_single_signal_intraday_range_skew_20d_v1",
        "intraday_range_skew_20d_raw",
        "ASC",
        "lower downside-skewed intraday range behavior may indicate healthier session microstructure and reduced downside dominance",
    ),
    CandidateSpec(
        "price_volume_single_signal_gap_reversal_intensity_20d_v1",
        "gap_reversal_intensity_20d_raw",
        "DESC",
        "stronger post-gap reversal intensity may encode short-horizon mean-repair dynamics beyond simple gap-fill frequency",
    ),
    CandidateSpec(
        "price_volume_single_signal_signed_dollar_flow_persistence_20d_v1",
        "signed_dollar_flow_persistence_20d_raw",
        "DESC",
        "more persistent signed dollar-flow alignment may capture sustained participation pressure beyond one-window imbalance levels",
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
                LAG(adj_close, 1) OVER w AS prev_close,
                LAG(
                    CASE
                        WHEN pct_ret > 0 THEN amount
                        WHEN pct_ret < 0 THEN -amount
                        ELSE 0.0
                    END,
                    1
                ) OVER w AS prev_signed_flow,
                CASE
                    WHEN amount > 0
                    THEN ABS(pct_ret) / amount
                    ELSE NULL
                END AS amihud_daily,
                CASE
                    WHEN adj_open > 0
                    THEN adj_close / adj_open - 1.0
                    ELSE NULL
                END AS intraday_ret,
                CASE
                    WHEN adj_high > adj_low
                    THEN (adj_close - (adj_open + adj_high + adj_low + adj_close) / 4.0)
                         / GREATEST((adj_open + adj_high + adj_low + adj_close) / 4.0, 1e-12)
                    ELSE NULL
                END AS close_to_vwap_bias_daily,
                CASE
                    WHEN adj_high > adj_low AND adj_close < adj_open
                    THEN (adj_open - adj_low) / GREATEST(adj_high - adj_low, 1e-12)
                    ELSE 0.0
                END AS downside_range_pressure_daily,
                CASE
                    WHEN adj_high > adj_low AND adj_close > adj_open
                    THEN (adj_high - adj_open) / GREATEST(adj_high - adj_low, 1e-12)
                    ELSE 0.0
                END AS upside_range_pressure_daily,
                CASE
                    WHEN prev_close > 0
                    THEN adj_open / prev_close - 1.0
                    ELSE NULL
                END AS gap_ret,
                CASE
                    WHEN pct_ret > 0 THEN amount
                    WHEN pct_ret < 0 THEN -amount
                    ELSE 0.0
                END AS signed_flow_daily
            FROM bars
            WINDOW w AS (PARTITION BY instrument ORDER BY signal_date)
        ),
        enriched AS (
            SELECT
                instrument,
                signal_date,
                amihud_daily,
                turnover_rate,
                close_to_vwap_bias_daily,
                downside_range_pressure_daily,
                upside_range_pressure_daily,
                signed_flow_daily,
                prev_signed_flow,
                CASE
                    WHEN gap_ret IS NOT NULL
                     AND ABS(gap_ret) > 1e-12
                     AND intraday_ret IS NOT NULL
                    THEN GREATEST(0.0, -SIGN(gap_ret) * intraday_ret) / ABS(gap_ret)
                    ELSE NULL
                END AS gap_reversal_intensity_daily
            FROM daily
        ),
        with_turnover_hhi AS (
            SELECT
                instrument,
                signal_date,
                amihud_daily,
                turnover_rate,
                close_to_vwap_bias_daily,
                downside_range_pressure_daily,
                upside_range_pressure_daily,
                gap_reversal_intensity_daily,
                signed_flow_daily,
                prev_signed_flow,
                CASE
                    WHEN SUM(GREATEST(turnover_rate, 0.0)) OVER w20 > 0
                    THEN GREATEST(turnover_rate, 0.0) / SUM(GREATEST(turnover_rate, 0.0)) OVER w20
                    ELSE NULL
                END AS turnover_share_20
            FROM enriched
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
            AVG(amihud_daily) OVER w20 AS amihud_illiquidity_20d_raw,
            SUM(POWER(turnover_share_20, 2)) OVER w20 AS turnover_concentration_hhi_20d_raw,
            AVG(close_to_vwap_bias_daily) OVER w20 AS close_to_vwap_bias_20d_raw,
            AVG(downside_range_pressure_daily) OVER w20
            - AVG(upside_range_pressure_daily) OVER w20 AS intraday_range_skew_20d_raw,
            AVG(gap_reversal_intensity_daily) OVER w20 AS gap_reversal_intensity_20d_raw,
            CORR(signed_flow_daily, prev_signed_flow) OVER w20 AS signed_dollar_flow_persistence_20d_raw
        FROM with_turnover_hhi
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
            b.amihud_illiquidity_20d_raw,
            b.turnover_concentration_hhi_20d_raw,
            b.close_to_vwap_bias_20d_raw,
            b.intraday_range_skew_20d_raw,
            b.gap_reversal_intensity_20d_raw,
            b.signed_dollar_flow_persistence_20d_raw
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
        round_label="Round-10",
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
            "Within the frozen v18 operational contract and whitelist-only source policy, "
            "does this literature-anchored atomic price-volume signal show positive and "
            "head-usable cross-sectional edge with better odds of passing composability hard-gate promotion?"
        ),
        positive_reason=(
            "Round 10 produced at least one clean positive whitelist keeper, so the next step can proceed "
            "to controlled composability screening under the frozen v18 reference."
        ),
        zero_reason=(
            "Round 10 produced zero clean positive whitelist keepers, so we should continue whitelist-only "
            "atomic discovery rather than reopening family construction."
        ),
        summary_intro=(
            "This round evaluated six whitelist-only Alpha158/literature-inspired atomic price-volume "
            "signals under the frozen `price_volume_v18_refresh_hysteresis` operational contract."
        ),
        round_note_prefix="Round 10 whitelist-only batch completed under the frozen v18 operational contract.",
    )


if __name__ == "__main__":
    main()
