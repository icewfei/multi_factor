#!/usr/bin/env python3
"""
Decompose clean composite TopK improvement versus RankIC damage.

This is train/validation diagnosis only. It does not train, does not tune,
does not run portfolio, does not backtest, does not generate holdings or
formal readouts, and does not read frozen test data.
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
DEFAULT_EXPOSURE_PANEL = DEFAULT_COMPOSITE_SCORES
DEFAULT_OUTPUT_JSON = Path("/private/tmp/clean_composite_topk_improvement_decomposition.json")
DEFAULT_OUTPUT_MD = Path("/private/tmp/clean_composite_topk_improvement_decomposition.md")

COMPOSITE = "clean_composite_reversal_tradability_v1"
NO_P98 = "no_p98_reversal_baseline_v1"
LIQUIDITY = "liquidity_quality"
P98 = "p98_conditional_reference"
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


class DiagnosisError(Exception):
    """Raised when the diagnostic cannot be completed safely."""


@dataclass(frozen=True)
class ModelSpec:
    key: str
    candidate_scheme_id: str
    score_path: Path
    effective_direction: int
    status: str
    label: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose clean composite TopK improvement decomposition.")
    parser.add_argument("--label-panel", type=Path, default=DEFAULT_LABEL_PANEL)
    parser.add_argument("--split-panel", type=Path, default=DEFAULT_SPLIT_PANEL)
    parser.add_argument("--no-p98-scores", type=Path, default=DEFAULT_NO_P98_SCORES)
    parser.add_argument("--liquidity-scores", type=Path, default=DEFAULT_LIQUIDITY_SCORES)
    parser.add_argument("--composite-scores", type=Path, default=DEFAULT_COMPOSITE_SCORES)
    parser.add_argument("--p98-scores", type=Path, default=DEFAULT_P98_SCORES)
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


def quantile_value(series: pd.Series, q: float) -> float | None:
    clean = series.dropna()
    if clean.empty:
        return None
    return safe_float(clean.quantile(q))


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
        "p05": quantile_value(clean, 0.05),
        "p25": quantile_value(clean, 0.25),
        "p75": quantile_value(clean, 0.75),
        "p95": quantile_value(clean, 0.95),
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
        COMPOSITE: ModelSpec(
            key=COMPOSITE,
            candidate_scheme_id=COMPOSITE,
            score_path=args.composite_scores,
            effective_direction=-1,
            status="clean_research_object",
            label="clean composite reversal tradability",
        ),
        NO_P98: ModelSpec(
            key=NO_P98,
            candidate_scheme_id=NO_P98,
            score_path=args.no_p98_scores,
            effective_direction=-1,
            status="clean_anchor",
            label="no p98 reversal baseline",
        ),
        LIQUIDITY: ModelSpec(
            key=LIQUIDITY,
            candidate_scheme_id="clean_reversal_5d_liquidity_quality_v1",
            score_path=args.liquidity_scores,
            effective_direction=-1,
            status="clean_comparator",
            label="liquidity quality clean comparator",
        ),
        P98: ModelSpec(
            key=P98,
            candidate_scheme_id="reversal_tail_exclude_p98_v1",
            score_path=args.p98_scores,
            effective_direction=1,
            status="conditional_reference_only",
            label="p98 conditional baseline; conditional reference only",
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
    exposure_columns = validate_columns(
        con,
        args.exposure_panel,
        {"snapshot_id", "instrument", "signal_date"},
        "exposure panel",
    )
    used_blocked = sorted(BLOCKED_FIELDS & set(USED_EXPOSURE_FIELDS))
    if used_blocked:
        raise DiagnosisError(f"blocked fields requested by diagnostic: {used_blocked}")

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
            if field == "signal_date":
                exposure_select.append("REPLACE(CAST(signal_date AS VARCHAR), '-', '') AS signal_date")
            elif field == "snapshot_id":
                exposure_select.append("CAST(snapshot_id AS VARCHAR) AS snapshot_id")
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
          ON l.snapshot_id = m.snapshot_id
         AND l.instrument = m.instrument
         AND l.signal_date = m.signal_date
        """
    ).df()


