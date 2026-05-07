#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Run the remaining round-8 orthogonal single-signal discovery candidates and
finalize a full round summary (including the already-completed first candidate).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import duckdb

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from single_signal_batch_common import (  # noqa: E402
    CandidateSpec,
    classify_signal,
    ensure_base_inputs,
    ensure_symlink,
    read_json,
    run_round_preflight,
    sql_path,
    sql_quote,
    update_candidate_registry,
    update_round_registry,
    write_phase_summary,
)


ROOT = Path("/Users/wy/MiscProject/multi_factor")
CONTRACTS_DIR = ROOT / "contracts"
RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
REGISTRY_DIR = ROOT / "artifacts" / "research_registry"
ROUND_ID = "rr_price_volume_single_signal_discovery_v18_round8_orthogonal_20260428"
AS_OF_DATE = "20260428"
BASE_RUN_ID = "signaldiag_rr_price_volume_single_signal_discovery_v18_round4_20260423_base"
BASE_RUN_DIR = RUN_STATE_DIR / BASE_RUN_ID
ROUND_DIR = REGISTRY_DIR / "research_rounds" / ROUND_ID
CANDIDATE_REGISTRY_PATH = REGISTRY_DIR / "candidate_scheme_registry.jsonl"
ROUND_REGISTRY_PATH = REGISTRY_DIR / "research_round_registry.jsonl"
BUILD_DIAGNOSIS_SCRIPT = ROOT / "scripts" / "build_signal_edge_diagnosis.py"
SCORE_BUILDER_NAME = "run_round8_single_signal_batch.py"
PYTHON = "/opt/anaconda3/envs/quant_trade/bin/python"


ALL_CANDIDATES: list[CandidateSpec] = [
    CandidateSpec(
        "price_volume_single_signal_overnight_strength_share_20d_v1",
        "overnight_strength_share_20d_raw",
        "DESC",
        "a higher share of positive overnight contribution may capture an overnight-strength mechanism distinct from intraday trend bias and close-to-close momentum",
    ),
    CandidateSpec(
        "price_volume_single_signal_overnight_intraday_consistency_20d_v1",
        "overnight_intraday_consistency_20d_raw",
        "DESC",
        "more consistent agreement between overnight direction and same-day intraday direction may capture a session-continuity mechanism distinct from plain price-volume correlation",
    ),
    CandidateSpec(
        "price_volume_single_signal_downside_gap_fill_ratio_20d_v1",
        "downside_gap_fill_ratio_20d_raw",
        "DESC",
        "stronger filling of downside gaps may capture recovery quality after overnight weakness, distinct from generic downside absorption",
    ),
    CandidateSpec(
        "price_volume_single_signal_intraday_reversal_asymmetry_20d_v1",
        "intraday_reversal_asymmetry_20d_raw",
        "DESC",
        "stronger asymmetry in intraday recovery versus intraday fade may capture session-level resilience distinct from intraday trend bias",
    ),
    CandidateSpec(
        "price_volume_single_signal_signed_turnover_imbalance_20d_v1",
        "signed_turnover_imbalance_20d_raw",
        "DESC",
        "more turnover concentrated on positive-return days may capture participation imbalance distinct from signed amount imbalance",
    ),
    CandidateSpec(
        "price_volume_single_signal_amount_entropy_20d_v1",
        "amount_entropy_20d_raw",
        "DESC",
        "higher entropy of daily traded amount may capture diversified activity persistence rather than one-sided spike behavior",
    ),
    CandidateSpec(
        "price_volume_single_signal_range_expansion_followthrough_20d_v1",
        "range_expansion_followthrough_20d_raw",
        "DESC",
        "stronger followthrough after wide-range days may capture event-state continuation distinct from simple breakout proximity",
    ),
    CandidateSpec(
        "price_volume_single_signal_low_break_recovery_rate_20d_v1",
        "low_break_recovery_rate_20d_raw",
        "DESC",
        "faster recovery after low-break events may capture structural repair capacity distinct from downside gap or downside absorption measures",
    ),
    CandidateSpec(
        "price_volume_single_signal_high_open_hold_ratio_20d_v1",
        "high_open_hold_ratio_20d_raw",
        "DESC",
        "better ability to hold gains after opening high may capture gap-hold quality distinct from intraday trend bias",
    ),
    CandidateSpec(
        "price_volume_single_signal_overnight_gap_stability_20d_v1",
        "overnight_gap_stability_20d_raw",
        "DESC",
        "more stable overnight gap behavior may capture overnight fragility or order-flow balance distinct from downside gap frequency",
    ),
]

