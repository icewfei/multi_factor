#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Run round11b batch04 (serial-only whitelist batch) under the frozen v18 contract.
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
ROUND_ID = "rr_price_volume_single_signal_discovery_v18_round11b_batch04_20260428"
AS_OF_DATE = "20260428"
BASE_RUN_ID = "signaldiag_rr_price_volume_single_signal_discovery_v18_round4_20260423_base"
BASE_RUN_DIR = RUN_STATE_DIR / BASE_RUN_ID
ROUND_DIR = REGISTRY_DIR / "research_rounds" / ROUND_ID
CANDIDATE_REGISTRY_PATH = REGISTRY_DIR / "candidate_scheme_registry.jsonl"
ROUND_REGISTRY_PATH = REGISTRY_DIR / "research_round_registry.jsonl"
BUILD_DIAGNOSIS_SCRIPT = ROOT / "scripts" / "build_signal_edge_diagnosis.py"
SCORE_BUILDER_NAME = "run_round11b_batch04_single_signal_batch.py"


CANDIDATES: list[CandidateSpec] = [
    CandidateSpec("price_volume_single_signal_alpha158_full_025_v1", "alpha158_full_025_raw", "ASC", "abs gap-return noise"),
    CandidateSpec("price_volume_single_signal_alpha158_full_026_v1", "alpha158_full_026_raw", "ASC", "abs intraday-return noise"),
    CandidateSpec("price_volume_single_signal_alpha158_full_027_v1", "alpha158_full_027_raw", "DESC", "return-turnover correlation"),
    CandidateSpec("price_volume_single_signal_alpha158_full_028_v1", "alpha158_full_028_raw", "DESC", "abs-return and amount correlation"),
    CandidateSpec("price_volume_single_signal_alpha158_full_029_v1", "alpha158_full_029_raw", "ASC", "turnover volatility"),
    CandidateSpec("price_volume_single_signal_alpha158_full_030_v1", "alpha158_full_030_raw", "DESC", "up-minus-down turnover spread"),
    CandidateSpec("price_volume_single_signal_alpha158_full_031_v1", "alpha158_full_031_raw", "DESC", "up-gap continuation frequency"),
    CandidateSpec("price_volume_single_signal_alpha158_full_032_v1", "alpha158_full_032_raw", "ASC", "down-gap continuation frequency"),
    CandidateSpec("price_volume_single_signal_alpha158_full_033_v1", "alpha158_full_033_raw", "DESC", "range-turnover correlation"),
    CandidateSpec("price_volume_single_signal_alpha158_full_034_v1", "alpha158_full_034_raw", "DESC", "close-location stability"),
    CandidateSpec("price_volume_single_signal_alpha158_full_035_v1", "alpha158_full_035_raw", "ASC", "shadow asymmetry amplitude"),
    CandidateSpec("price_volume_single_signal_alpha158_full_036_v1", "alpha158_full_036_raw", "DESC", "return-log-turnover correlation"),
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
                    THEN (adj_close - adj_low) / GREATEST(adj_high - adj_low, 1e-12)
                    ELSE NULL
                END AS close_loc_daily,
                CASE
                    WHEN adj_high > adj_low
                    THEN (adj_high - GREATEST(adj_open, adj_close)) / GREATEST(adj_high - adj_low, 1e-12)
                    ELSE NULL
                END AS upper_shadow_daily,
                CASE
                    WHEN adj_high > adj_low
                    THEN (LEAST(adj_open, adj_close) - adj_low) / GREATEST(adj_high - adj_low, 1e-12)
                    ELSE NULL
                END AS lower_shadow_daily
            FROM base
        )
        SELECT
            instrument,
            signal_date,
            AVG(ABS(gap_ret)) OVER w20 AS alpha158_full_025_raw,
            AVG(ABS(intraday_ret)) OVER w20 AS alpha158_full_026_raw,
            CORR(pct_ret, turnover_rate) OVER w20 AS alpha158_full_027_raw,
            CORR(ABS(pct_ret), log_amount) OVER w20 AS alpha158_full_028_raw,
            STDDEV_SAMP(turnover_rate) OVER w20 AS alpha158_full_029_raw,
            AVG(CASE WHEN pct_ret > 0 THEN turnover_rate ELSE 0.0 END) OVER w20
              - AVG(CASE WHEN pct_ret < 0 THEN turnover_rate ELSE 0.0 END) OVER w20 AS alpha158_full_030_raw,
            AVG(CASE WHEN gap_ret > 0 AND intraday_ret > 0 THEN 1.0 ELSE 0.0 END) OVER w20 AS alpha158_full_031_raw,
            AVG(CASE WHEN gap_ret < 0 AND intraday_ret < 0 THEN 1.0 ELSE 0.0 END) OVER w20 AS alpha158_full_032_raw,
            CORR(range_ratio_daily, turnover_rate) OVER w20 AS alpha158_full_033_raw,
            -STDDEV_SAMP(close_loc_daily) OVER w20 AS alpha158_full_034_raw,
            AVG(ABS(upper_shadow_daily - lower_shadow_daily)) OVER w20 AS alpha158_full_035_raw,
            CORR(pct_ret, log_turnover) OVER w20 AS alpha158_full_036_raw
        FROM enriched
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
            b.alpha158_full_025_raw,
            b.alpha158_full_026_raw,
            b.alpha158_full_027_raw,
            b.alpha158_full_028_raw,
            b.alpha158_full_029_raw,
            b.alpha158_full_030_raw,
            b.alpha158_full_031_raw,
            b.alpha158_full_032_raw,
            b.alpha158_full_033_raw,
            b.alpha158_full_034_raw,
            b.alpha158_full_035_raw,
            b.alpha158_full_036_raw
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
        round_label="Round-11b-Batch04",
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
            "Batch04 produced at least one clean positive keeper and can proceed to composability-screening intake after serial batch completion policy."
        ),
        zero_reason=(
            "Batch04 produced zero clean positive keepers; continue serial-only full158 discovery batches and do not reopen family construction."
        ),
        summary_intro=(
            "This batch is the fourth serial executable tranche inside round11b full158 governance under frozen "
            "`price_volume_v18_refresh_hysteresis` contract."
        ),
        round_note_prefix="Round11b batch04 serial run completed under whitelist-only governance.",
    )


if __name__ == "__main__":
    main()
