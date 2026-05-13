#!/usr/bin/env python3
"""
Decompose why clean liquidity-quality reversal improves RankIC but fails TopK.

This is train/validation diagnosis only. It does not tune thresholds, does not
create candidates, does not train, does not run portfolio or backtest, does not
generate holdings/formal readouts, and does not read frozen test data.
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
DEFAULT_P98_SCORES = ROOT / "artifacts" / "run_state" / "confirmatory_reversal_p98_trainval_20260506" / "model_scores_D0.parquet"
DEFAULT_MULTI_EQUAL_SCORES = ROOT / "artifacts" / "run_state" / "exploratory_multi_signal_composite_v1" / "model_scores_D0_multi.parquet"
DEFAULT_EXPOSURE_PANEL = DEFAULT_LIQUIDITY_SCORES
DEFAULT_OUTPUT_JSON = Path("/private/tmp/clean_liquidity_quality_failure_decomposition.json")
DEFAULT_OUTPUT_MD = Path("/private/tmp/clean_liquidity_quality_failure_decomposition.md")

LIQUIDITY = "clean_reversal_5d_liquidity_quality_v1"
NO_P98 = "no_p98_reversal_baseline_v1"
COMPOSITE = "clean_composite_reversal_tradability_v1"
P98 = "p98_conditional_reference"
MULTI = "multi_equal_weight_v1_conditional_reference"
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
    "limit_pct_rule",
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
    parser = argparse.ArgumentParser(description="Diagnose clean liquidity-quality failure decomposition.")
    parser.add_argument("--label-panel", type=Path, default=DEFAULT_LABEL_PANEL)
    parser.add_argument("--split-panel", type=Path, default=DEFAULT_SPLIT_PANEL)
    parser.add_argument("--no-p98-scores", type=Path, default=DEFAULT_NO_P98_SCORES)
    parser.add_argument("--liquidity-scores", type=Path, default=DEFAULT_LIQUIDITY_SCORES)
    parser.add_argument("--composite-scores", type=Path, default=DEFAULT_COMPOSITE_SCORES)
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


def mean_std_tstat(series: pd.Series) -> tuple[float | None, float | None, float | None]:
    clean = series.dropna()
    if clean.empty:
        return None, None, None
    mean_value = safe_float(clean.mean())
    std_value = safe_float(clean.std())
    if mean_value is None or std_value in (None, 0.0):
        return mean_value, std_value, None
    return mean_value, std_value, safe_float(mean_value / (std_value / math.sqrt(len(clean))))


def build_specs(args: argparse.Namespace) -> dict[str, ModelSpec]:
    return {
        LIQUIDITY: ModelSpec(
            key=LIQUIDITY,
            candidate_scheme_id=LIQUIDITY,
            score_path=args.liquidity_scores,
            effective_direction=-1,
            status="clean_research_object",
            label="clean liquidity-quality reversal",
        ),
        NO_P98: ModelSpec(
            key=NO_P98,
            candidate_scheme_id=NO_P98,
            score_path=args.no_p98_scores,
            effective_direction=-1,
            status="clean_anchor",
            label="no-p98 clean reversal baseline",
        ),
        COMPOSITE: ModelSpec(
            key=COMPOSITE,
            candidate_scheme_id=COMPOSITE,
            score_path=args.composite_scores,
            effective_direction=-1,
            status="rejected_comparator_only",
            label="rejected clean composite comparator",
        ),
        P98: ModelSpec(
            key=P98,
            candidate_scheme_id="reversal_tail_exclude_p98_v1",
            score_path=args.p98_scores,
            effective_direction=1,
            status="conditional_reference_only",
            label="p98 conditional baseline; conditional reference only",
        ),
        MULTI: ModelSpec(
            key=MULTI,
            candidate_scheme_id="multi_equal_weight_v1",
            score_path=args.multi_equal_scores,
            effective_direction=1,
            status="conditional_reference_only",
            label="multi_equal_weight_v1 conditional reference only",
            join_on_snapshot=False,
        ),
    }


def validate_columns(con: duckdb.DuckDBPyConnection, path: Path, required: set[str], label: str) -> list[str]:
    columns = [row[0] for row in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{sql_path(path)}')").fetchall()]
    missing = sorted(required - set(columns))
    if missing:
        raise DiagnosisError(f"{label} missing required columns: {missing}")
    return columns


def register_views(con: duckdb.DuckDBPyConnection, args: argparse.Namespace, specs: dict[str, ModelSpec]) -> None:
    validate_columns(
        con,
        args.label_panel,
        {"snapshot_id", "instrument", "signal_date", "label_defined", "label_5d_next_open_close"},
        "label panel",
    )
    validate_columns(
        con,
        args.split_panel,
        {"snapshot_id", "instrument", "signal_date", "train_flag", "validation_flag"},
        "split panel",
    )
    exposure_columns = validate_columns(con, args.exposure_panel, {"snapshot_id", "instrument", "signal_date"}, "exposure panel")
    blocked_requested = sorted(BLOCKED_FIELDS & set(USED_EXPOSURE_FIELDS))
    if blocked_requested:
        raise DiagnosisError(f"blocked fields requested: {blocked_requested}")

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
    exposure_select = []
    for field in USED_EXPOSURE_FIELDS:
        if field in exposure_columns:
            if field == "snapshot_id":
                exposure_select.append("CAST(snapshot_id AS VARCHAR) AS snapshot_id")
            elif field == "signal_date":
                exposure_select.append("REPLACE(CAST(signal_date AS VARCHAR), '-', '') AS signal_date")
            else:
                exposure_select.append(field)
        elif field not in {"snapshot_id", "instrument", "signal_date"}:
            exposure_select.append(f"NULL AS {field}")
    con.execute(
        f"""
        CREATE OR REPLACE TEMP VIEW exposure_t AS
        WITH exposure_base AS (
            SELECT {", ".join(exposure_select)}
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
        FROM exposure_base
        """
    )
    for spec in specs.values():
        validate_columns(
            con,
            spec.score_path,
            {"snapshot_id", "instrument", "signal_date", "candidate_scheme_id", "model_score_D0"},
            f"{spec.key} scores",
        )
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
            m.effective_score
        FROM label_t l
        INNER JOIN split_t s
          ON l.snapshot_id = s.snapshot_id
         AND l.instrument = s.instrument
         AND l.signal_date = s.signal_date
        LEFT JOIN {spec.key}_score_t m
          ON {join}
        """
    ).df()


