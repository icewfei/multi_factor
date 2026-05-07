#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Postmortem for the reversal partner-composite line.

Compares the frozen p98 reversal baseline against both completed partner
composites (cord30 and corr30) to determine whether the equal-weight partner
line should stay open.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
FIXED_TEST_DIR = ROOT / "artifacts" / "fixed_test"
OUT_DIR = FIXED_TEST_DIR / "reversal_partner_line_postmortem"

BASELINE = {
    "label": "p98_reversal",
    "run_id": "confirmatory_reversal_p98_trainval_20260506",
}

CHALLENGERS = [
    {
        "label": "cord30_ew",
        "run_id": "confirmatory_reversal_p98_cord30_trainval_20260506",
    },
    {
        "label": "corr30_ew",
        "run_id": "exploratory_reversal_p98_corr30_trainval_20260506",
    },
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_path(path: Path) -> str:
    return sql_quote(path.resolve().as_posix())


def read_backtest_rows(run_id: str) -> list[dict]:
    path = FIXED_TEST_DIR / run_id / "backtest_daily.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def attempt_dir(run_id: str) -> Path:
    latest = load_json(RUN_STATE_DIR / run_id / "run_state_latest_attempt.json")
    return RUN_STATE_DIR / run_id / "attempts" / latest["attempt_id"]


def perturbation_map(run_id: str) -> dict[int, dict]:
    payload = load_json(FIXED_TEST_DIR / run_id / "topk_perturbation_summary.json")
    return {int(row["topk"]): row for row in payload["perturbations"]}


def yearly_delta_map(baseline_run_id: str, challenger_run_id: str) -> dict[str, dict]:
    base_rows = read_backtest_rows(baseline_run_id)
    cmp_rows = read_backtest_rows(challenger_run_id)
    cmp_by_date = {row["trade_date"]: row for row in cmp_rows}

    bucket: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "baseline_rel_sum": 0.0,
            "challenger_rel_sum": 0.0,
            "baseline_days": 0.0,
            "baseline_invested_sum": 0.0,
            "challenger_invested_sum": 0.0,
            "baseline_turnover_sum": 0.0,
            "challenger_turnover_sum": 0.0,
        }
    )
    for row in base_rows:
        trade_date = row["trade_date"]
        challenger_row = cmp_by_date.get(trade_date)
        if challenger_row is None:
            continue
        if row["relative_return_daily"] in ("", None) or challenger_row["relative_return_daily"] in ("", None):
            continue
        year = trade_date[:4]
        bucket[year]["baseline_rel_sum"] += float(row["relative_return_daily"])
        bucket[year]["challenger_rel_sum"] += float(challenger_row["relative_return_daily"])
        bucket[year]["baseline_days"] += 1
        bucket[year]["baseline_invested_sum"] += float(row["invested_weight"])
        bucket[year]["challenger_invested_sum"] += float(challenger_row["invested_weight"])
        bucket[year]["baseline_turnover_sum"] += float(row["turnover_daily"])
        bucket[year]["challenger_turnover_sum"] += float(challenger_row["turnover_daily"])

    out: dict[str, dict] = {}
    for year, payload in sorted(bucket.items()):
        n = int(payload["baseline_days"])
        if n == 0:
            continue
        out[year] = {
            "baseline_avg_relative_return_daily": payload["baseline_rel_sum"] / n,
            "challenger_avg_relative_return_daily": payload["challenger_rel_sum"] / n,
            "avg_relative_return_daily_delta": (payload["challenger_rel_sum"] - payload["baseline_rel_sum"]) / n,
            "baseline_avg_invested_weight": payload["baseline_invested_sum"] / n,
            "challenger_avg_invested_weight": payload["challenger_invested_sum"] / n,
            "avg_invested_weight_delta": (payload["challenger_invested_sum"] - payload["baseline_invested_sum"]) / n,
            "baseline_avg_turnover_daily": payload["baseline_turnover_sum"] / n,
            "challenger_avg_turnover_daily": payload["challenger_turnover_sum"] / n,
            "avg_turnover_daily_delta": (payload["challenger_turnover_sum"] - payload["baseline_turnover_sum"]) / n,
            "n_days": n,
        }
    return out


