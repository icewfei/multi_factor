#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Run the full round-4 single-signal discovery batch under the frozen v18 contract.

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
ROUND_ID = "rr_price_volume_single_signal_discovery_v18_round4_20260423"
AS_OF_DATE = "20260423"
BASE_RUN_ID = "signaldiag_rr_price_volume_single_signal_discovery_v18_round4_20260423_base"
BASE_RUN_DIR = RUN_STATE_DIR / BASE_RUN_ID
ROUND_DIR = REGISTRY_DIR / "research_rounds" / ROUND_ID
CANDIDATE_REGISTRY_PATH = REGISTRY_DIR / "candidate_scheme_registry.jsonl"
ROUND_REGISTRY_PATH = REGISTRY_DIR / "research_round_registry.jsonl"
BUILD_DIAGNOSIS_SCRIPT = ROOT / "scripts" / "build_signal_edge_diagnosis.py"
SCORE_BUILDER_NAME = "run_round4_single_signal_batch.py"


CANDIDATES: list[CandidateSpec] = [
    CandidateSpec(
        "price_volume_single_signal_breakout_proximity_20d_v1",
        "breakout_proximity_20d_raw",
        "DESC",
        "signals trading near the recent 20-day breakout boundary may show cleaner structural continuation than broad momentum alone",
    ),
    CandidateSpec(
        "price_volume_single_signal_breakout_proximity_60d_v1",
        "breakout_proximity_60d_raw",
        "DESC",
        "signals trading near the recent 60-day breakout boundary may offer a slower and thicker structural trend-position signal",
    ),
    CandidateSpec(
        "price_volume_single_signal_close_location_value_20d_v1",
        "close_location_value_20d_raw",
        "DESC",
        "signals that persistently close near the top of their intraday range may encode a more durable trend-quality signal than simple up-day frequency",
    ),
    CandidateSpec(
        "price_volume_single_signal_upper_shadow_ratio_20d_v1",
        "upper_shadow_ratio_20d_raw",
        "ASC",
        "signals with consistently smaller upper-shadow pressure may indicate cleaner continuation and less near-term overhead supply",
    ),
    CandidateSpec(
        "price_volume_single_signal_amount_shock_5_20_v1",
        "amount_shock_5_20_raw",
        "DESC",
        "a short-horizon amount surge relative to a 20-day baseline may provide cleaner volume-intensity information than structural liquidity-level signals",
    ),
    CandidateSpec(
        "price_volume_single_signal_up_volume_share_20d_v1",
        "up_volume_share_20d_raw",
        "DESC",
        "signals whose recent traded amount is concentrated on up days may encode stronger price-volume confirmation",
    ),
    CandidateSpec(
        "price_volume_single_signal_breakout_volume_confirmation_20d_v1",
        "breakout_volume_confirmation_20d_raw",
        "DESC",
        "signals that are simultaneously near breakout and experiencing a recent amount shock may provide a stronger position-plus-confirmation atomic edge",
    ),
    CandidateSpec(
        "price_volume_single_signal_gap_followthrough_10d_v1",
        "gap_followthrough_10d_raw",
        "DESC",
        "signals that both gap and continue in the same direction may reveal a cleaner short-horizon continuation mechanism than close-to-close reversal variants",
    ),
    CandidateSpec(
        "price_volume_single_signal_downside_tail_pressure_20d_v1",
        "downside_tail_pressure_20d_raw",
        "ASC",
        "signals with lower recent downside-tail pressure may offer a more useful downside-quality filter than simple realized-volatility measures",
    ),
    CandidateSpec(
        "price_volume_single_signal_path_efficiency_20d_v1",
        "path_efficiency_20d_raw",
        "DESC",
        "signals that travel more efficiently over a 20-day path may provide a cleaner trend-quality atomic signal than raw consistency counts",
    ),
]


