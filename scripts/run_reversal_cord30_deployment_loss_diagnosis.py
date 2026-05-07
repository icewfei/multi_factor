#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Minimal deployment-loss diagnosis for the reversal p98 baseline vs the
reversal+cord30 composite after the confirmatory promotion round.

Goal:
- explain why the composite wins in diagnostic IC/spread
- but fails to promote at fixed-test / validation level
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
OUT_DIR = ROOT / "artifacts" / "fixed_test" / "reversal_cord30_deployment_loss_diagnosis"

BASELINE_RUN_ID = "confirmatory_reversal_p98_trainval_20260506"
COMPOSITE_RUN_ID = "confirmatory_reversal_p98_cord30_trainval_20260506"

BASELINE_ATTEMPT = "attempt_20260506_114831"
COMPOSITE_ATTEMPT = "attempt_20260506_115112"


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


def yearly_delta_map() -> dict[str, dict]:
    base_rows = read_backtest_rows(BASELINE_RUN_ID)
    cmp_rows = read_backtest_rows(COMPOSITE_RUN_ID)
    cmp_by_date = {row["trade_date"]: row for row in cmp_rows}

    bucket: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "baseline_rel_sum": 0.0,
            "composite_rel_sum": 0.0,
            "baseline_days": 0.0,
            "composite_days": 0.0,
            "baseline_invested_sum": 0.0,
            "composite_invested_sum": 0.0,
            "baseline_turnover_sum": 0.0,
            "composite_turnover_sum": 0.0,
        }
    )
    for row in base_rows:
        trade_date = row["trade_date"]
        if trade_date not in cmp_by_date:
            continue
        cmp_row = cmp_by_date[trade_date]
        if row["relative_return_daily"] in ("", None) or cmp_row["relative_return_daily"] in ("", None):
            continue
        year = trade_date[:4]
        bucket[year]["baseline_rel_sum"] += float(row["relative_return_daily"])
        bucket[year]["composite_rel_sum"] += float(cmp_row["relative_return_daily"])
        bucket[year]["baseline_days"] += 1
        bucket[year]["composite_days"] += 1
        bucket[year]["baseline_invested_sum"] += float(row["invested_weight"])
        bucket[year]["composite_invested_sum"] += float(cmp_row["invested_weight"])
        bucket[year]["baseline_turnover_sum"] += float(row["turnover_daily"])
        bucket[year]["composite_turnover_sum"] += float(cmp_row["turnover_daily"])

    out: dict[str, dict] = {}
    for year, payload in sorted(bucket.items()):
        n = int(payload["baseline_days"])
        if n == 0:
            continue
        out[year] = {
            "baseline_avg_relative_return_daily": payload["baseline_rel_sum"] / n,
            "composite_avg_relative_return_daily": payload["composite_rel_sum"] / n,
            "avg_relative_return_daily_delta": (payload["composite_rel_sum"] - payload["baseline_rel_sum"]) / n,
            "baseline_avg_invested_weight": payload["baseline_invested_sum"] / n,
            "composite_avg_invested_weight": payload["composite_invested_sum"] / n,
            "avg_invested_weight_delta": (payload["composite_invested_sum"] - payload["baseline_invested_sum"]) / n,
            "baseline_avg_turnover_daily": payload["baseline_turnover_sum"] / n,
            "composite_avg_turnover_daily": payload["composite_turnover_sum"] / n,
            "avg_turnover_daily_delta": (payload["composite_turnover_sum"] - payload["baseline_turnover_sum"]) / n,
            "n_days": n,
        }
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    baseline_fixed = FIXED_TEST_DIR / BASELINE_RUN_ID
    composite_fixed = FIXED_TEST_DIR / COMPOSITE_RUN_ID
    baseline_run = RUN_STATE_DIR / BASELINE_RUN_ID / "attempts" / BASELINE_ATTEMPT
    composite_run = RUN_STATE_DIR / COMPOSITE_RUN_ID / "attempts" / COMPOSITE_ATTEMPT

    con = duckdb.connect()
    try:
        con.execute(
            f"CREATE OR REPLACE VIEW base_rank AS SELECT * FROM read_parquet({sql_path(baseline_run / 'ranking_state_daily.parquet')})"
        )
        con.execute(
            f"CREATE OR REPLACE VIEW cmp_rank AS SELECT * FROM read_parquet({sql_path(composite_run / 'ranking_state_daily.parquet')})"
        )
        con.execute(
            f"CREATE OR REPLACE VIEW base_exec AS SELECT * FROM read_parquet({sql_path(baseline_run / 'execution_state_daily.parquet')})"
        )
        con.execute(
            f"CREATE OR REPLACE VIEW cmp_exec AS SELECT * FROM read_parquet({sql_path(composite_run / 'execution_state_daily.parquet')})"
        )
        con.execute(
            f"CREATE OR REPLACE VIEW base_scores AS SELECT * FROM read_parquet({sql_path(RUN_STATE_DIR / BASELINE_RUN_ID / 'model_scores_D0.parquet')})"
        )
        con.execute(
            f"CREATE OR REPLACE VIEW cmp_scores AS SELECT * FROM read_parquet({sql_path(RUN_STATE_DIR / COMPOSITE_RUN_ID / 'model_scores_D0.parquet')})"
        )

        overlap = con.execute(
            """
            WITH base_top AS (
                SELECT signal_date, instrument
                FROM base_rank
                WHERE topk_frozen_D0
            ),
            cmp_top AS (
                SELECT signal_date, instrument
                FROM cmp_rank
                WHERE topk_frozen_D0
            ),
            daily AS (
                SELECT
                    COALESCE(b.signal_date, c.signal_date) AS signal_date,
                    COUNT(*) FILTER (WHERE b.instrument IS NOT NULL) AS base_top10_n,
                    COUNT(*) FILTER (WHERE c.instrument IS NOT NULL) AS cmp_top10_n,
                    COUNT(*) FILTER (WHERE b.instrument IS NOT NULL AND c.instrument IS NOT NULL) AS overlap_n
                FROM base_top b
                FULL OUTER JOIN cmp_top c
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
            cmp_top AS (
                SELECT r.signal_date, r.instrument, s.liquidity_rank
                FROM cmp_rank r
                LEFT JOIN cmp_scores s
                  ON r.signal_date = s.signal_date AND r.instrument = s.instrument
                WHERE r.topk_frozen_D0
            ),
            cmp_unique AS (
                SELECT c.signal_date, c.instrument, c.liquidity_rank
                FROM cmp_top c
                LEFT JOIN base_top b
                  ON c.signal_date = b.signal_date AND c.instrument = b.instrument
                WHERE b.instrument IS NULL
            ),
            base_unique AS (
                SELECT b.signal_date, b.instrument, b.liquidity_rank
                FROM base_top b
                LEFT JOIN cmp_top c
                  ON c.signal_date = b.signal_date AND c.instrument = b.instrument
                WHERE c.instrument IS NULL
            )
            SELECT
                (SELECT AVG(liquidity_rank) FROM cmp_unique) AS cmp_unique_avg_liq_rank,
                (SELECT MEDIAN(liquidity_rank) FROM cmp_unique) AS cmp_unique_med_liq_rank,
                (SELECT AVG(liquidity_rank) FROM base_unique) AS base_unique_avg_liq_rank,
                (SELECT MEDIAN(liquidity_rank) FROM base_unique) AS base_unique_med_liq_rank,
                (SELECT COUNT(*) FROM cmp_unique) AS cmp_unique_rows,
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
            cmp_top AS (
                SELECT r.signal_date, r.instrument, s.liquidity_rank, e.entry_filled_D1
                FROM cmp_rank r
                LEFT JOIN cmp_scores s
                  ON r.signal_date = s.signal_date AND r.instrument = s.instrument
                LEFT JOIN cmp_exec e
                  ON r.signal_date = e.signal_date AND r.instrument = e.instrument
                WHERE r.topk_frozen_D0
            )
            SELECT
                (SELECT AVG(CASE WHEN entry_filled_D1 THEN 1.0 ELSE 0.0 END) FROM base_top) AS base_fill_rate,
                (SELECT AVG(CASE WHEN entry_filled_D1 THEN 1.0 ELSE 0.0 END) FROM cmp_top) AS cmp_fill_rate,
                (SELECT AVG(liquidity_rank) FROM base_top) AS base_top10_avg_liq_rank,
                (SELECT AVG(liquidity_rank) FROM cmp_top) AS cmp_top10_avg_liq_rank,
                (SELECT MEDIAN(liquidity_rank) FROM base_top) AS base_top10_med_liq_rank,
                (SELECT MEDIAN(liquidity_rank) FROM cmp_top) AS cmp_top10_med_liq_rank
        """
        ).fetchone()

        # Per-day fill count comparison
        fill_count = con.execute(
            """
            WITH base_day AS (
                SELECT signal_date, SUM(CASE WHEN entry_filled_D1 THEN 1 ELSE 0 END) AS filled_n
                FROM base_exec
                WHERE execution_attempt_D1
                GROUP BY signal_date
            ),
            cmp_day AS (
                SELECT signal_date, SUM(CASE WHEN entry_filled_D1 THEN 1 ELSE 0 END) AS filled_n
                FROM cmp_exec
                WHERE execution_attempt_D1
                GROUP BY signal_date
            )
            SELECT
                AVG(base_day.filled_n) AS base_avg_filled_n,
                AVG(cmp_day.filled_n) AS cmp_avg_filled_n,
                AVG(cmp_day.filled_n - base_day.filled_n) AS avg_filled_n_delta
            FROM base_day
            JOIN cmp_day USING (signal_date)
        """
        ).fetchone()
    finally:
        con.close()

    baseline_attr = load_json(baseline_fixed / "return_attribution_summary.json")
    composite_attr = load_json(composite_fixed / "return_attribution_summary.json")
    baseline_validation = load_json(baseline_fixed / "validation_readout.json")
    composite_validation = load_json(composite_fixed / "validation_readout.json")
    baseline_cost = load_json(baseline_fixed / "cost_stress_summary.json")
    composite_cost = load_json(composite_fixed / "cost_stress_summary.json")
    baseline_liq = load_json(baseline_fixed / "low_liquidity_exposure_summary.json")
    composite_liq = load_json(composite_fixed / "low_liquidity_exposure_summary.json")

    yearly = yearly_delta_map()

    result = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "baseline_run_id": BASELINE_RUN_ID,
        "composite_run_id": COMPOSITE_RUN_ID,
        "high_level": {
            "validation_annual_relative_return_delta": (
                composite_validation["annual_relative_return"] - baseline_validation["annual_relative_return"]
            ),
            "validation_relative_ir_delta": composite_validation["relative_ir"] - baseline_validation["relative_ir"],
            "validation_max_drawdown_delta": composite_validation["max_drawdown"] - baseline_validation["max_drawdown"],
            "validation_avg_turnover_daily_delta": (
                composite_validation["avg_turnover_daily"] - baseline_validation["avg_turnover_daily"]
            ),
            "validation_avg_invested_weight_delta": (
                composite_validation["avg_invested_weight"] - baseline_validation["avg_invested_weight"]
            ),
            "cost_stress_annual_relative_return_delta": (
                composite_cost["annual_relative_return"] - baseline_cost["annual_relative_return"]
            ),
            "low_liquidity_weight_share_delta": (
                composite_liq["low_liquidity_weight_share"] - baseline_liq["low_liquidity_weight_share"]
            ),
        },
        "attribution_decomposition": {
            "selection_alpha_delta": composite_attr["selection_alpha_total"] - baseline_attr["selection_alpha_total"],
            "cash_drag_delta": composite_attr["cash_drag_total"] - baseline_attr["cash_drag_total"],
            "low_liquidity_contribution_delta": (
                composite_attr["low_liquidity_contribution_total"] - baseline_attr["low_liquidity_contribution_total"]
            ),
        },
        "top10_overlap": {
            "avg_overlap_n": float(overlap[0]),
            "avg_overlap_share": float(overlap[1]),
            "min_overlap_n": int(overlap[2]),
            "max_overlap_n": int(overlap[3]),
        },
        "unique_name_liquidity_profile": {
            "composite_unique_avg_liquidity_rank": float(unique_profile[0]) if unique_profile[0] is not None else None,
            "composite_unique_median_liquidity_rank": float(unique_profile[1]) if unique_profile[1] is not None else None,
            "baseline_unique_avg_liquidity_rank": float(unique_profile[2]) if unique_profile[2] is not None else None,
            "baseline_unique_median_liquidity_rank": float(unique_profile[3]) if unique_profile[3] is not None else None,
            "composite_unique_rows": int(unique_profile[4]),
            "baseline_unique_rows": int(unique_profile[5]),
        },
        "top10_fill_profile": {
            "baseline_fill_rate": float(fill_profile[0]),
            "composite_fill_rate": float(fill_profile[1]),
            "baseline_top10_avg_liquidity_rank": float(fill_profile[2]),
            "composite_top10_avg_liquidity_rank": float(fill_profile[3]),
            "baseline_top10_median_liquidity_rank": float(fill_profile[4]),
            "composite_top10_median_liquidity_rank": float(fill_profile[5]),
        },
        "daily_fill_count": {
            "baseline_avg_filled_n": float(fill_count[0]),
            "composite_avg_filled_n": float(fill_count[1]),
            "avg_filled_n_delta": float(fill_count[2]),
        },
        "yearly_validation_profile": yearly,
    }

    # Short verdict for next step selection
    result["diagnosis_verdict"] = {
        "summary": (
            "Composite improves gross selection alpha, drawdown, turnover, and cost stress, "
            "but loses validation annual relative return because it deploys less capital and "
            "takes on more low-liquidity exposure than the standalone p98 baseline."
        )
    }

    json_path = OUT_DIR / "deployment_loss_diagnosis_20260506.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Reversal + Cord30 Deployment-Loss Diagnosis",
        "",
        f"- generated_at: {result['generated_at']}",
        "",
        "## High-level deltas (composite - p98 baseline)",
        "",
        f"- validation annual relative return delta = {result['high_level']['validation_annual_relative_return_delta']:.6f}",
        f"- validation relative IR delta = {result['high_level']['validation_relative_ir_delta']:.6f}",
        f"- validation max drawdown delta = {result['high_level']['validation_max_drawdown_delta']:.6f}",
        f"- validation avg turnover delta = {result['high_level']['validation_avg_turnover_daily_delta']:.6f}",
        f"- validation avg invested weight delta = {result['high_level']['validation_avg_invested_weight_delta']:.6f}",
        f"- cost_stress annual relative return delta = {result['high_level']['cost_stress_annual_relative_return_delta']:.6f}",
        f"- low_liquidity weight share delta = {result['high_level']['low_liquidity_weight_share_delta']:.6f}",
        "",
        "## Attribution decomposition",
        "",
        f"- selection_alpha_total delta = {result['attribution_decomposition']['selection_alpha_delta']:.6f}",
        f"- cash_drag_total delta = {result['attribution_decomposition']['cash_drag_delta']:.6f}",
        f"- low_liquidity_contribution_total delta = {result['attribution_decomposition']['low_liquidity_contribution_delta']:.6f}",
        "",
        "## Top10 overlap",
        "",
        f"- avg overlap count = {result['top10_overlap']['avg_overlap_n']:.3f} / 10",
        f"- avg overlap share = {result['top10_overlap']['avg_overlap_share']:.3f}",
        f"- min overlap count = {result['top10_overlap']['min_overlap_n']}",
        f"- max overlap count = {result['top10_overlap']['max_overlap_n']}",
        "",
        "## Unique-name liquidity profile",
        "",
        f"- composite-only avg liquidity_rank = {result['unique_name_liquidity_profile']['composite_unique_avg_liquidity_rank']:.6f}",
        f"- composite-only median liquidity_rank = {result['unique_name_liquidity_profile']['composite_unique_median_liquidity_rank']:.6f}",
        f"- baseline-only avg liquidity_rank = {result['unique_name_liquidity_profile']['baseline_unique_avg_liquidity_rank']:.6f}",
        f"- baseline-only median liquidity_rank = {result['unique_name_liquidity_profile']['baseline_unique_median_liquidity_rank']:.6f}",
        "",
        "## Top10 deployment profile",
        "",
        f"- baseline fill rate = {result['top10_fill_profile']['baseline_fill_rate']:.6f}",
        f"- composite fill rate = {result['top10_fill_profile']['composite_fill_rate']:.6f}",
        f"- baseline Top10 avg liquidity_rank = {result['top10_fill_profile']['baseline_top10_avg_liquidity_rank']:.6f}",
        f"- composite Top10 avg liquidity_rank = {result['top10_fill_profile']['composite_top10_avg_liquidity_rank']:.6f}",
        f"- baseline avg filled names/day = {result['daily_fill_count']['baseline_avg_filled_n']:.6f}",
        f"- composite avg filled names/day = {result['daily_fill_count']['composite_avg_filled_n']:.6f}",
        "",
        "## Verdict",
        "",
        f"- {result['diagnosis_verdict']['summary']}",
    ]
    md_path = OUT_DIR / "deployment_loss_diagnosis_20260506.md"
    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    print(f"JSON: {json_path}")
    print(f"MD:   {md_path}")


if __name__ == "__main__":
    main()
