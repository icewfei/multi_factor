#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Run round11b batch02 (serial-only whitelist batch) under the frozen v18 contract.
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
ROUND_ID = "rr_price_volume_single_signal_discovery_v18_round11b_batch02_20260428"
AS_OF_DATE = "20260428"
BASE_RUN_ID = "signaldiag_rr_price_volume_single_signal_discovery_v18_round4_20260423_base"
BASE_RUN_DIR = RUN_STATE_DIR / BASE_RUN_ID
ROUND_DIR = REGISTRY_DIR / "research_rounds" / ROUND_ID
CANDIDATE_REGISTRY_PATH = REGISTRY_DIR / "candidate_scheme_registry.jsonl"
ROUND_REGISTRY_PATH = REGISTRY_DIR / "research_round_registry.jsonl"
BUILD_DIAGNOSIS_SCRIPT = ROOT / "scripts" / "build_signal_edge_diagnosis.py"
SCORE_BUILDER_NAME = "run_round11b_batch02_single_signal_batch.py"


CANDIDATES: list[CandidateSpec] = [
    CandidateSpec("price_volume_single_signal_alpha158_full_001_v1", "alpha158_full_001_raw", "DESC", "short-minus-medium return drift"),
    CandidateSpec("price_volume_single_signal_alpha158_full_002_v1", "alpha158_full_002_raw", "ASC", "short-vs-medium volatility ratio"),
    CandidateSpec("price_volume_single_signal_alpha158_full_003_v1", "alpha158_full_003_raw", "DESC", "amount z-score"),
    CandidateSpec("price_volume_single_signal_alpha158_full_004_v1", "alpha158_full_004_raw", "DESC", "turnover z-score"),
    CandidateSpec("price_volume_single_signal_alpha158_full_005_v1", "alpha158_full_005_raw", "DESC", "close-to-rolling-high proximity"),
    CandidateSpec("price_volume_single_signal_alpha158_full_006_v1", "alpha158_full_006_raw", "DESC", "distance above rolling low"),
    CandidateSpec("price_volume_single_signal_alpha158_full_007_v1", "alpha158_full_007_raw", "DESC", "positive gap frequency"),
    CandidateSpec("price_volume_single_signal_alpha158_full_008_v1", "alpha158_full_008_raw", "ASC", "negative gap frequency"),
    CandidateSpec("price_volume_single_signal_alpha158_full_009_v1", "alpha158_full_009_raw", "DESC", "downside-gap intraday reversal intensity"),
    CandidateSpec("price_volume_single_signal_alpha158_full_010_v1", "alpha158_full_010_raw", "DESC", "signed amount flow autocorrelation"),
    CandidateSpec("price_volume_single_signal_alpha158_full_011_v1", "alpha158_full_011_raw", "ASC", "range-ratio volatility"),
    CandidateSpec("price_volume_single_signal_alpha158_full_012_v1", "alpha158_full_012_raw", "ASC", "upper-shadow volatility"),
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
        base AS (
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
                LAG(adj_close, 1) OVER w AS prev_close
            FROM bars
            WINDOW w AS (PARTITION BY instrument ORDER BY signal_date)
        ),
        enriched AS (
            SELECT
                *,
                CASE
                    WHEN prev_close > 0 THEN adj_open / prev_close - 1.0
                    ELSE NULL
                END AS gap_ret,
                CASE
                    WHEN adj_open > 0 THEN adj_close / adj_open - 1.0
                    ELSE NULL
                END AS intraday_ret,
                CASE
                    WHEN adj_close > 0 THEN (adj_high - adj_low) / adj_close
                    ELSE NULL
                END AS range_ratio_daily,
                CASE
                    WHEN adj_high > adj_low
                    THEN (adj_high - GREATEST(adj_open, adj_close)) / GREATEST(adj_high - adj_low, 1e-12)
                    ELSE NULL
                END AS upper_shadow_daily,
                CASE
                    WHEN pct_ret > 0 THEN amount
                    WHEN pct_ret < 0 THEN -amount
                    ELSE 0.0
                END AS signed_amount_daily
            FROM base
        ),
        with_lags AS (
            SELECT
                *,
                LAG(signed_amount_daily, 1) OVER (
                    PARTITION BY instrument
                    ORDER BY signal_date
                ) AS prev_signed_amount_daily
            FROM enriched
        )
        SELECT
            instrument,
            signal_date,
            AVG(pct_ret) OVER w5 - AVG(pct_ret) OVER w20 AS alpha158_full_001_raw,
            CASE
                WHEN STDDEV_SAMP(pct_ret) OVER w20 > 1e-12
                THEN STDDEV_SAMP(pct_ret) OVER w5 / STDDEV_SAMP(pct_ret) OVER w20
                ELSE NULL
            END AS alpha158_full_002_raw,
            CASE
                WHEN STDDEV_SAMP(log_amount) OVER w20 > 1e-12
                THEN (log_amount - AVG(log_amount) OVER w20) / STDDEV_SAMP(log_amount) OVER w20
                ELSE NULL
            END AS alpha158_full_003_raw,
            CASE
                WHEN STDDEV_SAMP(log_turnover) OVER w20 > 1e-12
                THEN (log_turnover - AVG(log_turnover) OVER w20) / STDDEV_SAMP(log_turnover) OVER w20
                ELSE NULL
            END AS alpha158_full_004_raw,
            CASE
                WHEN MAX(adj_close) OVER w20_prev > 1e-12
                THEN adj_close / MAX(adj_close) OVER w20_prev
                ELSE NULL
            END AS alpha158_full_005_raw,
            CASE
                WHEN MIN(adj_close) OVER w20_prev > 1e-12
                THEN adj_close / MIN(adj_close) OVER w20_prev
                ELSE NULL
            END AS alpha158_full_006_raw,
            AVG(CASE WHEN gap_ret > 0 THEN 1.0 ELSE 0.0 END) OVER w20 AS alpha158_full_007_raw,
            AVG(CASE WHEN gap_ret < 0 THEN 1.0 ELSE 0.0 END) OVER w20 AS alpha158_full_008_raw,
            AVG(
                CASE
                    WHEN gap_ret < 0 AND intraday_ret > 0
                    THEN intraday_ret
                    ELSE 0.0
                END
            ) OVER w20 AS alpha158_full_009_raw,
            CORR(signed_amount_daily, prev_signed_amount_daily) OVER w20 AS alpha158_full_010_raw,
            STDDEV_SAMP(range_ratio_daily) OVER w20 AS alpha158_full_011_raw,
            STDDEV_SAMP(upper_shadow_daily) OVER w20 AS alpha158_full_012_raw
        FROM with_lags
        WINDOW
            w5 AS (
                PARTITION BY instrument
                ORDER BY signal_date
                ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
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
            b.alpha158_full_001_raw,
            b.alpha158_full_002_raw,
            b.alpha158_full_003_raw,
            b.alpha158_full_004_raw,
            b.alpha158_full_005_raw,
            b.alpha158_full_006_raw,
            b.alpha158_full_007_raw,
            b.alpha158_full_008_raw,
            b.alpha158_full_009_raw,
            b.alpha158_full_010_raw,
            b.alpha158_full_011_raw,
            b.alpha158_full_012_raw
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
        round_label="Round-11b-Batch02",
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
            "Batch02 produced at least one clean positive keeper and can proceed to composability-screening intake after serial batch completion policy."
        ),
        zero_reason=(
            "Batch02 produced zero clean positive keepers; continue serial-only full158 discovery batches and do not reopen family construction."
        ),
        summary_intro=(
            "This batch is the second serial executable tranche inside round11b full158 governance under frozen "
            "`price_volume_v18_refresh_hysteresis` contract."
        ),
        round_note_prefix="Round11b batch02 serial run completed under whitelist-only governance.",
    )


if __name__ == "__main__":
    main()
