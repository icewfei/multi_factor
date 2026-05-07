#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Strict confirmatory round-2 recheck for the single passing Alpha158 candidate
price_volume_single_signal_alpha158_vsumd60_v1.

This round does not rebuild strategy artifacts. It freezes the candidate and the
reference from confirmatory round 1, then applies a stricter preregistered
validation rule using:
- validation-window deltas versus the v18 reference
- split-validation subperiod deltas
- cost-stress relative-return delta
- low-liquidity share delta
- TopK perturbation relative-return deltas
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path("/Users/wy/MiscProject/multi_factor")
ROUND1_ID = "rr_confirmatory_alpha158_standalone_shortlist_round1_20260429"
ROUND2_ID = "rr_confirmatory_alpha158_vsumd60_round2_strict_recheck_20260429"
ROUND2_DIR = ROOT / "artifacts" / "research_registry" / "research_rounds" / ROUND2_ID
FIXED_TEST_DIR = ROOT / "artifacts" / "fixed_test"

REFERENCE_RUN_ID = "confirmatory_reference_v18_trainval_20260429"
CANDIDATE_RUN_ID = "confirmatory_vsumd60_trainval_20260429"
REFERENCE_CANDIDATE_SCHEME_ID = "price_volume_v18_refresh_hysteresis"
CANDIDATE_SCHEME_ID = "price_volume_single_signal_alpha158_vsumd60_v1"
SNAPSHOT_ID = "warehouse_20260429_trainval_20211231"

VALIDATION_PERIODS = [
    ("validation_h1_2019_2020h1", "20190101", "20200630"),
    ("validation_h2_2020h2_2021", "20200701", "20211231"),
]

CODE_HASH_FILES = [
    ROOT / "scripts" / "run_confirmatory_alpha158_vsumd60_round2_strict_recheck.py",
]


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def compute_code_hash() -> str:
    hasher = hashlib.sha256()
    for path in CODE_HASH_FILES:
        hasher.update(path.name.encode("utf-8"))
        hasher.update(path.read_bytes())
    return hasher.hexdigest()


def load_backtest_rows(run_id: str) -> list[dict]:
    path = FIXED_TEST_DIR / run_id / "backtest_daily.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def parse_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def compute_window_stats(rows: list[dict], start_date: str, end_date: str) -> dict:
    window_rows = [
        row
        for row in rows
        if start_date <= row["trade_date"] <= end_date and parse_float(row["benchmark_return_daily"]) is not None
    ]
    if not window_rows:
        raise ValueError(f"No benchmark-overlap rows found in window {start_date}-{end_date}.")

    portfolio_equity = 1.0
    benchmark_equity = 1.0
    relative_returns: list[float] = []
    turnover_values: list[float] = []
    invested_values: list[float] = []
    positive_relative_days = 0

    for row in window_rows:
        portfolio_return = float(row["portfolio_daily_return"])
        benchmark_return = float(row["benchmark_return_daily"])
        relative_return = portfolio_return - benchmark_return
        relative_returns.append(relative_return)
        turnover_values.append(float(row["turnover_daily"]))
        invested_values.append(float(row["invested_weight"]))
        portfolio_equity *= 1.0 + portfolio_return
        benchmark_equity *= 1.0 + benchmark_return
        if relative_return > 0.0:
            positive_relative_days += 1

    n_days = len(window_rows)
    annual_relative_return = (portfolio_equity ** (252.0 / n_days) - 1.0) - (
        benchmark_equity ** (252.0 / n_days) - 1.0
    )
    relative_mean = sum(relative_returns) / n_days
    if n_days > 1:
        variance = sum((value - relative_mean) ** 2 for value in relative_returns) / (n_days - 1)
        relative_std = variance ** 0.5
    else:
        relative_std = 0.0
    relative_ir = (relative_mean / relative_std) * (252.0 ** 0.5) if relative_std > 0.0 else None

    curve = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for row in window_rows:
        curve *= 1.0 + float(row["portfolio_daily_return"])
        peak = max(peak, curve)
        max_drawdown = min(max_drawdown, curve / peak - 1.0)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "n_days": n_days,
        "annual_relative_return": annual_relative_return,
        "relative_ir": relative_ir,
        "max_drawdown": max_drawdown,
        "avg_turnover_daily": sum(turnover_values) / n_days,
        "avg_invested_weight": sum(invested_values) / n_days,
        "positive_relative_days": positive_relative_days,
    }


def perturbation_map(run_id: str) -> dict[int, dict]:
    payload = load_json(FIXED_TEST_DIR / run_id / "topk_perturbation_summary.json")
    return {int(row["topk"]): row for row in payload["perturbations"]}