def assign_rank_buckets(scored: pd.DataFrame, buckets: int, label: str) -> pd.DataFrame:
    work = scored.copy()
    rank = work.groupby("signal_date")["effective_score"].rank(method="first", ascending=False)
    counts = work.groupby("signal_date")["instrument"].transform("count")
    work[label] = ((rank - 1) / counts * buckets).astype(int).clip(0, buckets - 1) + 1
    return work


def bucket_curve(scored: pd.DataFrame, buckets: int, label: str) -> list[dict[str, Any]]:
    if scored.empty:
        return []
    work = assign_rank_buckets(scored, buckets, label)
    rows = []
    for bucket, group in work.groupby(label, sort=True):
        rows.append(
            {
                label: int(bucket),
                "mean_forward_return": safe_float(group["forward_return_5d"].mean()),
                "median_forward_return": safe_float(group["forward_return_5d"].median()),
                "row_count": int(len(group)),
            }
        )
    return rows


def monotonicity_score(curve: list[dict[str, Any]], key: str) -> dict[str, Any]:
    values = [row["mean_forward_return"] for row in sorted(curve, key=lambda x: x[key])]
    adjacent = []
    inversions = 0
    for left, right in zip(values, values[1:]):
        if left is None or right is None:
            continue
        ok = left >= right
        adjacent.append(ok)
        if not ok:
            inversions += 1
    return {
        "monotonicity_score": safe_float(sum(adjacent) / len(adjacent)) if adjacent else None,
        "adjacent_inversion_count": int(inversions),
    }


