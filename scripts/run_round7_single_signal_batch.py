#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Run the full round-7 orthogonal single-signal discovery batch under the frozen
v18 contract.
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
ROUND_ID = "rr_price_volume_single_signal_discovery_v18_round7_orthogonal_20260425"
AS_OF_DATE = "20260425"
BASE_RUN_ID = "signaldiag_rr_price_volume_single_signal_discovery_v18_round4_20260423_base"
BASE_RUN_DIR = RUN_STATE_DIR / BASE_RUN_ID
ROUND_DIR = REGISTRY_DIR / "research_rounds" / ROUND_ID
CANDIDATE_REGISTRY_PATH = REGISTRY_DIR / "candidate_scheme_registry.jsonl"
ROUND_REGISTRY_PATH = REGISTRY_DIR / "research_round_registry.jsonl"
BUILD_DIAGNOSIS_SCRIPT = ROOT / "scripts" / "build_signal_edge_diagnosis.py"
SCORE_BUILDER_NAME = "run_round7_single_signal_batch.py"


CANDIDATES: list[CandidateSpec] = [
    CandidateSpec(
        "price_volume_single_signal_return_autocorr_20d_v1",
        "return_autocorr_20d_raw",
        "DESC",
        "stronger positive short-horizon return autocorrelation may encode a serial-dependence mechanism distinct from simple medium-term momentum ranking",
    ),
    CandidateSpec(
        "price_volume_single_signal_amount_autocorr_20d_v1",
        "amount_autocorr_20d_raw",
        "DESC",
        "more persistent amount dynamics may reveal a trading-activity persistence mechanism distinct from one-off amount shocks",
    ),
    CandidateSpec(
        "price_volume_single_signal_downside_volume_skew_20d_v1",
        "downside_volume_skew_20d_raw",
        "ASC",
        "lower concentration of traded amount on down days may encode a downside-pressure mechanism distinct from broad price-volume confirmation",
    ),
    CandidateSpec(
        "price_volume_single_signal_upside_range_share_20d_v1",
        "upside_range_share_20d_raw",
        "DESC",
        "a larger share of recent trading range occurring on up days may capture directional range participation distinct from close-location or breakout proximity",
    ),
    CandidateSpec(
        "price_volume_single_signal_intraday_trend_bias_20d_v1",
        "intraday_trend_bias_20d_raw",
        "DESC",
        "stronger average intraday drift may encode a session-level trend-quality mechanism distinct from close-to-close momentum",
    ),
    CandidateSpec(
        "price_volume_single_signal_return_skew_20d_v1",
        "return_skew_20d_raw",
        "DESC",
        "more positively skewed recent return distributions may reveal an asymmetry mechanism distinct from volatility level or downside-tail pressure",
    ),
    CandidateSpec(
        "price_volume_single_signal_amount_volatility_20d_v1",
        "amount_volatility_20d_raw",
        "ASC",
        "lower recent amount volatility may encode steadier participation quality distinct from amount level or amount persistence",
    ),
    CandidateSpec(
        "price_volume_single_signal_downside_gap_frequency_20d_v1",
        "downside_gap_frequency_20d_raw",
        "ASC",
        "fewer recent downside gaps may encode an overnight fragility mechanism distinct from post-gap recovery strength",
    ),
    CandidateSpec(
        "price_volume_single_signal_high_low_break_balance_20d_v1",
        "high_low_break_balance_20d_raw",
        "DESC",
        "a stronger balance of high-break events versus low-break events may capture structural dominance more directly than distance-to-breakout or distance-to-breakdown signals",
    ),
    CandidateSpec(
        "price_volume_single_signal_downside_absorption_ratio_20d_v1",
        "downside_absorption_ratio_20d_raw",
        "DESC",
        "stronger absorption on weak days may encode a downside-resilience mechanism distinct from generic downside recovery or intraday skew signals",
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
                pct_ret,
                LN(GREATEST(amount, 0.0) + 1.0) AS log_amount,
                LAG(pct_ret, 1) OVER w AS prev_pct_ret,
                LAG(LN(GREATEST(amount, 0.0) + 1.0), 1) OVER w AS prev_log_amount,
                CASE
                    WHEN pct_ret < 0 THEN amount ELSE 0.0
                END AS downside_amount_daily,
                CASE
                    WHEN pct_ret > 0 AND adj_close > 0 THEN (adj_high - adj_low) / adj_close
                    ELSE 0.0
                END AS upside_range_daily,
                CASE
                    WHEN adj_open > 0 THEN adj_close / adj_open - 1.0
                    ELSE NULL
                END AS intraday_trend_daily,
                CASE
                    WHEN LAG(adj_close, 1) OVER w IS NOT NULL AND adj_open < LAG(adj_close, 1) OVER w
                    THEN 1.0 ELSE 0.0
                END AS downside_gap_daily,
                CASE
                    WHEN GREATEST(adj_high - adj_low, 1e-12) > 0 AND pct_ret < 0
                    THEN (adj_close - adj_low) / GREATEST(adj_high - adj_low, 1e-12)
                    ELSE NULL
                END AS downside_absorption_daily,
                CASE
                    WHEN MAX(adj_high) OVER w20_prev IS NOT NULL
                         AND adj_high >= MAX(adj_high) OVER w20_prev
                    THEN 1.0 ELSE 0.0
                END AS high_break_daily,
                CASE
                    WHEN MIN(adj_low) OVER w20_prev IS NOT NULL
                         AND adj_low <= MIN(adj_low) OVER w20_prev
                    THEN 1.0 ELSE 0.0
                END AS low_break_daily
            FROM bars
            WINDOW
                w AS (PARTITION BY instrument ORDER BY signal_date),
                w20_prev AS (
                    PARTITION BY instrument
                    ORDER BY signal_date
                    ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING
                )
        )
        SELECT
            instrument,
            signal_date,
            CORR(pct_ret, prev_pct_ret) OVER w20 AS return_autocorr_20d_raw,
            CORR(log_amount, prev_log_amount) OVER w20 AS amount_autocorr_20d_raw,
            CASE
                WHEN SUM(amount) OVER w20 > 0
                THEN SUM(downside_amount_daily) OVER w20 / SUM(amount) OVER w20
                ELSE NULL
            END AS downside_volume_skew_20d_raw,
            CASE
                WHEN SUM(CASE WHEN adj_close > 0 THEN (adj_high - adj_low) / adj_close ELSE 0.0 END) OVER w20 > 0
                THEN SUM(upside_range_daily) OVER w20
                     / SUM(CASE WHEN adj_close > 0 THEN (adj_high - adj_low) / adj_close ELSE 0.0 END) OVER w20
                ELSE NULL
            END AS upside_range_share_20d_raw,
            AVG(intraday_trend_daily) OVER w20 AS intraday_trend_bias_20d_raw,
            CASE
                WHEN (AVG(pct_ret * pct_ret) OVER w20 - POWER(AVG(pct_ret) OVER w20, 2)) > 0
                THEN (
                    AVG(pct_ret * pct_ret * pct_ret) OVER w20
                    - 3 * AVG(pct_ret) OVER w20 * AVG(pct_ret * pct_ret) OVER w20
                    + 2 * POWER(AVG(pct_ret) OVER w20, 3)
                ) / POWER(
                    AVG(pct_ret * pct_ret) OVER w20 - POWER(AVG(pct_ret) OVER w20, 2),
                    1.5
                )
                ELSE NULL
            END AS return_skew_20d_raw,
            STDDEV_SAMP(log_amount) OVER w20 AS amount_volatility_20d_raw,
            AVG(downside_gap_daily) OVER w20 AS downside_gap_frequency_20d_raw,
            AVG(high_break_daily - low_break_daily) OVER w20 AS high_low_break_balance_20d_raw,
            AVG(downside_absorption_daily) OVER w20 AS downside_absorption_ratio_20d_raw
        FROM daily
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
            b.return_autocorr_20d_raw,
            b.amount_autocorr_20d_raw,
            b.downside_volume_skew_20d_raw,
            b.upside_range_share_20d_raw,
            b.intraday_trend_bias_20d_raw,
            b.return_skew_20d_raw,
            b.amount_volatility_20d_raw,
            b.downside_gap_frequency_20d_raw,
            b.high_low_break_balance_20d_raw,
            b.downside_absorption_ratio_20d_raw
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
        round_label="Round-7",
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
            "Within the frozen v18 operational contract, does this more orthogonal atomic "
            "price-volume signal show genuinely positive and head-usable cross-sectional edge "
            "without colliding with existing canonical alias clusters or relying on family-level composition?"
        ),
        positive_reason=(
            "Round 7 produced at least one genuinely orthogonal clean positive keeper, which is enough "
            "new information to justify a later composability screen under the frozen v18 baseline."
        ),
        zero_reason=(
            "Round 7 produced zero genuinely orthogonal clean positive keepers, so the next step should "
            "remain atomic discovery or pause rather than reopening family construction."
        ),
        summary_intro=(
            "This round evaluated ten more orthogonal atomic price-volume signals under the frozen "
            "`price_volume_v18_refresh_hysteresis` operational contract after explicitly treating round 6 "
            "as a standardization-and-dedup pass."
        ),
        round_note_prefix="Round 7 batch completed under the frozen v18 operational contract.",
    )


if __name__ == "__main__":
    main()
