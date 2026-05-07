#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Build a family-level root-cause diagnosis that compares one challenger family to a
reference candidate across signal, selection, holdings tail, and fixed-test layers.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
FIXED_TEST_DIR = ROOT / "artifacts" / "fixed_test"
RESEARCH_ROUNDS_DIR = ROOT / "artifacts" / "research_registry" / "research_rounds"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build family-level root-cause diagnosis.")
    parser.add_argument("--research-round-id", required=True)
    parser.add_argument("--candidate-scheme-id", required=True)
    parser.add_argument("--reference-candidate-scheme-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--reference-run-id", required=True)
    parser.add_argument("--reference-attempt-id", required=True)
    parser.add_argument("--challenger-signal-diagnosis-json", required=True)
    parser.add_argument("--reference-signal-diagnosis-json", required=True)
    parser.add_argument("--as-of-date", required=True)
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require_path(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Required path not found: {path}")
    return path


def sql_path(path: Path) -> str:
    return "'" + path.resolve().as_posix().replace("'", "''") + "'"


def pct(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def signal_ic_block(payload: dict) -> dict:
    return payload.get("ic_readout") or payload.get("signal_quality") or {}


def signal_top_block(payload: dict) -> dict:
    return payload.get("top_slice_readout") or payload.get("top_bucket_readout") or {}


def main() -> None:
    args = parse_args()
    round_dir = RESEARCH_ROUNDS_DIR / args.research_round_id
    round_dir.mkdir(parents=True, exist_ok=True)

    challenger_run_dir = RUN_STATE_DIR / args.run_id / "attempts" / args.attempt_id
    reference_run_dir = RUN_STATE_DIR / args.reference_run_id / "attempts" / args.reference_attempt_id
    challenger_fixed_dir = FIXED_TEST_DIR / args.run_id
    reference_fixed_dir = FIXED_TEST_DIR / args.reference_run_id

    challenger_metrics = load_json(require_path(challenger_fixed_dir / "metrics.json"))
    challenger_audit = load_json(require_path(challenger_fixed_dir / "audit_summary.json"))
    challenger_liq = load_json(require_path(challenger_fixed_dir / "low_liquidity_exposure_summary.json"))
    challenger_topk = load_json(require_path(challenger_fixed_dir / "topk_perturbation_summary.json"))
    challenger_cost = load_json(require_path(challenger_fixed_dir / "cost_stress_summary.json"))

    reference_metrics = load_json(require_path(reference_fixed_dir / "metrics.json"))
    reference_audit = load_json(require_path(reference_fixed_dir / "audit_summary.json"))
    reference_liq = load_json(require_path(reference_fixed_dir / "low_liquidity_exposure_summary.json"))
    reference_topk = load_json(require_path(reference_fixed_dir / "topk_perturbation_summary.json"))
    reference_cost = load_json(require_path(reference_fixed_dir / "cost_stress_summary.json"))

    challenger_signal = load_json(require_path(Path(args.challenger_signal_diagnosis_json)))
    reference_signal = load_json(require_path(Path(args.reference_signal_diagnosis_json)))

    challenger_ic = signal_ic_block(challenger_signal)
    reference_ic = signal_ic_block(reference_signal)
    challenger_top = signal_top_block(challenger_signal)
    reference_top = signal_top_block(reference_signal)
    challenger_cutoff_gap = challenger_signal.get("cutoff_gap", {})
    reference_cutoff_gap = reference_signal.get("cutoff_gap", {})

    challenger_ranking = require_path(challenger_run_dir / "ranking_state_daily.parquet")
    reference_ranking = require_path(reference_run_dir / "ranking_state_daily.parquet")
    challenger_holdings = require_path(challenger_run_dir / "holdings.csv")
    reference_holdings = require_path(reference_run_dir / "holdings.csv")

    con = duckdb.connect()
    try:
        overlap_row = con.execute(
            f"""
            WITH ref AS (
                SELECT signal_date, instrument
                FROM read_parquet({sql_path(reference_ranking)})
                WHERE topk_frozen_D0
            ),
            chg AS (
                SELECT signal_date, instrument
                FROM read_parquet({sql_path(challenger_ranking)})
                WHERE topk_frozen_D0
            ),
            ref_counts AS (
                SELECT signal_date, COUNT(*) AS ref_topk_count
                FROM ref
                GROUP BY signal_date
            ),
            chg_counts AS (
                SELECT signal_date, COUNT(*) AS challenger_topk_count
                FROM chg
                GROUP BY signal_date
            ),
            overlap AS (
                SELECT
                    COALESCE(r.signal_date, c.signal_date) AS signal_date,
                    COALESCE(ref_topk_count, 0) AS ref_topk_count,
                    COALESCE(challenger_topk_count, 0) AS challenger_topk_count,
                    COUNT(o.instrument) AS overlap_count
                FROM ref_counts r
                FULL OUTER JOIN chg_counts c
                    ON r.signal_date = c.signal_date
                LEFT JOIN (
                    SELECT ref.signal_date, ref.instrument
                    FROM ref
                    INNER JOIN chg
                        USING (signal_date, instrument)
                ) o
                    ON COALESCE(r.signal_date, c.signal_date) = o.signal_date
                GROUP BY 1, 2, 3
            )
            SELECT
                COUNT(*) AS signal_dates,
                AVG(overlap_count) AS avg_overlap_count,
                MEDIAN(overlap_count) AS median_overlap_count,
                AVG(
                    CASE
                        WHEN LEAST(ref_topk_count, challenger_topk_count) > 0
                        THEN overlap_count::DOUBLE / LEAST(ref_topk_count, challenger_topk_count)
                        ELSE NULL
                    END
                ) AS avg_overlap_share_of_smaller_topk,
                SUM(CASE WHEN overlap_count = 0 THEN 1 ELSE 0 END) AS zero_overlap_days
            FROM overlap
            """
        ).fetchone()

        challenger_holdings_row = con.execute(
            f"""
            SELECT
                COUNT(*) AS holdings_count,
                AVG(execution_delayed_realized_return) AS avg_return,
                MEDIAN(execution_delayed_realized_return) AS median_return,
                QUANTILE_CONT(execution_delayed_realized_return, 0.10) AS p10_return,
                QUANTILE_CONT(execution_delayed_realized_return, 0.05) AS p05_return,
                QUANTILE_CONT(execution_delayed_realized_return, 0.90) AS p90_return
            FROM read_csv_auto({sql_path(challenger_holdings)}, HEADER=TRUE)
            WHERE execution_delayed_realized_return IS NOT NULL
            """
        ).fetchone()

        reference_holdings_row = con.execute(
            f"""
            SELECT
                COUNT(*) AS holdings_count,
                AVG(execution_delayed_realized_return) AS avg_return,
                MEDIAN(execution_delayed_realized_return) AS median_return,
                QUANTILE_CONT(execution_delayed_realized_return, 0.10) AS p10_return,
                QUANTILE_CONT(execution_delayed_realized_return, 0.05) AS p05_return,
                QUANTILE_CONT(execution_delayed_realized_return, 0.90) AS p90_return
            FROM read_csv_auto({sql_path(reference_holdings)}, HEADER=TRUE)
            WHERE execution_delayed_realized_return IS NOT NULL
            """
        ).fetchone()
    finally:
        con.close()

    overlap = {
        "signal_dates": int(overlap_row[0]),
        "avg_overlap_count": float(overlap_row[1]),
        "median_overlap_count": float(overlap_row[2]),
        "avg_overlap_share_of_smaller_topk": float(overlap_row[3]),
        "zero_overlap_days": int(overlap_row[4]),
        "zero_overlap_day_share": pct(int(overlap_row[4]), int(overlap_row[0])),
    }

    challenger_holdings_tail = {
        "holdings_count": int(challenger_holdings_row[0]),
        "avg_execution_delayed_realized_return": float(challenger_holdings_row[1]),
        "median_execution_delayed_realized_return": float(challenger_holdings_row[2]),
        "p10_execution_delayed_realized_return": float(challenger_holdings_row[3]),
        "p05_execution_delayed_realized_return": float(challenger_holdings_row[4]),
        "p90_execution_delayed_realized_return": float(challenger_holdings_row[5]),
    }
    reference_holdings_tail = {
        "holdings_count": int(reference_holdings_row[0]),
        "avg_execution_delayed_realized_return": float(reference_holdings_row[1]),
        "median_execution_delayed_realized_return": float(reference_holdings_row[2]),
        "p10_execution_delayed_realized_return": float(reference_holdings_row[3]),
        "p05_execution_delayed_realized_return": float(reference_holdings_row[4]),
        "p90_execution_delayed_realized_return": float(reference_holdings_row[5]),
    }

    base_rel = float(challenger_metrics["annual_relative_return"])
    stress_rel = float(challenger_cost["annual_relative_return"])
    cost_drag_delta = stress_rel - base_rel

    result = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "candidate_scheme_id": args.candidate_scheme_id,
        "reference_candidate_scheme_id": args.reference_candidate_scheme_id,
        "research_round_id": args.research_round_id,
        "as_of_date": args.as_of_date,
        "signal_layer": {
            "challenger": challenger_signal,
            "reference": reference_signal,
            "judgement": (
                "challenger signal edge is stronger than calibrated v7 at broad ordering level, "
                "but the top slice remains fragile because rank 11-20 still beats rank 1-10."
            ),
        },
        "selection_layer": {
            "topk_overlap_with_reference": overlap,
            "challenger_topk_cutoff_gap": challenger_cutoff_gap,
            "reference_topk_cutoff_gap": reference_cutoff_gap,
            "judgement": (
                "The challenger materially changes the selected basket relative to v7 while still "
                "operating in a thin-cutoff regime; this helps explain why relative return can improve "
                "yet perturbation robustness still fails."
            ),
        },
        "fixed_test_layer": {
            "challenger_metrics": {
                "annual_relative_return": float(challenger_metrics["annual_relative_return"]),
                "relative_ir": float(challenger_metrics["relative_ir"]),
                "max_drawdown": float(challenger_metrics["max_drawdown"]),
                "avg_cash_weight": float(challenger_metrics["avg_cash_weight"]),
                "avg_invested_weight": float(challenger_metrics["avg_invested_weight"]),
                "avg_turnover_daily": float(challenger_metrics["avg_turnover_daily"]),
            },
            "reference_metrics": {
                "annual_relative_return": float(reference_metrics["annual_relative_return"]),
                "relative_ir": float(reference_metrics["relative_ir"]),
                "max_drawdown": float(reference_metrics["max_drawdown"]),
                "avg_cash_weight": float(reference_metrics["avg_cash_weight"]),
                "avg_invested_weight": float(reference_metrics["avg_invested_weight"]),
                "avg_turnover_daily": float(reference_metrics["avg_turnover_daily"]),
            },
            "challenger_low_liquidity": challenger_liq,
            "reference_low_liquidity": reference_liq,
            "challenger_audit_flags": {
                "topk_perturbation_pass": bool(challenger_audit["topk_perturbation_pass"]),
                "cost_stress_pass": bool(challenger_audit["cost_stress_pass"]),
                "low_liquidity_flag_high": bool(challenger_audit["low_liquidity_flag_high"]),
            },
            "reference_audit_flags": {
                "topk_perturbation_pass": bool(reference_audit["topk_perturbation_pass"]),
                "cost_stress_pass": bool(reference_audit["cost_stress_pass"]),
                "low_liquidity_flag_high": bool(reference_audit["low_liquidity_flag_high"]),
            },
            "cost_drag_delta_annual_relative_return": cost_drag_delta,
            "judgement": (
                "v15 improves annual_relative_return and relative_ir and lowers turnover versus v7, "
                "but drawdown becomes worse and cost stress still pushes annual_relative_return materially lower."
            ),
        },
        "holdings_tail_layer": {
            "challenger": challenger_holdings_tail,
            "reference": reference_holdings_tail,
            "judgement": (
                "The challenger improves average holding return and also improves single-position left-tail "
                "quantiles versus v7. This suggests the worse portfolio-level drawdown is more likely driven "
                "by path dependence, basket concentration, or synchronized losses rather than by worse single-name tails."
            ),
        },
        "conclusion": [
            "The first constructed family is directionally more promising than several earlier mixed-family attempts because its broad signal edge is stronger than calibrated v7 and that improvement does survive into annual_relative_return and relative_ir.",
            "The main blocker is no longer gross edge absence. The blocker is that the family still extracts a fragile top slice, fails TopK perturbation, and converts some of its new edge into worse downside outcomes and higher low-liquidity share.",
            "This means the next best research action is not to discard the family outright, but to diagnose which retained atomic signal is driving the worse drawdown and liquidity share inside the mixed family."
        ],
    }

    json_path = round_dir / f"{args.candidate_scheme_id}_family_root_cause_diagnosis_{args.as_of_date}.json"
    md_path = round_dir / f"{args.candidate_scheme_id}_family_root_cause_diagnosis_{args.as_of_date}.md"
    write_json(json_path, result)

    md_lines = [
        f"# {args.candidate_scheme_id} Family-Level Root-Cause Diagnosis",
        "",
        f"- Generated at: `{result['generated_at']}`",
        f"- Candidate: `{args.candidate_scheme_id}`",
        f"- Reference: `{args.reference_candidate_scheme_id}`",
        f"- Research round: `{args.research_round_id}`",
        "",
        "## Signal Layer",
        "",
        f"- full_sample_corr_ic（全样本IC）: `{reference_ic.get('full_sample_corr_ic', float('nan')):.6f} -> {challenger_ic.get('full_sample_corr_ic', float('nan')):.6f}`",
        f"- avg_daily_ic（平均日IC）: `{reference_ic.get('avg_daily_ic', float('nan')):.6f} -> {challenger_ic.get('avg_daily_ic', float('nan')):.6f}`",
        f"- positive_daily_ic_share（正IC日占比）: `{reference_ic.get('positive_daily_ic_share', float('nan')):.4f} -> {challenger_ic.get('positive_daily_ic_share', float('nan')):.4f}`",
        f"- avg_label_top10（前10平均标签）: `{reference_top.get('avg_label_top10', float('nan')):.6f} -> {challenger_top.get('avg_label_top10', float('nan')):.6f}`",
        f"- avg_label_rank11_20（11-20名平均标签）: `{reference_top.get('avg_label_rank11_20', float('nan')):.6f} -> {challenger_top.get('avg_label_rank11_20', float('nan')):.6f}`",
        "",
        result["signal_layer"]["judgement"],
        "",
        "## Selection Layer",
        "",
        f"- avg_overlap_count（平均TopK重叠只数）: `{overlap['avg_overlap_count']:.3f}`",
        f"- avg_overlap_share_of_smaller_topk（平均TopK重叠比例）: `{overlap['avg_overlap_share_of_smaller_topk']:.4f}`",
        f"- zero_overlap_day_share（零重叠交易日占比）: `{overlap['zero_overlap_day_share']:.4f}`",
        f"- challenger median rank10_11 gap（挑战者10/11位中位分差）: `{challenger_cutoff_gap.get('median_rank10_11_score_gap', float('nan')):.6f}`",
        f"- reference median rank10_11 gap（参考10/11位中位分差）: `{reference_cutoff_gap.get('median_rank10_11_score_gap', float('nan')):.6f}`",
        "",
        result["selection_layer"]["judgement"],
        "",
        "## Fixed-Test Layer",
        "",
        f"- annual_relative_return（年化超额收益）: `{reference_metrics['annual_relative_return']:.6f} -> {challenger_metrics['annual_relative_return']:.6f}`",
        f"- relative_ir（相对信息比率）: `{reference_metrics['relative_ir']:.6f} -> {challenger_metrics['relative_ir']:.6f}`",
        f"- max_drawdown（最大回撤）: `{reference_metrics['max_drawdown']:.6f} -> {challenger_metrics['max_drawdown']:.6f}`",
        f"- avg_turnover_daily（平均日换手）: `{reference_metrics['avg_turnover_daily']:.6f} -> {challenger_metrics['avg_turnover_daily']:.6f}`",
        f"- low_liquidity_weight_share（低流动性权重占比）: `{reference_liq['low_liquidity_weight_share']:.6f} -> {challenger_liq['low_liquidity_weight_share']:.6f}`",
        f"- cost_drag_delta_annual_relative_return（成本压力额外拖累的年化超额收益）: `{cost_drag_delta:.6f}`",
        f"- topk_perturbation_pass（TopK扰动通过）: `{reference_audit['topk_perturbation_pass']} -> {challenger_audit['topk_perturbation_pass']}`",
        f"- cost_stress_pass（成本压力通过）: `{reference_audit['cost_stress_pass']} -> {challenger_audit['cost_stress_pass']}`",
        "",
        result["fixed_test_layer"]["judgement"],
        "",
        "## Holdings Tail",
        "",
        f"- p10_execution_delayed_realized_return（持仓收益10分位）: `{reference_holdings_tail['p10_execution_delayed_realized_return']:.6f} -> {challenger_holdings_tail['p10_execution_delayed_realized_return']:.6f}`",
        f"- p05_execution_delayed_realized_return（持仓收益5分位）: `{reference_holdings_tail['p05_execution_delayed_realized_return']:.6f} -> {challenger_holdings_tail['p05_execution_delayed_realized_return']:.6f}`",
        f"- avg_execution_delayed_realized_return（平均持仓真实收益）: `{reference_holdings_tail['avg_execution_delayed_realized_return']:.6f} -> {challenger_holdings_tail['avg_execution_delayed_realized_return']:.6f}`",
        "",
        result["holdings_tail_layer"]["judgement"],
        "",
        "## Conclusion",
        "",
    ]
    md_lines.extend([f"- {line}" for line in result["conclusion"]])
    md_lines.append("")
    md_path.write_text("\n".join(md_lines), encoding="utf-8")


if __name__ == "__main__":
    main()