def assign_deciles(scored: pd.DataFrame) -> pd.DataFrame:
    work = scored.copy()
    rank = work.groupby("signal_date")["effective_score"].rank(method="first", ascending=False)
    counts = work.groupby("signal_date")["instrument"].transform("count")
    work["decile"] = ((rank - 1) / counts * 10).astype(int).clip(0, 9) + 1
    return work


def compute_decile_curve(scored: pd.DataFrame) -> list[dict[str, Any]]:
    if scored.empty:
        return []
    work = assign_deciles(scored)
    rows = []
    for decile, group in work.groupby("decile", sort=True):
        rows.append(
            {
                "decile": int(decile),
                "mean_forward_return": safe_float(group["forward_return_5d"].mean()),
                "median_forward_return": safe_float(group["forward_return_5d"].median()),
                "row_count": int(len(group)),
            }
        )
    return rows


def decile_shape(curve: list[dict[str, Any]]) -> dict[str, Any]:
    values = {row["decile"]: row["mean_forward_return"] for row in curve}
    adjacent = []
    inversions = 0
    for idx in range(1, 10):
        left = values.get(idx)
        right = values.get(idx + 1)
        if left is None or right is None:
            continue
        ok = left >= right
        adjacent.append(ok)
        if not ok:
            inversions += 1
    middle_inversions = 0
    for idx in range(4, 7):
        left = values.get(idx)
        right = values.get(idx + 1)
        if left is not None and right is not None and left < right:
            middle_inversions += 1
    return {
        "monotonicity_score": safe_float(sum(adjacent) / len(adjacent)) if adjacent else None,
        "adjacent_inversion_count": int(inversions),
        "middle_decile_inversion_count": int(middle_inversions),
        "bottom_decile_mean": values.get(10),
        "bottom_minus_decile9": (
            values[10] - values[9] if values.get(10) is not None and values.get(9) is not None else None
        ),
    }


def compute_daily_rankic(scored: pd.DataFrame) -> pd.DataFrame:
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


