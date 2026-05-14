#!/usr/bin/env python3
"""
Diagnose cross-model agreement / disagreement structure for clean score heads.

This is exploratory descriptive research only. It does not claim alpha, create
candidates, create new baselines, train, backtest, run portfolio, generate
holdings/readouts, or read frozen test data.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from diagnose_rank_band_full_profile import (
    BOARD,
    COMP,
    DEFAULT_BOARD_NEUTRAL_SCORES,
    DEFAULT_COMPOSITE_SCORES,
    DEFAULT_EXPOSURE_PANEL,
    DEFAULT_LABEL_PANEL,
    DEFAULT_LIMIT_AWARE_SCORES,
    DEFAULT_LISTING_AGE_SCORES,
    DEFAULT_LIQUIDITY_SCORES,
    DEFAULT_MULTI_EQUAL_SCORES,
    DEFAULT_NO_P98_SCORES,
    DEFAULT_P98_SCORES,
    DEFAULT_SPLIT_PANEL,
    DEFAULT_TRADABILITY_FILTERED_SCORES,
    LIMIT,
    LISTING,
    LIQ,
    MULTI,
    NO_P98,
    P98,
    TRAD,
    DiagnosisError,
    assign_exposure_buckets,
    build_specs,
    ensure_exists,
    fetch_model_frame,
    register_views,
    safe_float,
    summarize_bool,
    summarize_distribution,
    tail_contribution,
)


ROOT = Path("/Users/wy/MiscProject/multi_factor")
DEFAULT_OUTPUT_JSON = Path("/private/tmp/cross_model_agreement_descriptive_diagnosis.json")
DEFAULT_OUTPUT_MD = Path("/private/tmp/cross_model_agreement_descriptive_diagnosis.md")

CLEAN_MODEL_KEYS = [NO_P98, LIQ, BOARD, LIMIT, TRAD, LISTING]
REJECTED_COMPARATOR_KEYS = [COMP]
REFERENCE_KEYS = [P98, MULTI]

TOPK_THRESHOLD = 30
NEXTK_START = 31
NEXTK_END = 60
MID_HEAD_END = 100
BROAD_HEAD_END = 200
MIDDLE_START = 101
MIDDLE_END = 300
COMMON_THRESHOLD = 4

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

RANK_GROUPS = {
    "topk": {"label": "rank_1_30", "rank_start": 1, "rank_end": 30},
    "nextk": {"label": "rank_31_60", "rank_start": 31, "rank_end": 60},
    "mid_head": {"label": "rank_31_100", "rank_start": 31, "rank_end": 100},
    "broad_head": {"label": "rank_31_200", "rank_start": 31, "rank_end": 200},
    "middle": {"label": "rank_101_300", "rank_start": 101, "rank_end": 300},
}

MIGRATION_NOTE = (
    "Cross-band migration uses exclusive placement bands: TopK=1-30, nextK=31-60, "
    "mid_head=61-100, middle=101-300. Aggregated rank_31_100 summaries are reported separately."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose cross-model agreement / disagreement structure.")
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
    return parser.parse_args()


def summarize_returns(frame: pd.DataFrame) -> dict[str, Any]:
    returns = frame["forward_return_5d"].dropna() if "forward_return_5d" in frame else pd.Series(dtype=float)
    if returns.empty:
        return {
            "count": 0,
            "mean_return": None,
            "median_return": None,
            "positive_rate": None,
            "p05_return": None,
            "p95_return": None,
            "best_5pct_contribution": None,
            "worst_5pct_damage": None,
        }
    tail = tail_contribution(returns)
    return {
        "count": int(len(returns)),
        "mean_return": safe_float(returns.mean()),
        "median_return": safe_float(returns.median()),
        "positive_rate": safe_float((returns > 0).mean()),
        "p05_return": safe_float(returns.quantile(0.05)),
        "p95_return": safe_float(returns.quantile(0.95)),
        "best_5pct_contribution": safe_float(tail["best_5pct_contribution"]),
        "worst_5pct_damage": safe_float(tail["worst_5pct_damage"]),
    }


def summarize_exposure(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {"status": "empty"}
    return {
        "amount_bucket": summarize_distribution(frame, "amount_bucket"),
        "board_type": summarize_distribution(frame, "board_type"),
        "exchange": summarize_distribution(frame, "exchange"),
        "listing_age_days_bucket": summarize_distribution(frame, "listing_age_days_bucket"),
        "limit_tradability": {
            "is_limit_down": summarize_bool(frame, "is_limit_down"),
            "close_at_down_limit": summarize_bool(frame, "close_at_down_limit"),
            "open_at_up_limit": summarize_bool(frame, "open_at_up_limit"),
            "entry_buyable": summarize_bool(frame, "entry_buyable"),
            "no_trade_flag": summarize_bool(frame, "no_trade_flag"),
            "is_suspended": summarize_bool(frame, "is_suspended"),
            "volume_zero_flag": summarize_bool(frame, "volume_zero_flag"),
            "amount_zero_flag": summarize_bool(frame, "amount_zero_flag"),
            "is_limit_up": summarize_bool(frame, "is_limit_up"),
        },
        "extreme_reversal_state": {"status": "unavailable"},
    }


def comparison_payload(left: pd.DataFrame, right: pd.DataFrame, left_label: str, right_label: str) -> dict[str, Any]:
    left_stats = summarize_returns(left)
    right_stats = summarize_returns(right)
    left_mean = left_stats["mean_return"]
    right_mean = right_stats["mean_return"]
    left_median = left_stats["median_return"]
    right_median = right_stats["median_return"]
    return {
        left_label: {
            "returns": left_stats,
            "exposure": summarize_exposure(left),
        },
        right_label: {
            "returns": right_stats,
            "exposure": summarize_exposure(right),
        },
        "mean_return_delta": safe_float(left_mean - right_mean) if left_mean is not None and right_mean is not None else None,
        "median_return_delta": safe_float(left_median - right_median) if left_median is not None and right_median is not None else None,
    }


def top_owner(frame: pd.DataFrame, model_keys: list[str], flag_suffix: str) -> pd.Series:
    owner = pd.Series([None] * len(frame), index=frame.index, dtype="object")
    for model in model_keys:
        owner = owner.mask(frame[f"{model}__{flag_suffix}"], model)
    return owner


def exclusive_band_counts(frame: pd.DataFrame, model_keys: list[str], band_name: str) -> pd.Series:
    cols = [f"{model}__exclusive_band" for model in model_keys]
    return (frame[cols] == band_name).sum(axis=1)


def prepare_rank_frame(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.dropna(subset=["effective_score", "forward_return_5d"]).copy()
    work["split_bucket"] = np.where(work["train_flag"], "train", np.where(work["validation_flag"], "validation", None))
    work = work[work["split_bucket"].notna()].copy()
    work = work.sort_values(["signal_date", "effective_score", "instrument"], ascending=[True, False, True]).reset_index(drop=True)
    work["exact_rank"] = work.groupby(["split_bucket", "signal_date"], sort=False).cumcount() + 1
    work["topk_flag"] = work["exact_rank"] <= TOPK_THRESHOLD
    work["nextk_flag"] = work["exact_rank"].between(NEXTK_START, NEXTK_END)
    work["mid_head_flag"] = work["exact_rank"].between(NEXTK_START, MID_HEAD_END)
    work["broad_head_flag"] = work["exact_rank"].between(NEXTK_START, BROAD_HEAD_END)
    work["middle_flag"] = work["exact_rank"].between(MIDDLE_START, MIDDLE_END)
    work["exclusive_band"] = np.select(
        [
            work["exact_rank"] <= TOPK_THRESHOLD,
            work["exact_rank"].between(NEXTK_START, NEXTK_END),
            work["exact_rank"].between(NEXTK_END + 1, MID_HEAD_END),
            work["exact_rank"].between(MIDDLE_START, MIDDLE_END),
        ],
        ["topk", "nextk", "mid_head", "middle"],
        default="outside",
    )
    return work[
        [
            "snapshot_id",
            "instrument",
            "signal_date",
            "split_bucket",
            "exact_rank",
            "topk_flag",
            "nextk_flag",
            "mid_head_flag",
            "broad_head_flag",
            "middle_flag",
            "exclusive_band",
        ]
    ].copy()


def merge_rank_columns(base: pd.DataFrame, rank_frame: pd.DataFrame, model_key: str) -> pd.DataFrame:
    renamed = rank_frame.rename(
        columns={
            "exact_rank": f"{model_key}__exact_rank",
            "topk_flag": f"{model_key}__topk_flag",
            "nextk_flag": f"{model_key}__nextk_flag",
            "mid_head_flag": f"{model_key}__mid_head_flag",
            "broad_head_flag": f"{model_key}__broad_head_flag",
            "middle_flag": f"{model_key}__middle_flag",
            "exclusive_band": f"{model_key}__exclusive_band",
        }
    )
    merged = base.merge(
        renamed,
        on=["snapshot_id", "instrument", "signal_date", "split_bucket"],
        how="left",
    )
    for suffix in ["topk_flag", "nextk_flag", "mid_head_flag", "broad_head_flag", "middle_flag"]:
        merged[f"{model_key}__{suffix}"] = merged[f"{model_key}__{suffix}"].fillna(False).astype(bool)
    merged[f"{model_key}__exclusive_band"] = merged[f"{model_key}__exclusive_band"].fillna("outside")
    return merged


def build_master_frame(con: duckdb.DuckDBPyConnection, args: argparse.Namespace) -> tuple[pd.DataFrame, dict[str, Any]]:
    specs = build_specs(args)
    register_views(con, args, specs)

    base_frame: pd.DataFrame | None = None
    rank_tables: dict[str, pd.DataFrame] = {}
    model_metadata: dict[str, Any] = {}
    for model_key in CLEAN_MODEL_KEYS + REJECTED_COMPARATOR_KEYS + REFERENCE_KEYS:
        spec = specs[model_key]
        frame = fetch_model_frame(con, spec)
        if base_frame is None:
            base_frame = frame[
                [
                    "snapshot_id",
                    "instrument",
                    "signal_date",
                    "forward_return_5d",
                    "train_flag",
                    "validation_flag",
                    "amount",
                    "amount_percentile_asc",
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
            ].copy()
        rank_tables[model_key] = prepare_rank_frame(frame)
        model_metadata[model_key] = {
            "candidate_scheme_id": spec.candidate_scheme_id,
            "status": spec.status,
            "label": spec.label,
        }
    if base_frame is None:
        raise DiagnosisError("no base frame available")

    base = base_frame.copy()
    base["split_bucket"] = np.where(base["train_flag"], "train", np.where(base["validation_flag"], "validation", None))
    base = base[base["split_bucket"].notna()].copy()
    base = assign_exposure_buckets(base)
    base["year"] = base["signal_date"].astype(str).str[:4]
    base = base.drop(columns=["train_flag", "validation_flag"]).drop_duplicates(
        subset=["snapshot_id", "instrument", "signal_date", "split_bucket"]
    )

    master = base
    for model_key in CLEAN_MODEL_KEYS + REJECTED_COMPARATOR_KEYS + REFERENCE_KEYS:
        master = merge_rank_columns(master, rank_tables[model_key], model_key)

    clean_topk_cols = [f"{model}__topk_flag" for model in CLEAN_MODEL_KEYS]
    clean_nextk_cols = [f"{model}__nextk_flag" for model in CLEAN_MODEL_KEYS]
    clean_mid_head_cols = [f"{model}__mid_head_flag" for model in CLEAN_MODEL_KEYS]
    clean_broad_head_cols = [f"{model}__broad_head_flag" for model in CLEAN_MODEL_KEYS]
    clean_middle_cols = [f"{model}__middle_flag" for model in CLEAN_MODEL_KEYS]

    master["topk_agreement_count"] = master[clean_topk_cols].sum(axis=1)
    master["nextk_agreement_count"] = master[clean_nextk_cols].sum(axis=1)
    master["mid_head_agreement_count"] = master[clean_mid_head_cols].sum(axis=1)
    master["broad_head_agreement_count"] = master[clean_broad_head_cols].sum(axis=1)
    master["middle_agreement_count"] = master[clean_middle_cols].sum(axis=1)
    master["topk_owner_model"] = top_owner(master, CLEAN_MODEL_KEYS, "topk_flag")

    master["exclusive_topk_count"] = master["topk_agreement_count"]
    master["exclusive_nextk_count"] = exclusive_band_counts(master, CLEAN_MODEL_KEYS, "nextk")
    master["exclusive_mid_head_count"] = exclusive_band_counts(master, CLEAN_MODEL_KEYS, "mid_head")
    master["exclusive_middle_count"] = exclusive_band_counts(master, CLEAN_MODEL_KEYS, "middle")

    master["high_agreement_topk"] = master["topk_agreement_count"] >= COMMON_THRESHOLD
    master["low_agreement_topk"] = master["topk_agreement_count"] == 1
    master["common_topk"] = master["high_agreement_topk"]
    master["model_specific_topk"] = master["low_agreement_topk"]
    master["common_nextk"] = (master["nextk_agreement_count"] >= COMMON_THRESHOLD) & (master["topk_agreement_count"] == 0)
    master["common_mid_head"] = (master["mid_head_agreement_count"] >= COMMON_THRESHOLD) & (master["topk_agreement_count"] == 0)
    master["common_broad_head"] = (master["broad_head_agreement_count"] >= COMMON_THRESHOLD) & (master["topk_agreement_count"] == 0)
    master["near_head_disagreement"] = master["topk_agreement_count"].between(1, COMMON_THRESHOLD - 1) & (
        (master["exclusive_nextk_count"] + master["exclusive_mid_head_count"]) >= 1
    )

    master["migration_pattern"] = np.select(
        [
            master["exclusive_topk_count"] >= COMMON_THRESHOLD,
            (master["exclusive_topk_count"] == 1) & ((master["exclusive_nextk_count"] + master["exclusive_mid_head_count"]) >= 1),
            (master["exclusive_topk_count"] == 0) & ((master["exclusive_nextk_count"] + master["exclusive_mid_head_count"]) >= COMMON_THRESHOLD),
            (master["exclusive_topk_count"] == 0) & (master["exclusive_middle_count"] >= COMMON_THRESHOLD),
        ],
        [
            "topk_by_many_models",
            "topk_by_one_others_nextk_or_mid_head",
            "mid_head_by_many_models",
            "middle_by_many_models",
        ],
        default="scattered_or_outside",
    )
    return master, model_metadata


def agreement_bucket_payload(frame: pd.DataFrame, count_column: str) -> dict[str, Any]:
    buckets: dict[str, Any] = {}
    for count in range(0, len(CLEAN_MODEL_KEYS) + 1):
        subset = frame[frame[count_column] == count].copy()
        buckets[str(count)] = {
            "returns": summarize_returns(subset),
            "exposure": summarize_exposure(subset),
        }
    return buckets


def specific_topk_per_model(frame: pd.DataFrame) -> dict[str, Any]:
    out: dict[str, Any] = {}
    specific = frame[frame["model_specific_topk"]].copy()
    for model in CLEAN_MODEL_KEYS:
        subset = specific[specific[f"{model}__topk_flag"]].copy()
        out[model] = {
            "returns": summarize_returns(subset),
            "exposure": summarize_exposure(subset),
        }
    return out


def migration_payload(frame: pd.DataFrame) -> dict[str, Any]:
    patterns: dict[str, Any] = {}
    for pattern in [
        "topk_by_one_others_nextk_or_mid_head",
        "topk_by_many_models",
        "mid_head_by_many_models",
        "middle_by_many_models",
        "scattered_or_outside",
    ]:
        subset = frame[frame["migration_pattern"] == pattern].copy()
        patterns[pattern] = {
            "returns": summarize_returns(subset),
            "exposure": summarize_exposure(subset),
        }
    return {
        "note": MIGRATION_NOTE,
        "patterns": patterns,
    }


def overlap_stats(reference_mask: pd.Series, cohort_mask: pd.Series, frame: pd.DataFrame) -> dict[str, Any]:
    overlap = frame[reference_mask & cohort_mask].copy()
    ref_only = frame[reference_mask & ~cohort_mask].copy()
    cohort_only = frame[cohort_mask & ~reference_mask].copy()
    return {
        "overlap_count": int(len(overlap)),
        "reference_only_count": int(len(ref_only)),
        "cohort_only_count": int(len(cohort_only)),
        "overlap_returns": summarize_returns(overlap),
        "reference_only_returns": summarize_returns(ref_only),
        "cohort_only_returns": summarize_returns(cohort_only),
    }


def conditional_reference_payload(frame: pd.DataFrame, reference_key: str) -> dict[str, Any]:
    topk_flag = frame[f"{reference_key}__topk_flag"]
    return {
        "reference_status": "conditional_reference_only",
        "note": f"{reference_key} is conditional reference only",
        "topk_vs_common_topk": overlap_stats(topk_flag, frame["common_topk"], frame),
        "topk_vs_common_nextk": overlap_stats(topk_flag, frame["common_nextk"], frame),
        "topk_vs_common_mid_head": overlap_stats(topk_flag, frame["common_mid_head"], frame),
        "p98_only_vs_clean_common_only": comparison_payload(
            frame[topk_flag & ~(frame["common_topk"] | frame["common_nextk"] | frame["common_mid_head"])].copy(),
            frame[frame["common_topk"] & ~topk_flag].copy(),
            "reference_only",
            "clean_common_topk_only",
        )
        if reference_key == P98
        else comparison_payload(
            frame[topk_flag & ~(frame["common_topk"] | frame["common_nextk"] | frame["common_mid_head"])].copy(),
            frame[frame["common_topk"] & ~topk_flag].copy(),
            "reference_only",
            "clean_common_topk_only",
        ),
    }


def yearly_direction(validation_frame: pd.DataFrame, left_mask_name: str, right_mask_name: str, prefer: str) -> dict[str, Any]:
    per_year: dict[str, Any] = {}
    directions: list[str] = []
    for year, year_frame in validation_frame.groupby("year", sort=True):
        left = summarize_returns(year_frame[year_frame[left_mask_name]].copy())
        right = summarize_returns(year_frame[year_frame[right_mask_name]].copy())
        left_mean = left["mean_return"]
        right_mean = right["mean_return"]
        direction = "insufficient"
        if left_mean is not None and right_mean is not None:
            if left_mean > right_mean:
                direction = "left_gt_right"
            elif left_mean < right_mean:
                direction = "left_lt_right"
            else:
                direction = "equal"
        per_year[str(year)] = {
            "left_mean_return": left_mean,
            "right_mean_return": right_mean,
            "direction": direction,
        }
        if direction in {"left_gt_right", "left_lt_right"}:
            directions.append(direction)
    target = "left_lt_right" if prefer == "weaker" else "left_gt_right"
    if not directions:
        return {"status": "insufficient_evidence", "per_year": per_year, "validation_yearly_consistent": None}
    return {
        "status": "ok",
        "per_year": per_year,
        "validation_yearly_consistent": all(direction == target for direction in directions),
    }


def stability_check(train_frame: pd.DataFrame, validation_frame: pd.DataFrame, left_mask_name: str, right_mask_name: str, prefer: str) -> dict[str, Any]:
    train_left = summarize_returns(train_frame[train_frame[left_mask_name]].copy())
    train_right = summarize_returns(train_frame[train_frame[right_mask_name]].copy())
    validation_left = summarize_returns(validation_frame[validation_frame[left_mask_name]].copy())
    validation_right = summarize_returns(validation_frame[validation_frame[right_mask_name]].copy())

    def direction(left_mean: float | None, right_mean: float | None) -> str:
        if left_mean is None or right_mean is None:
            return "insufficient"
        if left_mean > right_mean:
            return "left_gt_right"
        if left_mean < right_mean:
            return "left_lt_right"
        return "equal"

    train_direction = direction(train_left["mean_return"], train_right["mean_return"])
    validation_direction = direction(validation_left["mean_return"], validation_right["mean_return"])
    expected = "left_lt_right" if prefer == "weaker" else "left_gt_right"
    yearly = yearly_direction(validation_frame, left_mask_name, right_mask_name, prefer)
    consistent = train_direction == expected and validation_direction == expected and yearly.get("validation_yearly_consistent") is True
    status = "insufficient_evidence"
    if consistent:
        status = "consistent"
    elif train_direction in {"left_gt_right", "left_lt_right"} and validation_direction in {"left_gt_right", "left_lt_right"}:
        status = "inconsistent"
    return {
        "status": status,
        "train_direction": train_direction,
        "validation_direction": validation_direction,
        "train_mean_return": train_left["mean_return"],
        "validation_mean_return": validation_left["mean_return"],
        "train_validation_direction_consistent": train_direction == validation_direction and train_direction == expected,
        "validation_yearly": yearly,
    }


def split_payload(frame: pd.DataFrame) -> dict[str, Any]:
    common_topk = frame[frame["common_topk"]].copy()
    model_specific_topk = frame[frame["model_specific_topk"]].copy()
    common_nextk = frame[frame["common_nextk"]].copy()
    common_mid_head = frame[frame["common_mid_head"]].copy()
    common_broad_head = frame[frame["common_broad_head"]].copy()
    near_head_disagreement = frame[frame["near_head_disagreement"]].copy()
    return {
        "agreement_count_buckets_topk": agreement_bucket_payload(frame, "topk_agreement_count"),
        "high_agreement_topk_vs_low_agreement_topk": comparison_payload(
            common_topk,
            model_specific_topk,
            "high_agreement_topk",
            "low_agreement_topk",
        ),
        "common_topk_vs_model_specific_topk": {
            **comparison_payload(common_topk, model_specific_topk, "common_topk", "model_specific_topk"),
            "model_specific_topk_per_model": specific_topk_per_model(frame),
        },
        "agreement_in_near_head_bands": {
            "common_topk": {"returns": summarize_returns(common_topk), "exposure": summarize_exposure(common_topk)},
            "common_nextk": {"returns": summarize_returns(common_nextk), "exposure": summarize_exposure(common_nextk)},
            "common_mid_head": {"returns": summarize_returns(common_mid_head), "exposure": summarize_exposure(common_mid_head)},
            "common_broad_head": {"returns": summarize_returns(common_broad_head), "exposure": summarize_exposure(common_broad_head)},
            "near_head_disagreement": {"returns": summarize_returns(near_head_disagreement), "exposure": summarize_exposure(near_head_disagreement)},
            "common_nextk_vs_common_topk_mean_delta": safe_float(
                summarize_returns(common_nextk)["mean_return"] - summarize_returns(common_topk)["mean_return"]
            )
            if summarize_returns(common_nextk)["mean_return"] is not None and summarize_returns(common_topk)["mean_return"] is not None
            else None,
            "common_mid_head_vs_common_topk_mean_delta": safe_float(
                summarize_returns(common_mid_head)["mean_return"] - summarize_returns(common_topk)["mean_return"]
            )
            if summarize_returns(common_mid_head)["mean_return"] is not None and summarize_returns(common_topk)["mean_return"] is not None
            else None,
            "near_head_disagreement_vs_common_mid_head_mean_delta": safe_float(
                summarize_returns(near_head_disagreement)["mean_return"] - summarize_returns(common_mid_head)["mean_return"]
            )
            if summarize_returns(near_head_disagreement)["mean_return"] is not None
            and summarize_returns(common_mid_head)["mean_return"] is not None
            else None,
        },
        "cross_band_migration": migration_payload(frame),
        "exposure_decomposition_by_topk_agreement_count": agreement_bucket_payload(frame, "topk_agreement_count"),
        "conditional_reference_comparison": {
            "p98_conditional_reference": conditional_reference_payload(frame, P98),
            "multi_equal_weight_v1_conditional_reference": conditional_reference_payload(frame, MULTI),
        },
    }


def build_stability(master: pd.DataFrame) -> dict[str, Any]:
    train_frame = master[master["split_bucket"] == "train"].copy()
    validation_frame = master[master["split_bucket"] == "validation"].copy()
    return {
        "high_agreement_topk_is_stably_weaker_than_model_specific_topk": stability_check(
            train_frame, validation_frame, "common_topk", "model_specific_topk", "weaker"
        ),
        "common_mid_head_is_stably_stronger_than_common_topk": stability_check(
            train_frame, validation_frame, "common_mid_head", "common_topk", "stronger"
        ),
        "common_nextk_is_stably_stronger_than_common_topk": stability_check(
            train_frame, validation_frame, "common_nextk", "common_topk", "stronger"
        ),
    }


def build_hypotheses(payload: dict[str, Any]) -> list[dict[str, Any]]:
    validation = payload["diagnostics"]["validation"]
    stability = payload["stability"]
    common_topk_exposure = validation["common_topk_vs_model_specific_topk"]["common_topk"]["exposure"]
    model_specific_exposure = validation["common_topk_vs_model_specific_topk"]["model_specific_topk"]["exposure"]

    def true_share(exposure: dict[str, Any], field: str) -> float | None:
        item = exposure["limit_tradability"].get(field, {})
        return item.get("true_share")

    common_limit_down = true_share(common_topk_exposure, "is_limit_down")
    specific_limit_down = true_share(model_specific_exposure, "is_limit_down")
    common_close_down = true_share(common_topk_exposure, "close_at_down_limit")
    specific_close_down = true_share(model_specific_exposure, "close_at_down_limit")

    hypotheses: list[dict[str, Any]] = []
    status_one = stability["high_agreement_topk_is_stably_weaker_than_model_specific_topk"]["status"]
    if status_one == "consistent" and (
        (common_limit_down is not None and specific_limit_down is not None and common_limit_down > specific_limit_down)
        or (common_close_down is not None and specific_close_down is not None and common_close_down > specific_close_down)
    ):
        hypotheses.append(
            {
                "hypothesis_id": "consensus_topk_stress_crowding",
                "status": "paper_only_candidate_for_preregistration",
                "statement": "descriptive evidence suggests common TopK consensus may crowd into limit-like or state-anomaly names rather than stabilizing the head",
            }
        )
    else:
        hypotheses.append(
            {
                "hypothesis_id": "consensus_topk_stress_crowding",
                "status": "insufficient_evidence",
                "statement": "evidence is insufficient to claim a stable stress-crowding mechanism for common TopK",
            }
        )

    status_two = stability["common_mid_head_is_stably_stronger_than_common_topk"]["status"]
    if status_two == "consistent":
        hypotheses.append(
            {
                "hypothesis_id": "near_head_consensus_better_than_head_consensus",
                "status": "paper_only_candidate_for_preregistration",
                "statement": "descriptive evidence suggests cleaner shared information may survive as near-head consensus instead of exact TopK consensus",
            }
        )
    else:
        hypotheses.append(
            {
                "hypothesis_id": "near_head_consensus_better_than_head_consensus",
                "status": "insufficient_evidence",
                "statement": "common mid-head superiority is not stable enough for stronger mechanism language",
            }
        )

    p98_overlap_topk = validation["conditional_reference_comparison"]["p98_conditional_reference"]["topk_vs_common_topk"]["overlap_count"]
    p98_overlap_mid = validation["conditional_reference_comparison"]["p98_conditional_reference"]["topk_vs_common_mid_head"]["overlap_count"]
    if p98_overlap_mid > p98_overlap_topk:
        hypotheses.append(
            {
                "hypothesis_id": "p98_aligns_more_with_clean_near_head_than_clean_common_topk",
                "status": "paper_only_candidate_for_preregistration",
                "statement": "conditional reference only: p98 TopK may align more with clean near-head consensus than with clean common TopK consensus",
            }
        )
    else:
        hypotheses.append(
            {
                "hypothesis_id": "p98_aligns_more_with_clean_near_head_than_clean_common_topk",
                "status": "insufficient_evidence",
                "statement": "conditional reference only: p98 overlap structure does not clearly favor clean near-head consensus over clean common TopK",
            }
        )
    return hypotheses


def build_markdown(payload: dict[str, Any]) -> str:
    validation = payload["diagnostics"]["validation"]
    common_topk = validation["common_topk_vs_model_specific_topk"]["common_topk"]["returns"]
    model_specific = validation["common_topk_vs_model_specific_topk"]["model_specific_topk"]["returns"]
    common_mid = validation["agreement_in_near_head_bands"]["common_mid_head"]["returns"]
    common_nextk = validation["agreement_in_near_head_bands"]["common_nextk"]["returns"]
    disagreement = validation["agreement_in_near_head_bands"]["near_head_disagreement"]["returns"]
    lines = [
        "# Cross-Model Agreement Descriptive Diagnosis",
        "",
        "This is exploratory descriptive research only. It is not alpha, not a candidate, not a new baseline, not v4, not training, not backtest, not portfolio, not OOS, and frozen test remains unread.",
        "",
        "## Boundary",
        "",
        "- descriptive-only",
        "- no alpha claim",
        "- no candidate",
        "- no portfolio",
        "- no frozen test",
        "- trainval not OOS",
        "- p98 / multi_equal_weight_v1 conditional reference only",
        "- agreement_count cannot directly form any trading rule",
        "",
        "## Migration Note",
        "",
        MIGRATION_NOTE,
        "",
        "## Validation Snapshot",
        "",
        f"- common TopK mean `{common_topk['mean_return']}` vs model-specific TopK mean `{model_specific['mean_return']}`",
        f"- common nextK mean `{common_nextk['mean_return']}`",
        f"- common mid_head mean `{common_mid['mean_return']}`",
        f"- near-head disagreement mean `{disagreement['mean_return']}`",
        "",
        "## Conditional References",
        "",
        "- `p98_conditional_reference`: conditional reference only",
        "- `multi_equal_weight_v1_conditional_reference`: conditional reference only",
        "",
        "## Final Statement",
        "",
        "This output is descriptive only. It does not restart strategy research, does not authorize portfolio recommendation, and does not create a trading rule.",
    ]
    return "\n".join(lines) + "\n"


def run(args: argparse.Namespace) -> dict[str, Any]:
    paths = [
        (args.label_panel, "label panel"),
        (args.split_panel, "split panel"),
        (args.exposure_panel, "exposure panel"),
        (args.no_p98_scores, "no-p98 scores"),
        (args.liquidity_scores, "liquidity scores"),
        (args.composite_scores, "composite scores"),
        (args.limit_aware_scores, "limit-aware scores"),
        (args.board_neutral_scores, "board-neutral scores"),
        (args.tradability_filtered_scores, "tradability-filtered scores"),
        (args.listing_age_scores, "listing-age scores"),
        (args.p98_scores, "p98 scores"),
        (args.multi_equal_scores, "multi-equal scores"),
    ]
    for path, label in paths:
        ensure_exists(path, label)

    con = duckdb.connect()
    try:
        master, model_metadata = build_master_frame(con, args)
    finally:
        con.close()

    diagnostics = {
        split: split_payload(master[master["split_bucket"] == split].copy()) for split in ["train", "validation"]
    }
    payload = {
        "diagnosis_name": "cross_model_agreement_descriptive_diagnosis",
        "diagnosis_label": "DESCRIPTIVE_ONLY_TRAINVAL_NOT_OOS_NOT_PORTFOLIO",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "governance": {
            "research_type": "exploratory_descriptive_mechanism_research",
            "alpha_claim": False,
            "candidate_created": False,
            "new_baseline_created": False,
            "v4_created": False,
            "training_run_executed": False,
            "backtest_run_executed": False,
            "portfolio_run_executed": False,
            "portfolio_dry_run_executed": False,
            "holdings_generated": False,
            "formal_metrics_generated": False,
            "frozen_test_accessed": False,
            "trainval_not_oos": True,
            "strategy_research_restarted": False,
            "p98_conditional_reference_only": True,
            "multi_equal_weight_v1_conditional_reference_only": True,
        },
        "fixed_rank_groups": RANK_GROUPS,
        "migration_note": MIGRATION_NOTE,
        "clean_model_keys": CLEAN_MODEL_KEYS,
        "rejected_comparator_keys": REJECTED_COMPARATOR_KEYS,
        "conditional_reference_keys": REFERENCE_KEYS,
        "common_topk_threshold_clean_models": COMMON_THRESHOLD,
        "used_exposure_fields": USED_EXPOSURE_FIELDS,
        "blocked_fields_used": sorted(BLOCKED_FIELDS & set(USED_EXPOSURE_FIELDS)),
        "model_metadata": model_metadata,
        "diagnostics": diagnostics,
        "stability": build_stability(master),
        "future_paper_only_hypotheses": [],
        "final_statement": (
            "exploratory descriptive research only; not alpha; not candidate; not portfolio; "
            "not OOS; no frozen test; agreement_count cannot form a trading rule"
        ),
    }
    payload["future_paper_only_hypotheses"] = build_hypotheses(payload)

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    args.output_md.write_text(build_markdown(payload), encoding="utf-8")
    return payload


def main() -> int:
    try:
        run(parse_args())
    except DiagnosisError as exc:
        print(f"ERROR: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