def build_feature_views(con: duckdb.DuckDBPyConnection, sample_panel: Path, source_db_path: Path, snapshot_id: str) -> None:
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
                CASE
                    WHEN GREATEST(adj_high - adj_low, 1e-12) > 0
                    THEN (adj_close - adj_low) / GREATEST(adj_high - adj_low, 1e-12)
                    ELSE NULL
                END AS close_location_daily,
                CASE
                    WHEN GREATEST(adj_high - adj_low, 1e-12) > 0
                    THEN (adj_high - adj_close) / GREATEST(adj_high - adj_low, 1e-12)
                    ELSE NULL
                END AS upper_shadow_daily,
                CASE
                    WHEN pct_ret > 0 THEN amount ELSE 0.0 END AS up_amount_daily,
                CASE
                    WHEN LAG(adj_close, 1) OVER w IS NOT NULL
                         AND GREATEST(adj_open, 1e-12) > 0
                    THEN
                        ((adj_open / LAG(adj_close, 1) OVER w) - 1.0) *
                        CASE
                            WHEN (adj_close / GREATEST(adj_open, 1e-12) - 1.0) > 0 THEN 1.0
                            WHEN (adj_close / GREATEST(adj_open, 1e-12) - 1.0) < 0 THEN -1.0
                            ELSE 0.0
                        END
                    ELSE NULL
                END AS gap_followthrough_daily,
                POWER(ABS(LEAST(pct_ret, 0.0)), 2) AS downside_tail_pressure_daily
            FROM bars
            WINDOW w AS (PARTITION BY instrument ORDER BY signal_date)
        )
        SELECT
            instrument,
            signal_date,
            adj_open,
            adj_high,
            adj_low,
            adj_close,
            amount,
            pct_ret,
            MAX(adj_close) OVER w20_prev AS breakout_anchor_20d,
            MAX(adj_close) OVER w60_prev AS breakout_anchor_60d,
            CASE
                WHEN MAX(adj_close) OVER w20_prev IS NOT NULL AND MAX(adj_close) OVER w20_prev > 0
                THEN adj_close / (MAX(adj_close) OVER w20_prev)
                ELSE NULL
            END AS breakout_proximity_20d_raw,
            CASE
                WHEN MAX(adj_close) OVER w60_prev IS NOT NULL AND MAX(adj_close) OVER w60_prev > 0
                THEN adj_close / (MAX(adj_close) OVER w60_prev)
                ELSE NULL
            END AS breakout_proximity_60d_raw,
            AVG(close_location_daily) OVER w20 AS close_location_value_20d_raw,
            AVG(upper_shadow_daily) OVER w20 AS upper_shadow_ratio_20d_raw,
            AVG(LN(GREATEST(amount, 0.0) + 1.0)) OVER w5
                - AVG(LN(GREATEST(amount, 0.0) + 1.0)) OVER w20 AS amount_shock_5_20_raw,
            CASE
                WHEN SUM(amount) OVER w20 > 0
                THEN SUM(up_amount_daily) OVER w20 / SUM(amount) OVER w20
                ELSE NULL
            END AS up_volume_share_20d_raw,
            AVG(gap_followthrough_daily) OVER w10 AS gap_followthrough_10d_raw,
            AVG(downside_tail_pressure_daily) OVER w20 AS downside_tail_pressure_20d_raw,
            CASE
                WHEN SUM(ABS(pct_ret)) OVER w20 > 0
                     AND LAG(adj_close, 20) OVER w IS NOT NULL
                     AND LAG(adj_close, 20) OVER w > 0
                THEN (adj_close / LAG(adj_close, 20) OVER w - 1.0) / (SUM(ABS(pct_ret)) OVER w20)
                ELSE NULL
            END AS path_efficiency_20d_raw
        FROM daily
        WINDOW
            w AS (PARTITION BY instrument ORDER BY signal_date),
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
            ),
            w60_prev AS (
                PARTITION BY instrument
                ORDER BY signal_date
                ROWS BETWEEN 60 PRECEDING AND 1 PRECEDING
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
            b.breakout_proximity_20d_raw,
            b.breakout_proximity_60d_raw,
            b.close_location_value_20d_raw,
            b.upper_shadow_ratio_20d_raw,
            b.amount_shock_5_20_raw,
            b.up_volume_share_20d_raw,
            CASE
                WHEN b.breakout_proximity_20d_raw IS NOT NULL AND b.amount_shock_5_20_raw IS NOT NULL
                THEN b.breakout_proximity_20d_raw * b.amount_shock_5_20_raw
                ELSE NULL
            END AS breakout_volume_confirmation_20d_raw,
            b.gap_followthrough_10d_raw,
            b.downside_tail_pressure_20d_raw,
            b.path_efficiency_20d_raw
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
        round_label="Round-4",
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
            "Round 4 produced at least one new clean positive keeper, which is enough new information "
            "to reopen family construction with a disciplined one-step composition test."
        ),
        zero_reason=(
            "Round 4 produced zero new clean positive keepers, so the next step should remain "
            "single-signal discovery rather than another family remix."
        ),
        summary_intro=(
            "This round evaluated ten candidate price-volume atomic signals under the frozen "
            "`price_volume_v18_refresh_hysteresis` operational contract."
        ),
        round_note_prefix="Round 4 batch completed under the frozen v18 operational contract.",
    )


if __name__ == "__main__":
    main()
