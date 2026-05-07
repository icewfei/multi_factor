#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Minimal diagnosis for the live p98 reversal baseline.

Goal:
- summarize the current remaining deployment bottlenecks
- decide whether the next exploratory axis should be TopK geometry
  or a tighter liquidity guard
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
OUT_DIR = FIXED_TEST_DIR / "reversal_p98_baseline_diagnosis"

RUN_ID = "confirmatory_reversal_p98_trainval_20260506"
PANEL_RUN_ID = "project_panels_research_trainval_20211231_20260429"
TOPK_GRID = [8, 10, 12, 15, 20]


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


def yearly_profile() -> dict[str, dict]:
    rows = read_backtest_rows(RUN_ID)
    bucket: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "rel_sum": 0.0,
            "days": 0.0,
            "invested_sum": 0.0,
            "turnover_sum": 0.0,
        }
    )
    for row in rows:
        if row["relative_return_daily"] in ("", None):
            continue
        year = row["trade_date"][:4]
        bucket[year]["rel_sum"] += float(row["relative_return_daily"])
        bucket[year]["days"] += 1
        bucket[year]["invested_sum"] += float(row["invested_weight"])
        bucket[year]["turnover_sum"] += float(row["turnover_daily"])

    out: dict[str, dict] = {}
    for year, payload in sorted(bucket.items()):
        n = int(payload["days"])
        if n == 0:
            continue
        out[year] = {
            "avg_relative_return_daily": payload["rel_sum"] / n,
            "avg_invested_weight": payload["invested_sum"] / n,
            "avg_turnover_daily": payload["turnover_sum"] / n,
            "n_days": n,
        }
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    latest_attempt = load_json(RUN_STATE_DIR / RUN_ID / "run_state_latest_attempt.json")
    attempt_dir = RUN_STATE_DIR / RUN_ID / "attempts" / latest_attempt["attempt_id"]
    fixed_dir = FIXED_TEST_DIR / RUN_ID

    validation = load_json(fixed_dir / "validation_readout.json")
    cost = load_json(fixed_dir / "cost_stress_summary.json")
    low_liq = load_json(fixed_dir / "low_liquidity_exposure_summary.json")
    topk_perturb = load_json(fixed_dir / "topk_perturbation_summary.json")
    scores_path = RUN_STATE_DIR / RUN_ID / "model_scores_D0.parquet"
    label_path = RUN_STATE_DIR / PANEL_RUN_ID / "project_label_panel.parquet"
    rank_path = attempt_dir / "ranking_state_daily.parquet"
    exec_path = attempt_dir / "execution_state_daily.parquet"

    con = duckdb.connect()
    try:
        con.execute(f"CREATE OR REPLACE VIEW scores AS SELECT * FROM read_parquet({sql_path(scores_path)})")
        con.execute(f"CREATE OR REPLACE VIEW labels AS SELECT * FROM read_parquet({sql_path(label_path)})")
        con.execute(f"CREATE OR REPLACE VIEW rank_state AS SELECT * FROM read_parquet({sql_path(rank_path)})")
        con.execute(f"CREATE OR REPLACE VIEW exec_state AS SELECT * FROM read_parquet({sql_path(exec_path)})")

        top10_profile = con.execute(
            """
            WITH top10 AS (
                SELECT
                    r.signal_date,
                    r.instrument,
                    s.liquidity_rank,
                    e.entry_filled_D1
                FROM rank_state r
                LEFT JOIN scores s
                  ON r.signal_date = s.signal_date AND r.instrument = s.instrument
                LEFT JOIN exec_state e
                  ON r.signal_date = e.signal_date AND r.instrument = e.instrument
                WHERE r.topk_frozen_D0
            )
            SELECT
                AVG(CASE WHEN entry_filled_D1 THEN 1.0 ELSE 0.0 END) AS fill_rate,
                AVG(liquidity_rank) AS avg_liquidity_rank,
                MEDIAN(liquidity_rank) AS median_liquidity_rank,
                AVG(CASE WHEN liquidity_rank < 0.60 THEN 1.0 ELSE 0.0 END) AS share_below_060
            FROM top10
            """
        ).fetchone()

        topk_curve = []
        for topk in TOPK_GRID:
            row = con.execute(
                f"""
                WITH ranked AS (
                    SELECT
                        s.signal_date,
                        s.instrument,
                        s.model_score_D0,
                        s.liquidity_rank,
                        l.label_5d_next_open_close AS oracle_label,
                        ROW_NUMBER() OVER (
                            PARTITION BY s.signal_date
                            ORDER BY s.model_score_D0 DESC, s.instrument ASC
                        ) AS rank_desc
                    FROM scores s
                    JOIN labels l
                      ON s.snapshot_id = l.snapshot_id
                     AND s.instrument = l.instrument
                     AND s.signal_date = l.signal_date
                    WHERE s.model_score_D0 IS NOT NULL
                      AND l.label_5d_next_open_close IS NOT NULL
                )
                SELECT
                    AVG(CASE WHEN rank_desc <= {topk} THEN oracle_label END) AS topk_avg_label,
                    AVG(CASE WHEN rank_desc <= {topk} THEN liquidity_rank END) AS topk_avg_liquidity_rank
                FROM ranked
                """
            ).fetchone()
            topk_curve.append(
                {
                    "topk": topk,
                    "avg_oracle_label": float(row[0]) if row[0] is not None else None,
                    "avg_liquidity_rank": float(row[1]) if row[1] is not None else None,
                }
            )
    finally:
        con.close()

    next_axis = "topk_geometry"
    if low_liq["low_liquidity_weight_share"] > 0.15 or (top10_profile[3] is not None and float(top10_profile[3]) > 0.35):
        next_axis = "liquidity_guard"
    else:
        top10 = next(row for row in topk_curve if row["topk"] == 10)
        top12 = next(row for row in topk_curve if row["topk"] == 12)
        top15 = next(row for row in topk_curve if row["topk"] == 15)
        if (
            top12["avg_oracle_label"] is not None
            and top10["avg_oracle_label"] is not None
            and top15["avg_oracle_label"] is not None
            and top12["avg_oracle_label"] >= top10["avg_oracle_label"] * 0.97
            and top15["avg_oracle_label"] >= top10["avg_oracle_label"] * 0.94
            and top12["avg_liquidity_rank"] is not None
            and top10["avg_liquidity_rank"] is not None
            and top12["avg_liquidity_rank"] > top10["avg_liquidity_rank"]
        ):
            next_axis = "topk_geometry"
        else:
            next_axis = "liquidity_guard"

    payload = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "run_id": RUN_ID,
        "validation": validation,
        "cost_stress": cost,
        "low_liquidity": low_liq,
        "topk_perturbation": topk_perturb,
        "top10_deployment_profile": {
            "fill_rate": float(top10_profile[0]) if top10_profile[0] is not None else None,
            "avg_liquidity_rank": float(top10_profile[1]) if top10_profile[1] is not None else None,
            "median_liquidity_rank": float(top10_profile[2]) if top10_profile[2] is not None else None,
            "share_below_060": float(top10_profile[3]) if top10_profile[3] is not None else None,
        },
        "oracle_topk_curve": topk_curve,
        "yearly_profile": yearly_profile(),
        "recommended_next_axis": next_axis,
    }

    json_path = OUT_DIR / "reversal_p98_baseline_diagnosis_20260506.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Reversal P98 Baseline Diagnosis",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- validation annual_relative_return = {validation['annual_relative_return']:.6f}",
        f"- validation relative_ir = {validation['relative_ir']:.6f}",
        f"- validation max_drawdown = {validation['max_drawdown']:.6f}",
        f"- validation avg_invested_weight = {validation['avg_invested_weight']:.6f}",
        f"- cost_stress annual_relative_return = {cost['annual_relative_return']:.6f}",
        f"- low_liquidity_weight_share = {low_liq['low_liquidity_weight_share']:.6f}",
        f"- low_liquidity_contribution_total = {low_liq['low_liquidity_contribution_total']:.6f}",
        "",
        "## Top10 deployment profile",
        "",
        f"- fill_rate = {payload['top10_deployment_profile']['fill_rate']:.6f}",
        f"- avg_liquidity_rank = {payload['top10_deployment_profile']['avg_liquidity_rank']:.6f}",
        f"- median_liquidity_rank = {payload['top10_deployment_profile']['median_liquidity_rank']:.6f}",
        f"- share_below_060 = {payload['top10_deployment_profile']['share_below_060']:.6f}",
        "",
        "## Oracle TopK curve",
        "",
        "| topk | avg_oracle_label | avg_liquidity_rank |",
        "|---|---|---|",
    ]
    for row in topk_curve:
        lines.append(
            f"| {row['topk']} | {row['avg_oracle_label']:.6f} | {row['avg_liquidity_rank']:.6f} |"
        )
    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            f"- recommended_next_axis = `{next_axis}`",
        ]
    )

    md_path = OUT_DIR / "reversal_p98_baseline_diagnosis_20260506.md"
    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    print(f"JSON: {json_path}")
    print(f"MD:   {md_path}")


if __name__ == "__main__":
    main()