def compute_daily_score_dispersion(scored: pd.DataFrame) -> dict[str, Any]:
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
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return {"daily_count": 0, "score_std": summarize_series(pd.Series(dtype=float)), "score_range": summarize_series(pd.Series(dtype=float)), "score_iqr": summarize_series(pd.Series(dtype=float))}
    return {
        "daily_count": int(len(frame)),
        "score_std": summarize_series(frame["score_std"]),
        "score_range": summarize_series(frame["score_range"]),
        "score_iqr": summarize_series(frame["score_iqr"]),
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
        bottom = ordered.tail(topk).copy()
        top_mean = safe_float(top["forward_return_5d"].mean())
        next_mean = safe_float(nextk["forward_return_5d"].mean()) if not nextk.empty else None
        bottom_mean = safe_float(bottom["forward_return_5d"].mean()) if not bottom.empty else None
        daily_rows.append(
            {
                "signal_date": str(signal_date),
                "topk_return": top_mean,
                "nextk_return": next_mean,
                "bottom_return": bottom_mean,
                "topk_minus_nextk": top_mean - next_mean if top_mean is not None and next_mean is not None else None,
                "topk_minus_bottom": top_mean - bottom_mean if top_mean is not None and bottom_mean is not None else None,
            }
        )
        top = top.assign(model_key=model_key, split=split, topk_rank=range(1, len(top) + 1))
        member_rows.append(top[["model_key", "split", "signal_date", "snapshot_id", "instrument", "topk_rank", "forward_return_5d", "effective_score"]])
    daily = pd.DataFrame(daily_rows)
    members = pd.concat(member_rows, ignore_index=True) if member_rows else pd.DataFrame(
        columns=["model_key", "split", "signal_date", "snapshot_id", "instrument", "topk_rank", "forward_return_5d", "effective_score"]
    )
    return daily, members


def contribution_stats(daily: pd.DataFrame, members: pd.DataFrame) -> dict[str, Any]:
    topk_returns = members["forward_return_5d"] if "forward_return_5d" in members else pd.Series(dtype=float)
    daily_spread = daily["topk_minus_nextk"] if "topk_minus_nextk" in daily else pd.Series(dtype=float)
    positive_daily = daily_spread[daily_spread > 0].sort_values(ascending=False)
    negative_daily = daily_spread[daily_spread < 0].sort_values(ascending=True)
    positive_members = topk_returns[topk_returns > 0]
    negative_members = topk_returns[topk_returns < 0]
    top_n = max(1, math.ceil(len(positive_daily) * 0.05)) if len(positive_daily) else 0
    worst_n = max(1, math.ceil(len(negative_daily) * 0.05)) if len(negative_daily) else 0
    total_positive_daily = positive_daily.sum()
    total_negative_daily = negative_daily.sum()
    total_positive_members = positive_members.sum()
    total_negative_members = negative_members.sum()
    return {
        "topk_return": summarize_series(topk_returns),
        "nextk_daily_return": summarize_series(daily["nextk_return"] if "nextk_return" in daily else pd.Series(dtype=float)),
        "topk_minus_nextk_daily": summarize_series(daily_spread),
        "top_winner_contribution": (
            safe_float(positive_members.max() / total_positive_members) if len(positive_members) and total_positive_members != 0 else None
        ),
        "bottom_loser_contribution": (
            safe_float(negative_members.min() / abs(total_negative_members)) if len(negative_members) and total_negative_members != 0 else None
        ),
        "percentage_of_daily_edge_from_top_5pct_days": (
            safe_float(positive_daily.head(top_n).sum() / total_positive_daily) if top_n and total_positive_daily != 0 else None
        ),
        "percentage_of_daily_damage_from_worst_5pct_days": (
            safe_float(abs(negative_daily.head(worst_n).sum()) / abs(total_negative_daily)) if worst_n and total_negative_daily != 0 else None
        ),
    }


def split_metrics(frame: pd.DataFrame, *, topk: int, split: str, model_key: str) -> tuple[dict[str, Any], pd.DataFrame]:
    eligible_rows = int(len(frame))
    scored = frame.dropna(subset=["effective_score", "forward_return_5d"]).copy()
    scored_rows = int(len(scored))
    if scored.empty:
        empty = pd.DataFrame()
        return {
            "coverage": {"eligible_rows": eligible_rows, "scored_rows": 0, "score_coverage": 0.0},
            "rank_ic": {"mean": None, "std": None, "t_stat": None, "daily_count": 0},
            "icir": None,
            "top_bottom_spread": None,
            "topk_proxy": {"topk": topk, "mean_topk_forward_return": None, "topk_minus_nextk": None, "n_days": 0},
            "rankic_damage_decomposition": {},
            "topk_quality_decomposition": {},
        }, empty

    daily_ic = compute_daily_rankic(scored)
    rankic_mean, rankic_std, rankic_t = (
        mean_std_tstat(daily_ic["rank_ic"]) if not daily_ic.empty else (None, None, None)
    )
    decile_curve = compute_decile_curve(scored)
    shape = decile_shape(decile_curve)
    top = next((row["mean_forward_return"] for row in decile_curve if row["decile"] == 1), None)
    bottom = next((row["mean_forward_return"] for row in decile_curve if row["decile"] == 10), None)
    daily_topk, members = topk_daily_and_members(scored, topk=topk, split=split, model_key=model_key)
    topk_mean, _, topk_t = (
        mean_std_tstat(daily_topk["topk_return"]) if not daily_topk.empty else (None, None, None)
    )
    spread_mean, _, spread_t = (
        mean_std_tstat(daily_topk["topk_minus_nextk"]) if not daily_topk.empty else (None, None, None)
    )
    yearly_rankic = []
    if not daily_ic.empty:
        daily_ic["year"] = daily_ic["signal_date"].astype(str).str[:4]
        for year, group in daily_ic.groupby("year", sort=True):
            y_mean, y_std, _ = mean_std_tstat(group["rank_ic"])
            yearly_rankic.append({"year": str(year), "rank_ic_mean": y_mean, "rank_ic_std": y_std, "n_days": int(len(group))})
    yearly_topk = []
    if not daily_topk.empty:
        daily_topk["year"] = daily_topk["signal_date"].astype(str).str[:4]
        for year, group in daily_topk.groupby("year", sort=True):
            y_topk, _, _ = mean_std_tstat(group["topk_return"])
            y_spread, _, _ = mean_std_tstat(group["topk_minus_nextk"])
            yearly_topk.append({"year": str(year), "topk_return_mean": y_topk, "topk_minus_nextk_mean": y_spread, "n_days": int(len(group))})
    return {
        "coverage": {
            "eligible_rows": eligible_rows,
            "scored_rows": scored_rows,
            "score_coverage": safe_float(scored_rows / eligible_rows) if eligible_rows else None,
            "signal_dates": int(scored["signal_date"].nunique()),
            "instruments": int(scored["instrument"].nunique()),
        },
        "rank_ic": {"mean": rankic_mean, "std": rankic_std, "t_stat": rankic_t, "daily_count": int(len(daily_ic))},
        "icir": safe_float(rankic_mean / rankic_std) if rankic_mean is not None and rankic_std not in (None, 0.0) else None,
        "top_bottom_spread": top - bottom if top is not None and bottom is not None else None,
        "topk_proxy": {
            "topk": topk,
            "n_days": int(len(daily_topk)),
            "mean_topk_forward_return": topk_mean,
            "topk_mean_t_stat": topk_t,
            "topk_minus_nextk": spread_mean,
            "topk_minus_nextk_t_stat": spread_t,
        },
        "rankic_damage_decomposition": {
            "decile_return_curve": decile_curve,
            "daily_rankic_distribution": summarize_series(daily_ic["rank_ic"] if not daily_ic.empty else pd.Series(dtype=float)),
            "yearly_rankic_distribution": yearly_rankic,
            "yearly_topk_distribution": yearly_topk,
            "score_dispersion_compression": compute_daily_score_dispersion(scored),
            **shape,
        },
        "topk_quality_decomposition": contribution_stats(daily_topk, members),
    }, members


def diagnose_models(con: duckdb.DuckDBPyConnection, specs: dict[str, ModelSpec], topk: int) -> tuple[dict[str, Any], pd.DataFrame]:
    diagnostics = {}
    all_members = []
    for spec in specs.values():
        frame = fetch_model_frame(con, spec)
        split_payload = {}
        for split, mask in [("train", frame["train_flag"]), ("validation", frame["validation_flag"])]:
            metrics, members = split_metrics(frame[mask], topk=topk, split=split, model_key=spec.key)
            split_payload[split] = metrics
            all_members.append(members)
        diagnostics[spec.key] = {
            "candidate_scheme_id": spec.candidate_scheme_id,
            "status": spec.status,
            "label": spec.label,
            **split_payload,
        }
    topk_members = pd.concat(all_members, ignore_index=True) if all_members else pd.DataFrame()
    return diagnostics, topk_members


def delta(a: float | None, b: float | None) -> float | None:
    return a - b if a is not None and b is not None else None


def comparison_delta(diagnostics: dict[str, Any], comparator: str, split: str) -> dict[str, Any]:
    comp = diagnostics[COMPOSITE][split]
    other = diagnostics[comparator][split]
    return {
        "rankic_delta": delta(comp["rank_ic"]["mean"], other["rank_ic"]["mean"]),
        "icir_delta": delta(comp["icir"], other["icir"]),
        "top_bottom_delta": delta(comp["top_bottom_spread"], other["top_bottom_spread"]),
        "topk_proxy_delta": delta(comp["topk_proxy"]["mean_topk_forward_return"], other["topk_proxy"]["mean_topk_forward_return"]),
        "topk_minus_nextk_delta": delta(comp["topk_proxy"]["topk_minus_nextk"], other["topk_proxy"]["topk_minus_nextk"]),
        "coverage_delta": delta(comp["coverage"]["score_coverage"], other["coverage"]["score_coverage"]),
    }


def build_comparisons(diagnostics: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for comparator in [NO_P98, LIQUIDITY, P98]:
        result[f"composite_vs_{comparator}"] = {
            "reference_status": diagnostics[comparator]["status"],
            "train": comparison_delta(diagnostics, comparator, "train"),
            "validation": comparison_delta(diagnostics, comparator, "validation"),
        }
    result[f"composite_vs_{P98}"]["p98_note"] = "p98 is conditional reference only"
    return result


def overlap_pair(members: pd.DataFrame, comparator: str, split: str) -> dict[str, Any]:
    comp = members[(members["model_key"] == COMPOSITE) & (members["split"] == split)]
    other = members[(members["model_key"] == comparator) & (members["split"] == split)]
    daily_rows = []
    for signal_date in sorted(set(comp["signal_date"]) | set(other["signal_date"])):
        c_day = comp[comp["signal_date"] == signal_date]
        o_day = other[other["signal_date"] == signal_date]
        c_map = dict(zip(c_day["instrument"], c_day["forward_return_5d"]))
        o_map = dict(zip(o_day["instrument"], o_day["forward_return_5d"]))
        c_set = set(c_map)
        o_set = set(o_map)
        overlap = c_set & o_set
        union = c_set | o_set
        c_only = c_set - o_set
        o_only = o_set - c_set
        daily_rows.append(
            {
                "signal_date": str(signal_date),
                "overlap_count": len(overlap),
                "union_count": len(union),
                "jaccard": len(overlap) / len(union) if union else None,
                "composite_only_mean_return": safe_float(pd.Series([c_map[x] for x in c_only]).mean()) if c_only else None,
                "comparator_only_mean_return": safe_float(pd.Series([o_map[x] for x in o_only]).mean()) if o_only else None,
                "overlap_mean_return": safe_float(pd.Series([c_map[x] for x in overlap]).mean()) if overlap else None,
            }
        )
    daily = pd.DataFrame(daily_rows)
    if daily.empty:
        return {"daily_count": 0}
    return {
        "daily_count": int(len(daily)),
        "overlap_count": {
            "total": int(daily["overlap_count"].sum()),
            "mean": safe_float(daily["overlap_count"].mean()),
            "median": safe_float(daily["overlap_count"].median()),
        },
        "jaccard": summarize_series(daily["jaccard"]),
        "composite_only_realized_return": summarize_series(daily["composite_only_mean_return"]),
        "comparator_only_realized_return": summarize_series(daily["comparator_only_mean_return"]),
        "composite_only_minus_comparator_only": delta(
            safe_float(daily["composite_only_mean_return"].mean()),
            safe_float(daily["comparator_only_mean_return"].mean()),
        ),
        "overlap_realized_return": summarize_series(daily["overlap_mean_return"]),
        "daily_overlap_distribution": daily[["signal_date", "overlap_count", "jaccard"]].to_dict(orient="records"),
    }


def build_overlap(members: pd.DataFrame) -> dict[str, Any]:
    return {
        split: {
            f"composite_vs_{comparator}": overlap_pair(members, comparator, split)
            for comparator in [NO_P98, LIQUIDITY, P98]
        }
        for split in ["train", "validation"]
    }


def load_topk_exposure(con: duckdb.DuckDBPyConnection, members: pd.DataFrame) -> pd.DataFrame:
    if members.empty:
        return members
    con.register("topk_members_df", members)
    return con.execute(
        """
        SELECT
            m.*,
            e.amount,
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
            e.amount_percentile_asc
        FROM topk_members_df m
        LEFT JOIN exposure_t e
          ON m.snapshot_id = e.snapshot_id
         AND m.instrument = e.instrument
         AND m.signal_date = e.signal_date
        """
    ).df()


def summarize_category(frame: pd.DataFrame, column: str) -> dict[str, Any]:
    if column not in frame or frame[column].dropna().empty:
        return {"status": "unavailable"}
    counts = frame[column].fillna("missing").astype(str).value_counts()
    total = counts.sum()
    return {
        "status": "available",
        "rows": int(total),
        "distribution": [
            {"value": str(value), "count": int(count), "share": safe_float(count / total) if total else None}
            for value, count in counts.items()
        ],
    }


def summarize_boolean(frame: pd.DataFrame, column: str) -> dict[str, Any]:
    if column not in frame or frame[column].dropna().empty:
        return {"status": "unavailable"}
    values = frame[column].fillna(False).astype(bool)
    return {"status": "available", "true_count": int(values.sum()), "true_share": safe_float(values.mean()), "rows": int(len(values))}


def add_buckets(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    if "amount_percentile_asc" in work and not work["amount_percentile_asc"].dropna().empty:
        pct = work["amount_percentile_asc"]
    elif "amount" in work and not work["amount"].dropna().empty:
        pct = work.groupby("signal_date")["amount"].rank(pct=True, method="average")
    else:
        pct = None
    if pct is not None:
        work["liquidity_bucket"] = pd.cut(
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


def exposure_summary(frame: pd.DataFrame) -> dict[str, Any]:
    work = add_buckets(frame)
    return {
        "board_type": summarize_category(work, "board_type"),
        "exchange": summarize_category(work, "exchange"),
        "limit_status": {
            col: summarize_boolean(work, col)
            for col in ["is_limit_up", "is_limit_down", "open_at_up_limit", "close_at_down_limit"]
        },
        "tradability_status": {
            col: summarize_boolean(work, col)
            for col in ["entry_buyable", "no_trade_flag", "is_suspended", "volume_zero_flag", "amount_zero_flag"]
        },
        "liquidity_bucket": summarize_category(work, "liquidity_bucket"),
        "listing_age_days_bucket": summarize_category(work, "listing_age_days_bucket"),
    }


def build_exposure_decomposition(topk_exposure: pd.DataFrame) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for split in ["train", "validation"]:
        split_frame = topk_exposure[topk_exposure["split"] == split]
        result[split] = {}
        for model_key in [COMPOSITE, NO_P98, LIQUIDITY, P98]:
            result[split][model_key] = exposure_summary(split_frame[split_frame["model_key"] == model_key])
        for comparator in [NO_P98, LIQUIDITY, P98]:
            comp = split_frame[split_frame["model_key"] == COMPOSITE]
            other = split_frame[split_frame["model_key"] == comparator]
            rows = []
            for signal_date in sorted(set(comp["signal_date"]) | set(other["signal_date"])):
                c_day = comp[comp["signal_date"] == signal_date]
                o_day = other[other["signal_date"] == signal_date]
                c_set = set(c_day["instrument"])
                o_set = set(o_day["instrument"])
                c_only = c_day[c_day["instrument"].isin(c_set - o_set)]
                rows.append(c_only)
            comp_only = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
            result[split][f"composite_only_vs_{comparator}"] = exposure_summary(comp_only)
    return result


def yearly_map(diagnostics: dict[str, Any], model_key: str, split: str, metric: str) -> dict[str, float | None]:
    rows = diagnostics[model_key][split]["rankic_damage_decomposition"]["yearly_topk_distribution"]
    if metric == "rankic":
        rows = diagnostics[model_key][split]["rankic_damage_decomposition"]["yearly_rankic_distribution"]
        return {row["year"]: row.get("rank_ic_mean") for row in rows}
    return {row["year"]: row.get(metric) for row in rows}


def build_stability_checks(diagnostics: dict[str, Any]) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    comp_train_spread = diagnostics[COMPOSITE]["train"]["topk_proxy"]["topk_minus_nextk"]
    comp_val_spread = diagnostics[COMPOSITE]["validation"]["topk_proxy"]["topk_minus_nextk"]
    comp_val_year_spread = yearly_map(diagnostics, COMPOSITE, "validation", "topk_minus_nextk_mean")
    for comparator in [NO_P98, LIQUIDITY, P98]:
        train_delta = comparison_delta(diagnostics, comparator, "train")
        val_delta = comparison_delta(diagnostics, comparator, "validation")
        topk_consistent = (
            train_delta["topk_proxy_delta"] is not None
            and val_delta["topk_proxy_delta"] is not None
            and train_delta["topk_proxy_delta"] > 0
            and val_delta["topk_proxy_delta"] > 0
        )
        spread_delta_consistent = (
            train_delta["topk_minus_nextk_delta"] is not None
            and val_delta["topk_minus_nextk_delta"] is not None
            and train_delta["topk_minus_nextk_delta"] > 0
            and val_delta["topk_minus_nextk_delta"] > 0
        )
        rankic_damage_consistent = (
            train_delta["rankic_delta"] is not None
            and val_delta["rankic_delta"] is not None
            and train_delta["rankic_delta"] < 0
            and val_delta["rankic_delta"] < 0
        )
        comp_year_topk = yearly_map(diagnostics, COMPOSITE, "validation", "topk_return_mean")
        other_year_topk = yearly_map(diagnostics, comparator, "validation", "topk_return_mean")
        comp_year_rankic = yearly_map(diagnostics, COMPOSITE, "validation", "rankic")
        other_year_rankic = yearly_map(diagnostics, comparator, "validation", "rankic")
        years = sorted(set(comp_year_topk) & set(other_year_topk))
        topk_by_year = {
            year: delta(comp_year_topk.get(year), other_year_topk.get(year))
            for year in years
        }
        rankic_by_year = {
            year: delta(comp_year_rankic.get(year), other_year_rankic.get(year))
            for year in sorted(set(comp_year_rankic) & set(other_year_rankic))
        }
        checks[f"composite_vs_{comparator}"] = {
            "train_vs_validation_topk_direction_consistent": bool(topk_consistent),
            "train_vs_validation_topk_minus_nextk_delta_consistent": bool(spread_delta_consistent),
            "composite_train_topk_minus_nextk_positive": bool(comp_train_spread is not None and comp_train_spread > 0),
            "composite_validation_topk_minus_nextk_positive": bool(comp_val_spread is not None and comp_val_spread > 0),
            "train_vs_validation_rankic_damage_direction_consistent": bool(rankic_damage_consistent),
            "validation_yearly_topk_improvement_delta": topk_by_year,
            "validation_topk_improvement_exists_each_year": bool(topk_by_year) and all(v is not None and v > 0 for v in topk_by_year.values()),
            "composite_validation_yearly_topk_minus_nextk": comp_val_year_spread,
            "composite_validation_topk_minus_nextk_positive_each_year": (
                bool(comp_val_year_spread) and all(v is not None and v > 0 for v in comp_val_year_spread.values())
            ),
            "validation_yearly_rankic_damage_delta": rankic_by_year,
            "validation_rankic_damage_exists_each_year": bool(rankic_by_year) and all(v is not None and v < 0 for v in rankic_by_year.values()),
        }
    return checks


def build_decision_summary(payload: dict[str, Any]) -> dict[str, Any]:
    checks = payload["stability_checks"]["composite_vs_no_p98_reversal_baseline_v1"]
    val = payload["comparisons"]["composite_vs_no_p98_reversal_baseline_v1"]["validation"]
    concentration = payload["diagnostics"][COMPOSITE]["validation"]["topk_quality_decomposition"]
    edge_concentration = concentration.get("percentage_of_daily_edge_from_top_5pct_days")
    topk_stable = bool(
        checks["train_vs_validation_topk_direction_consistent"]
        and checks["train_vs_validation_topk_minus_nextk_delta_consistent"]
        and checks["composite_train_topk_minus_nextk_positive"]
        and checks["composite_validation_topk_minus_nextk_positive"]
        and checks["validation_topk_improvement_exists_each_year"]
        and checks["composite_validation_topk_minus_nextk_positive_each_year"]
    )
    rankic_damage_severe = val["rankic_delta"] is not None and val["rankic_delta"] < -0.01
    concentrated = edge_concentration is not None and edge_concentration > 0.5
    recommend = bool(topk_stable and not rankic_damage_severe and not concentrated)
    return {
        "composite_topk_improvement_stable_vs_no_p98": topk_stable,
        "composite_topk_proxy_delta_stable_vs_no_p98": bool(
            checks["train_vs_validation_topk_direction_consistent"] and checks["validation_topk_improvement_exists_each_year"]
        ),
        "composite_topk_minus_nextk_stable_positive": bool(
            checks["composite_train_topk_minus_nextk_positive"]
            and checks["composite_validation_topk_minus_nextk_positive"]
            and checks["composite_validation_topk_minus_nextk_positive_each_year"]
        ),
        "rankic_damage_severe_vs_no_p98": rankic_damage_severe,
        "topk_edge_concentrated_in_top_5pct_days": concentrated,
        "recommend_next_preregistered_candidate": recommend,
        "recommend_portfolio_dry_run": False,
        "continue_portfolio_ban": True,
        "frozen_test_accessed": False,
        "training_backtest_or_portfolio_run": False,
        "interpretation": (
            "May proceed only to preregistered clean candidate design."
            if recommend
            else "Do not open a new candidate from this evidence; the decomposition does not clear stability and RankIC damage rules."
        ),
    }


def build_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Clean Composite TopK Improvement Decomposition",
        "",
        "Train/validation diagnosis only. Not OOS, not strategy approval, not portfolio, not backtest, not formal metrics/readout, and frozen test remains unread.",
        "",
        "## Boundary",
        "",
        f"- p98 status: `{payload['p98_reference_status']}`",
        f"- portfolio dry-run: `{payload['portfolio_run_executed']}`",
        f"- training/backtest/portfolio: `{payload['training_performed']}` / `{payload['backtest_run_executed']}` / `{payload['portfolio_run_executed']}`",
        f"- blocked fields used: `{payload['blocked_fields_used']}`",
        "",
        "## Validation Deltas",
        "",
    ]
    for name, section in payload["comparisons"].items():
        val = section["validation"]
        lines.append(
            f"- `{name}`: RankIC delta `{val['rankic_delta']}`, ICIR delta `{val['icir_delta']}`, "
            f"TopK delta `{val['topk_proxy_delta']}`, TopK-minus-nextK delta `{val['topk_minus_nextk_delta']}`, "
            f"coverage delta `{val['coverage_delta']}`"
        )
    lines.extend(["", "## Stability", ""])
    for name, section in payload["stability_checks"].items():
        lines.append(
            f"- `{name}`: train/validation TopK direction `{section['train_vs_validation_topk_direction_consistent']}`, "
            f"train/validation TopK-minus-nextK delta `{section['train_vs_validation_topk_minus_nextk_delta_consistent']}`, "
            f"composite train TopK-minus-nextK positive `{section['composite_train_topk_minus_nextk_positive']}`, "
            f"validation yearly TopK each year `{section['validation_topk_improvement_exists_each_year']}`, "
            f"validation yearly TopK-minus-nextK positive each year `{section['composite_validation_topk_minus_nextk_positive_each_year']}`, "
            f"validation yearly RankIC damage each year `{section['validation_rankic_damage_exists_each_year']}`"
        )
    decision = payload["decision_summary"]
    lines.extend(
        [
            "",
            "## Decision Summary",
            "",
            f"- composite TopK stable vs no_p98: `{decision['composite_topk_improvement_stable_vs_no_p98']}`",
            f"- RankIC damage severe vs no_p98: `{decision['rankic_damage_severe_vs_no_p98']}`",
            f"- TopK edge concentrated in top 5% days: `{decision['topk_edge_concentrated_in_top_5pct_days']}`",
            f"- recommend next preregistered candidate: `{decision['recommend_next_preregistered_candidate']}`",
            f"- recommend portfolio dry-run: `{decision['recommend_portfolio_dry_run']}`",
            f"- interpretation: {decision['interpretation']}",
        ]
    )
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
        diagnostics, topk_members = diagnose_models(con, specs, args.topk)
        topk_exposure = load_topk_exposure(con, topk_members)
        payload = {
            "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "round_id": "clean_composite_topk_improvement_decomposition_round_v1",
            "diagnosis_label": "TRAINVAL_DIAGNOSIS_ONLY_NOT_OOS_NOT_PORTFOLIO",
            "training_performed": False,
            "backtest_run_executed": False,
            "portfolio_run_executed": False,
            "holdings_generated": False,
            "formal_metrics_generated": False,
            "frozen_test_accessed": False,
            "p98_reference_status": "conditional_reference_only",
            "p98_used_as_clean_component": False,
            "blocked_fields": sorted(BLOCKED_FIELDS),
            "blocked_fields_used": [],
            "used_exposure_fields": USED_EXPOSURE_FIELDS,
            "topk": args.topk,
            "diagnostics": diagnostics,
            "comparisons": build_comparisons(diagnostics),
            "topk_overlap_divergence": build_overlap(topk_members),
            "exposure_decomposition": build_exposure_decomposition(topk_exposure),
            "stability_checks": build_stability_checks(diagnostics),
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
