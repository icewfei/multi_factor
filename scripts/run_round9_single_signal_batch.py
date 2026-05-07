#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Run the full round-9 composability-first single-signal discovery batch
under the frozen v18 contract.
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
ROUND_ID = "rr_price_volume_single_signal_discovery_v18_round9_composability_first_20260428"
AS_OF_DATE = "20260428"
BASE_RUN_ID = "signaldiag_rr_price_volume_single_signal_discovery_v18_round4_20260423_base"
BASE_RUN_DIR = RUN_STATE_DIR / BASE_RUN_ID
ROUND_DIR = REGISTRY_DIR / "research_rounds" / ROUND_ID
CANDIDATE_REGISTRY_PATH = REGISTRY_DIR / "candidate_scheme_registry.jsonl"
ROUND_REGISTRY_PATH = REGISTRY_DIR / "research_round_registry.jsonl"
BUILD_DIAGNOSIS_SCRIPT = ROOT / "scripts" / "build_signal_edge_diagnosis.py"
SCORE_BUILDER_NAME = "run_round9_single_signal_batch.py"


CANDIDATES: list[CandidateSpec] = [
    CandidateSpec(
        "price_volume_single_signal_overnight_return_bias_20d_v1",
        "overnight_return_bias_20d_raw",
        "DESC",
        "persistent positive overnight return bias as an overnight-session drift mechanism distinct from intraday drift and close-to-close momentum",
    ),
    CandidateSpec(
        "price_volume_single_signal_gap_fill_rate_20d_v1",
        "gap_fill_rate_20d_raw",
        "DESC",
        "higher average gap-fill rate as a gap-handling quality mechanism distinct from pure gap frequency",
    ),
    CandidateSpec(
        "price_volume_single_signal_lower_shadow_support_20d_v1",
        "lower_shadow_support_20d_raw",
        "DESC",
        "stronger lower-shadow support as a downside-absorption microstructure mechanism distinct from generic recovery averages",
    ),
    CandidateSpec(
        "price_volume_single_signal_downside_semivol_ratio_20d_v1",
        "downside_semivol_ratio_20d_raw",
        "ASC",
        "lower downside semivol ratio as a tail-risk balance mechanism distinct from total volatility level",
    ),
    CandidateSpec(
        "price_volume_single_signal_post_downday_volume_recovery_20d_v1",
        "post_downday_volume_recovery_20d_raw",
        "DESC",
        "faster volume normalization after down days as a participation-recovery mechanism distinct from amount-shock level displacement",
    ),
    CandidateSpec(
        "price_volume_single_signal_intraday_range_efficiency_20d_v1",
        "intraday_range_efficiency_20d_raw",
        "DESC",
        "higher intraday range efficiency as a path-quality mechanism distinct from directional range share and simple close-location",
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
                LAG(adj_close, 1) OVER w AS prev_close,
                LAG(pct_ret, 1) OVER w AS prev_ret,
                LN(GREATEST(amount, 0.0) + 1.0) AS log_amount,
                CASE
                    WHEN LAG(adj_close, 1) OVER w > 0
                    THEN adj_open / LAG(adj_close, 1) OVER w - 1.0
                    ELSE NULL
                END AS overnight_ret,
                CASE
                    WHEN adj_open > 0
                    THEN (adj_close - adj_open) / adj_open
                    ELSE NULL
                END AS intraday_ret,
                CASE
                    WHEN adj_high > adj_low
                    THEN (LEAST(adj_open, adj_close) - adj_low) / GREATEST(adj_high - adj_low, 1e-12)
                    ELSE NULL
                END AS lower_shadow_support_daily,
                CASE
                    WHEN ABS(pct_ret) IS NOT NULL
                    THEN pct_ret * pct_ret
                    ELSE NULL
                END AS ret_sq,
                CASE
                    WHEN pct_ret < 0
                    THEN pct_ret * pct_ret
                    ELSE 0.0
                END AS downside_ret_sq,
                CASE
                    WHEN LAG(adj_close, 1) OVER w IS NOT NULL
                         AND adj_open <> LAG(adj_close, 1) OVER w
                    THEN 1.0 ELSE 0.0
                END AS gap_event,
                CASE
                    WHEN LAG(adj_close, 1) OVER w IS NOT NULL
                         AND adj_open > LAG(adj_close, 1) OVER w
                         AND adj_low <= LAG(adj_close, 1) OVER w
                    THEN 1.0
                    WHEN LAG(adj_close, 1) OVER w IS NOT NULL
                         AND adj_open < LAG(adj_close, 1) OVER w
                         AND adj_high >= LAG(adj_close, 1) OVER w
                    THEN 1.0
                    ELSE 0.0
                END AS gap_fill_event,
                CASE
                    WHEN LAG(pct_ret, 1) OVER w < 0
                    THEN -ABS(
                        LN(GREATEST(amount, 0.0) + 1.0)
                        - AVG(LN(GREATEST(amount, 0.0) + 1.0)) OVER w20_prev
                    )
                    ELSE NULL
                END AS post_downday_volume_recovery_daily,
                CASE
                    WHEN adj_high > adj_low
                    THEN ABS(adj_close - adj_open) / GREATEST(adj_high - adj_low, 1e-12)
                    ELSE NULL
                END AS intraday_range_efficiency_daily
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
            AVG(overnight_ret) OVER w20 AS overnight_return_bias_20d_raw,
            CASE
                WHEN SUM(gap_event) OVER w20 > 0
                THEN SUM(gap_fill_event) OVER w20 / SUM(gap_event) OVER w20
                ELSE NULL
            END AS gap_fill_rate_20d_raw,
            AVG(lower_shadow_support_daily) OVER w20 AS lower_shadow_support_20d_raw,
            CASE
                WHEN AVG(ret_sq) OVER w20 > 0
                THEN SQRT(AVG(downside_ret_sq) OVER w20 / AVG(ret_sq) OVER w20)
                ELSE NULL
            END AS downside_semivol_ratio_20d_raw,
            AVG(post_downday_volume_recovery_daily) OVER w20 AS post_downday_volume_recovery_20d_raw,
            AVG(intraday_range_efficiency_daily) OVER w20 AS intraday_range_efficiency_20d_raw
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
            b.overnight_return_bias_20d_raw,
            b.gap_fill_rate_20d_raw,
            b.lower_shadow_support_20d_raw,
            b.downside_semivol_ratio_20d_raw,
            b.post_downday_volume_recovery_20d_raw,
            b.intraday_range_efficiency_20d_raw
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
        round_label="Round-9",
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
            "Within the frozen v18 operational contract, does this mechanism-orthogonal atomic "
            "price-volume signal show positive and head-usable cross-sectional edge with better "
            "odds of passing the composability hard gate before any family promotion?"
        ),
        positive_reason=(
            "Round 9 produced at least one clean positive keeper, so the next step can include a "
            "controlled composability screening stage before any family-level promotion."
        ),
        zero_reason=(
            "Round 9 produced zero clean positive keepers, so we should continue orthogonal atomic "
            "discovery instead of reopening family construction."
        ),
        summary_intro=(
            "This round evaluated six mechanism-orthogonal atomic price-volume signals under the frozen "
            "`price_volume_v18_refresh_hysteresis` operational contract with a composability-first intent."
        ),
        round_note_prefix="Round 9 batch completed under the frozen v18 composability-first contract.",
    )


if __name__ == "__main__":
    main()