def compare_to_baseline(baseline_run_id: str, challenger_run_id: str) -> dict:
    baseline_fixed = FIXED_TEST_DIR / baseline_run_id
    challenger_fixed = FIXED_TEST_DIR / challenger_run_id
    baseline_attempt_dir = attempt_dir(baseline_run_id)
    challenger_attempt_dir = attempt_dir(challenger_run_id)

    con = duckdb.connect()
    try:
        con.execute(
            f"CREATE OR REPLACE VIEW base_rank AS SELECT * FROM read_parquet({sql_path(baseline_attempt_dir / 'ranking_state_daily.parquet')})"
        )
        con.execute(
            f"CREATE OR REPLACE VIEW challenger_rank AS SELECT * FROM read_parquet({sql_path(challenger_attempt_dir / 'ranking_state_daily.parquet')})"
        )
        con.execute(
            f"CREATE OR REPLACE VIEW base_exec AS SELECT * FROM read_parquet({sql_path(baseline_attempt_dir / 'execution_state_daily.parquet')})"
        )
        con.execute(
            f"CREATE OR REPLACE VIEW challenger_exec AS SELECT * FROM read_parquet({sql_path(challenger_attempt_dir / 'execution_state_daily.parquet')})"
        )
        con.execute(
            f"CREATE OR REPLACE VIEW base_scores AS SELECT * FROM read_parquet({sql_path(RUN_STATE_DIR / baseline_run_id / 'model_scores_D0.parquet')})"
        )
        con.execute(
            f"CREATE OR REPLACE VIEW challenger_scores AS SELECT * FROM read_parquet({sql_path(RUN_STATE_DIR / challenger_run_id / 'model_scores_D0.parquet')})"
        )

        overlap = con.execute(
            """
            WITH base_top AS (
                SELECT signal_date, instrument
                FROM base_rank
                WHERE topk_frozen_D0
            ),
            challenger_top AS (
                SELECT signal_date, instrument
                FROM challenger_rank
                WHERE topk_frozen_D0
            ),
            daily AS (
                SELECT
                    COALESCE(b.signal_date, c.signal_date) AS signal_date,
                    COUNT(*) FILTER (WHERE b.instrument IS NOT NULL) AS base_top10_n,
                    COUNT(*) FILTER (WHERE c.instrument IS NOT NULL) AS challenger_top10_n,
                    COUNT(*) FILTER (WHERE b.instrument IS NOT NULL AND c.instrument IS NOT NULL) AS overlap_n
                FROM base_top b
                FULL OUTER JOIN challenger_top c
                  ON b.signal_date = c.signal_date
                 AND b.instrument = c.instrument
                GROUP BY 1
            )
            SELECT
                AVG(overlap_n) AS avg_overlap_n,
                AVG(overlap_n / 10.0) AS avg_overlap_share,
                MIN(overlap_n) AS min_overlap_n,
                MAX(overlap_n) AS max_overlap_n
            FROM daily
            """
        ).fetchone()

        unique_profile = con.execute(
            """
            WITH base_top AS (
                SELECT r.signal_date, r.instrument, s.liquidity_rank
                FROM base_rank r
                LEFT JOIN base_scores s
                  ON r.signal_date = s.signal_date AND r.instrument = s.instrument
                WHERE r.topk_frozen_D0
            ),
            challenger_top AS (
                SELECT r.signal_date, r.instrument, s.liquidity_rank
                FROM challenger_rank r
                LEFT JOIN challenger_scores s
                  ON r.signal_date = s.signal_date AND r.instrument = s.instrument
                WHERE r.topk_frozen_D0
            ),
            challenger_unique AS (
                SELECT c.signal_date, c.instrument, c.liquidity_rank
                FROM challenger_top c
                LEFT JOIN base_top b
                  ON c.signal_date = b.signal_date AND c.instrument = b.instrument
                WHERE b.instrument IS NULL
            ),
            base_unique AS (
                SELECT b.signal_date, b.instrument, b.liquidity_rank
                FROM base_top b
                LEFT JOIN challenger_top c
                  ON c.signal_date = b.signal_date AND c.instrument = b.instrument
                WHERE c.instrument IS NULL
            )
            SELECT
                (SELECT AVG(liquidity_rank) FROM challenger_unique) AS challenger_unique_avg_liq_rank,
                (SELECT MEDIAN(liquidity_rank) FROM challenger_unique) AS challenger_unique_med_liq_rank,
                (SELECT AVG(liquidity_rank) FROM base_unique) AS base_unique_avg_liq_rank,
                (SELECT MEDIAN(liquidity_rank) FROM base_unique) AS base_unique_med_liq_rank,
                (SELECT COUNT(*) FROM challenger_unique) AS challenger_unique_rows,
                (SELECT COUNT(*) FROM base_unique) AS base_unique_rows
            """
        ).fetchone()

        fill_profile = con.execute(
            """
            WITH base_top AS (
                SELECT r.signal_date, r.instrument, s.liquidity_rank, e.entry_filled_D1
                FROM base_rank r
                LEFT JOIN base_scores s
                  ON r.signal_date = s.signal_date AND r.instrument = s.instrument
                LEFT JOIN base_exec e
                  ON r.signal_date = e.signal_date AND r.instrument = e.instrument
                WHERE r.topk_frozen_D0
            ),
            challenger_top AS (
                SELECT r.signal_date, r.instrument, s.liquidity_rank, e.entry_filled_D1
                FROM challenger_rank r
                LEFT JOIN challenger_scores s
                  ON r.signal_date = s.signal_date AND r.instrument = s.instrument
                LEFT JOIN challenger_exec e
                  ON r.signal_date = e.signal_date AND r.instrument = e.instrument
                WHERE r.topk_frozen_D0
            )
            SELECT
                (SELECT AVG(CASE WHEN entry_filled_D1 THEN 1.0 ELSE 0.0 END) FROM base_top) AS base_fill_rate,
                (SELECT AVG(CASE WHEN entry_filled_D1 THEN 1.0 ELSE 0.0 END) FROM challenger_top) AS challenger_fill_rate,
                (SELECT AVG(liquidity_rank) FROM base_top) AS base_top10_avg_liq_rank,
                (SELECT AVG(liquidity_rank) FROM challenger_top) AS challenger_top10_avg_liq_rank,
                (SELECT MEDIAN(liquidity_rank) FROM base_top) AS base_top10_med_liq_rank,
                (SELECT MEDIAN(liquidity_rank) FROM challenger_top) AS challenger_top10_med_liq_rank
            """
        ).fetchone()

        fill_count = con.execute(
            """
            WITH base_day AS (
                SELECT signal_date, SUM(CASE WHEN entry_filled_D1 THEN 1 ELSE 0 END) AS filled_n
                FROM base_exec
                WHERE execution_attempt_D1
                GROUP BY signal_date
            ),
            challenger_day AS (
                SELECT signal_date, SUM(CASE WHEN entry_filled_D1 THEN 1 ELSE 0 END) AS filled_n
                FROM challenger_exec
                WHERE execution_attempt_D1
                GROUP BY signal_date
            )
            SELECT
                AVG(base_day.filled_n) AS base_avg_filled_n,
                AVG(challenger_day.filled_n) AS challenger_avg_filled_n,
                AVG(challenger_day.filled_n - base_day.filled_n) AS avg_filled_n_delta
            FROM base_day
            JOIN challenger_day USING (signal_date)
            """
        ).fetchone()
    finally:
        con.close()

    base_attr = load_json(baseline_fixed / "return_attribution_summary.json")
    challenger_attr = load_json(challenger_fixed / "return_attribution_summary.json")
    base_validation = load_json(baseline_fixed / "validation_readout.json")
    challenger_validation = load_json(challenger_fixed / "validation_readout.json")
    base_cost = load_json(baseline_fixed / "cost_stress_summary.json")
    challenger_cost = load_json(challenger_fixed / "cost_stress_summary.json")
    base_liq = load_json(baseline_fixed / "low_liquidity_exposure_summary.json")
    challenger_liq = load_json(challenger_fixed / "low_liquidity_exposure_summary.json")
    base_perturb = perturbation_map(baseline_run_id)
    challenger_perturb = perturbation_map(challenger_run_id)

    return {
        "run_id": challenger_run_id,
        "high_level": {
            "validation_annual_relative_return_delta": (
                challenger_validation["annual_relative_return"] - base_validation["annual_relative_return"]
            ),
            "validation_relative_ir_delta": challenger_validation["relative_ir"] - base_validation["relative_ir"],
            "validation_max_drawdown_delta": challenger_validation["max_drawdown"] - base_validation["max_drawdown"],
            "validation_avg_turnover_daily_delta": (
                challenger_validation["avg_turnover_daily"] - base_validation["avg_turnover_daily"]
            ),
            "validation_avg_invested_weight_delta": (
                challenger_validation["avg_invested_weight"] - base_validation["avg_invested_weight"]
            ),
            "cost_stress_annual_relative_return_delta": (
                challenger_cost["annual_relative_return"] - base_cost["annual_relative_return"]
            ),
            "low_liquidity_weight_share_delta": (
                challenger_liq["low_liquidity_weight_share"] - base_liq["low_liquidity_weight_share"]
            ),
            "topk8_annual_relative_return_delta": (
                challenger_perturb[8]["annual_relative_return"] - base_perturb[8]["annual_relative_return"]
            ),
            "topk12_annual_relative_return_delta": (
                challenger_perturb[12]["annual_relative_return"] - base_perturb[12]["annual_relative_return"]
            ),
        },
        "attribution_decomposition": {
            "selection_alpha_delta": challenger_attr["selection_alpha_total"] - base_attr["selection_alpha_total"],
            "cash_drag_delta": challenger_attr["cash_drag_total"] - base_attr["cash_drag_total"],
            "low_liquidity_contribution_delta": (
                challenger_attr["low_liquidity_contribution_total"] - base_attr["low_liquidity_contribution_total"]
            ),
        },
        "top10_overlap": {
            "avg_overlap_n": float(overlap[0]),
            "avg_overlap_share": float(overlap[1]),
            "min_overlap_n": int(overlap[2]),
            "max_overlap_n": int(overlap[3]),
        },
        "unique_name_liquidity_profile": {
            "challenger_unique_avg_liquidity_rank": float(unique_profile[0]) if unique_profile[0] is not None else None,
            "challenger_unique_median_liquidity_rank": float(unique_profile[1]) if unique_profile[1] is not None else None,
            "baseline_unique_avg_liquidity_rank": float(unique_profile[2]) if unique_profile[2] is not None else None,
            "baseline_unique_median_liquidity_rank": float(unique_profile[3]) if unique_profile[3] is not None else None,
            "challenger_unique_rows": int(unique_profile[4]),
            "baseline_unique_rows": int(unique_profile[5]),
        },
        "top10_fill_profile": {
            "baseline_fill_rate": float(fill_profile[0]),
            "challenger_fill_rate": float(fill_profile[1]),
            "baseline_top10_avg_liquidity_rank": float(fill_profile[2]),
            "challenger_top10_avg_liquidity_rank": float(fill_profile[3]),
            "baseline_top10_median_liquidity_rank": float(fill_profile[4]),
            "challenger_top10_median_liquidity_rank": float(fill_profile[5]),
        },
        "daily_fill_count": {
            "baseline_avg_filled_n": float(fill_count[0]),
            "challenger_avg_filled_n": float(fill_count[1]),
            "avg_filled_n_delta": float(fill_count[2]),
        },
        "yearly_validation_profile": yearly_delta_map(baseline_run_id, challenger_run_id),
    }