def main() -> None:
    ROUND2_DIR.mkdir(parents=True, exist_ok=True)

    reference_validation = load_json(FIXED_TEST_DIR / REFERENCE_RUN_ID / "validation_readout.json")
    candidate_validation = load_json(FIXED_TEST_DIR / CANDIDATE_RUN_ID / "validation_readout.json")
    reference_cost = load_json(FIXED_TEST_DIR / REFERENCE_RUN_ID / "cost_stress_summary.json")
    candidate_cost = load_json(FIXED_TEST_DIR / CANDIDATE_RUN_ID / "cost_stress_summary.json")
    reference_liq = load_json(FIXED_TEST_DIR / REFERENCE_RUN_ID / "low_liquidity_exposure_summary.json")
    candidate_liq = load_json(FIXED_TEST_DIR / CANDIDATE_RUN_ID / "low_liquidity_exposure_summary.json")
    reference_perturb = perturbation_map(REFERENCE_RUN_ID)
    candidate_perturb = perturbation_map(CANDIDATE_RUN_ID)
    reference_rows = load_backtest_rows(REFERENCE_RUN_ID)
    candidate_rows = load_backtest_rows(CANDIDATE_RUN_ID)

    subperiods: list[dict] = []
    for period_name, start_date, end_date in VALIDATION_PERIODS:
        ref_stats = compute_window_stats(reference_rows, start_date, end_date)
        cand_stats = compute_window_stats(candidate_rows, start_date, end_date)
        subperiods.append(
            {
                "period_name": period_name,
                "reference": ref_stats,
                "candidate": cand_stats,
                "annual_relative_return_delta": cand_stats["annual_relative_return"] - ref_stats["annual_relative_return"],
                "relative_ir_delta": (
                    cand_stats["relative_ir"] - ref_stats["relative_ir"]
                    if cand_stats["relative_ir"] is not None and ref_stats["relative_ir"] is not None
                    else None
                ),
            }
        )

    validation_annual_relative_return_delta = (
        candidate_validation["annual_relative_return"] - reference_validation["annual_relative_return"]
    )
    validation_relative_ir_delta = candidate_validation["relative_ir"] - reference_validation["relative_ir"]
    validation_max_drawdown_delta = candidate_validation["max_drawdown"] - reference_validation["max_drawdown"]
    validation_avg_turnover_daily_delta = (
        candidate_validation["avg_turnover_daily"] - reference_validation["avg_turnover_daily"]
    )
    cost_stress_annual_relative_return_delta = (
        candidate_cost["annual_relative_return"] - reference_cost["annual_relative_return"]
    )
    low_liquidity_weight_share_delta = (
        candidate_liq["low_liquidity_weight_share"] - reference_liq["low_liquidity_weight_share"]
    )

    perturbation_deltas = {}
    for topk in (8, 12):
        perturbation_deltas[topk] = {
            "candidate_annual_relative_return": candidate_perturb[topk]["annual_relative_return"],
            "reference_annual_relative_return": reference_perturb[topk]["annual_relative_return"],
            "annual_relative_return_delta": (
                candidate_perturb[topk]["annual_relative_return"] - reference_perturb[topk]["annual_relative_return"]
            ),
            "candidate_relative_ir": candidate_perturb[topk]["relative_ir"],
            "reference_relative_ir": reference_perturb[topk]["relative_ir"],
            "relative_ir_delta": candidate_perturb[topk]["relative_ir"] - reference_perturb[topk]["relative_ir"],
        }

    pass_boolean = bool(
        validation_annual_relative_return_delta > 0.10
        and validation_relative_ir_delta > 0.50
        and validation_max_drawdown_delta >= 0.10
        and validation_avg_turnover_daily_delta <= 0.02
        and candidate_validation["avg_invested_weight"] >= 0.18
        and all(period["annual_relative_return_delta"] > 0.0 for period in subperiods)
        and all((period["relative_ir_delta"] or 0.0) > 0.0 for period in subperiods)
        and cost_stress_annual_relative_return_delta > 0.0
        and low_liquidity_weight_share_delta <= 0.0
        and perturbation_deltas[8]["annual_relative_return_delta"] > 0.0
        and perturbation_deltas[12]["annual_relative_return_delta"] > 0.0
    )

    result = {
        "research_round_id": ROUND2_ID,
        "generated_at": now_iso(),
        "snapshot_id": SNAPSHOT_ID,
        "based_on_round_id": ROUND1_ID,
        "candidate_scheme_id": CANDIDATE_SCHEME_ID,
        "reference_candidate_scheme_id": REFERENCE_CANDIDATE_SCHEME_ID,
        "code_hash": compute_code_hash(),
        "validation_deltas": {
            "annual_relative_return_delta": validation_annual_relative_return_delta,
            "relative_ir_delta": validation_relative_ir_delta,
            "max_drawdown_delta": validation_max_drawdown_delta,
            "avg_turnover_daily_delta": validation_avg_turnover_daily_delta,
            "candidate_avg_invested_weight": candidate_validation["avg_invested_weight"],
        },
        "subperiod_rechecks": subperiods,
        "cost_stress_recheck": {
            "candidate_annual_relative_return": candidate_cost["annual_relative_return"],
            "reference_annual_relative_return": reference_cost["annual_relative_return"],
            "annual_relative_return_delta": cost_stress_annual_relative_return_delta,
        },
        "low_liquidity_recheck": {
            "candidate_low_liquidity_weight_share": candidate_liq["low_liquidity_weight_share"],
            "reference_low_liquidity_weight_share": reference_liq["low_liquidity_weight_share"],
            "low_liquidity_weight_share_delta": low_liquidity_weight_share_delta,
        },
        "topk_perturbation_recheck": perturbation_deltas,
        "strict_boolean_expression": (
            "(validation_annual_relative_return_delta > 0.10) "
            "AND (validation_relative_ir_delta > 0.50) "
            "AND (validation_max_drawdown_delta >= 0.10) "
            "AND (validation_avg_turnover_daily_delta <= 0.02) "
            "AND (candidate_avg_invested_weight >= 0.18) "
            "AND (validation_h1_annual_relative_return_delta > 0) "
            "AND (validation_h1_relative_ir_delta > 0) "
            "AND (validation_h2_annual_relative_return_delta > 0) "
            "AND (validation_h2_relative_ir_delta > 0) "
            "AND (cost_stress_annual_relative_return_delta > 0) "
            "AND (low_liquidity_weight_share_delta <= 0) "
            "AND (topk8_annual_relative_return_delta > 0) "
            "AND (topk12_annual_relative_return_delta > 0)"
        ),
        "pass_boolean": pass_boolean,
        "round_decision": "KEEP" if pass_boolean else "REJECT",
    }
    write_json(ROUND2_DIR / "confirmatory_round2_strict_recheck_results.json", result)

    lines = [
        f"# {ROUND2_ID} results",
        "",
        f"- `candidate_scheme_id(候选方案ID) = {CANDIDATE_SCHEME_ID}`",
        f"- `round_decision(轮次结论) = {result['round_decision']}`",
        f"- `pass_boolean(布尔通过) = {str(pass_boolean).lower()}`",
        "",
        "## Validation Deltas",
        "",
        f"- `annual_relative_return_delta(年化超额收益变化) = {validation_annual_relative_return_delta:.6f}`",
        f"- `relative_ir_delta(相对信息比率变化) = {validation_relative_ir_delta:.6f}`",
        f"- `max_drawdown_delta(最大回撤变化) = {validation_max_drawdown_delta:.6f}`",
        f"- `avg_turnover_daily_delta(平均日换手变化) = {validation_avg_turnover_daily_delta:.6f}`",
        f"- `candidate_avg_invested_weight(候选平均持仓权重) = {candidate_validation['avg_invested_weight']:.6f}`",
        "",
        "## Subperiod Rechecks",
        "",
    ]
    for period in subperiods:
        lines.extend(
            [
                f"- `{period['period_name']}`",
                f"  - `annual_relative_return_delta(年化超额收益变化) = {period['annual_relative_return_delta']:.6f}`",
                f"  - `relative_ir_delta(相对信息比率变化) = {period['relative_ir_delta']:.6f}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Stress And Robustness",
            "",
            f"- `cost_stress_annual_relative_return_delta(成本压力年化超额收益变化) = {cost_stress_annual_relative_return_delta:.6f}`",
            f"- `low_liquidity_weight_share_delta(低流动性权重占比变化) = {low_liquidity_weight_share_delta:.6f}`",
            f"- `topk8_annual_relative_return_delta(TopK=8年化超额收益变化) = {perturbation_deltas[8]['annual_relative_return_delta']:.6f}`",
            f"- `topk12_annual_relative_return_delta(TopK=12年化超额收益变化) = {perturbation_deltas[12]['annual_relative_return_delta']:.6f}`",
            "",
            "## Rule",
            "",
            f"- `{result['strict_boolean_expression']}`",
        ]
    )
    (ROUND2_DIR / "confirmatory_round2_strict_recheck_results.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