COMPLETED_IDS = {"price_volume_single_signal_overnight_intraday_consistency_20d_v1"}
REMAINING_CANDIDATES = [c for c in ALL_CANDIDATES if c.candidate_scheme_id not in COMPLETED_IDS]
ALL_BY_ID = {c.candidate_scheme_id: c for c in ALL_CANDIDATES}


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
                turnover_rate AS turnover
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
                COALESCE(turnover, 0.0) AS turnover,
                LAG(adj_close, 1) OVER w AS prev_close,
                CASE
                    WHEN LAG(adj_close, 1) OVER w > 0
                    THEN adj_open / LAG(adj_close, 1) OVER w - 1.0
                    ELSE NULL
                END AS overnight_ret,
                CASE
                    WHEN adj_open > 0 THEN adj_close / adj_open - 1.0
                    ELSE NULL
                END AS intraday_ret,
                CASE
                    WHEN adj_close > 0 THEN (adj_high - adj_low) / adj_close
                    ELSE NULL
                END AS range_ratio,
                LN(GREATEST(amount, 0.0) + 1.0) AS log_amount,
                CASE
                    WHEN MAX(adj_high) OVER w20_prev IS NOT NULL
                     AND adj_high >= MAX(adj_high) OVER w20_prev
                    THEN 1.0 ELSE 0.0
                END AS high_break_event,
                CASE
                    WHEN MIN(adj_low) OVER w20_prev IS NOT NULL
                     AND adj_low <= MIN(adj_low) OVER w20_prev
                    THEN 1.0 ELSE 0.0
                END AS low_break_event
            FROM bars
            WINDOW
                w AS (PARTITION BY instrument ORDER BY signal_date),
                w20_prev AS (
                    PARTITION BY instrument
                    ORDER BY signal_date
                    ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING
                )
        ),
        enriched AS (
            SELECT
                instrument,
                signal_date,
                overnight_ret,
                intraday_ret,
                range_ratio,
                log_amount,
                turnover,
                prev_close,
                adj_open,
                adj_high,
                adj_low,
                adj_close,
                high_break_event,
                low_break_event,
                AVG(range_ratio) OVER w20 AS range_ma20,
                SUM(GREATEST(overnight_ret, 0.0)) OVER w20 AS overnight_pos_sum20,
                SUM(ABS(overnight_ret)) OVER w20 AS overnight_abs_sum20,
                AVG(
                    CASE
                        WHEN prev_close > 0 AND adj_open < prev_close AND (prev_close - adj_open) > 0
                        THEN (adj_close - adj_open) / (prev_close - adj_open)
                        ELSE NULL
                    END
                ) OVER w20 AS downside_gap_fill_ratio_20d_raw,
                AVG(
                    CASE
                        WHEN adj_high > adj_low AND intraday_ret < 0
                        THEN (adj_close - adj_low) / (adj_high - adj_low)
                        ELSE NULL
                    END
                ) OVER w20 AS down_recovery_part,
                AVG(
                    CASE
                        WHEN adj_high > adj_low AND intraday_ret > 0
                        THEN (adj_high - adj_close) / (adj_high - adj_low)
                        ELSE NULL
                    END
                ) OVER w20 AS up_fade_part,
                SUM(SIGN(COALESCE(intraday_ret, 0.0)) * turnover) OVER w20 AS signed_turnover_sum20,
                SUM(ABS(turnover)) OVER w20 AS turnover_abs_sum20,
                SUM(amount) OVER w20 AS amount_sum20,
                SUM(amount * amount) OVER w20 AS amount_sq_sum20,
                AVG(
                    CASE
                        WHEN low_break_event > 0.5 AND adj_high > adj_low
                        THEN (adj_close - adj_low) / (adj_high - adj_low)
                        ELSE NULL
                    END
                ) OVER w20 AS low_break_recovery_rate_20d_raw,
                AVG(
                    CASE
                        WHEN prev_close > 0 AND adj_open > prev_close AND (adj_open - prev_close) > 0
                        THEN (adj_close - prev_close) / (adj_open - prev_close)
                        ELSE NULL
                    END
                ) OVER w20 AS high_open_hold_ratio_20d_raw,
                STDDEV_SAMP(overnight_ret) OVER w20 AS overnight_gap_std20
            FROM daily
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
                WHEN overnight_abs_sum20 > 0 THEN overnight_pos_sum20 / overnight_abs_sum20
                ELSE NULL
            END AS overnight_strength_share_20d_raw,
            AVG(
                CASE
                    WHEN overnight_ret IS NOT NULL AND intraday_ret IS NOT NULL
                    THEN overnight_ret * intraday_ret
                    ELSE NULL
                END
            ) OVER (
                PARTITION BY instrument
                ORDER BY signal_date
                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
            ) AS overnight_intraday_consistency_20d_raw,
            downside_gap_fill_ratio_20d_raw,
            (down_recovery_part - up_fade_part) AS intraday_reversal_asymmetry_20d_raw,
            CASE
                WHEN turnover_abs_sum20 > 0 THEN signed_turnover_sum20 / turnover_abs_sum20
                ELSE NULL
            END AS signed_turnover_imbalance_20d_raw,
            CASE
                WHEN amount_sum20 > 0 AND amount_sq_sum20 > 0
                THEN -LN(amount_sq_sum20 / (amount_sum20 * amount_sum20))
                ELSE NULL
            END AS amount_entropy_20d_raw,
            AVG(
                (COALESCE(range_ratio, 0.0) - COALESCE(range_ma20, 0.0)) * COALESCE(intraday_ret, 0.0)
            ) OVER (
                PARTITION BY instrument
                ORDER BY signal_date
                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
            ) AS range_expansion_followthrough_20d_raw,
            low_break_recovery_rate_20d_raw,
            high_open_hold_ratio_20d_raw,
            CASE
                WHEN overnight_gap_std20 IS NOT NULL
                THEN -overnight_gap_std20
                ELSE NULL
            END AS overnight_gap_stability_20d_raw
        FROM enriched
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
            b.overnight_strength_share_20d_raw,
            b.overnight_intraday_consistency_20d_raw,
            b.downside_gap_fill_ratio_20d_raw,
            b.intraday_reversal_asymmetry_20d_raw,
            b.signed_turnover_imbalance_20d_raw,
            b.amount_entropy_20d_raw,
            b.range_expansion_followthrough_20d_raw,
            b.low_break_recovery_rate_20d_raw,
            b.high_open_hold_ratio_20d_raw,
            b.overnight_gap_stability_20d_raw
        FROM project_sample_panel p
        LEFT JOIN bar_features b
          ON p.instrument = b.instrument
         AND p.signal_date = b.signal_date
        """
    )


def materialize_single_signal(
    con: duckdb.DuckDBPyConnection, spec: CandidateSpec, run_dir: Path
) -> None:
    from single_signal_batch_common import materialize_ranked_single_signal

    materialize_ranked_single_signal(
        con=con,
        spec=spec,
        run_dir=run_dir,
        score_builder_name=SCORE_BUILDER_NAME,
    )


def row_from_diag(spec: CandidateSpec, payload: dict, classification: str) -> dict:
    return {
        "candidate_scheme_id": spec.candidate_scheme_id,
        "field_name": spec.field_name,
        "ranking_direction": spec.ranking_direction,
        "classification": classification,
        "full_sample_corr_ic": payload["ic_readout"]["full_sample_corr_ic"],
        "avg_daily_ic": payload["ic_readout"]["avg_daily_ic"],
        "positive_daily_ic_share": payload["ic_readout"]["positive_daily_ic_share"],
        "avg_label_top10": payload["top_slice_readout"]["avg_label_top10"],
        "avg_label_rank11_20": payload["top_slice_readout"]["avg_label_rank11_20"],
        "avg_label_bottom10": payload["top_slice_readout"]["avg_label_bottom10"],
        "notes": (
            f"Round-8 atomic signal candidate built from {spec.field_name} under the frozen "
            f"price_volume_v18_refresh_hysteresis operational contract. "
            f"Signal-edge diagnosis classified this candidate as {classification}."
        ),
    }


def main() -> None:
    run_round_preflight(ROUND_ID)
    sample_panel, label_panel = ensure_base_inputs(BASE_RUN_DIR, "Round-8")
    ROUND_DIR.mkdir(parents=True, exist_ok=True)

    run_input = read_json(CONTRACTS_DIR / "run_input_contract.current.json")
    snapshot_id = run_input["snapshot_id"]
    source_db_path = Path(run_input["source_root"]["snapshot_path"]) / "duckdb" / "warehouse.duckdb"
    if not source_db_path.exists():
        raise FileNotFoundError(f"Shared warehouse DB not found: {source_db_path}")

    con = duckdb.connect()
    try:
        build_feature_views(con, sample_panel, source_db_path, snapshot_id)
        for spec in REMAINING_CANDIDATES:
            run_id = f"signaldiag_{spec.candidate_scheme_id}_{AS_OF_DATE}"
            run_dir = RUN_STATE_DIR / run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            ensure_symlink(sample_panel, run_dir / "project_sample_panel.parquet")
            ensure_symlink(label_panel, run_dir / "project_label_panel.parquet")
            materialize_single_signal(con, spec, run_dir)

            subprocess.run(
                [
                    PYTHON,
                    str(BUILD_DIAGNOSIS_SCRIPT),
                    "--run-id",
                    run_id,
                    "--candidate-scheme-id",
                    spec.candidate_scheme_id,
                    "--research-round-id",
                    ROUND_ID,
                    "--title",
                    spec.candidate_scheme_id,
                    "--as-of-date",
                    AS_OF_DATE,
                    "--input-dir",
                    str(run_dir),
                ],
                check=True,
            )
    finally:
        con.close()

    result_rows: list[dict] = []
    for spec in ALL_CANDIDATES:
        diag_json = ROUND_DIR / f"{spec.candidate_scheme_id}_signal_edge_diagnosis_{AS_OF_DATE}.json"
        if not diag_json.exists():
            raise FileNotFoundError(f"Missing diagnosis json for {spec.candidate_scheme_id}: {diag_json}")
        payload = read_json(diag_json)
        classification = classify_signal(payload)
        result_rows.append(row_from_diag(spec, payload, classification))

    positive = [row for row in result_rows if row["classification"] == "signal_edge_positive"]
    decision = {
        "continue_pool_expansion": len(positive) == 0,
        "reopen_family_construction": len(positive) > 0,
        "reason": (
            "Round 8 produced at least one genuinely orthogonal clean positive keeper, which is enough new information to justify a later composability screen under the frozen v18 baseline."
            if positive
            else "Round 8 produced zero genuinely orthogonal clean positive keepers, so the next step should remain atomic discovery or pause rather than reopening family construction."
        ),
    }

    update_candidate_registry(
        candidate_registry_path=CANDIDATE_REGISTRY_PATH,
        result_rows=result_rows,
        research_round_id=ROUND_ID,
        score_builder_name=SCORE_BUILDER_NAME,
        baseline_reference_candidate_scheme_id="price_volume_v18_refresh_hysteresis",
        status_question=(
            "Within the frozen v18 operational contract, does this orthogonal overnight/gap/recovery atomic "
            "signal show genuinely positive and head-usable cross-sectional edge without colliding with "
            "existing canonical clusters or relying on family-level composition?"
        ),
    )
    update_round_registry(
        round_registry_path=ROUND_REGISTRY_PATH,
        research_round_id=ROUND_ID,
        candidate_ids=[row["candidate_scheme_id"] for row in result_rows],
        decision=decision,
        round_note_prefix="Round 8 batch completed under the frozen v18 operational contract.",
    )
    write_phase_summary(
        round_dir=ROUND_DIR,
        research_round_id=ROUND_ID,
        as_of_date=AS_OF_DATE,
        baseline_reference_candidate_scheme_id="price_volume_v18_refresh_hysteresis",
        results=result_rows,
        decision=decision,
        summary_intro=(
            "This round evaluated ten more orthogonal atomic price-volume signals under the frozen "
            "`price_volume_v18_refresh_hysteresis` operational contract after both round7 keepers "
            "returned mixed composability screens against the v18 core family."
        ),
    )


if __name__ == "__main__":
    main()