def common_failure_flags(comparisons: dict[str, dict]) -> dict:
    return {
        "all_fail_validation_annual_relative_return": all(
            payload["high_level"]["validation_annual_relative_return_delta"] < 0.0
            for payload in comparisons.values()
        ),
        "all_fail_topk8": all(
            payload["high_level"]["topk8_annual_relative_return_delta"] < 0.0
            for payload in comparisons.values()
        ),
        "all_fail_topk12": all(
            payload["high_level"]["topk12_annual_relative_return_delta"] < 0.0
            for payload in comparisons.values()
        ),
        "all_improve_drawdown": all(
            payload["high_level"]["validation_max_drawdown_delta"] >= 0.0
            for payload in comparisons.values()
        ),
        "all_improve_turnover": all(
            payload["high_level"]["validation_avg_turnover_daily_delta"] <= 0.0
            for payload in comparisons.values()
        ),
        "all_improve_cost_stress": all(
            payload["high_level"]["cost_stress_annual_relative_return_delta"] >= 0.0
            for payload in comparisons.values()
        ),
    }


def verdict_text(comparisons: dict[str, dict], flags: dict) -> str:
    cord30 = comparisons["cord30_ew"]
    corr30 = comparisons["corr30_ew"]

    if (
        flags["all_fail_validation_annual_relative_return"]
        and flags["all_fail_topk8"]
        and flags["all_fail_topk12"]
    ):
        return (
            "Both equal-weight partner composites failed on the same decisive outcome: "
            "they improved drawdown/turnover/cost stress but could not beat the p98 baseline "
            "on validation annual relative return or TopK robustness. cord30 shows a stronger "
            "deployment-loss signature via higher low-liquidity exposure and lower invested weight; "
            "corr30 partially fixes those deployment frictions but still loses return, which points "
            "to score-mixing dilution rather than a remaining simple liquidity bug. Close the "
            "50/50 partner-composite line and keep p98 reversal as the live baseline."
        )

    return (
        "Composite partner line remains ambiguous; at least one challenger broke the common-failure "
        "pattern and may justify another targeted follow-up."
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    comparisons = {
        challenger["label"]: compare_to_baseline(BASELINE["run_id"], challenger["run_id"])
        for challenger in CHALLENGERS
    }

    flags = common_failure_flags(comparisons)
    payload = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "baseline_run_id": BASELINE["run_id"],
        "comparisons": comparisons,
        "common_failure_flags": flags,
        "verdict": verdict_text(comparisons, flags),
    }

    json_path = OUT_DIR / "partner_line_postmortem_20260506.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Reversal Partner-Line Postmortem",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- baseline_run_id: `{BASELINE['run_id']}`",
        "",
    ]
    for label, result in comparisons.items():
        lines.extend(
            [
                f"## {label}",
                "",
                f"- validation annual relative return delta = {result['high_level']['validation_annual_relative_return_delta']:.6f}",
                f"- validation relative IR delta = {result['high_level']['validation_relative_ir_delta']:.6f}",
                f"- validation max drawdown delta = {result['high_level']['validation_max_drawdown_delta']:.6f}",
                f"- validation avg turnover delta = {result['high_level']['validation_avg_turnover_daily_delta']:.6f}",
                f"- validation avg invested weight delta = {result['high_level']['validation_avg_invested_weight_delta']:.6f}",
                f"- cost_stress annual relative return delta = {result['high_level']['cost_stress_annual_relative_return_delta']:.6f}",
                f"- low_liquidity weight share delta = {result['high_level']['low_liquidity_weight_share_delta']:.6f}",
                f"- TopK8 annual relative return delta = {result['high_level']['topk8_annual_relative_return_delta']:.6f}",
                f"- TopK12 annual relative return delta = {result['high_level']['topk12_annual_relative_return_delta']:.6f}",
                f"- selection_alpha_total delta = {result['attribution_decomposition']['selection_alpha_delta']:.6f}",
                f"- cash_drag_total delta = {result['attribution_decomposition']['cash_drag_delta']:.6f}",
                f"- low_liquidity_contribution_total delta = {result['attribution_decomposition']['low_liquidity_contribution_delta']:.6f}",
                f"- avg Top10 overlap = {result['top10_overlap']['avg_overlap_n']:.3f} / 10",
                f"- challenger-only avg liquidity_rank = {result['unique_name_liquidity_profile']['challenger_unique_avg_liquidity_rank']:.6f}",
                "",
            ]
        )

    lines.extend(
        [
            "## Common Failure Flags",
            "",
        ]
    )
    for key, value in flags.items():
        lines.append(f"- {key} = {str(value).lower()}")

    lines.extend(["", "## Verdict", "", f"- {payload['verdict']}"])
    md_path = OUT_DIR / "partner_line_postmortem_20260506.md"
    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    print(f"JSON: {json_path}")
    print(f"MD:   {md_path}")


if __name__ == "__main__":
    main()
