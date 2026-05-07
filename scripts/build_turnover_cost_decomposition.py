#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Build a turnover / cost decomposition report for one completed run-state attempt.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


ROOT = Path("/Users/wy/MiscProject/multi_factor")
ARTIFACTS_RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
ARTIFACTS_FIXED_TEST_DIR = ROOT / "artifacts" / "fixed_test"
RESEARCH_REGISTRY_DIR = ROOT / "artifacts" / "research_registry"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build turnover / cost decomposition report.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--candidate-scheme-id", required=True)
    parser.add_argument("--research-round-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--as-of-date", required=True)
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def compute_ratio(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def main() -> None:
    args = parse_args()

    run_dir = ARTIFACTS_RUN_STATE_DIR / args.run_id
    fixed_test_dir = ARTIFACTS_FIXED_TEST_DIR / args.run_id
    attempt_dir = run_dir / "attempts" / args.attempt_id
    round_dir = RESEARCH_REGISTRY_DIR / "research_rounds" / args.research_round_id
    round_dir.mkdir(parents=True, exist_ok=True)

    holdings_path = attempt_dir / "holdings.csv"
    weights_path = attempt_dir / "portfolio_weights_daily.csv"
    turnover_path = attempt_dir / "turnover_daily.csv"
    portfolio_manifest_path = attempt_dir / "portfolio_artifacts_manifest.json"
    metrics_path = fixed_test_dir / "metrics.json"
    audit_path = fixed_test_dir / "audit_summary.json"
    trade_stats_path = fixed_test_dir / "trade_statistics_summary.json"
    cost_stress_path = fixed_test_dir / "cost_stress_summary.json"

    for path in (
        holdings_path,
        weights_path,
        turnover_path,
        portfolio_manifest_path,
        metrics_path,
        audit_path,
        trade_stats_path,
        cost_stress_path,
    ):
        if not path.exists():
            raise FileNotFoundError(f"Required input file not found: {path}")

    holdings = pd.read_csv(holdings_path)
    weights = pd.read_csv(weights_path)
    turnover = pd.read_csv(turnover_path)
    portfolio_manifest = load_json(portfolio_manifest_path)
    metrics = load_json(metrics_path)
    audit = load_json(audit_path)
    trade_stats = load_json(trade_stats_path)
    cost_stress = load_json(cost_stress_path)

    weights["buy_component"] = (weights["closing_weight"] - weights["opening_weight"]).clip(lower=0.0)
    weights["sell_component"] = (weights["opening_weight"] - weights["closing_weight"]).clip(lower=0.0)

    weights["entrant_buy"] = (
        (weights["opening_weight"] <= 0.0) & (weights["closing_weight"] > 0.0)
    ) * weights["buy_component"]
    weights["incumbent_resize_buy"] = (
        (weights["opening_weight"] > 0.0) & (weights["closing_weight"] > weights["opening_weight"])
    ) * weights["buy_component"]
    weights["exit_sell"] = (
        (weights["opening_weight"] > 0.0) & (weights["closing_weight"] <= 0.0)
    ) * weights["sell_component"]
    weights["incumbent_resize_sell"] = (
        (weights["closing_weight"] > 0.0) & (weights["opening_weight"] > weights["closing_weight"])
    ) * weights["sell_component"]

    daily_components = (
        weights.groupby("trade_date", as_index=False)[
            [
                "buy_component",
                "sell_component",
                "entrant_buy",
                "incumbent_resize_buy",
                "exit_sell",
                "incumbent_resize_sell",
            ]
        ]
        .sum()
        .sort_values("trade_date")
    )

    daily_merged = turnover.merge(daily_components, on="trade_date", how="left").fillna(0.0)
    daily_merged["gross_flow_notional"] = daily_merged["buy_notional_daily"] + daily_merged["sell_notional_daily"]
    daily_merged["replacement_turnover_component"] = (
        daily_merged["entrant_buy"] + daily_merged["exit_sell"]
    )
    daily_merged["incumbent_resize_component"] = (
        daily_merged["incumbent_resize_buy"] + daily_merged["incumbent_resize_sell"]
    )

    holding_cohort_count = int(portfolio_manifest["assumptions"]["holding_cohort_count"])
    warmup_trade_dates = sorted(daily_merged["trade_date"].tolist())[:holding_cohort_count]
    post_warmup = daily_merged.loc[~daily_merged["trade_date"].isin(warmup_trade_dates)].copy()
    if post_warmup.empty:
        post_warmup = daily_merged.copy()

    total_turnover = float(daily_merged["turnover_daily"].sum())
    total_buy = float(daily_merged["buy_notional_daily"].sum())
    total_sell = float(daily_merged["sell_notional_daily"].sum())
    total_gross_flow = float(daily_merged["gross_flow_notional"].sum())
    total_replacement = float(daily_merged["replacement_turnover_component"].sum())
    total_resize = float(daily_merged["incumbent_resize_component"].sum())

    post_total_turnover = float(post_warmup["turnover_daily"].sum())
    post_total_replacement = float(post_warmup["replacement_turnover_component"].sum())
    post_total_resize = float(post_warmup["incumbent_resize_component"].sum())

    annual_relative_return = float(metrics["annual_relative_return"])
    stressed_annual_relative_return = float(cost_stress["annual_relative_return"])
    annual_relative_cost_drag = stressed_annual_relative_return - annual_relative_return
    annualized_turnover_proxy = float(metrics["avg_turnover_daily"]) * 252.0
    drag_per_1x_annual_turnover = compute_ratio(-annual_relative_cost_drag, annualized_turnover_proxy)

    entry_only_days = int(
        ((daily_merged["entrant_buy"] > 0.0) & (daily_merged["exit_sell"] == 0.0) & (daily_merged["incumbent_resize_component"] == 0.0)).sum()
    )
    exit_only_days = int(
        ((daily_merged["exit_sell"] > 0.0) & (daily_merged["entrant_buy"] == 0.0) & (daily_merged["incumbent_resize_component"] == 0.0)).sum()
    )
    mixed_replacement_days = int(
        ((daily_merged["entrant_buy"] > 0.0) & (daily_merged["exit_sell"] > 0.0)).sum()
    )
    resize_active_days = int((daily_merged["incumbent_resize_component"] > 0.0).sum())

    payload = {
        "candidate_scheme_id": args.candidate_scheme_id,
        "research_round_id": args.research_round_id,
        "run_id": args.run_id,
        "attempt_id": args.attempt_id,
        "as_of_date": args.as_of_date,
        "inputs": {
            "holdings_csv": holdings_path.as_posix(),
            "portfolio_weights_daily_csv": weights_path.as_posix(),
            "turnover_daily_csv": turnover_path.as_posix(),
            "metrics_json": metrics_path.as_posix(),
            "audit_summary_json": audit_path.as_posix(),
            "trade_statistics_summary_json": trade_stats_path.as_posix(),
            "cost_stress_summary_json": cost_stress_path.as_posix(),
        },
        "headline_metrics": {
            "annual_relative_return": annual_relative_return,
            "relative_ir": float(metrics["relative_ir"]),
            "max_drawdown": float(metrics["max_drawdown"]),
            "avg_turnover_daily": float(metrics["avg_turnover_daily"]),
            "cost_stress_annual_relative_return": stressed_annual_relative_return,
            "annual_relative_cost_drag": annual_relative_cost_drag,
        },
        "turnover_decomposition": {
            "total_turnover": total_turnover,
            "total_buy_notional": total_buy,
            "total_sell_notional": total_sell,
            "total_gross_flow_notional": total_gross_flow,
            "replacement_turnover_component_total": total_replacement,
            "incumbent_resize_component_total": total_resize,
            "replacement_share_of_component_flow": compute_ratio(total_replacement, total_replacement + total_resize),
            "incumbent_resize_share_of_component_flow": compute_ratio(total_resize, total_replacement + total_resize),
            "post_warmup_replacement_share_of_component_flow": compute_ratio(
                post_total_replacement, post_total_replacement + post_total_resize
            ),
            "post_warmup_incumbent_resize_share_of_component_flow": compute_ratio(
                post_total_resize, post_total_replacement + post_total_resize
            ),
            "holding_cohort_count": holding_cohort_count,
            "warmup_days_excluded_from_post_warmup_view": len(warmup_trade_dates),
        },
        "daily_pattern_summary": {
            "rebalance_days": int(trade_stats["rebalance_days"]),
            "entry_only_days": entry_only_days,
            "exit_only_days": exit_only_days,
            "mixed_replacement_days": mixed_replacement_days,
            "resize_active_days": resize_active_days,
            "median_turnover_daily": float(trade_stats["median_turnover_daily"]),
            "max_turnover_daily": float(trade_stats["max_turnover_daily"]),
            "p90_turnover_daily": float(daily_merged["turnover_daily"].quantile(0.90)),
            "p99_turnover_daily": float(daily_merged["turnover_daily"].quantile(0.99)),
        },
        "cost_drag_interpretation": {
            "annualized_turnover_proxy": annualized_turnover_proxy,
            "drag_per_1x_annual_turnover": drag_per_1x_annual_turnover,
            "topk_perturbation_pass": bool(audit["topk_perturbation_pass"]),
            "cost_stress_pass": bool(audit["cost_stress_pass"]),
        },
        "diagnosis": {
            "main_turnover_source": (
                "incumbent_resize" if total_resize >= total_replacement else "replacement"
            ),
            "post_warmup_main_turnover_source": (
                "incumbent_resize" if post_total_resize >= post_total_replacement else "replacement"
            ),
            "summary": (
                "Turnover is dominated by incumbent resize flow rather than pure entry/exit replacement flow."
                if post_total_resize >= post_total_replacement
                else "Turnover is dominated by replacement flow rather than incumbent resize flow."
            ),
        },
    }

    stem = f"{args.candidate_scheme_id}_turnover_cost_decomposition_{args.as_of_date}"
    json_output = round_dir / f"{stem}.json"
    md_output = round_dir / f"{stem}.md"
    write_json(json_output, payload)

    lines = [
        f"# {args.title} ({args.as_of_date})",
        "",
        f"Candidate: `{args.candidate_scheme_id}`",
        f"Research round: `{args.research_round_id}`",
        "",
        "## Headline",
        "",
        f"- `annual_relative_return(年化超额收益) = {annual_relative_return:.6f}`",
        f"- `relative_ir(相对信息比率) = {float(metrics['relative_ir']):.6f}`",
        f"- `max_drawdown(最大回撤) = {float(metrics['max_drawdown']):.6f}`",
        f"- `avg_turnover_daily(平均日换手) = {float(metrics['avg_turnover_daily']):.6f}`",
        f"- `cost_stress_annual_relative_return(成本压力年化超额收益) = {stressed_annual_relative_return:.6f}`",
        f"- `annual_relative_cost_drag(年化超额收益成本拖累) = {annual_relative_cost_drag:.6f}`",
        "",
        "## Turnover Decomposition",
        "",
        f"- `replacement_turnover_component_total(替换型换手总量) = {total_replacement:.6f}`",
        f"- `incumbent_resize_component_total(存量调权换手总量) = {total_resize:.6f}`",
        f"- `replacement_share_of_component_flow(替换型换手占组件流量比) = {payload['turnover_decomposition']['replacement_share_of_component_flow']:.6f}`",
        f"- `incumbent_resize_share_of_component_flow(存量调权换手占组件流量比) = {payload['turnover_decomposition']['incumbent_resize_share_of_component_flow']:.6f}`",
        f"- `post_warmup_replacement_share_of_component_flow(剔除建仓期后替换型换手占比) = {payload['turnover_decomposition']['post_warmup_replacement_share_of_component_flow']:.6f}`",
        f"- `post_warmup_incumbent_resize_share_of_component_flow(剔除建仓期后存量调权换手占比) = {payload['turnover_decomposition']['post_warmup_incumbent_resize_share_of_component_flow']:.6f}`",
        "",
        "## Daily Pattern",
        "",
        f"- `entry_only_days(仅进场日数) = {entry_only_days}`",
        f"- `exit_only_days(仅退出日数) = {exit_only_days}`",
        f"- `mixed_replacement_days(同时换入换出日数) = {mixed_replacement_days}`",
        f"- `resize_active_days(存在存量调权日数) = {resize_active_days}`",
        f"- `median_turnover_daily(中位日换手) = {float(trade_stats['median_turnover_daily']):.6f}`",
        f"- `p90_turnover_daily(日换手90分位) = {float(daily_merged['turnover_daily'].quantile(0.90)):.6f}`",
        f"- `p99_turnover_daily(日换手99分位) = {float(daily_merged['turnover_daily'].quantile(0.99)):.6f}`",
        "",
        "## Cost Drag Interpretation",
        "",
        f"- `annualized_turnover_proxy(年化换手代理) = {annualized_turnover_proxy:.6f}`",
        f"- `drag_per_1x_annual_turnover(每1倍年化换手的成本拖累代理) = {drag_per_1x_annual_turnover:.6f}`",
        f"- `topk_perturbation_pass(TopK扰动通过) = {str(bool(audit['topk_perturbation_pass'])).lower()}`",
        f"- `cost_stress_pass(成本压力通过) = {str(bool(audit['cost_stress_pass'])).lower()}`",
        "",
        "## Diagnosis",
        "",
        f"- Main source: `{payload['diagnosis']['main_turnover_source']}`",
        f"- Post-warmup main source: `{payload['diagnosis']['post_warmup_main_turnover_source']}`",
        f"- Summary: {payload['diagnosis']['summary']}",
        "",
    ]
    md_output.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