def daily_rankic(scored: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for signal_date, day in scored.groupby("signal_date", sort=True):
        if day["effective_score"].nunique() >= 2 and day["forward_return_5d"].nunique() >= 2:
            rows.append(
                {
                    "signal_date": str(signal_date),
                    "rank_ic": safe_float(day["effective_score"].corr(day["forward_return_5d"], method="spearman")),
                }
            )
    return pd.DataFrame(rows)


def daily_score_dispersion(scored: pd.DataFrame) -> dict[str, Any]:
    rows = []
    for signal_date, day in scored.groupby("signal_date", sort=True):
        score = day["effective_score"].dropna()
        if score.empty:
            continue
        rows.append(
            {
                "signal_date": str(signal_date),
                "score_std": safe_float(score.std()),
                "score_range": safe_float(score.max() - score.min()),
                "score_iqr": safe_float(score.quantile(0.75) - score.quantile(0.25)),
                "top30_score_share": safe_float(score.nlargest(min(30, len(score))).sum() / score.sum()) if score.sum() != 0 else None,
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return {
            "daily_count": 0,
            "score_std": summarize_series(pd.Series(dtype=float)),
            "score_range": summarize_series(pd.Series(dtype=float)),
            "score_iqr": summarize_series(pd.Series(dtype=float)),
            "top30_score_share": summarize_series(pd.Series(dtype=float)),
        }
    return {
        "daily_count": int(len(frame)),
        "score_std": summarize_series(frame["score_std"]),
        "score_range": summarize_series(frame["score_range"]),
        "score_iqr": summarize_series(frame["score_iqr"]),
        "top30_score_share": summarize_series(frame["top30_score_share"]),
    }


def topk_daily_and_members(scored: pd.DataFrame, *, topk: int, split: str, model_key: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    daily_rows = []
    member_rows = []
    for signal_date, day in scored.groupby("signal_date", sort=True):
        ordered = day.sort_values(["effective_score", "instrument"], ascending=[False, True]).reset_index(drop=True)
        if len(ordered) < topk:
            continue
        top = ordered.iloc[:topk].copy()
        nextk = ordered.iloc[topk : topk * 2].copy()
        rank31_100 = ordered.iloc[topk : min(100, len(ordered))].copy()
        bottom = ordered.tail(topk).copy()
        top_mean = safe_float(top["forward_return_5d"].mean())
        next_mean = safe_float(nextk["forward_return_5d"].mean()) if not nextk.empty else None
        rank31_100_mean = safe_float(rank31_100["forward_return_5d"].mean()) if not rank31_100.empty else None
        bottom_mean = safe_float(bottom["forward_return_5d"].mean()) if not bottom.empty else None
        daily_rows.append(
            {
                "signal_date": str(signal_date),
                "topk_return": top_mean,
                "topk_median": safe_float(top["forward_return_5d"].median()),
                "nextk_return": next_mean,
                "nextk_median": safe_float(nextk["forward_return_5d"].median()) if not nextk.empty else None,
                "rank31_100_return": rank31_100_mean,
                "bottom_return": bottom_mean,
                "topk_minus_nextk": top_mean - next_mean if top_mean is not None and next_mean is not None else None,
                "topk_daily_win": top_mean > next_mean if top_mean is not None and next_mean is not None else None,
            }
        )
        for bucket_name, bucket_frame in [("topk", top), ("nextk", nextk), ("rank31_100", rank31_100)]:
            if bucket_frame.empty:
                continue
            bucket_frame = bucket_frame.assign(
                model_key=model_key,
                split=split,
                rank_bucket=bucket_name,
                rank_position=range(1, len(bucket_frame) + 1),
            )
            member_rows.append(
                bucket_frame[
                    [
                        "model_key",
                        "split",
                        "signal_date",
                        "snapshot_id",
                        "instrument",
                        "rank_bucket",
                        "rank_position",
                        "forward_return_5d",
                        "effective_score",
                    ]
                ]
            )
    daily = pd.DataFrame(daily_rows)
    members = (
        pd.concat(member_rows, ignore_index=True)
        if member_rows
        else pd.DataFrame(
            columns=[
                "model_key",
                "split",
                "signal_date",
                "snapshot_id",
                "instrument",
                "rank_bucket",
                "rank_position",
                "forward_return_5d",
                "effective_score",
            ]
        )
    )
    return daily, members


def contribution_stats(daily: pd.DataFrame, members: pd.DataFrame) -> dict[str, Any]:
    top_members = members[members["rank_bucket"] == "topk"] if not members.empty else pd.DataFrame()
    next_members = members[members["rank_bucket"] == "nextk"] if not members.empty else pd.DataFrame()
    top_returns = top_members["forward_return_5d"] if not top_members.empty else pd.Series(dtype=float)
    next_returns = next_members["forward_return_5d"] if not next_members.empty else pd.Series(dtype=float)
    spread = daily["topk_minus_nextk"] if "topk_minus_nextk" in daily else pd.Series(dtype=float)
    positive = spread[spread > 0].sort_values(ascending=False)
    negative = spread[spread < 0].sort_values(ascending=True)
    top_n = max(1, math.ceil(len(positive) * 0.05)) if len(positive) else 0
    worst_n = max(1, math.ceil(len(negative) * 0.05)) if len(negative) else 0
    top_pos = top_returns[top_returns > 0]
    top_neg = top_returns[top_returns < 0]
    return {
        "topk_return": summarize_series(top_returns),
        "nextk_return": summarize_series(next_returns),
        "rank31_100_daily_return": summarize_series(daily["rank31_100_return"] if "rank31_100_return" in daily else pd.Series(dtype=float)),
        "topk_minus_nextk_daily": summarize_series(spread),
        "topk_vs_nextk_daily_win_rate": safe_float(pd.Series(daily["topk_daily_win"]).dropna().astype(bool).mean()) if "topk_daily_win" in daily and not daily.empty else None,
        "top_winner_contribution": safe_float(top_pos.max() / top_pos.sum()) if len(top_pos) and top_pos.sum() != 0 else None,
        "bottom_loser_contribution": safe_float(top_neg.min() / abs(top_neg.sum())) if len(top_neg) and top_neg.sum() != 0 else None,
        "topk_edge_concentration_top_5pct_days": safe_float(positive.head(top_n).sum() / positive.sum()) if top_n and positive.sum() != 0 else None,
        "worst_5pct_days_damage": safe_float(abs(negative.head(worst_n).sum()) / abs(negative.sum())) if worst_n and negative.sum() != 0 else None,
    }


def segment_rankic(scored: pd.DataFrame) -> dict[str, Any]:
    if scored.empty:
        return {}
    work = assign_rank_buckets(scored, 10, "decile")
    segments = {
        "top_decile": work[work["decile"] == 1],
        "middle_deciles_4_to_7": work[work["decile"].between(4, 7)],
        "bottom_decile": work[work["decile"] == 10],
    }
    result = {}
    overall_mean = safe_float(work["forward_return_5d"].mean())
    for name, seg in segments.items():
        daily = daily_rankic(seg)
        mean_ic, std_ic, _ = mean_std_tstat(daily["rank_ic"]) if not daily.empty else (None, None, None)
        seg_mean = safe_float(seg["forward_return_5d"].mean()) if not seg.empty else None
        result[name] = {
            "row_count": int(len(seg)),
            "mean_forward_return": seg_mean,
            "mean_minus_overall": seg_mean - overall_mean if seg_mean is not None and overall_mean is not None else None,
            "segment_rankic_mean": mean_ic,
            "segment_rankic_std": std_ic,
        }
    return result


def split_metrics(frame: pd.DataFrame, *, topk: int, split: str, model_key: str) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    eligible_rows = int(len(frame))
    scored = frame.dropna(subset=["effective_score", "forward_return_5d"]).copy()
    scored_rows = int(len(scored))
    if scored.empty:
        return {
            "coverage": {"eligible_rows": eligible_rows, "scored_rows": 0, "score_coverage": 0.0},
            "rank_ic": {"mean": None, "std": None, "t_stat": None, "daily_count": 0},
            "icir": None,
            "top_bottom_spread": None,
            "topk_nextk_decomposition": {},
            "rankic_source_decomposition": {},
        }, pd.DataFrame(), pd.DataFrame()

    d_ic = daily_rankic(scored)
    rankic_mean, rankic_std, rankic_t = mean_std_tstat(d_ic["rank_ic"]) if not d_ic.empty else (None, None, None)
    deciles = bucket_curve(scored, 10, "decile")
    ventiles = bucket_curve(scored, 20, "ventile")
    top_decile = next((row["mean_forward_return"] for row in deciles if row["decile"] == 1), None)
    bottom_decile = next((row["mean_forward_return"] for row in deciles if row["decile"] == 10), None)
    daily_topk, members = topk_daily_and_members(scored, topk=topk, split=split, model_key=model_key)
    topk_mean, _, topk_t = mean_std_tstat(daily_topk["topk_return"]) if not daily_topk.empty else (None, None, None)
    spread_mean, _, spread_t = mean_std_tstat(daily_topk["topk_minus_nextk"]) if not daily_topk.empty else (None, None, None)
    yearly_rankic = []
    if not d_ic.empty:
        d_ic["year"] = d_ic["signal_date"].astype(str).str[:4]
        for year, group in d_ic.groupby("year", sort=True):
            y_mean, y_std, _ = mean_std_tstat(group["rank_ic"])
            yearly_rankic.append({"year": str(year), "rank_ic_mean": y_mean, "rank_ic_std": y_std, "n_days": int(len(group))})
    yearly_topk = []
    if not daily_topk.empty:
        daily_topk["year"] = daily_topk["signal_date"].astype(str).str[:4]
        for year, group in daily_topk.groupby("year", sort=True):
            y_top, _, _ = mean_std_tstat(group["topk_return"])
            y_next, _, _ = mean_std_tstat(group["nextk_return"])
            y_spread, _, _ = mean_std_tstat(group["topk_minus_nextk"])
            yearly_topk.append({"year": str(year), "topk_return_mean": y_top, "nextk_return_mean": y_next, "topk_minus_nextk_mean": y_spread, "n_days": int(len(group))})
    decile_shape = monotonicity_score(deciles, "decile")
    ventile_shape = monotonicity_score(ventiles, "ventile")
    return {
        "coverage": {
            "eligible_rows": eligible_rows,
            "scored_rows": scored_rows,
            "score_coverage": safe_float(scored_rows / eligible_rows) if eligible_rows else None,
            "signal_dates": int(scored["signal_date"].nunique()),
            "instruments": int(scored["instrument"].nunique()),
        },
        "rank_ic": {"mean": rankic_mean, "std": rankic_std, "t_stat": rankic_t, "daily_count": int(len(d_ic))},
        "icir": safe_float(rankic_mean / rankic_std) if rankic_mean is not None and rankic_std not in (None, 0.0) else None,
        "top_bottom_spread": top_decile - bottom_decile if top_decile is not None and bottom_decile is not None else None,
        "topk_proxy": {
            "topk": topk,
            "n_days": int(len(daily_topk)),
            "mean_topk_forward_return": topk_mean,
            "topk_mean_t_stat": topk_t,
            "topk_minus_nextk": spread_mean,
            "topk_minus_nextk_t_stat": spread_t,
        },
        "topk_nextk_decomposition": contribution_stats(daily_topk, members),
        "rankic_source_decomposition": {
            "decile_return_curve": deciles,
            "ventile_return_curve": ventiles,
            "decile_monotonicity_score": decile_shape["monotonicity_score"],
            "decile_adjacent_inversion_count": decile_shape["adjacent_inversion_count"],
            "ventile_monotonicity_score": ventile_shape["monotonicity_score"],
            "ventile_adjacent_inversion_count": ventile_shape["adjacent_inversion_count"],
            "middle_bucket_contribution": segment_rankic(scored).get("middle_deciles_4_to_7"),
            "top_decile_contribution": segment_rankic(scored).get("top_decile"),
            "bottom_decile_contribution": segment_rankic(scored).get("bottom_decile"),
            "daily_rankic_distribution": summarize_series(d_ic["rank_ic"] if not d_ic.empty else pd.Series(dtype=float)),
            "yearly_rankic_distribution": yearly_rankic,
            "yearly_topk_distribution": yearly_topk,
            "score_dispersion_rank_concentration": daily_score_dispersion(scored),
        },
    }, members, daily_topk


def diagnose_models(con: duckdb.DuckDBPyConnection, specs: dict[str, ModelSpec], topk: int) -> tuple[dict[str, Any], pd.DataFrame, dict[str, pd.DataFrame]]:
    diagnostics = {}
    all_members = []
    daily_topk_by_model_split = {}
    for spec in specs.values():
        frame = fetch_model_frame(con, spec)
        payload = {}
        for split, mask in [("train", frame["train_flag"]), ("validation", frame["validation_flag"])]:
            metrics, members, daily_topk = split_metrics(frame[mask], topk=topk, split=split, model_key=spec.key)
            payload[split] = metrics
            all_members.append(members)
            daily_topk_by_model_split[f"{spec.key}:{split}"] = daily_topk
        diagnostics[spec.key] = {
            "candidate_scheme_id": spec.candidate_scheme_id,
            "status": spec.status,
            "label": spec.label,
            **payload,
        }
    return diagnostics, pd.concat(all_members, ignore_index=True) if all_members else pd.DataFrame(), daily_topk_by_model_split


def delta(a: float | None, b: float | None) -> float | None:
    return a - b if a is not None and b is not None else None


def comparison_delta(diagnostics: dict[str, Any], comparator: str, split: str) -> dict[str, Any]:
    liq = diagnostics[LIQUIDITY][split]
    other = diagnostics[comparator][split]
    return {
        "rankic_delta": delta(liq["rank_ic"]["mean"], other["rank_ic"]["mean"]),
        "icir_delta": delta(liq["icir"], other["icir"]),
        "top_bottom_delta": delta(liq["top_bottom_spread"], other["top_bottom_spread"]),
        "topk_proxy_delta": delta(liq["topk_proxy"]["mean_topk_forward_return"], other["topk_proxy"]["mean_topk_forward_return"]),
        "topk_minus_nextk_delta": delta(liq["topk_proxy"]["topk_minus_nextk"], other["topk_proxy"]["topk_minus_nextk"]),
        "coverage_delta": delta(liq["coverage"]["score_coverage"], other["coverage"]["score_coverage"]),
    }


def build_comparisons(diagnostics: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for comparator in [NO_P98, P98, COMPOSITE, MULTI]:
        result[f"liquidity_quality_vs_{comparator}"] = {
            "reference_status": diagnostics[comparator]["status"],
            "train": comparison_delta(diagnostics, comparator, "train"),
            "validation": comparison_delta(diagnostics, comparator, "validation"),
        }
    result[f"liquidity_quality_vs_{P98}"]["p98_note"] = "p98 is conditional reference only"
    result[f"liquidity_quality_vs_{MULTI}"]["multi_equal_weight_note"] = "multi_equal_weight_v1 is conditional reference only"
    result[f"liquidity_quality_vs_{COMPOSITE}"]["composite_note"] = "clean composite is rejected comparator only"
    return result


def overlap_pair(members: pd.DataFrame, comparator: str, split: str) -> dict[str, Any]:
    liq = members[(members["model_key"] == LIQUIDITY) & (members["split"] == split) & (members["rank_bucket"] == "topk")]
    other = members[(members["model_key"] == comparator) & (members["split"] == split) & (members["rank_bucket"] == "topk")]
    daily_rows = []
    for signal_date in sorted(set(liq["signal_date"]) | set(other["signal_date"])):
        l_day = liq[liq["signal_date"] == signal_date]
        o_day = other[other["signal_date"] == signal_date]
        l_map = dict(zip(l_day["instrument"], l_day["forward_return_5d"]))
        o_map = dict(zip(o_day["instrument"], o_day["forward_return_5d"]))
        l_set = set(l_map)
        o_set = set(o_map)
        overlap = l_set & o_set
        union = l_set | o_set
        l_only = l_set - o_set
        o_only = o_set - l_set
        daily_rows.append(
            {
                "signal_date": str(signal_date),
                "overlap_count": len(overlap),
                "union_count": len(union),
                "jaccard": len(overlap) / len(union) if union else None,
                "liquidity_only_mean_return": safe_float(pd.Series([l_map[x] for x in l_only]).mean()) if l_only else None,
                "comparator_only_mean_return": safe_float(pd.Series([o_map[x] for x in o_only]).mean()) if o_only else None,
                "overlap_mean_return": safe_float(pd.Series([l_map[x] for x in overlap]).mean()) if overlap else None,
            }
        )
    daily = pd.DataFrame(daily_rows)
    if daily.empty:
        return {"daily_count": 0}
    return {
        "daily_count": int(len(daily)),
        "overlap_count": {"total": int(daily["overlap_count"].sum()), "mean": safe_float(daily["overlap_count"].mean()), "median": safe_float(daily["overlap_count"].median())},
        "jaccard": summarize_series(daily["jaccard"]),
        "liquidity_only_realized_return": summarize_series(daily["liquidity_only_mean_return"]),
        "comparator_only_realized_return": summarize_series(daily["comparator_only_mean_return"]),
        "liquidity_only_minus_comparator_only": delta(safe_float(daily["liquidity_only_mean_return"].mean()), safe_float(daily["comparator_only_mean_return"].mean())),
        "overlap_realized_return": summarize_series(daily["overlap_mean_return"]),
        "daily_overlap_distribution": daily[["signal_date", "overlap_count", "jaccard"]].to_dict(orient="records"),
    }


def build_overlap(members: pd.DataFrame) -> dict[str, Any]:
    return {
        split: {f"liquidity_quality_vs_{comparator}": overlap_pair(members, comparator, split) for comparator in [NO_P98, P98]}
        for split in ["train", "validation"]
    }


def load_rank_exposure(con: duckdb.DuckDBPyConnection, members: pd.DataFrame) -> pd.DataFrame:
    if members.empty:
        return members
    con.register("rank_members_df", members)
    return con.execute(
        """
        SELECT
            m.*,
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
            e.exchange,
            e.limit_pct_rule
        FROM rank_members_df m
        LEFT JOIN exposure_t e
          ON m.snapshot_id = e.snapshot_id
         AND m.instrument = e.instrument
         AND m.signal_date = e.signal_date
        """
    ).df()


def add_amount_bucket(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    if "amount_percentile_asc" in work and not work["amount_percentile_asc"].dropna().empty:
        pct = work["amount_percentile_asc"]
    elif "amount" in work and not work["amount"].dropna().empty:
        pct = work.groupby("signal_date")["amount"].rank(pct=True, method="average")
    else:
        pct = None
    if pct is not None:
        work["amount_bucket"] = pd.cut(
            pct,
            bins=[0.0, 0.2, 0.5, 0.8, 1.0],
            labels=["bottom_20pct", "20_50pct", "50_80pct", "top_20pct"],
            include_lowest=True,
        ).astype("object")
    if "listing_age_days" in work and not work["listing_age_days"].dropna().empty:
        work["listing_age_days_bucket"] = pd.cut(
            work["listing_age_days"],
            bins=[-math.inf, 90, 180, 365, 1095, math.inf],
            labels=["lt_90d", "90_180d", "180_365d", "1y_3y", "ge_3y"],
        ).astype("object")
    return work


def summarize_category(frame: pd.DataFrame, column: str) -> dict[str, Any]:
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


def exposure_summary(frame: pd.DataFrame) -> dict[str, Any]:
    work = add_amount_bucket(frame)
    return {
        "amount_bucket_distribution": summarize_category(work, "amount_bucket"),
        "board_type": summarize_category(work, "board_type"),
        "exchange": summarize_category(work, "exchange"),
        "listing_age_days_bucket": summarize_category(work, "listing_age_days_bucket"),
        "limit_status": {col: summarize_bool(work, col) for col in ["is_limit_up", "is_limit_down", "open_at_up_limit", "close_at_down_limit"]},
        "tradability_status": {col: summarize_bool(work, col) for col in ["entry_buyable", "no_trade_flag", "is_suspended", "volume_zero_flag", "amount_zero_flag"]},
        "mean_forward_return": safe_float(work["forward_return_5d"].mean()) if "forward_return_5d" in work and not work.empty else None,
    }


def high_vs_mid_liquidity_returns(frame: pd.DataFrame) -> dict[str, Any]:
    work = add_amount_bucket(frame)
    if "amount_bucket" not in work:
        return {"status": "unavailable"}
    top = work[work["amount_bucket"] == "top_20pct"]["forward_return_5d"]
    mid = work[work["amount_bucket"].isin(["20_50pct", "50_80pct"])]["forward_return_5d"]
    return {
        "status": "available",
        "top_liquidity_return": summarize_series(top),
        "mid_liquidity_return": summarize_series(mid),
        "top_minus_mid_return": delta(safe_float(top.mean()), safe_float(mid.mean())),
    }


def winners_excluded_by_liquidity(rank_exposure: pd.DataFrame, split: str) -> dict[str, Any]:
    liq_top = rank_exposure[(rank_exposure["model_key"] == LIQUIDITY) & (rank_exposure["split"] == split) & (rank_exposure["rank_bucket"] == "topk")]
    no_top = rank_exposure[(rank_exposure["model_key"] == NO_P98) & (rank_exposure["split"] == split) & (rank_exposure["rank_bucket"] == "topk")]
    rows = []
    for signal_date in sorted(set(no_top["signal_date"])):
        l_set = set(liq_top[liq_top["signal_date"] == signal_date]["instrument"])
        n_day = no_top[no_top["signal_date"] == signal_date]
        rows.append(n_day[~n_day["instrument"].isin(l_set)])
    excluded = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    winners = excluded[excluded["forward_return_5d"] > 0] if not excluded.empty else excluded
    return {
        "no_p98_topk_names_excluded_from_liquidity_topk": int(len(excluded)),
        "positive_winners_excluded_count": int(len(winners)),
        "excluded_mean_return": safe_float(excluded["forward_return_5d"].mean()) if not excluded.empty else None,
        "excluded_positive_winner_mean_return": safe_float(winners["forward_return_5d"].mean()) if not winners.empty else None,
        "excluded_exposure": exposure_summary(excluded) if not excluded.empty else {"status": "unavailable"},
    }


def build_liquidity_exposure(rank_exposure: pd.DataFrame) -> dict[str, Any]:
    result = {}
    for split in ["train", "validation"]:
        split_frame = rank_exposure[(rank_exposure["split"] == split) & (rank_exposure["model_key"] == LIQUIDITY)]
        top = split_frame[split_frame["rank_bucket"] == "topk"]
        nextk = split_frame[split_frame["rank_bucket"] == "nextk"]
        rank31_100 = split_frame[split_frame["rank_bucket"] == "rank31_100"]
        top_summary = exposure_summary(top)
        next_summary = exposure_summary(nextk)
        top_bucket = top_summary["amount_bucket_distribution"]
        top_overrepresented = None
        if top_bucket.get("status") == "available":
            top_share = next((row["share"] for row in top_bucket["distribution"] if row["value"] == "top_20pct"), None)
            top_overrepresented = top_share is not None and top_share > 0.20
        result[split] = {
            "topk_exposure": top_summary,
            "nextk_exposure": next_summary,
            "rank31_100_exposure": exposure_summary(rank31_100),
            "topk_amount_bucket_vs_nextk_amount_bucket": {
                "topk": top_summary["amount_bucket_distribution"],
                "nextk": next_summary["amount_bucket_distribution"],
            },
            "high_liquidity_names_return_vs_mid_liquidity_names_return": high_vs_mid_liquidity_returns(split_frame),
            "top_liquidity_bucket_overrepresented": top_overrepresented,
            "winners_excluded_by_liquidity_quality_filter": winners_excluded_by_liquidity(rank_exposure, split),
        }
    return result


def yearly_metric_map(diagnostics: dict[str, Any], model_key: str, split: str, metric: str) -> dict[str, float | None]:
    if metric == "rankic":
        rows = diagnostics[model_key][split]["rankic_source_decomposition"]["yearly_rankic_distribution"]
        return {row["year"]: row.get("rank_ic_mean") for row in rows}
    rows = diagnostics[model_key][split]["rankic_source_decomposition"]["yearly_topk_distribution"]
    return {row["year"]: row.get(metric) for row in rows}


def build_stability(diagnostics: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for comparator in [NO_P98, P98]:
        train_delta = comparison_delta(diagnostics, comparator, "train")
        val_delta = comparison_delta(diagnostics, comparator, "validation")
        liq_year_rankic = yearly_metric_map(diagnostics, LIQUIDITY, "validation", "rankic")
        other_year_rankic = yearly_metric_map(diagnostics, comparator, "validation", "rankic")
        rankic_by_year = {year: delta(liq_year_rankic.get(year), other_year_rankic.get(year)) for year in sorted(set(liq_year_rankic) & set(other_year_rankic))}
        liq_year_spread = yearly_metric_map(diagnostics, LIQUIDITY, "validation", "topk_minus_nextk_mean")
        result[f"liquidity_quality_vs_{comparator}"] = {
            "train_vs_validation_rankic_delta_direction_consistent": bool(train_delta["rankic_delta"] is not None and val_delta["rankic_delta"] is not None and train_delta["rankic_delta"] > 0 and val_delta["rankic_delta"] > 0),
            "train_vs_validation_topk_minus_nextk_negative": bool(diagnostics[LIQUIDITY]["train"]["topk_proxy"]["topk_minus_nextk"] is not None and diagnostics[LIQUIDITY]["validation"]["topk_proxy"]["topk_minus_nextk"] is not None and diagnostics[LIQUIDITY]["train"]["topk_proxy"]["topk_minus_nextk"] < 0 and diagnostics[LIQUIDITY]["validation"]["topk_proxy"]["topk_minus_nextk"] < 0),
            "validation_yearly_rankic_improvement_delta": rankic_by_year,
            "rankic_improvement_exists_each_validation_year": bool(rankic_by_year) and all(v is not None and v > 0 for v in rankic_by_year.values()),
            "validation_yearly_topk_minus_nextk": liq_year_spread,
            "topk_minus_nextk_remains_negative_each_validation_year": bool(liq_year_spread) and all(v is not None and v < 0 for v in liq_year_spread.values()),
        }
    return result


def build_decision_summary(payload: dict[str, Any]) -> dict[str, Any]:
    no_p98_val = payload["comparisons"][f"liquidity_quality_vs_{NO_P98}"]["validation"]
    liq_val = payload["diagnostics"][LIQUIDITY]["validation"]
    rankic_improvement = no_p98_val["rankic_delta"] is not None and no_p98_val["rankic_delta"] > 0
    spread_negative = liq_val["topk_proxy"]["topk_minus_nextk"] is not None and liq_val["topk_proxy"]["topk_minus_nextk"] < 0
    source = liq_val["rankic_source_decomposition"]
    top_contrib = source["top_decile_contribution"]
    middle_contrib = source["middle_bucket_contribution"]
    bottom_contrib = source["bottom_decile_contribution"]
    middle_or_tail_driven = False
    if top_contrib and middle_contrib and bottom_contrib:
        top_abs = abs(top_contrib.get("mean_minus_overall") or 0.0)
        middle_abs = abs(middle_contrib.get("mean_minus_overall") or 0.0)
        bottom_abs = abs(bottom_contrib.get("mean_minus_overall") or 0.0)
        middle_or_tail_driven = max(middle_abs, bottom_abs) >= top_abs
    stable = payload["stability_checks"][f"liquidity_quality_vs_{NO_P98}"]["rankic_improvement_exists_each_validation_year"]
    recommend_candidate = bool(rankic_improvement and stable and not spread_negative and not middle_or_tail_driven)
    return {
        "rankic_improvement_real_vs_no_p98": rankic_improvement,
        "topk_minus_nextk_negative": spread_negative,
        "rankic_improvement_middle_or_tail_driven": middle_or_tail_driven,
        "trainval_yearly_rankic_improvement_stable_vs_no_p98": bool(stable),
        "recommend_next_preregistered_candidate": recommend_candidate,
        "recommend_portfolio_dry_run": False,
        "continue_portfolio_ban": True,
        "frozen_test_accessed": False,
        "training_backtest_or_portfolio_run": False,
        "interpretation": (
            "Do not enter portfolio. A next candidate would need separate preregistration."
            if not recommend_candidate
            else "May only consider a separately preregistered clean candidate design; no portfolio in this round."
        ),
    }


def build_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Clean Liquidity Quality Failure Decomposition",
        "",
        "Train/validation diagnosis only. Not OOS, not strategy approval, not portfolio, not backtest, not formal metrics/readout, and frozen test remains unread.",
        "",
        "## Boundary",
        "",
        f"- p98 status: `{payload['p98_reference_status']}`",
        f"- multi_equal_weight_v1 status: `{payload['multi_equal_weight_v1_reference_status']}`",
        f"- portfolio dry-run: `{payload['portfolio_run_executed']}`",
        f"- training/backtest/portfolio: `{payload['training_performed']}` / `{payload['backtest_run_executed']}` / `{payload['portfolio_run_executed']}`",
        f"- blocked fields used: `{payload['blocked_fields_used']}`",
        "",
        "## Validation Deltas",
        "",
    ]
    for name in [f"liquidity_quality_vs_{NO_P98}", f"liquidity_quality_vs_{P98}"]:
        val = payload["comparisons"][name]["validation"]
        lines.append(
            f"- `{name}`: RankIC delta `{val['rankic_delta']}`, ICIR delta `{val['icir_delta']}`, "
            f"TopK delta `{val['topk_proxy_delta']}`, TopK-minus-nextK delta `{val['topk_minus_nextk_delta']}`, "
            f"coverage delta `{val['coverage_delta']}`"
        )
    liq = payload["diagnostics"][LIQUIDITY]["validation"]
    lines.extend(
        [
            "",
            "## Liquidity TopK",
            "",
            f"- TopK proxy: `{liq['topk_proxy']['mean_topk_forward_return']}`",
            f"- TopK-minus-nextK: `{liq['topk_proxy']['topk_minus_nextk']}`",
            f"- TopK vs nextK win rate: `{liq['topk_nextk_decomposition']['topk_vs_nextk_daily_win_rate']}`",
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
        diagnostics, rank_members, _ = diagnose_models(con, specs, args.topk)
        rank_exposure = load_rank_exposure(con, rank_members)
        payload = {
            "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "round_id": "clean_liquidity_quality_failure_decomposition_round_v1",
            "diagnosis_label": "TRAINVAL_DIAGNOSIS_ONLY_NOT_OOS_NOT_PORTFOLIO",
            "training_performed": False,
            "backtest_run_executed": False,
            "portfolio_run_executed": False,
            "holdings_generated": False,
            "formal_metrics_generated": False,
            "frozen_test_accessed": False,
            "p98_reference_status": "conditional_reference_only",
            "multi_equal_weight_v1_reference_status": "conditional_reference_only",
            "p98_used_as_clean_component": False,
            "blocked_fields": sorted(BLOCKED_FIELDS),
            "blocked_fields_used": [],
            "used_exposure_fields": USED_EXPOSURE_FIELDS,
            "topk": args.topk,
            "diagnostics": diagnostics,
            "comparisons": build_comparisons(diagnostics),
            "topk_overlap_divergence": build_overlap(rank_members),
            "liquidity_exposure_decomposition": build_liquidity_exposure(rank_exposure),
            "stability_checks": build_stability(diagnostics),
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
