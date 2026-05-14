#!/usr/bin/env python3
"""
Diagnose market-state conditional rank-band profiles.

This is exploratory descriptive research only. It does not create candidates,
train, backtest, run portfolio, generate holdings/readouts, or read frozen test.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from diagnose_rank_band_full_profile import (
    BLOCKED_FIELDS,
    CLEAN_MODEL_KEYS,
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
    FIXED_RANK_BANDS,
    MULTI,
    P98,
    REFERENCE_KEYS,
    DiagnosisError,
    build_specs,
    daily_band_members,
    ensure_exists,
    fetch_model_frame,
    register_views,
    safe_float,
)


DEFAULT_OUTPUT_JSON = Path("/private/tmp/market_state_conditional_rank_band_profile.json")
DEFAULT_OUTPUT_MD = Path("/private/tmp/market_state_conditional_rank_band_profile.md")

REQUIRED_CONDITION_FIELDS = [
    "amount_bucket_3",
    "amount_zero_flag",
    "volume_zero_flag",
    "board_type",
    "exchange",
    "is_limit_up",
    "is_limit_down",
    "open_at_up_limit",
    "close_at_down_limit",
    "entry_buyable",
    "exit_sellable",
    "sellable_retry_next_open",
    "no_trade_flag",
    "is_suspended",
    "listing_age_days_bucket",
    "daily_amount_aggregate_bucket",
    "daily_universe_median_return",
    "daily_universe_volatility_proxy",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose market-state conditional rank-band profile.")
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


def top_n_contribution(returns: pd.Series, positive: bool) -> float | None:
    clean = returns.dropna()
    if clean.empty:
        return None
    if positive:
        pos = clean[clean > 0].sort_values(ascending=False)
        if pos.empty or pos.sum() == 0:
            return None
        n = max(1, math.ceil(len(pos) * 0.05))
        return safe_float(pos.head(n).sum() / pos.sum())
    neg = clean[clean < 0].sort_values(ascending=True)
    if neg.empty or neg.sum() == 0:
        return None
    n = max(1, math.ceil(len(neg) * 0.05))
    return safe_float(abs(neg.head(n).sum()) / abs(neg.sum()))


def condition_status(frame: pd.DataFrame) -> dict[str, str]:
    status = {}
    for field in REQUIRED_CONDITION_FIELDS:
        if field in frame and not frame[field].dropna().empty:
            status[field] = "available"
        else:
            status[field] = "unavailable"
    return status


def add_condition_fields(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    if "amount_percentile_asc" in work and not work["amount_percentile_asc"].dropna().empty:
        work["amount_bucket_3"] = pd.cut(
            work["amount_percentile_asc"],
            bins=[0.0, 0.2, 0.8, 1.0],
            labels=["bottom_20pct", "mid_60pct", "top_20pct"],
            include_lowest=True,
        ).astype("object")
    else:
        work["amount_bucket_3"] = None
    if "listing_age_days" in work and not work["listing_age_days"].dropna().empty:
        work["listing_age_days_bucket"] = pd.cut(
            work["listing_age_days"],
            bins=[-math.inf, 120, 252, 756, math.inf],
            labels=["lt_120d", "120_252d", "252_756d", "gte_756d"],
        ).astype("object")
    else:
        work["listing_age_days_bucket"] = None
    for field in ["exit_sellable", "sellable_retry_next_open", "daily_universe_median_return", "daily_universe_volatility_proxy"]:
        if field not in work:
            work[field] = None
    if "amount" in work and not work["amount"].dropna().empty:
        daily_amount = work.groupby("signal_date", sort=True)["amount"].sum().rename("daily_amount_sum")
        work = work.merge(daily_amount, on="signal_date", how="left")
        ranks = work[["signal_date", "daily_amount_sum"]].drop_duplicates().sort_values("signal_date")
        if len(ranks) >= 3:
            ranks["daily_amount_aggregate_bucket"] = pd.qcut(
                ranks["daily_amount_sum"].rank(method="first"),
                q=3,
                labels=["low_daily_amount", "mid_daily_amount", "high_daily_amount"],
            ).astype("object")
        else:
            ranks["daily_amount_aggregate_bucket"] = "insufficient_days"
        work = work.merge(ranks[["signal_date", "daily_amount_aggregate_bucket"]], on="signal_date", how="left")
    else:
        work["daily_amount_aggregate_bucket"] = None
    return work


def build_members(frame: pd.DataFrame, split: str, model_key: str) -> pd.DataFrame:
    scored = add_condition_fields(frame.dropna(subset=["effective_score", "forward_return_5d"]).copy())
    _, members = daily_band_members(scored, split, model_key)
    return members


def condition_values(members: pd.DataFrame, field: str) -> list[str]:
    if field not in members or members[field].dropna().empty:
        return []
    return sorted(members[field].dropna().astype(str).unique().tolist())


def summarize_condition_field(members: pd.DataFrame, field: str, baseline_diff: float | None) -> dict[str, Any]:
    if field not in members or members[field].dropna().empty:
        return {"status": "unavailable"}
    work = members[["signal_date", "rank_band", "forward_return_5d", field]].dropna(subset=[field]).copy()
    if work.empty:
        return {"status": "unavailable"}
    work["_condition_value"] = work[field].astype(str)
    grouped = work.groupby(["_condition_value", "rank_band"], sort=True)["forward_return_5d"]
    stats = grouped.agg(count="count", mean_return="mean", median_return="median").reset_index()
    daily = (
        work.groupby(["_condition_value", "rank_band", "signal_date"], sort=True)["forward_return_5d"]
        .mean()
        .reset_index(name="daily_return")
    )
    daily_win = (
        daily.assign(win=daily["daily_return"] > 0)
        .groupby(["_condition_value", "rank_band"], sort=True)["win"]
        .mean()
        .to_dict()
    )
    tail_records = []
    for (condition_value, rank_band), series in grouped:
        tail_records.append(
            {
                "_condition_value": condition_value,
                "rank_band": rank_band,
                "best_5pct_contribution": top_n_contribution(series, positive=True),
                "worst_5pct_damage": top_n_contribution(series, positive=False),
            }
        )
    tail = pd.DataFrame(tail_records)
    merged = stats.merge(tail, on=["_condition_value", "rank_band"], how="left")
    mean_lookup = {
        (row["_condition_value"], row["rank_band"]): safe_float(row["mean_return"])
        for _, row in merged.iterrows()
    }
    values: dict[str, Any] = {}
    for condition_value in sorted(merged["_condition_value"].unique().tolist()):
        top_mean = mean_lookup.get((condition_value, "rank_1_30"))
        mid_mean = mean_lookup.get((condition_value, "rank_31_100"))
        top_minus_mid = top_mean - mid_mean if top_mean is not None and mid_mean is not None else None
        mid_minus_top = mid_mean - top_mean if top_mean is not None and mid_mean is not None else None
        band_payload: dict[str, Any] = {}
        value_rows = merged[merged["_condition_value"] == condition_value]
        row_lookup = {row["rank_band"]: row for _, row in value_rows.iterrows()}
        for band_name in FIXED_RANK_BANDS:
            row = row_lookup.get(band_name)
            if row is None:
                band_payload[band_name] = {
                    "count": 0,
                    "mean_return": None,
                    "median_return": None,
                    "daily_win_rate_vs_0": None,
                    "topk_minus_rank31_100_within_condition": safe_float(top_minus_mid),
                    "rank31_100_minus_topk_within_condition": safe_float(mid_minus_top),
                    "worst_5pct_damage": None,
                    "best_5pct_contribution": None,
                    "condition_worsens_head_failure": False,
                    "condition_strengthens_mid_rank": False,
                }
                continue
            band_payload[band_name] = {
                "count": int(row["count"]),
                "mean_return": safe_float(row["mean_return"]),
                "median_return": safe_float(row["median_return"]),
                "daily_win_rate_vs_0": safe_float(daily_win.get((condition_value, band_name))),
                "topk_minus_rank31_100_within_condition": safe_float(top_minus_mid),
                "rank31_100_minus_topk_within_condition": safe_float(mid_minus_top),
                "worst_5pct_damage": safe_float(row["worst_5pct_damage"]),
                "best_5pct_contribution": safe_float(row["best_5pct_contribution"]),
                "condition_worsens_head_failure": bool(top_minus_mid is not None and baseline_diff is not None and top_minus_mid < baseline_diff),
                "condition_strengthens_mid_rank": bool(mid_minus_top is not None and baseline_diff is not None and mid_minus_top > -baseline_diff),
            }
        values[condition_value] = band_payload
    return {"status": "available", "values": values}


def summarize_split_conditions(members: pd.DataFrame) -> dict[str, Any]:
    if members.empty:
        return {"status": "empty", "conditions": {}}
    top_all = members[members["rank_band"] == "rank_1_30"]["forward_return_5d"].mean()
    mid_all = members[members["rank_band"] == "rank_31_100"]["forward_return_5d"].mean()
    baseline_diff = safe_float(top_all - mid_all)
    conditions: dict[str, Any] = {}
    for field in REQUIRED_CONDITION_FIELDS:
        conditions[field] = summarize_condition_field(members, field, baseline_diff)
    return {"status": "ok", "baseline_topk_minus_rank31_100": baseline_diff, "conditions": conditions}


def top_condition_effects(split_payload: dict[str, Any]) -> dict[str, Any]:
    head = []
    mid = []
    for field, field_payload in split_payload.get("conditions", {}).items():
        if field_payload.get("status") != "available":
            continue
        for value, value_payload in field_payload["values"].items():
            metric = value_payload["rank_1_30"].get("topk_minus_rank31_100_within_condition")
            inv = value_payload["rank_1_30"].get("rank31_100_minus_topk_within_condition")
            if metric is not None:
                head.append({"condition": field, "value": value, "topk_minus_rank31_100": metric})
            if inv is not None:
                mid.append({"condition": field, "value": value, "rank31_100_minus_topk": inv})
    return {
        "strongest_head_failure_conditions": sorted(head, key=lambda x: x["topk_minus_rank31_100"])[:10],
        "strongest_mid_rank_strength_conditions": sorted(mid, key=lambda x: x["rank31_100_minus_topk"], reverse=True)[:10],
    }


def yearly_condition_stability(members: pd.DataFrame) -> dict[str, Any]:
    if members.empty:
        return {}
    work = members.copy()
    work["year"] = work["signal_date"].astype(str).str[:4]
    result: dict[str, Any] = {}
    for field in REQUIRED_CONDITION_FIELDS:
        if field not in work or work[field].dropna().empty:
            result[field] = {"status": "unavailable"}
            continue
        field_result = {"status": "available", "values": {}}
        for value in condition_values(work, field):
            value_result = {}
            subset = work[work[field].astype(str) == value]
            for year, group in subset.groupby("year", sort=True):
                top = group[group["rank_band"] == "rank_1_30"]["forward_return_5d"].mean()
                mid = group[group["rank_band"] == "rank_31_100"]["forward_return_5d"].mean()
                value_result[str(year)] = {
                    "topk_minus_rank31_100": safe_float(top - mid),
                    "rank31_100_minus_topk": safe_float(mid - top),
                }
            diffs = [v["rank31_100_minus_topk"] for v in value_result.values() if v["rank31_100_minus_topk"] is not None]
            field_result["values"][value] = {
                "yearly": value_result,
                "validation_yearly_same_positive_direction": bool(diffs and all(d > 0 for d in diffs)),
            }
        result[field] = field_result
    return result


def diagnose_models(con: duckdb.DuckDBPyConnection, specs: dict[str, Any]) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {}
    for spec in specs.values():
        frame = fetch_model_frame(con, spec)
        model_payload = {
            "candidate_scheme_id": spec.candidate_scheme_id,
            "status": spec.status,
            "label": spec.label,
        }
        for split_name, mask in [("train", frame["train_flag"]), ("validation", frame["validation_flag"])]:
            members = build_members(frame[mask], split_name, spec.key)
            split_payload = summarize_split_conditions(members)
            split_payload["condition_effect_summary"] = top_condition_effects(split_payload)
            if split_name == "validation":
                split_payload["validation_yearly_stability"] = yearly_condition_stability(members)
            model_payload[split_name] = split_payload
            model_payload[f"{split_name}_condition_availability"] = condition_status(add_condition_fields(frame[mask]))
        diagnostics[spec.key] = model_payload
    return diagnostics


def cross_model_summary(diagnostics: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for split in ["train", "validation"]:
        split_result: dict[str, Any] = {}
        for field in REQUIRED_CONDITION_FIELDS:
            values: dict[str, dict[str, int]] = {}
            for model in CLEAN_MODEL_KEYS:
                field_payload = diagnostics[model][split]["conditions"].get(field, {})
                if field_payload.get("status") != "available":
                    continue
                for value, value_payload in field_payload["values"].items():
                    metric = value_payload["rank_1_30"].get("rank31_100_minus_topk_within_condition")
                    if metric is None:
                        continue
                    values.setdefault(value, {"n_models": 0, "n_mid_rank_stronger": 0, "n_head_failure": 0})
                    values[value]["n_models"] += 1
                    if metric > 0:
                        values[value]["n_mid_rank_stronger"] += 1
                        values[value]["n_head_failure"] += 1
            split_result[field] = values if values else {"status": "unavailable_or_empty"}
        result[split] = split_result
    return result


def condition_direction_consistency_summary(diagnostics: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field in REQUIRED_CONDITION_FIELDS:
        values: dict[str, Any] = {}
        for model in CLEAN_MODEL_KEYS:
            train_field = diagnostics[model]["train"]["conditions"].get(field, {})
            val_field = diagnostics[model]["validation"]["conditions"].get(field, {})
            if train_field.get("status") != "available" or val_field.get("status") != "available":
                continue
            for value in sorted(set(train_field["values"]) & set(val_field["values"])):
                train_metric = train_field["values"][value]["rank_1_30"].get("rank31_100_minus_topk_within_condition")
                val_metric = val_field["values"][value]["rank_1_30"].get("rank31_100_minus_topk_within_condition")
                if train_metric is None or val_metric is None:
                    continue
                values.setdefault(
                    value,
                    {
                        "n_models": 0,
                        "n_train_validation_same_positive_direction": 0,
                        "n_validation_yearly_same_positive_direction": 0,
                        "models_same_positive_direction": [],
                        "models_validation_yearly_stable": [],
                    },
                )
                values[value]["n_models"] += 1
                if train_metric > 0 and val_metric > 0:
                    values[value]["n_train_validation_same_positive_direction"] += 1
                    values[value]["models_same_positive_direction"].append(model)
                yearly_payload = (
                    diagnostics[model]["validation"]
                    .get("validation_yearly_stability", {})
                    .get(field, {})
                    .get("values", {})
                    .get(value, {})
                )
                if yearly_payload.get("validation_yearly_same_positive_direction"):
                    values[value]["n_validation_yearly_same_positive_direction"] += 1
                    values[value]["models_validation_yearly_stable"].append(model)
        result[field] = values if values else {"status": "unavailable_or_empty"}
    return result


def build_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Market-State Conditional Rank-Band Profile",
        "",
        "This is exploratory descriptive research. It is descriptive-only, not alpha, not a candidate, not portfolio, not OOS, and frozen test remains unread.",
        "",
        "## Boundary",
        "",
        "- no alpha claim",
        "- no candidate",
        "- no new baseline",
        "- no v4",
        "- no training",
        "- no backtest",
        "- no portfolio / no portfolio dry-run",
        "- no holdings / backtest_daily / formal metrics/readout",
        "- no frozen test",
        "- trainval not OOS",
        "- p98 / multi_equal_weight_v1 conditional reference only",
        "- no validation tuning",
        "- no trading rule",
        "",
        "## Unavailable Fields",
        "",
    ]
    for field, status in payload["field_availability"].items():
        if status == "unavailable":
            lines.append(f"- `{field}`: unavailable")
    lines.extend(["", "## Validation Strongest Condition Snapshots", ""])
    for model in CLEAN_MODEL_KEYS:
        lines.append(f"### {model}")
        effects = payload["diagnostics"][model]["validation"]["condition_effect_summary"]
        head = effects["strongest_head_failure_conditions"][:3]
        mid = effects["strongest_mid_rank_strength_conditions"][:3]
        lines.append(f"- strongest_head_failure_conditions: `{head}`")
        lines.append(f"- strongest_mid_rank_strength_conditions: `{mid}`")
        lines.append("")
    lines.extend(
        [
            "## Conditional References",
            "",
            "- `p98_conditional_reference`: conditional reference only",
            "- `multi_equal_weight_v1_conditional_reference`: conditional reference only",
            "",
            "## Future Paper-Only Hypotheses",
            "",
            "- Whether high-liquidity states intensify TopK failure.",
            "- Whether limit/tradability states explain a larger share of TopK weakness than board/exchange.",
            "- Whether listing-age calendar buckets change mid-rank strength without using blocked fields.",
            "- Whether conditional references show different state sensitivity from clean scores.",
            "",
            "## Final Statement",
            "",
            "This output cannot directly form any trading rule. It gives no deployment conclusion and no portfolio recommendation.",
        ]
    )
    return "\n".join(lines) + "\n"


def run(args: argparse.Namespace) -> dict[str, Any]:
    for path, label in [
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
    ]:
        ensure_exists(path, label)
    specs = build_specs(args)
    con = duckdb.connect()
    try:
        register_views(con, args, specs)
        diagnostics = diagnose_models(con, specs)
    finally:
        con.close()
    availability = {}
    for field in REQUIRED_CONDITION_FIELDS:
        statuses = [diagnostics[m]["validation_condition_availability"].get(field) for m in diagnostics]
        availability[field] = "available" if any(s == "available" for s in statuses) else "unavailable"
    payload = {
        "diagnosis_name": "market_state_conditional_rank_band_profile",
        "diagnosis_label": "EXPLORATORY_DESCRIPTIVE_TRAINVAL_NOT_OOS_NOT_PORTFOLIO",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "governance": {
            "research_type": "exploratory_descriptive_research",
            "alpha_claim": False,
            "candidate_created": False,
            "new_baseline_created": False,
            "v4_opened": False,
            "training_run_executed": False,
            "backtest_run_executed": False,
            "portfolio_run_executed": False,
            "portfolio_dry_run_executed": False,
            "holdings_generated": False,
            "formal_metrics_generated": False,
            "frozen_test_accessed": False,
            "trainval_not_oos": True,
            "validation_tuning": False,
            "trading_rule_designed": False,
            "p98_conditional_reference_only": True,
            "multi_equal_weight_v1_conditional_reference_only": True,
        },
        "fixed_rank_bands": FIXED_RANK_BANDS,
        "condition_dimensions": REQUIRED_CONDITION_FIELDS,
        "blocked_fields_used": sorted(BLOCKED_FIELDS & set(REQUIRED_CONDITION_FIELDS)),
        "forbidden_conditioning_fields_used": [],
        "conditional_reference_keys": REFERENCE_KEYS,
        "clean_model_keys": CLEAN_MODEL_KEYS,
        "field_availability": availability,
        "diagnostics": diagnostics,
        "cross_model_summary": cross_model_summary(diagnostics),
        "condition_direction_consistency_summary": condition_direction_consistency_summary(diagnostics),
        "future_paper_only_hypotheses": [
            "High-liquidity states may intensify TopK failure.",
            "Limit/tradability states may explain TopK weakness more than board/exchange.",
            "Listing-age calendar buckets may affect mid-rank strength without blocked fields.",
            "Conditional references may have different state sensitivity from clean scores.",
        ],
        "final_statement": "descriptive only; no alpha; no candidate; no portfolio; no trading rule; no strategy restart",
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
