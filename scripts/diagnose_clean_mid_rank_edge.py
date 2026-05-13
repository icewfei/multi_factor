#!/usr/bin/env python3
"""
Diagnose whether clean score edge lives mainly in mid-rank bands rather than TopK.

This is train/validation diagnosis only. It does not tune bands, create
candidates, train models, run portfolio/backtest, generate holdings/readouts,
or read frozen test data.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


ROOT = Path("/Users/wy/MiscProject/multi_factor")
DEFAULT_LABEL_PANEL = ROOT / "artifacts" / "run_state" / "project_panels_research_trainval_20211231_20260429" / "project_label_panel.parquet"
DEFAULT_SPLIT_PANEL = ROOT / "artifacts" / "run_state" / "project_panels_research_trainval_20211231_20260429" / "dataset_split_daily.parquet"
DEFAULT_NO_P98_SCORES = Path("/private/tmp/clean_baseline_family_score_gate_20260513/no_p98_reversal_baseline_v1/model_scores_D0.parquet")
DEFAULT_LIQUIDITY_SCORES = Path("/private/tmp/clean_baseline_redesign_round_v1/scores/clean_reversal_5d_liquidity_quality_v1/model_scores_D0.parquet")
DEFAULT_COMPOSITE_SCORES = Path("/private/tmp/clean_baseline_redesign_round_v1/scores/clean_composite_reversal_tradability_v1/model_scores_D0.parquet")
DEFAULT_LIMIT_AWARE_SCORES = Path("/private/tmp/clean_baseline_redesign_round_v1/scores/clean_reversal_5d_limit_aware_v1/model_scores_D0.parquet")
DEFAULT_BOARD_NEUTRAL_SCORES = Path("/private/tmp/clean_baseline_redesign_round_v1/scores/clean_reversal_5d_board_neutral_v1/model_scores_D0.parquet")
DEFAULT_TRADABILITY_FILTERED_SCORES = Path("/private/tmp/clean_baseline_redesign_round_v1/scores/clean_reversal_5d_tradability_filtered_v1/model_scores_D0.parquet")
DEFAULT_LISTING_AGE_SCORES = Path("/private/tmp/clean_baseline_redesign_round_v1/scores/clean_reversal_5d_listing_age_calendar_v1/model_scores_D0.parquet")
DEFAULT_P98_SCORES = ROOT / "artifacts" / "run_state" / "confirmatory_reversal_p98_trainval_20260506" / "model_scores_D0.parquet"
DEFAULT_MULTI_EQUAL_SCORES = ROOT / "artifacts" / "run_state" / "exploratory_multi_signal_composite_v1" / "model_scores_D0_multi.parquet"
DEFAULT_EXPOSURE_PANEL = DEFAULT_LIQUIDITY_SCORES
DEFAULT_OUTPUT_JSON = Path("/private/tmp/clean_mid_rank_edge_diagnosis.json")
DEFAULT_OUTPUT_MD = Path("/private/tmp/clean_mid_rank_edge_diagnosis.md")

NO_P98 = "no_p98_reversal_baseline_v1"
LIQ = "clean_reversal_5d_liquidity_quality_v1"
COMP = "clean_composite_reversal_tradability_v1"
LIMIT = "clean_reversal_5d_limit_aware_v1"
BOARD = "clean_reversal_5d_board_neutral_v1"
TRAD = "clean_reversal_5d_tradability_filtered_v1"
LISTING = "clean_reversal_5d_listing_age_calendar_v1"
P98 = "p98_conditional_reference"
MULTI = "multi_equal_weight_v1_conditional_reference"

CLEAN_MODEL_KEYS = [NO_P98, LIQ, COMP, LIMIT, BOARD, TRAD, LISTING]
BLOCKED_FIELDS = {"listing_age_trading_days", "newly_listed_flag"}
USED_EXPOSURE_FIELDS = [
    "snapshot_id",
    "instrument",
    "signal_date",
    "amount",
    "entry_buyable",
    "is_suspended",
    "no_trade_flag",
    "volume_zero_flag",
    "amount_zero_flag",
    "is_limit_up",
    "is_limit_down",
    "open_at_up_limit",
    "close_at_down_limit",
    "listing_age_days",
    "board_type",
    "exchange",
]

RANK_BANDS: dict[str, tuple[int, int]] = {
    "topk": (1, 30),
    "nextk": (31, 60),
    "mid_head": (31, 100),
    "broad_head": (31, 200),
    "middle": (101, 300),
}

_ACTIVE_BANDS: dict[str, tuple[int, int]] = dict(RANK_BANDS)


class DiagnosisError(Exception):
    """Raised when diagnosis cannot be completed safely."""


@dataclass(frozen=True)
class ModelSpec:
    key: str
    candidate_scheme_id: str
    score_path: Path
    effective_direction: int
    status: str
    label: str
    join_on_snapshot: bool = True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose clean mid-rank edge.")
    parser.add_argument("--label-panel", type=Path, default=DEFAULT_LABEL_PANEL)
    parser.add_argument("--split-panel", type=Path, default=DEFAULT_SPLIT_PANEL)
    parser.add_argument("--no-p98-scores", type=Path, default=DEFAULT_NO_P98_SCORES)
    parser.add_argument("--liquidity-scores", type=Path, default=DEFAULT_LIQUIDITY_SCORES)
    parser.add_argument("--composite-scores", type=Path, default=DEFAULT_COMPOSITE_SCORES)
    parser.add_argument("--limit-aware-scores", type=Path, default=DEFAULT_LIMIT_AWARE_SCORES)
    parser.add_argument("--board-neutral-scores", type=Path, default=DEFAULT_BOARD_NEUTRAL_SCORES)
    parser.add_argument("--tradability-filtered-scores", type=Path, default=DEFAULT_TRADABILITY_FILTERED_SCORES)
    parser.add_argument("--listing-age-scores", type=Path, default=DEFAULT_LISTING_AGE_SCORES)
    parser.add_argument("--p98-scores", type=Path, default=DEFAULT_P98_SCORES)
    parser.add_argument("--multi-equal-scores", type=Path, default=DEFAULT_MULTI_EQUAL_SCORES)
    parser.add_argument("--exposure-panel", type=Path, default=DEFAULT_EXPOSURE_PANEL)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--band-override-json", type=str, default=None, help="JSON map of band_name->[start, end] to override RANK_BANDS")
    return parser.parse_args()


def sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def ensure_exists(path: Path, label: str) -> None:
    if not path.exists():
        raise DiagnosisError(f"{label} not found: {path}")
    lowered = path.as_posix().lower()
    if "frozen_test" in lowered or "fixed_test" in lowered:
        raise DiagnosisError(f"{label} path looks like frozen/fixed test access: {path}")


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(result) else result


def summarize_series(series: pd.Series) -> dict[str, Any]:
    clean = series.dropna()
    if clean.empty:
        return {
            "count": 0,
            "mean": None,
            "std": None,
            "median": None,
            "min": None,
            "p05": None,
            "p25": None,
            "p75": None,
            "p95": None,
            "max": None,
            "positive_ratio": None,
        }
    return {
        "count": int(len(clean)),
        "mean": safe_float(clean.mean()),
        "std": safe_float(clean.std()),
        "median": safe_float(clean.median()),
        "min": safe_float(clean.min()),
        "p05": safe_float(clean.quantile(0.05)),
        "p25": safe_float(clean.quantile(0.25)),
        "p75": safe_float(clean.quantile(0.75)),
        "p95": safe_float(clean.quantile(0.95)),
        "max": safe_float(clean.max()),
        "positive_ratio": safe_float((clean > 0).mean()),
    }


def build_specs(args: argparse.Namespace) -> dict[str, ModelSpec]:
    return {
        NO_P98: ModelSpec(NO_P98, NO_P98, args.no_p98_scores, -1, "clean_anchor", "no-p98 clean reversal"),
        LIQ: ModelSpec(LIQ, LIQ, args.liquidity_scores, -1, "clean_candidate", "liquidity-quality clean reversal"),
        COMP: ModelSpec(COMP, COMP, args.composite_scores, -1, "rejected_clean_candidate", "rejected clean composite"),
        LIMIT: ModelSpec(LIMIT, LIMIT, args.limit_aware_scores, -1, "clean_candidate", "limit-aware clean reversal"),
        BOARD: ModelSpec(BOARD, BOARD, args.board_neutral_scores, -1, "clean_candidate", "board-neutral clean reversal"),
        TRAD: ModelSpec(TRAD, TRAD, args.tradability_filtered_scores, -1, "clean_candidate", "tradability-filtered clean reversal"),
        LISTING: ModelSpec(LISTING, LISTING, args.listing_age_scores, -1, "clean_candidate", "listing-age-calendar clean reversal"),
        P98: ModelSpec(P98, "reversal_tail_exclude_p98_v1", args.p98_scores, 1, "conditional_reference_only", "p98 conditional baseline"),
        MULTI: ModelSpec(MULTI, "multi_equal_weight_v1", args.multi_equal_scores, 1, "conditional_reference_only", "multi_equal_weight_v1 conditional reference", join_on_snapshot=False),
    }


def validate_columns(con: duckdb.DuckDBPyConnection, path: Path, required: set[str], label: str) -> list[str]:
    columns = [row[0] for row in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{sql_path(path)}')").fetchall()]
    missing = sorted(required - set(columns))
    if missing:
        raise DiagnosisError(f"{label} missing required columns: {missing}")
    return columns


def register_views(con: duckdb.DuckDBPyConnection, args: argparse.Namespace, specs: dict[str, ModelSpec]) -> None:
    validate_columns(con, args.label_panel, {"snapshot_id", "instrument", "signal_date", "label_defined", "label_5d_next_open_close"}, "label panel")
    validate_columns(con, args.split_panel, {"snapshot_id", "instrument", "signal_date", "train_flag", "validation_flag"}, "split panel")
    exposure_columns = validate_columns(con, args.exposure_panel, {"snapshot_id", "instrument", "signal_date"}, "exposure panel")
    if BLOCKED_FIELDS & set(USED_EXPOSURE_FIELDS):
        raise DiagnosisError("blocked fields requested")
    con.execute(
        f"""
        CREATE OR REPLACE TEMP VIEW label_t AS
        SELECT
            CAST(snapshot_id AS VARCHAR) AS snapshot_id,
            instrument,
            REPLACE(CAST(signal_date AS VARCHAR), '-', '') AS signal_date,
            label_5d_next_open_close AS forward_return_5d
        FROM read_parquet('{sql_path(args.label_panel)}')
        WHERE label_defined
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TEMP VIEW split_t AS
        SELECT
            CAST(snapshot_id AS VARCHAR) AS snapshot_id,
            instrument,
            REPLACE(CAST(signal_date AS VARCHAR), '-', '') AS signal_date,
            train_flag,
            validation_flag
        FROM read_parquet('{sql_path(args.split_panel)}')
        WHERE train_flag OR validation_flag
        """
    )
    select_cols = []
    for field in USED_EXPOSURE_FIELDS:
        if field in exposure_columns:
            if field == "snapshot_id":
                select_cols.append("CAST(snapshot_id AS VARCHAR) AS snapshot_id")
            elif field == "signal_date":
                select_cols.append("REPLACE(CAST(signal_date AS VARCHAR), '-', '') AS signal_date")
            else:
                select_cols.append(field)
        elif field not in {"snapshot_id", "instrument", "signal_date"}:
            select_cols.append(f"NULL AS {field}")
    con.execute(
        f"""
        CREATE OR REPLACE TEMP VIEW exposure_t AS
        WITH base AS (
            SELECT {", ".join(select_cols)}
            FROM read_parquet('{sql_path(args.exposure_panel)}')
        )
        SELECT
            *,
            CASE
                WHEN amount IS NOT NULL THEN PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY amount ASC NULLS FIRST, instrument ASC
                )
            END AS amount_percentile_asc
        FROM base
        """
    )
    for spec in specs.values():
        validate_columns(con, spec.score_path, {"snapshot_id", "instrument", "signal_date", "candidate_scheme_id", "model_score_D0"}, f"{spec.key} scores")
        con.execute(
            f"""
            CREATE OR REPLACE TEMP VIEW {spec.key}_score_t AS
            SELECT
                CAST(snapshot_id AS VARCHAR) AS snapshot_id,
                instrument,
                REPLACE(CAST(signal_date AS VARCHAR), '-', '') AS signal_date,
                model_score_D0 AS raw_score,
                {spec.effective_direction} * model_score_D0 AS effective_score
            FROM read_parquet('{sql_path(spec.score_path)}')
            WHERE candidate_scheme_id = '{spec.candidate_scheme_id}'
            """
        )


def fetch_model_frame(con: duckdb.DuckDBPyConnection, spec: ModelSpec) -> pd.DataFrame:
    join = (
        "l.snapshot_id = m.snapshot_id AND l.instrument = m.instrument AND l.signal_date = m.signal_date"
        if spec.join_on_snapshot
        else "l.instrument = m.instrument AND l.signal_date = m.signal_date"
    )
    return con.execute(
        f"""
        SELECT
            l.snapshot_id,
            l.instrument,
            l.signal_date,
            l.forward_return_5d,
            s.train_flag,
            s.validation_flag,
            m.raw_score,
            m.effective_score,
            e.amount,
            e.amount_percentile_asc,
            e.entry_buyable,
            e.is_suspended,
            e.no_trade_flag,
            e.volume_zero_flag,
            e.amount_zero_flag,
            e.is_limit_up,
            e.is_limit_down,
            e.open_at_up_limit,
            e.close_at_down_limit,
            e.listing_age_days,
            e.board_type,
            e.exchange
        FROM label_t l
        INNER JOIN split_t s
          ON l.snapshot_id = s.snapshot_id
         AND l.instrument = s.instrument
         AND l.signal_date = s.signal_date
        LEFT JOIN {spec.key}_score_t m
          ON {join}
        LEFT JOIN exposure_t e
          ON l.snapshot_id = e.snapshot_id
         AND l.instrument = e.instrument
         AND l.signal_date = e.signal_date
        """
    ).df()


def assign_amount_bucket(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    pct = work["amount_percentile_asc"] if "amount_percentile_asc" in work else None
    if pct is not None and not pct.dropna().empty:
        work["amount_bucket"] = pd.cut(
            pct,
            bins=[0.0, 0.2, 0.5, 0.8, 1.0],
            labels=["bottom_20pct", "20_50pct", "50_80pct", "top_20pct"],
            include_lowest=True,
        ).astype("object")
    return work


def rank_band_structures(scored: pd.DataFrame, split: str, model_key: str) -> tuple[dict[str, dict[str, Any]], pd.DataFrame, pd.DataFrame]:
    daily_rows: list[dict[str, Any]] = []
    member_rows: list[pd.DataFrame] = []
    scored = assign_amount_bucket(scored)
    for signal_date, day in scored.groupby("signal_date", sort=True):
        ordered = day.sort_values(["effective_score", "instrument"], ascending=[False, True]).reset_index(drop=True)
        min_needed = max(v[1] for v in _ACTIVE_BANDS.values())
        if len(ordered) < min_needed:
            continue
        day_data: dict[str, Any] = {"signal_date": str(signal_date)}
        for band_name, (start, end) in _ACTIVE_BANDS.items():
            band = ordered.iloc[start - 1 : end].copy()
            band = band.assign(
                model_key=model_key,
                split=split,
                rank_band=band_name,
            )
            member_rows.append(band)
            day_data[f"{band_name}_mean"] = safe_float(band["forward_return_5d"].mean())
            day_data[f"{band_name}_median"] = safe_float(band["forward_return_5d"].median())
        for band_name in _ACTIVE_BANDS:
            topk_mean = day_data.get("topk_mean")
            band_mean = day_data.get(f"{band_name}_mean")
            day_data[f"{band_name}_win_topk"] = (band_mean > topk_mean) if (band_mean is not None and topk_mean is not None) else None
            day_data[f"{band_name}_minus_topk"] = band_mean - topk_mean if (band_mean is not None and topk_mean is not None) else None
        daily_rows.append(day_data)
    daily = pd.DataFrame(daily_rows)
    members = pd.concat(member_rows, ignore_index=True) if member_rows else pd.DataFrame()
    if daily.empty:
        return {}, daily, members
    band_summaries: dict[str, dict[str, Any]] = {}
    for band_name, (start, end) in _ACTIVE_BANDS.items():
        mean_col = f"{band_name}_mean"
        median_col = f"{band_name}_median"
        win_col = f"{band_name}_win_topk"
        minus_col = f"{band_name}_minus_topk"
        band_summaries[band_name] = {
            "rank_start": start,
            "rank_end": end,
            "mean_return": safe_float(daily[mean_col].mean()),
            "median_return": safe_float(daily[median_col].mean()),
            "daily_win_rate_vs_topk": safe_float(pd.Series(daily[win_col]).dropna().astype(bool).mean()),
            "mean_minus_topk": safe_float(daily[minus_col].mean()),
            "n_days": int(len(daily)),
        }
    return band_summaries, daily, members


def exposure_payload(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {"status": "empty"}
    return {
        "amount_bucket": summarize_bucket(frame, "amount_bucket"),
        "board_type": summarize_bucket(frame, "board_type"),
        "exchange": summarize_bucket(frame, "exchange"),
        "entry_buyable": summarize_bool(frame, "entry_buyable"),
        "no_trade_flag": summarize_bool(frame, "no_trade_flag"),
        "is_suspended": summarize_bool(frame, "is_suspended"),
        "is_limit_up": summarize_bool(frame, "is_limit_up"),
        "is_limit_down": summarize_bool(frame, "is_limit_down"),
        "open_at_up_limit": summarize_bool(frame, "open_at_up_limit"),
        "close_at_down_limit": summarize_bool(frame, "close_at_down_limit"),
        "mean_return": safe_float(frame["forward_return_5d"].mean()),
    }


def summarize_bucket(frame: pd.DataFrame, column: str) -> dict[str, Any]:
    if column not in frame or frame[column].dropna().empty:
        return {"status": "unavailable"}
    counts = frame[column].fillna("missing").astype(str).value_counts()
    total = counts.sum()
    return {
        "status": "available",
        "rows": int(total),
        "distribution": [{"value": str(value), "count": int(count), "share": safe_float(count / total) if total else None} for value, count in counts.items()],
    }


def summarize_bool(frame: pd.DataFrame, column: str) -> dict[str, Any]:
    if column not in frame or frame[column].dropna().empty:
        return {"status": "unavailable"}
    values = frame[column].fillna(False).astype(bool)
    return {"status": "available", "true_count": int(values.sum()), "true_share": safe_float(values.mean()), "rows": int(len(values))}


def winner_loser_contribution(frame: pd.DataFrame) -> dict[str, Any]:
    returns = frame["forward_return_5d"] if not frame.empty else pd.Series(dtype=float)
    positive = returns[returns > 0].sort_values(ascending=False)
    negative = returns[returns < 0].sort_values(ascending=True)
    top_n = max(1, math.ceil(len(positive) * 0.05)) if len(positive) else 0
    worst_n = max(1, math.ceil(len(negative) * 0.05)) if len(negative) else 0
    return {
        "top_5pct_winners_contribution": safe_float(positive.head(top_n).sum() / positive.sum()) if top_n and positive.sum() != 0 else None,
        "worst_5pct_losers_contribution": safe_float(abs(negative.head(worst_n).sum()) / abs(negative.sum())) if worst_n and negative.sum() != 0 else None,
        "mean": safe_float(returns.mean()) if not returns.empty else None,
        "median": safe_float(returns.median()) if not returns.empty else None,
    }


def yearly_band_direction(daily: pd.DataFrame) -> dict[str, Any]:
    if daily.empty:
        return {}
    work = daily.copy()
    work["year"] = work["signal_date"].astype(str).str[:4]
    by_year: dict[str, Any] = {}
    for year, group in work.groupby("year", sort=True):
        year_data: dict[str, Any] = {}
        for band_name in _ACTIVE_BANDS:
            minus_col = f"{band_name}_minus_topk"
            if minus_col in group:
                year_data[f"{band_name}_minus_topk_mean"] = safe_float(group[minus_col].mean())
                win_col = f"{band_name}_win_topk"
                if win_col in group:
                    year_data[f"{band_name}_win_rate_vs_topk"] = safe_float(pd.Series(group[win_col]).dropna().astype(bool).mean())
        by_year[str(year)] = year_data
    return by_year


def diagnose_model_split(frame: pd.DataFrame, split: str, model_key: str) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    scored = frame.dropna(subset=["effective_score", "forward_return_5d"]).copy()
    if scored.empty:
        return {}, pd.DataFrame(), pd.DataFrame()
    band_structure, daily, members = rank_band_structures(scored, split, model_key)
    band_exposures: dict[str, Any] = {}
    band_tails: dict[str, Any] = {}
    for band_name in _ACTIVE_BANDS:
        band_frame = members[members["rank_band"] == band_name] if not members.empty else pd.DataFrame()
        band_exposures[band_name] = exposure_payload(band_frame)
        band_tails[band_name] = winner_loser_contribution(band_frame)
    return {
        "rank_band_structure": band_structure,
        "yearly_stability": yearly_band_direction(daily),
        "band_exposures": band_exposures,
        "band_tail_contribution": band_tails,
    }, daily, members


def delta(a: float | None, b: float | None) -> float | None:
    return a - b if a is not None and b is not None else None


def diagnose_models(con: duckdb.DuckDBPyConnection, specs: dict[str, ModelSpec]) -> tuple[dict[str, Any], dict[str, pd.DataFrame], pd.DataFrame]:
    diagnostics: dict[str, Any] = {}
    daily_map: dict[str, pd.DataFrame] = {}
    members_list: list[pd.DataFrame] = []
    for spec in specs.values():
        frame = fetch_model_frame(con, spec)
        splits: dict[str, Any] = {}
        for split_name, mask in [("train", frame["train_flag"]), ("validation", frame["validation_flag"])]:
            payload, daily, members = diagnose_model_split(frame[mask], split_name, spec.key)
            splits[split_name] = payload
            daily_map[f"{spec.key}:{split_name}"] = daily
            members_list.append(members)
        diagnostics[spec.key] = {"candidate_scheme_id": spec.candidate_scheme_id, "status": spec.status, "label": spec.label, **splits}
    members = pd.concat(members_list, ignore_index=True) if members_list else pd.DataFrame()
    return diagnostics, daily_map, members


def build_mid_rank_commonality(diagnostics: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for split in ["train", "validation"]:
        band_model_counts: dict[str, dict[str, Any]] = {}
        for band_name in ["mid_head", "broad_head", "nextk"]:
            models_beat_topk = []
            for model in CLEAN_MODEL_KEYS:
                structure = diagnostics[model][split].get("rank_band_structure", {})
                if band_name in structure:
                    minus = structure[band_name].get("mean_minus_topk")
                    if minus is not None and minus > 0:
                        models_beat_topk.append(model)
            band_model_counts[band_name] = {
                "n_models_beat_topk": len(models_beat_topk),
                "models_beat_topk": models_beat_topk,
                "n_clean_models_total": len(CLEAN_MODEL_KEYS),
            }
        result[split] = band_model_counts
    per_model: dict[str, Any] = {}
    for model in CLEAN_MODEL_KEYS:
        train = diagnostics[model]["train"].get("rank_band_structure", {})
        val = diagnostics[model]["validation"].get("rank_band_structure", {})
        yearly = diagnostics[model]["validation"].get("yearly_stability", {})
        model_bands: dict[str, Any] = {}
        for band_name in ["mid_head", "broad_head"]:
            train_direction = train.get(band_name, {}).get("mean_minus_topk")
            val_direction = val.get(band_name, {}).get("mean_minus_topk")
            train_val_consistent = (
                train_direction is not None and val_direction is not None
                and (train_direction > 0) == (val_direction > 0)
            )
            yearly_consistent = True
            if yearly:
                for year_data in yearly.values():
                    year_minus = year_data.get(f"{band_name}_minus_topk_mean")
                    if year_minus is not None and year_minus <= 0:
                        yearly_consistent = False
                        break
            model_bands[band_name] = {
                "train_mean_minus_topk": train_direction,
                "validation_mean_minus_topk": val_direction,
                "train_validation_same_direction": train_val_consistent,
                "validation_yearly_all_same_direction": yearly_consistent,
            }
        per_model[model] = model_bands
    result["per_model_band_consistency"] = per_model
    return result


def build_decision_summary(payload: dict[str, Any]) -> dict[str, Any]:
    common = payload["mid_rank_commonality"]
    val_mid = common["validation"].get("mid_head", {})
    val_broad = common["validation"].get("broad_head", {})
    mid_beats_topk_most = val_mid.get("n_models_beat_topk", 0) >= 4
    broad_beats_topk_most = val_broad.get("n_models_beat_topk", 0) >= 4
    all_consistent = True
    for model, bands in common.get("per_model_band_consistency", {}).items():
        for band_name in ["mid_head", "broad_head"]:
            if band_name in bands:
                if not bands[band_name].get("train_validation_same_direction", False):
                    all_consistent = False
                if not bands[band_name].get("validation_yearly_all_same_direction", False):
                    all_consistent = False
    stable_mid_rank_edge = bool(mid_beats_topk_most and all_consistent)
    recommend_dry_run = bool(stable_mid_rank_edge and (mid_beats_topk_most or broad_beats_topk_most))
    return {
        "mid_rank_beats_topk_most_clean_models": mid_beats_topk_most,
        "broad_rank_beats_topk_most_clean_models": broad_beats_topk_most,
        "train_validation_yearly_stable": all_consistent,
        "stable_mid_rank_edge_exists": stable_mid_rank_edge,
        "recommend_next_stage_diagnostic_portfolio_dry_run": recommend_dry_run,
        "this_round_runs_portfolio": False,
        "frozen_test_accessed": False,
        "training_backtest_or_portfolio_run": False,
        "rank_bands_were_tuned": False,
        "p98_used_as_clean_component": False,
        "interpretation": (
            "Stable mid-rank edge found; may recommend separately preregistered diagnostic portfolio dry-run."
            if recommend_dry_run
            else "No stable mid-rank edge; do not recommend diagnostic portfolio dry-run."
        ),
    }


def build_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Clean Mid-Rank Edge Diagnosis",
        "",
        "Train/validation diagnosis only. Not OOS, not strategy approval, not portfolio, not backtest, not formal metrics/readout, and frozen test remains unread.",
        "",
        "## Rank-Band Structure",
        "",
    ]
    for split in ["train", "validation"]:
        lines.append(f"### {split}")
        lines.append("")
        for model in CLEAN_MODEL_KEYS:
            structure = payload["diagnostics"][model][split].get("rank_band_structure", {})
            if not structure:
                continue
            label = payload["diagnostics"][model]["label"]
            lines.append(f"**{model}** ({label}):")
            for band_name in ["topk", "nextk", "mid_head", "broad_head", "middle"]:
                if band_name in structure:
                    s = structure[band_name]
                    lines.append(f"- `{band_name}` (rank {s['rank_start']}-{s['rank_end']}): mean `{s['mean_return']}`, win vs TopK `{s['daily_win_rate_vs_topk']}`, minus TopK `{s['mean_minus_topk']}`")
            lines.append("")
    lines.extend([
        "## Mid-Rank Commonality",
        "",
    ])
    for split in ["train", "validation"]:
        common = payload["mid_rank_commonality"][split]
        lines.append(f"### {split}")
        for band_name in ["nextk", "mid_head", "broad_head"]:
            if band_name in common:
                c = common[band_name]
                lines.append(f"- `{band_name}` beats TopK: `{c['n_models_beat_topk']}` / `{c['n_clean_models_total']}` clean models")
        lines.append("")
    lines.extend([
        "## Decision Summary",
        "",
    ])
    for key, value in payload["decision_summary"].items():
        lines.append(f"- {key}: `{value}`")
    return "\n".join(lines) + "\n"


def resolve_bands(args: argparse.Namespace) -> dict[str, tuple[int, int]]:
    if args.band_override_json is not None:
        override = json.loads(args.band_override_json)
        return {k: (int(v[0]), int(v[1])) for k, v in override.items()}
    return dict(RANK_BANDS)


def run_diagnosis(args: argparse.Namespace) -> dict[str, Any]:
    global _ACTIVE_BANDS
    _ACTIVE_BANDS = resolve_bands(args)
    bands = _ACTIVE_BANDS
    specs = build_specs(args)
    for path, label in [
        (args.label_panel, "label panel"),
        (args.split_panel, "split panel"),
        (args.exposure_panel, "exposure panel"),
        *[(spec.score_path, f"{spec.key} scores") for spec in specs.values()],
    ]:
        ensure_exists(path, label)
    con = duckdb.connect()
    try:
        register_views(con, args, specs)
        diagnostics, _, _ = diagnose_models(con, specs)
        payload = {
            "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "round_id": "clean_mid_rank_portfolio_hypothesis_round_v1",
            "diagnosis_label": "TRAINVAL_DIAGNOSIS_ONLY_NOT_OOS_NOT_PORTFOLIO",
            "training_performed": False,
            "backtest_run_executed": False,
            "portfolio_run_executed": False,
            "holdings_generated": False,
            "formal_metrics_generated": False,
            "frozen_test_accessed": False,
            "rank_bands_were_tuned": False,
            "p98_reference_status": "conditional_reference_only",
            "multi_equal_weight_v1_reference_status": "conditional_reference_only",
            "blocked_fields": sorted(BLOCKED_FIELDS),
            "blocked_fields_used": [],
            "used_exposure_fields": USED_EXPOSURE_FIELDS,
            "rank_bands": {k: {"start": v[0], "end": v[1]} for k, v in bands.items()},
            "diagnostics": diagnostics,
            "mid_rank_commonality": build_mid_rank_commonality(diagnostics),
        }
        payload["decision_summary"] = build_decision_summary(payload)
        return payload
    finally:
        con.close()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    payload = run_diagnosis(args)
    write_json(args.output_json, payload)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(build_markdown(payload), encoding="utf-8")


if __name__ == "__main__":
    main()
