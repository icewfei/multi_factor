#!/usr/bin/env python3
"""
Diagnose cross-model clean TopK selection failure.

This is train/validation diagnosis only. It does not create candidates, tune
parameters, train, run portfolio/backtest, generate holdings/readouts, or read
frozen test data.
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
DEFAULT_P98_SCORES = ROOT / "artifacts" / "run_state" / "confirmatory_reversal_p98_trainval_20260506" / "model_scores_D0.parquet"
DEFAULT_MULTI_EQUAL_SCORES = ROOT / "artifacts" / "run_state" / "exploratory_multi_signal_composite_v1" / "model_scores_D0_multi.parquet"
DEFAULT_EXPOSURE_PANEL = DEFAULT_LIQUIDITY_SCORES
DEFAULT_OUTPUT_JSON = Path("/private/tmp/clean_topk_selection_failure_diagnosis.json")
DEFAULT_OUTPUT_MD = Path("/private/tmp/clean_topk_selection_failure_diagnosis.md")

NO_P98 = "no_p98_reversal_baseline_v1"
LIQ = "clean_reversal_5d_liquidity_quality_v1"
COMP = "clean_composite_reversal_tradability_v1"
LIMIT = "clean_reversal_5d_limit_aware_v1"
BOARD = "clean_reversal_5d_board_neutral_v1"
TRAD = "clean_reversal_5d_tradability_filtered_v1"
P98 = "p98_conditional_reference"
MULTI = "multi_equal_weight_v1_conditional_reference"
CLEAN_MODEL_KEYS = [NO_P98, LIQ, COMP, LIMIT, BOARD, TRAD]
BLOCKED_FIELDS = {"listing_age_trading_days", "newly_listed_flag"}
USED_EXPOSURE_FIELDS = [
    "snapshot_id",
    "instrument",
    "signal_date",
    "reversal_5d_raw",
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
    parser = argparse.ArgumentParser(description="Diagnose clean TopK selection failure.")
    parser.add_argument("--label-panel", type=Path, default=DEFAULT_LABEL_PANEL)
    parser.add_argument("--split-panel", type=Path, default=DEFAULT_SPLIT_PANEL)
    parser.add_argument("--no-p98-scores", type=Path, default=DEFAULT_NO_P98_SCORES)
    parser.add_argument("--liquidity-scores", type=Path, default=DEFAULT_LIQUIDITY_SCORES)
    parser.add_argument("--composite-scores", type=Path, default=DEFAULT_COMPOSITE_SCORES)
    parser.add_argument("--limit-aware-scores", type=Path, default=DEFAULT_LIMIT_AWARE_SCORES)
    parser.add_argument("--board-neutral-scores", type=Path, default=DEFAULT_BOARD_NEUTRAL_SCORES)
    parser.add_argument("--tradability-filtered-scores", type=Path, default=DEFAULT_TRADABILITY_FILTERED_SCORES)
    parser.add_argument("--p98-scores", type=Path, default=DEFAULT_P98_SCORES)
    parser.add_argument("--multi-equal-scores", type=Path, default=DEFAULT_MULTI_EQUAL_SCORES)
    parser.add_argument("--exposure-panel", type=Path, default=DEFAULT_EXPOSURE_PANEL)
    parser.add_argument("--topk", type=int, default=30)
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
            e.reversal_5d_raw,
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


def top_structures(scored: pd.DataFrame, topk: int, split: str, model_key: str) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    daily_rows: list[dict[str, Any]] = []
    member_rows: list[pd.DataFrame] = []
    scored = assign_amount_bucket(scored)
    for signal_date, day in scored.groupby("signal_date", sort=True):
        ordered = day.sort_values(["effective_score", "instrument"], ascending=[False, True]).reset_index(drop=True)
        if len(ordered) < topk:
            continue
        top = ordered.iloc[:topk].copy()
        nextk = ordered.iloc[topk : topk * 2].copy()
        rank31_100 = ordered.iloc[topk : min(100, len(ordered))].copy()
        for bucket, bucket_frame in [("topk", top), ("nextk", nextk), ("rank31_100", rank31_100)]:
            if bucket_frame.empty:
                continue
            bucket_frame = bucket_frame.assign(
                model_key=model_key,
                split=split,
                rank_bucket=bucket,
                rank_position=range(1, len(bucket_frame) + 1),
            )
            member_rows.append(bucket_frame)
        top_mean = safe_float(top["forward_return_5d"].mean())
        next_mean = safe_float(nextk["forward_return_5d"].mean()) if not nextk.empty else None
        r100_mean = safe_float(rank31_100["forward_return_5d"].mean()) if not rank31_100.empty else None
        daily_rows.append(
            {
                "signal_date": str(signal_date),
                "topk_mean": top_mean,
                "topk_median": safe_float(top["forward_return_5d"].median()),
                "nextk_mean": next_mean,
                "nextk_median": safe_float(nextk["forward_return_5d"].median()) if not nextk.empty else None,
                "rank31_100_mean": r100_mean,
                "rank31_100_median": safe_float(rank31_100["forward_return_5d"].median()) if not rank31_100.empty else None,
                "topk_minus_nextk": top_mean - next_mean if top_mean is not None and next_mean is not None else None,
                "topk_minus_rank31_100": top_mean - r100_mean if top_mean is not None and r100_mean is not None else None,
                "topk_win_nextk": top_mean > next_mean if top_mean is not None and next_mean is not None else None,
                "topk_win_rank31_100": top_mean > r100_mean if top_mean is not None and r100_mean is not None else None,
            }
        )
    daily = pd.DataFrame(daily_rows)
    members = pd.concat(member_rows, ignore_index=True) if member_rows else pd.DataFrame()
    if daily.empty:
        return {}, daily, members
    return {
        "topk_mean": safe_float(daily["topk_mean"].mean()),
        "topk_median": safe_float(daily["topk_median"].mean()),
        "nextk_mean": safe_float(daily["nextk_mean"].mean()),
        "nextk_median": safe_float(daily["nextk_median"].mean()),
        "rank31_100_mean": safe_float(daily["rank31_100_mean"].mean()),
        "rank31_100_median": safe_float(daily["rank31_100_median"].mean()),
        "topk_minus_nextk": safe_float(daily["topk_minus_nextk"].mean()),
        "topk_minus_rank31_100": safe_float(daily["topk_minus_rank31_100"].mean()),
        "topk_daily_win_rate_vs_nextk": safe_float(pd.Series(daily["topk_win_nextk"]).dropna().astype(bool).mean()),
        "topk_daily_win_rate_vs_rank31_100": safe_float(pd.Series(daily["topk_win_rank31_100"]).dropna().astype(bool).mean()),
        "n_days": int(len(daily)),
    }, daily, members


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


def exposure_payload(frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "amount_bucket_distribution": summarize_bucket(frame, "amount_bucket"),
        "board_type": summarize_bucket(frame, "board_type"),
        "exchange": summarize_bucket(frame, "exchange"),
        "entry_buyable": summarize_bool(frame, "entry_buyable"),
        "no_trade_flag": summarize_bool(frame, "no_trade_flag"),
        "is_suspended": summarize_bool(frame, "is_suspended"),
        "is_limit_up": summarize_bool(frame, "is_limit_up"),
        "is_limit_down": summarize_bool(frame, "is_limit_down"),
        "open_at_up_limit": summarize_bool(frame, "open_at_up_limit"),
        "close_at_down_limit": summarize_bool(frame, "close_at_down_limit"),
        "mean_return": safe_float(frame["forward_return_5d"].mean()) if not frame.empty else None,
    }


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


def extremeness_payload(top_frame: pd.DataFrame, next_frame: pd.DataFrame) -> dict[str, Any]:
    if top_frame.empty or next_frame.empty:
        return {}
    top_abs = top_frame["reversal_5d_raw"].abs()
    next_abs = next_frame["reversal_5d_raw"].abs()
    return {
        "topk_score_dispersion": {
            "std": safe_float(top_frame["effective_score"].std()),
            "iqr": safe_float(top_frame["effective_score"].quantile(0.75) - top_frame["effective_score"].quantile(0.25)),
        },
        "nextk_score_dispersion": {
            "std": safe_float(next_frame["effective_score"].std()),
            "iqr": safe_float(next_frame["effective_score"].quantile(0.75) - next_frame["effective_score"].quantile(0.25)),
        },
        "topk_reversal_5d_raw_extremeness": summarize_series(top_abs),
        "nextk_reversal_5d_raw_extremeness": summarize_series(next_abs),
        "topk_more_extreme_than_nextk": safe_float(top_abs.mean()) > safe_float(next_abs.mean()),
        "extreme_reversal_bucket_return": safe_float(top_frame.loc[top_abs >= top_abs.quantile(0.8), "forward_return_5d"].mean()) if not top_abs.dropna().empty else None,
        "non_extreme_head_bucket_return": safe_float(top_frame.loc[top_abs < top_abs.quantile(0.8), "forward_return_5d"].mean()) if not top_abs.dropna().empty else None,
    }


def yearly_direction(daily: pd.DataFrame) -> dict[str, Any]:
    if daily.empty:
        return {}
    work = daily.copy()
    work["year"] = work["signal_date"].astype(str).str[:4]
    by_year = {}
    for year, group in work.groupby("year", sort=True):
        by_year[str(year)] = {
            "topk_minus_nextk_mean": safe_float(group["topk_minus_nextk"].mean()),
            "topk_minus_rank31_100_mean": safe_float(group["topk_minus_rank31_100"].mean()),
        }
    return by_year


def diagnose_model_split(frame: pd.DataFrame, topk: int, split: str, model_key: str) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    scored = frame.dropna(subset=["effective_score", "forward_return_5d"]).copy()
    if scored.empty:
        return {}, pd.DataFrame(), pd.DataFrame()
    scored = assign_amount_bucket(scored)
    structure, daily, members = top_structures(scored, topk, split, model_key)
    top = members[members["rank_bucket"] == "topk"] if not members.empty else pd.DataFrame()
    nextk = members[members["rank_bucket"] == "nextk"] if not members.empty else pd.DataFrame()
    rank31_100 = members[members["rank_bucket"] == "rank31_100"] if not members.empty else pd.DataFrame()
    board_level = {}
    if not top.empty and not nextk.empty and "board_type" in top and "board_type" in nextk:
        for board in sorted(set(top["board_type"].dropna()) | set(nextk["board_type"].dropna())):
            t = top[top["board_type"] == board]["forward_return_5d"]
            n = nextk[nextk["board_type"] == board]["forward_return_5d"]
            board_level[str(board)] = delta(safe_float(t.mean()), safe_float(n.mean()))
    return {
        "per_model_topk_structure": structure,
        "yearly_stability": yearly_direction(daily),
        "extremeness_decomposition": extremeness_payload(top, nextk),
        "liquidity_tradability_exposure": {
            "topk": exposure_payload(top),
            "nextk": exposure_payload(nextk),
            "rank31_100": exposure_payload(rank31_100),
            "high_liquidity_topk_return_vs_mid_liquidity_nextk_return": delta(
                safe_float(top.loc[top["amount_bucket"] == "top_20pct", "forward_return_5d"].mean()) if "amount_bucket" in top else None,
                safe_float(nextk.loc[nextk["amount_bucket"].isin(["20_50pct", "50_80pct"]), "forward_return_5d"].mean()) if "amount_bucket" in nextk else None,
            ),
        },
        "board_exchange_exposure": {
            "topk": {"board_type": summarize_bucket(top, "board_type"), "exchange": summarize_bucket(top, "exchange")},
            "nextk": {"board_type": summarize_bucket(nextk, "board_type"), "exchange": summarize_bucket(nextk, "exchange")},
            "board_level_topk_minus_nextk": board_level if board_level else {"status": "unavailable"},
        },
        "winner_loser_contribution": {
            "topk": winner_loser_contribution(top),
            "nextk": winner_loser_contribution(nextk),
            "topk_failure_more_large_losers_than_nextk": (
                (winner_loser_contribution(top).get("worst_5pct_losers_contribution") or 0.0)
                > (winner_loser_contribution(nextk).get("worst_5pct_losers_contribution") or 0.0)
            ),
            "topk_failure_fewer_large_winners_than_nextk": (
                (winner_loser_contribution(top).get("top_5pct_winners_contribution") or 0.0)
                < (winner_loser_contribution(nextk).get("top_5pct_winners_contribution") or 0.0)
            ),
        },
    }, daily, members


def delta(a: float | None, b: float | None) -> float | None:
    return a - b if a is not None and b is not None else None


def diagnose_models(con: duckdb.DuckDBPyConnection, specs: dict[str, ModelSpec], topk: int) -> tuple[dict[str, Any], dict[str, pd.DataFrame], pd.DataFrame]:
    diagnostics: dict[str, Any] = {}
    daily_map: dict[str, pd.DataFrame] = {}
    members_list: list[pd.DataFrame] = []
    for spec in specs.values():
        frame = fetch_model_frame(con, spec)
        splits = {}
        for split, mask in [("train", frame["train_flag"]), ("validation", frame["validation_flag"])]:
            payload, daily, members = diagnose_model_split(frame[mask], topk, split, spec.key)
            splits[split] = payload
            daily_map[f"{spec.key}:{split}"] = daily
            members_list.append(members)
        diagnostics[spec.key] = {"candidate_scheme_id": spec.candidate_scheme_id, "status": spec.status, "label": spec.label, **splits}
    members = pd.concat(members_list, ignore_index=True) if members_list else pd.DataFrame()
    return diagnostics, daily_map, members


def build_common_failure(diagnostics: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for split in ["train", "validation"]:
        topk_lt_nextk = []
        topk_lt_rank31_100 = []
        for model in CLEAN_MODEL_KEYS:
            structure = diagnostics[model][split]["per_model_topk_structure"]
            if not structure:
                continue
            if structure["topk_minus_nextk"] is not None and structure["topk_minus_nextk"] < 0:
                topk_lt_nextk.append(model)
            if structure["topk_minus_rank31_100"] is not None and structure["topk_minus_rank31_100"] < 0:
                topk_lt_rank31_100.append(model)
        result[split] = {
            "n_clean_models_topk_lt_nextk": len(topk_lt_nextk),
            "models_topk_lt_nextk": topk_lt_nextk,
            "n_clean_models_topk_lt_rank31_100": len(topk_lt_rank31_100),
            "models_topk_lt_rank31_100": topk_lt_rank31_100,
        }
    per_model = {}
    for model in CLEAN_MODEL_KEYS:
        train = diagnostics[model]["train"]["per_model_topk_structure"]
        val = diagnostics[model]["validation"]["per_model_topk_structure"]
        yearly = diagnostics[model]["validation"]["yearly_stability"]
        per_model[model] = {
            "train_validation_topk_lt_nextk_same_direction": bool(train and val and train["topk_minus_nextk"] < 0 and val["topk_minus_nextk"] < 0),
            "train_validation_topk_lt_rank31_100_same_direction": bool(train and val and train["topk_minus_rank31_100"] < 0 and val["topk_minus_rank31_100"] < 0),
            "validation_yearly_topk_lt_nextk_same_direction": bool(yearly) and all((row["topk_minus_nextk_mean"] or 0.0) < 0 for row in yearly.values()),
            "validation_yearly_topk_lt_rank31_100_same_direction": bool(yearly) and all((row["topk_minus_rank31_100_mean"] or 0.0) < 0 for row in yearly.values()),
        }
    result["per_model_direction_consistency"] = per_model
    return result


def build_overlap_divergence(members: pd.DataFrame) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for split in ["train", "validation"]:
        split_members = members[members["split"] == split]
        daily_common_topk = []
        daily_common_losers = []
        daily_common_nextk_winners = []
        daily_common_rank31_100_winners = []
        per_model_only = {model: [] for model in CLEAN_MODEL_KEYS}
        p98_overlap = {model: [] for model in CLEAN_MODEL_KEYS}
        for signal_date in sorted(set(split_members["signal_date"])):
            day = split_members[split_members["signal_date"] == signal_date]
            top_sets = {}
            nextk_sets = {}
            r100_sets = {}
            returns_map = {}
            for model in CLEAN_MODEL_KEYS + [P98]:
                model_day = day[(day["model_key"] == model)]
                top_day = model_day[model_day["rank_bucket"] == "topk"]
                next_day = model_day[model_day["rank_bucket"] == "nextk"]
                r100_day = model_day[model_day["rank_bucket"] == "rank31_100"]
                top_sets[model] = set(top_day["instrument"])
                nextk_sets[model] = set(next_day["instrument"])
                r100_sets[model] = set(r100_day["instrument"])
                returns_map[model] = dict(zip(top_day["instrument"], top_day["forward_return_5d"]))
            common_topk = set.intersection(*[top_sets[m] for m in CLEAN_MODEL_KEYS]) if all(m in top_sets for m in CLEAN_MODEL_KEYS) else set()
            common_nextk = set.intersection(*[nextk_sets[m] for m in CLEAN_MODEL_KEYS]) if all(m in nextk_sets for m in CLEAN_MODEL_KEYS) else set()
            common_r100 = set.intersection(*[r100_sets[m] for m in CLEAN_MODEL_KEYS]) if all(m in r100_sets for m in CLEAN_MODEL_KEYS) else set()
            common_topk_returns = [returns_map[CLEAN_MODEL_KEYS[0]][name] for name in common_topk if name in returns_map[CLEAN_MODEL_KEYS[0]]]
            daily_common_topk.append({"signal_date": str(signal_date), "common_topk_count": len(common_topk), "common_topk_mean_return": safe_float(pd.Series(common_topk_returns).mean()) if common_topk_returns else None})
            common_losers = [x for x in common_topk_returns if x < 0]
            daily_common_losers.append({"signal_date": str(signal_date), "common_topk_loser_count": len(common_losers), "common_topk_loser_mean": safe_float(pd.Series(common_losers).mean()) if common_losers else None})
            nextk_winner_vals = []
            for name in common_nextk:
                vals = []
                for model in CLEAN_MODEL_KEYS:
                    md = day[(day["model_key"] == model) & (day["rank_bucket"] == "nextk") & (day["instrument"] == name)]["forward_return_5d"]
                    if not md.empty:
                        vals.append(float(md.iloc[0]))
                if vals and min(vals) > 0:
                    nextk_winner_vals.extend(vals)
            daily_common_nextk_winners.append({"signal_date": str(signal_date), "common_nextk_winner_count": len(nextk_winner_vals), "common_nextk_winner_mean": safe_float(pd.Series(nextk_winner_vals).mean()) if nextk_winner_vals else None})
            r100_winner_vals = []
            for name in common_r100:
                vals = []
                for model in CLEAN_MODEL_KEYS:
                    md = day[(day["model_key"] == model) & (day["rank_bucket"] == "rank31_100") & (day["instrument"] == name)]["forward_return_5d"]
                    if not md.empty:
                        vals.append(float(md.iloc[0]))
                if vals and min(vals) > 0:
                    r100_winner_vals.extend(vals)
            daily_common_rank31_100_winners.append({"signal_date": str(signal_date), "common_rank31_100_winner_count": len(r100_winner_vals), "common_rank31_100_winner_mean": safe_float(pd.Series(r100_winner_vals).mean()) if r100_winner_vals else None})
            clean_union = {m: set.union(*[top_sets[x] for x in CLEAN_MODEL_KEYS if x != m]) for m in CLEAN_MODEL_KEYS}
            for model in CLEAN_MODEL_KEYS:
                only_names = top_sets[model] - clean_union[model]
                only_returns = [returns_map[model][x] for x in only_names if x in returns_map[model]]
                per_model_only[model].append({"signal_date": str(signal_date), "only_count": len(only_names), "only_mean_return": safe_float(pd.Series(only_returns).mean()) if only_returns else None})
                overlap = top_sets[model] & top_sets[P98]
                union = top_sets[model] | top_sets[P98]
                p98_overlap[model].append({"signal_date": str(signal_date), "overlap_count": len(overlap), "jaccard": len(overlap) / len(union) if union else None})
        result[split] = {
            "common_topk_across_clean_models": {
                "mean_count": safe_float(pd.DataFrame(daily_common_topk)["common_topk_count"].mean()) if daily_common_topk else None,
                "mean_return": safe_float(pd.DataFrame(daily_common_topk)["common_topk_mean_return"].mean()) if daily_common_topk else None,
            },
            "model_specific_topk_only_names": {model: {"mean_only_count": safe_float(pd.DataFrame(rows)["only_count"].mean()) if rows else None, "mean_only_return": safe_float(pd.DataFrame(rows)["only_mean_return"].mean()) if rows else None} for model, rows in per_model_only.items()},
            "common_losers_across_clean_topks": {
                "mean_count": safe_float(pd.DataFrame(daily_common_losers)["common_topk_loser_count"].mean()) if daily_common_losers else None,
                "mean_return": safe_float(pd.DataFrame(daily_common_losers)["common_topk_loser_mean"].mean()) if daily_common_losers else None,
            },
            "common_winners_in_nextk": {
                "mean_count": safe_float(pd.DataFrame(daily_common_nextk_winners)["common_nextk_winner_count"].mean()) if daily_common_nextk_winners else None,
                "mean_return": safe_float(pd.DataFrame(daily_common_nextk_winners)["common_nextk_winner_mean"].mean()) if daily_common_nextk_winners else None,
            },
            "common_winners_in_rank31_100": {
                "mean_count": safe_float(pd.DataFrame(daily_common_rank31_100_winners)["common_rank31_100_winner_count"].mean()) if daily_common_rank31_100_winners else None,
                "mean_return": safe_float(pd.DataFrame(daily_common_rank31_100_winners)["common_rank31_100_winner_mean"].mean()) if daily_common_rank31_100_winners else None,
            },
            "overlap_with_p98_conditional_reference": {
                "reference_status": "conditional_reference_only",
                **{model: {"mean_overlap_count": safe_float(pd.DataFrame(rows)["overlap_count"].mean()) if rows else None, "mean_jaccard": safe_float(pd.DataFrame(rows)["jaccard"].mean()) if rows else None} for model, rows in p98_overlap.items()},
            },
        }
    return result


def condition_mask(frame: pd.DataFrame, condition_id: str) -> pd.Series:
    if condition_id == "high_liquidity":
        return frame["amount_percentile_asc"] >= 0.8
    if condition_id == "limit_down_like":
        return frame["is_limit_down"].fillna(False) | frame["close_at_down_limit"].fillna(False)
    if condition_id == "state_anomaly":
        return (
            frame["no_trade_flag"].fillna(False)
            | frame["is_suspended"].fillna(False)
            | frame["amount_zero_flag"].fillna(False)
            | frame["volume_zero_flag"].fillna(False)
            | (~frame["entry_buyable"].fillna(True))
        )
    raise KeyError(condition_id)


def evaluate_head_exclusion_evidence(members: pd.DataFrame) -> dict[str, Any]:
    candidate_conditions = ["high_liquidity", "limit_down_like", "state_anomaly"]
    evaluations = {}
    sufficient = []
    for condition_id in candidate_conditions:
        per_model = {}
        all_clean_pass = True
        for model in CLEAN_MODEL_KEYS:
            model_members = members[members["model_key"] == model]
            split_eval = {}
            for split in ["train", "validation"]:
                split_members = model_members[model_members["split"] == split]
                top = split_members[split_members["rank_bucket"] == "topk"]
                nextk = split_members[split_members["rank_bucket"] == "nextk"]
                if top.empty or nextk.empty:
                    split_eval[split] = {"top_minus_next": None}
                    all_clean_pass = False
                    continue
                top_mask = condition_mask(top, condition_id)
                next_mask = condition_mask(nextk, condition_id)
                top_mean = safe_float(top.loc[top_mask, "forward_return_5d"].mean()) if top_mask.any() else None
                next_mean = safe_float(nextk.loc[next_mask, "forward_return_5d"].mean()) if next_mask.any() else None
                split_eval[split] = {"top_minus_next": delta(top_mean, next_mean)}
                if split_eval[split]["top_minus_next"] is None or split_eval[split]["top_minus_next"] >= 0:
                    all_clean_pass = False
            yearly_rows = []
            val_members = model_members[model_members["split"] == "validation"]
            if not val_members.empty:
                for year, year_frame in val_members.groupby(val_members["signal_date"].astype(str).str[:4]):
                    top = year_frame[year_frame["rank_bucket"] == "topk"]
                    nextk = year_frame[year_frame["rank_bucket"] == "nextk"]
                    top_mask = condition_mask(top, condition_id) if not top.empty else pd.Series(dtype=bool)
                    next_mask = condition_mask(nextk, condition_id) if not nextk.empty else pd.Series(dtype=bool)
                    top_mean = safe_float(top.loc[top_mask, "forward_return_5d"].mean()) if not top.empty and top_mask.any() else None
                    next_mean = safe_float(nextk.loc[next_mask, "forward_return_5d"].mean()) if not nextk.empty and next_mask.any() else None
                    yearly_rows.append({"year": str(year), "top_minus_next": delta(top_mean, next_mean)})
                    if yearly_rows[-1]["top_minus_next"] is None or yearly_rows[-1]["top_minus_next"] >= 0:
                        all_clean_pass = False
            per_model[model] = {"splits": split_eval, "validation_yearly": yearly_rows}
        status = "sufficient" if all_clean_pass else "insufficient"
        evaluations[condition_id] = {"status": status, "per_model": per_model}
        if all_clean_pass:
            sufficient.append(condition_id)
    return {
        "status": "sufficient" if sufficient else "insufficient",
        "sufficient_conditions": sufficient,
        "evaluations": evaluations,
    }


def build_decision_summary(payload: dict[str, Any]) -> dict[str, Any]:
    validation = payload["cross_model_common_failure"]["validation"]
    common_all = (
        validation["n_clean_models_topk_lt_nextk"] == len(CLEAN_MODEL_KEYS)
        and validation["n_clean_models_topk_lt_rank31_100"] == len(CLEAN_MODEL_KEYS)
    )
    stable = all(
        item["train_validation_topk_lt_nextk_same_direction"]
        and item["validation_yearly_topk_lt_nextk_same_direction"]
        and item["train_validation_topk_lt_rank31_100_same_direction"]
        and item["validation_yearly_topk_lt_rank31_100_same_direction"]
        for item in payload["cross_model_common_failure"]["per_model_direction_consistency"].values()
    )
    head_evidence = payload["head_exclusion_evidence"]["status"] == "sufficient"
    recommend = bool(common_all and stable and head_evidence)
    return {
        "topk_selection_failure_common_across_clean_models": common_all,
        "topk_selection_failure_train_validation_yearly_stable": stable,
        "stable_d0_visible_head_exclusion_evidence_exists": head_evidence,
        "recommend_next_preregistered_head_exclusion_candidate_design": recommend,
        "recommend_portfolio_dry_run": False,
        "continue_portfolio_ban": True,
        "frozen_test_accessed": False,
        "training_backtest_or_portfolio_run": False,
        "interpretation": (
            "Do not open a head-exclusion candidate from this evidence."
            if not recommend
            else "May consider a separately preregistered head-exclusion candidate design; no portfolio in this round."
        ),
    }


def build_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Clean TopK Selection Failure Diagnosis",
        "",
        "Train/validation diagnosis only. Not OOS, not strategy approval, not portfolio, not backtest, not formal metrics/readout, and frozen test remains unread.",
        "",
        "## Cross-Model Failure",
        "",
    ]
    for split in ["train", "validation"]:
        section = payload["cross_model_common_failure"][split]
        lines.append(
            f"- `{split}`: TopK<nextK `{section['n_clean_models_topk_lt_nextk']}` / {len(CLEAN_MODEL_KEYS)}, "
            f"TopK<rank31_100 `{section['n_clean_models_topk_lt_rank31_100']}` / {len(CLEAN_MODEL_KEYS)}"
        )
    lines.extend(
        [
            "",
            "## Head-Exclusion Evidence",
            "",
            f"- status: `{payload['head_exclusion_evidence']['status']}`",
            f"- sufficient conditions: `{payload['head_exclusion_evidence']['sufficient_conditions']}`",
            "",
            "## Decision Summary",
            "",
        ]
    )
    for key, value in payload["decision_summary"].items():
        lines.append(f"- {key}: `{value}`")
    return "\n".join(lines) + "\n"


def run_diagnosis(args: argparse.Namespace) -> dict[str, Any]:
    if args.topk <= 0:
        raise DiagnosisError("--topk must be positive")
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
        diagnostics, _, members = diagnose_models(con, specs, args.topk)
        payload = {
            "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "round_id": "clean_topk_selection_failure_diagnosis_round_v1",
            "diagnosis_label": "TRAINVAL_DIAGNOSIS_ONLY_NOT_OOS_NOT_PORTFOLIO",
            "training_performed": False,
            "backtest_run_executed": False,
            "portfolio_run_executed": False,
            "holdings_generated": False,
            "formal_metrics_generated": False,
            "frozen_test_accessed": False,
            "p98_reference_status": "conditional_reference_only",
            "multi_equal_weight_v1_reference_status": "conditional_reference_only",
            "blocked_fields": sorted(BLOCKED_FIELDS),
            "blocked_fields_used": [],
            "used_exposure_fields": USED_EXPOSURE_FIELDS,
            "topk": args.topk,
            "diagnostics": diagnostics,
            "cross_model_common_failure": build_common_failure(diagnostics),
            "overlap_divergence": build_overlap_divergence(members),
            "head_exclusion_evidence": evaluate_head_exclusion_evidence(members),
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
