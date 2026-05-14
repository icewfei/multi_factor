#!/usr/bin/env python3
"""
Build a descriptive full rank-band profile for existing clean scores.

This is exploratory descriptive research only. It does not claim alpha, create
candidates, train models, run backtests, run portfolio, generate holdings, or
read frozen test data.
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
DEFAULT_OUTPUT_JSON = Path("/private/tmp/rank_band_full_profile_descriptive_diagnosis.json")
DEFAULT_OUTPUT_MD = Path("/private/tmp/rank_band_full_profile_descriptive_diagnosis.md")

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
REFERENCE_KEYS = [P98, MULTI]
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

FIXED_RANK_BANDS: dict[str, dict[str, int | str]] = {
    "rank_1_30": {"rank_start": 1, "rank_end": 30, "label": "1-30"},
    "rank_31_60": {"rank_start": 31, "rank_end": 60, "label": "31-60"},
    "rank_31_100": {"rank_start": 31, "rank_end": 100, "label": "31-100"},
    "rank_31_200": {"rank_start": 31, "rank_end": 200, "label": "31-200"},
    "rank_101_300": {"rank_start": 101, "rank_end": 300, "label": "101-300"},
    "rank_301_600": {"rank_start": 301, "rank_end": 600, "label": "301-600"},
    "bottom_30": {"rank_start": "bottom_30", "rank_end": "bottom_1", "label": "bottom 30"},
}


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
    parser = argparse.ArgumentParser(description="Build rank-band full profile descriptive diagnosis.")
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


def quantile_float(series: pd.Series, q: float) -> float | None:
    clean = series.dropna()
    return safe_float(clean.quantile(q)) if not clean.empty else None


def summarize_distribution(frame: pd.DataFrame, column: str) -> dict[str, Any]:
    if column not in frame or frame[column].dropna().empty:
        return {"status": "unavailable"}
    counts = frame[column].fillna("missing").astype(str).value_counts()
    total = int(counts.sum())
    return {
        "status": "available",
        "rows": total,
        "distribution": [
            {"value": str(value), "count": int(count), "share": safe_float(count / total) if total else None}
            for value, count in counts.items()
        ],
    }


def summarize_bool(frame: pd.DataFrame, column: str) -> dict[str, Any]:
    if column not in frame or frame[column].dropna().empty:
        return {"status": "unavailable"}
    values = frame[column].fillna(False).astype(bool)
    return {"status": "available", "true_count": int(values.sum()), "true_share": safe_float(values.mean()), "rows": int(len(values))}


def build_specs(args: argparse.Namespace) -> dict[str, ModelSpec]:
    return {
        NO_P98: ModelSpec(NO_P98, NO_P98, args.no_p98_scores, -1, "clean_anchor", "no-p98 clean reversal"),
        LIQ: ModelSpec(LIQ, LIQ, args.liquidity_scores, -1, "clean_candidate", "liquidity-quality clean reversal"),
        COMP: ModelSpec(COMP, COMP, args.composite_scores, -1, "rejected_clean_candidate", "rejected clean composite"),
        LIMIT: ModelSpec(LIMIT, LIMIT, args.limit_aware_scores, -1, "clean_candidate", "limit-aware clean reversal"),
        BOARD: ModelSpec(BOARD, BOARD, args.board_neutral_scores, -1, "clean_candidate", "board-neutral clean reversal"),
        TRAD: ModelSpec(TRAD, TRAD, args.tradability_filtered_scores, -1, "clean_candidate", "tradability-filtered clean reversal"),
        LISTING: ModelSpec(LISTING, LISTING, args.listing_age_scores, -1, "clean_candidate", "listing-age-calendar clean reversal"),
        P98: ModelSpec(P98, "reversal_tail_exclude_p98_v1", args.p98_scores, 1, "conditional_reference_only", "p98 conditional reference"),
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


def assign_exposure_buckets(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    if "amount_percentile_asc" in work and not work["amount_percentile_asc"].dropna().empty:
        work["amount_bucket"] = pd.cut(
            work["amount_percentile_asc"],
            bins=[0.0, 0.2, 0.5, 0.8, 1.0],
            labels=["bottom_20pct", "20_50pct", "50_80pct", "top_20pct"],
            include_lowest=True,
        ).astype("object")
    else:
        work["amount_bucket"] = None
    if "listing_age_days" in work and not work["listing_age_days"].dropna().empty:
        work["listing_age_days_bucket"] = pd.cut(
            work["listing_age_days"],
            bins=[-math.inf, 120, 252, 756, math.inf],
            labels=["lt_120d", "120_252d", "252_756d", "gte_756d"],
        ).astype("object")
    else:
        work["listing_age_days_bucket"] = None
    return work


def select_band(ordered: pd.DataFrame, band_name: str, band_spec: dict[str, int | str]) -> pd.DataFrame:
    if band_name == "bottom_30":
        return ordered.tail(30).copy()
    start = int(band_spec["rank_start"])
    end = int(band_spec["rank_end"])
    return ordered.iloc[start - 1 : end].copy()


def daily_band_members(scored: pd.DataFrame, split: str, model_key: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    daily_rows: list[dict[str, Any]] = []
    member_rows: list[pd.DataFrame] = []
    scored = assign_exposure_buckets(scored)
    min_needed = max(int(v["rank_end"]) for k, v in FIXED_RANK_BANDS.items() if k != "bottom_30")
    for signal_date, day in scored.groupby("signal_date", sort=True):
        ordered = day.sort_values(["effective_score", "instrument"], ascending=[False, True]).reset_index(drop=True)
        if len(ordered) < min_needed:
            continue
        for band_name, band_spec in FIXED_RANK_BANDS.items():
            band = select_band(ordered, band_name, band_spec)
            if band.empty:
                continue
            band = band.assign(model_key=model_key, split=split, rank_band=band_name, daily_rank=band.index + 1)
            member_rows.append(band)
            daily_rows.append(
                {
                    "signal_date": str(signal_date),
                    "model_key": model_key,
                    "split": split,
                    "rank_band": band_name,
                    "band_label": band_spec["label"],
                    "n_members": int(len(band)),
                    "daily_band_return": safe_float(band["forward_return_5d"].mean()),
                    "daily_band_median": safe_float(band["forward_return_5d"].median()),
                }
            )
    daily = pd.DataFrame(daily_rows)
    members = pd.concat(member_rows, ignore_index=True) if member_rows else pd.DataFrame()
    return daily, members


def tail_contribution(member_returns: pd.Series) -> dict[str, Any]:
    returns = member_returns.dropna()
    if returns.empty:
        return {"best_5pct_contribution": None, "worst_5pct_damage": None}
    n = max(1, math.ceil(len(returns) * 0.05))
    total_positive = returns[returns > 0].sum()
    total_negative_abs = abs(returns[returns < 0].sum())
    best_sum = returns.sort_values(ascending=False).head(n).sum()
    worst_sum_abs = abs(returns.sort_values(ascending=True).head(n).sum())
    return {
        "best_5pct_contribution": safe_float(best_sum / total_positive) if total_positive != 0 else None,
        "worst_5pct_damage": safe_float(worst_sum_abs / total_negative_abs) if total_negative_abs != 0 else None,
    }


def exposure_profile(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {"status": "empty"}
    return {
        "amount_bucket": summarize_distribution(frame, "amount_bucket"),
        "board_type": summarize_distribution(frame, "board_type"),
        "exchange": summarize_distribution(frame, "exchange"),
        "limit_tradability": {
            "entry_buyable": summarize_bool(frame, "entry_buyable"),
            "is_suspended": summarize_bool(frame, "is_suspended"),
            "no_trade_flag": summarize_bool(frame, "no_trade_flag"),
            "volume_zero_flag": summarize_bool(frame, "volume_zero_flag"),
            "amount_zero_flag": summarize_bool(frame, "amount_zero_flag"),
            "is_limit_up": summarize_bool(frame, "is_limit_up"),
            "is_limit_down": summarize_bool(frame, "is_limit_down"),
            "open_at_up_limit": summarize_bool(frame, "open_at_up_limit"),
            "close_at_down_limit": summarize_bool(frame, "close_at_down_limit"),
        },
        "listing_age_days_bucket": summarize_distribution(frame, "listing_age_days_bucket"),
    }


def summarize_band(daily: pd.DataFrame, members: pd.DataFrame, band_name: str) -> dict[str, Any]:
    band_daily = daily[daily["rank_band"] == band_name]
    band_members = members[members["rank_band"] == band_name]
    daily_returns = band_daily["daily_band_return"].dropna() if not band_daily.empty else pd.Series(dtype=float)
    member_returns = band_members["forward_return_5d"].dropna() if not band_members.empty else pd.Series(dtype=float)
    yearly_mean: dict[str, float | None] = {}
    if not band_daily.empty:
        work = band_daily.copy()
        work["year"] = work["signal_date"].astype(str).str[:4]
        for year, group in work.groupby("year", sort=True):
            yearly_mean[str(year)] = safe_float(group["daily_band_return"].mean())
    payload = {
        "band_label": FIXED_RANK_BANDS[band_name]["label"],
        "rank_start": FIXED_RANK_BANDS[band_name]["rank_start"],
        "rank_end": FIXED_RANK_BANDS[band_name]["rank_end"],
        "n_days": int(len(daily_returns)),
        "n_member_rows": int(len(member_returns)),
        "mean": safe_float(daily_returns.mean()) if not daily_returns.empty else None,
        "median": safe_float(daily_returns.median()) if not daily_returns.empty else None,
        "volatility": safe_float(daily_returns.std()) if not daily_returns.empty else None,
        "daily_win_rate_vs_0": safe_float((daily_returns > 0).mean()) if not daily_returns.empty else None,
        "yearly_mean": yearly_mean,
        "member_mean": safe_float(member_returns.mean()) if not member_returns.empty else None,
        "member_median": safe_float(member_returns.median()) if not member_returns.empty else None,
        "member_p05": quantile_float(member_returns, 0.05),
        "member_p95": quantile_float(member_returns, 0.95),
        **tail_contribution(member_returns),
        "exposure": exposure_profile(band_members),
    }
    return payload


def infer_shape(bands: dict[str, Any]) -> dict[str, Any]:
    means = {name: data.get("mean") for name, data in bands.items()}
    head = means.get("rank_1_30")
    nextk = means.get("rank_31_60")
    mid100 = means.get("rank_31_100")
    mid200 = means.get("rank_31_200")
    tail = means.get("bottom_30")
    ordered_names = ["rank_1_30", "rank_31_60", "rank_101_300", "rank_301_600", "bottom_30"]
    ordered_values = [means.get(name) for name in ordered_names if means.get(name) is not None]
    monotonic_nonincreasing = all(ordered_values[i] >= ordered_values[i + 1] for i in range(len(ordered_values) - 1)) if len(ordered_values) >= 2 else None
    return {
        "head_failure": bool(head is not None and ((nextk is not None and head < nextk) or (mid100 is not None and head < mid100))),
        "mid_rank_strength": bool(head is not None and ((mid100 is not None and mid100 > head) or (mid200 is not None and mid200 > head))),
        "tail_separation": bool(tail is not None and head is not None and tail < head),
        "monotonicity": "monotonic_nonincreasing" if monotonic_nonincreasing else "non_monotonic",
        "band_means": means,
    }


def diagnose_model_split(frame: pd.DataFrame, split: str, model_key: str) -> dict[str, Any]:
    scored = frame.dropna(subset=["effective_score", "forward_return_5d"]).copy()
    if scored.empty:
        return {"status": "empty"}
    daily, members = daily_band_members(scored, split, model_key)
    band_profiles = {band_name: summarize_band(daily, members, band_name) for band_name in FIXED_RANK_BANDS}
    return {
        "status": "ok",
        "band_profiles": band_profiles,
        "band_profile_shape": infer_shape(band_profiles),
    }


def diagnose_models(con: duckdb.DuckDBPyConnection, specs: dict[str, ModelSpec]) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {}
    for spec in specs.values():
        frame = fetch_model_frame(con, spec)
        diagnostics[spec.key] = {
            "candidate_scheme_id": spec.candidate_scheme_id,
            "status": spec.status,
            "label": spec.label,
            "train": diagnose_model_split(frame[frame["train_flag"]], "train", spec.key),
            "validation": diagnose_model_split(frame[frame["validation_flag"]], "validation", spec.key),
        }
    return diagnostics


def build_cross_model_summary(diagnostics: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for split in ["train", "validation"]:
        split_summary: dict[str, Any] = {}
        for band_name in FIXED_RANK_BANDS:
            clean_means = []
            for model in CLEAN_MODEL_KEYS:
                mean = diagnostics[model][split].get("band_profiles", {}).get(band_name, {}).get("mean")
                if mean is not None:
                    clean_means.append(mean)
            split_summary[band_name] = {
                "clean_model_mean_of_means": safe_float(pd.Series(clean_means).mean()) if clean_means else None,
                "n_clean_models": len(clean_means),
            }
        shape_counts = {"head_failure": 0, "mid_rank_strength": 0, "tail_separation": 0, "non_monotonic": 0}
        for model in CLEAN_MODEL_KEYS:
            shape = diagnostics[model][split].get("band_profile_shape", {})
            if shape.get("head_failure"):
                shape_counts["head_failure"] += 1
            if shape.get("mid_rank_strength"):
                shape_counts["mid_rank_strength"] += 1
            if shape.get("tail_separation"):
                shape_counts["tail_separation"] += 1
            if shape.get("monotonicity") == "non_monotonic":
                shape_counts["non_monotonic"] += 1
        summary[split] = {"band_summary": split_summary, "shape_counts_clean_models": shape_counts}
    return summary


def build_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Rank-Band Full Profile Descriptive Diagnosis",
        "",
        "This is descriptive-only trainval diagnosis. It is not OOS, not alpha, not a candidate, not portfolio, not backtest, and frozen test remains unread.",
        "",
        "## Boundary",
        "",
        "- no alpha claim",
        "- no candidate",
        "- no portfolio",
        "- no frozen test",
        "- trainval not OOS",
        "- p98 / multi_equal_weight_v1 conditional reference only",
        "",
        "## Fixed Rank Bands",
        "",
    ]
    for band_name, spec in payload["fixed_rank_bands"].items():
        lines.append(f"- `{band_name}`: {spec['label']}")
    lines.extend(["", "## Validation Profile Snapshot", ""])
    for model in CLEAN_MODEL_KEYS:
        model_data = payload["diagnostics"][model]
        lines.append(f"### {model}")
        lines.append(f"status: `{model_data['status']}`")
        shape = model_data["validation"].get("band_profile_shape", {})
        lines.append(f"- head_failure: `{shape.get('head_failure')}`")
        lines.append(f"- mid_rank_strength: `{shape.get('mid_rank_strength')}`")
        lines.append(f"- tail_separation: `{shape.get('tail_separation')}`")
        lines.append(f"- monotonicity: `{shape.get('monotonicity')}`")
        for band_name in FIXED_RANK_BANDS:
            band = model_data["validation"].get("band_profiles", {}).get(band_name, {})
            lines.append(
                f"- `{band_name}` mean `{band.get('mean')}`, median `{band.get('median')}`, "
                f"vol `{band.get('volatility')}`, win_vs_0 `{band.get('daily_win_rate_vs_0')}`"
            )
        lines.append("")
    lines.extend(
        [
            "## Conditional References",
            "",
            "- `p98_conditional_reference`: conditional reference only",
            "- `multi_equal_weight_v1_conditional_reference`: conditional reference only",
            "",
            "## Final Statement",
            "",
            "This output is descriptive only. It gives no deployment conclusion and no portfolio recommendation.",
        ]
    )
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
    specs = build_specs(args)
    con = duckdb.connect()
    try:
        register_views(con, args, specs)
        diagnostics = diagnose_models(con, specs)
    finally:
        con.close()
    payload = {
        "diagnosis_name": "rank_band_full_profile_descriptive_diagnosis",
        "diagnosis_label": "DESCRIPTIVE_ONLY_TRAINVAL_NOT_OOS_NOT_PORTFOLIO",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "governance": {
            "research_type": "exploratory_descriptive_mechanism_research",
            "alpha_claim": False,
            "candidate_created": False,
            "portfolio_run_executed": False,
            "portfolio_recommendation": False,
            "frozen_test_accessed": False,
            "training_run_executed": False,
            "backtest_run_executed": False,
            "holdings_generated": False,
            "formal_metrics_generated": False,
            "trainval_not_oos": True,
            "p98_conditional_reference_only": True,
            "multi_equal_weight_v1_conditional_reference_only": True,
        },
        "fixed_rank_bands": FIXED_RANK_BANDS,
        "clean_model_keys": CLEAN_MODEL_KEYS,
        "conditional_reference_keys": REFERENCE_KEYS,
        "used_exposure_fields": USED_EXPOSURE_FIELDS,
        "blocked_fields_used": sorted(BLOCKED_FIELDS & set(USED_EXPOSURE_FIELDS)),
        "diagnostics": diagnostics,
        "cross_model_summary": build_cross_model_summary(diagnostics),
        "final_statement": "descriptive only; no deployment conclusion; no portfolio recommendation",
    }
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
