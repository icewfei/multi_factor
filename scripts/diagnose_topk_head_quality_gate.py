#!/opt/anaconda3/envs/quant_trade/bin/python
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DB = Path(
    "/Users/wy/MiscProject/tushare_data/parquet_duckdb/data/snapshots/"
    "warehouse_20260429_trainval_20211231/duckdb/warehouse.duckdb"
)
DEFAULT_SPLIT_PANEL = (
    ROOT / "artifacts" / "run_state" / "project_panels_research_trainval_20211231_20260429" / "dataset_split_daily.parquet"
)
DEFAULT_EXECUTION_PANEL = (
    ROOT / "artifacts" / "run_state" / "project_panels_research_trainval_20211231_20260429" / "project_execution_panel.parquet"
)
DEFAULT_BASELINE_SCORES = Path("/private/tmp/baseline_multi_equal_weight_v1_exact_model_scores_D0.parquet")
DEFAULT_CONFIRMED5_SCORES = Path("/private/tmp/confirmed5_same_contract_registered_model_scores_D0.parquet")
DEFAULT_V2_SCORES = Path("/private/tmp/local_nlc_v2_confirmed5_locked_cs_volatility_discount_20260509/model_scores_D0.parquet")
DEFAULT_V3_SCORES = Path("/private/tmp/nlc_v3_real_trainval_score_gate_20260512/out/model_scores_D0.parquet")

METRIC_SPECS: list[dict[str, str]] = [
    {
        "name": "top1_minus_top2",
        "label": "TopK 内部头两名 score gap",
        "family": "score_shape",
    },
    {
        "name": "top1_minus_topk_min",
        "label": "TopK 内部 top1 到 weakest-head 的 score gap",
        "family": "score_shape",
    },
    {
        "name": "topk_score_std",
        "label": "TopK 内部 score dispersion",
        "family": "score_shape",
    },
    {
        "name": "topk_mean_minus_pool_median",
        "label": "TopK 均值相对候选池中位数的 score separation",
        "family": "score_shape",
    },
    {
        "name": "topk_min_minus_pool_median",
        "label": "TopK 最弱头部相对候选池中位数的 score separation",
        "family": "score_shape",
    },
    {
        "name": "topk_mean_vs_pool_iqr",
        "label": "TopK 均值相对候选池 IQR 的标准化 separation",
        "family": "score_shape",
    },
    {
        "name": "topk_min_vs_pool_iqr",
        "label": "TopK 最弱头部相对候选池 IQR 的标准化 separation",
        "family": "score_shape",
    },
    {
        "name": "topk_avg_volatility_20d",
        "label": "TopK 平均 volatility_20d",
        "family": "exposure",
    },
    {
        "name": "topk_avg_amount",
        "label": "TopK 平均 amount",
        "family": "exposure",
    },
    {
        "name": "topk_avg_total_mv",
        "label": "TopK 平均 total_mv",
        "family": "exposure",
    },
    {
        "name": "topk_avg_turnover_rate",
        "label": "TopK 平均 turnover_rate",
        "family": "exposure",
    },
]


def sql_path(path: Path) -> str:
    return path.as_posix().replace("'", "''")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose whether D0-visible TopK head states support a low-degree head-quality gate."
    )
    parser.add_argument("--source-db", type=Path, default=DEFAULT_SOURCE_DB)
    parser.add_argument("--split-panel", type=Path, default=DEFAULT_SPLIT_PANEL)
    parser.add_argument("--execution-panel", type=Path, default=DEFAULT_EXECUTION_PANEL)
    parser.add_argument("--baseline-scores", type=Path, default=DEFAULT_BASELINE_SCORES)
    parser.add_argument("--confirmed5-scores", type=Path, default=DEFAULT_CONFIRMED5_SCORES)
    parser.add_argument("--v2-scores", type=Path, default=DEFAULT_V2_SCORES)
    parser.add_argument("--v3-scores", type=Path, default=DEFAULT_V3_SCORES)
    parser.add_argument("--include-v3-reference", action="store_true")
    parser.add_argument("--topk", type=int, default=10)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    return parser.parse_args()


def ensure_exists(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} not found: {path}")


def summarize_numeric(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "p10": None,
            "p90": None,
            "min": None,
            "max": None,
        }
    series = pd.Series(values, dtype="float64")
    return {
        "count": int(series.size),
        "mean": float(series.mean()),
        "median": float(series.median()),
        "p10": float(series.quantile(0.10)),
        "p90": float(series.quantile(0.90)),
        "min": float(series.min()),
        "max": float(series.max()),
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_daily_head_frame(
    con: duckdb.DuckDBPyConnection,
    score_path: Path,
    *,
    view_name: str,
    topk: int,
) -> pd.DataFrame:
    con.execute(f"CREATE OR REPLACE VIEW {view_name} AS SELECT * FROM read_parquet('{sql_path(score_path)}')")
    query = f"""
    WITH scoped AS (
        SELECT
            s.snapshot_id,
            s.instrument,
            s.signal_date,
            s.model_score_D0,
            d.split_bucket
        FROM {view_name} s
        INNER JOIN split_days d
            USING (signal_date)
    ),
    ranked AS (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY signal_date
                ORDER BY model_score_D0 DESC, instrument ASC
            ) AS rank_position
        FROM scoped
    ),
    pool_stats AS (
        SELECT
            split_bucket,
            signal_date,
            COUNT(*) AS pool_count,
            MEDIAN(model_score_D0) AS pool_score_median,
            AVG(model_score_D0) AS pool_score_mean,
            STDDEV_SAMP(model_score_D0) AS pool_score_std,
            QUANTILE_CONT(model_score_D0, 0.25) AS pool_score_q25,
            QUANTILE_CONT(model_score_D0, 0.75) AS pool_score_q75
        FROM ranked
        GROUP BY 1, 2
    ),
    topk_rows AS (
        SELECT
            r.split_bucket,
            r.signal_date,
            r.snapshot_id,
            r.instrument,
            r.rank_position,
            r.model_score_D0,
            e.execution_delayed_realized_return,
            f.amount,
            f.total_mv,
            f.turnover_rate,
            f.volatility_20d
        FROM ranked r
        LEFT JOIN execution_panel e
            USING (snapshot_id, instrument, signal_date)
        LEFT JOIN source_features f
            USING (snapshot_id, instrument, signal_date)
        WHERE r.rank_position <= {topk}
    ),
    daily AS (
        SELECT
            split_bucket,
            signal_date,
            COUNT(*) AS topk_count,
            AVG(model_score_D0) AS topk_score_mean,
            MEDIAN(model_score_D0) AS topk_score_median,
            STDDEV_SAMP(model_score_D0) AS topk_score_std,
            MIN(model_score_D0) AS topk_score_min,
            MAX(model_score_D0) AS top1_score,
            MAX(CASE WHEN rank_position = 2 THEN model_score_D0 END) AS top2_score,
            AVG(amount) AS topk_avg_amount,
            AVG(total_mv) AS topk_avg_total_mv,
            AVG(turnover_rate) AS topk_avg_turnover_rate,
            AVG(volatility_20d) AS topk_avg_volatility_20d,
            AVG(execution_delayed_realized_return) AS topk_realized_return_mean,
            MEDIAN(execution_delayed_realized_return) AS topk_realized_return_median,
            AVG(CASE WHEN execution_delayed_realized_return > 0 THEN 1.0 ELSE 0.0 END) AS topk_positive_rate,
            AVG(CASE WHEN execution_delayed_realized_return <= 0 THEN 1.0 ELSE 0.0 END) AS topk_non_positive_rate,
            AVG(CASE WHEN execution_delayed_realized_return <= -0.05 THEN 1.0 ELSE 0.0 END) AS topk_tail_loss_share_5pct,
            AVG(CASE WHEN execution_delayed_realized_return <= -0.10 THEN 1.0 ELSE 0.0 END) AS topk_tail_loss_share_10pct
        FROM topk_rows
        GROUP BY 1, 2
    )
    SELECT
        d.*,
        p.pool_count,
        p.pool_score_median,
        p.pool_score_mean,
        p.pool_score_std,
        p.pool_score_q25,
        p.pool_score_q75,
        d.top1_score - d.top2_score AS top1_minus_top2,
        d.top1_score - d.topk_score_min AS top1_minus_topk_min,
        d.topk_score_mean - p.pool_score_median AS topk_mean_minus_pool_median,
        d.topk_score_min - p.pool_score_median AS topk_min_minus_pool_median,
        CASE
            WHEN (p.pool_score_q75 - p.pool_score_q25) != 0
            THEN (d.topk_score_mean - p.pool_score_median) / (p.pool_score_q75 - p.pool_score_q25)
            ELSE NULL
        END AS topk_mean_vs_pool_iqr,
        CASE
            WHEN (p.pool_score_q75 - p.pool_score_q25) != 0
            THEN (d.topk_score_min - p.pool_score_median) / (p.pool_score_q75 - p.pool_score_q25)
            ELSE NULL
        END AS topk_min_vs_pool_iqr
    FROM daily d
    INNER JOIN pool_stats p
        USING (split_bucket, signal_date)
    ORDER BY signal_date
    """
    return con.execute(query).fetchdf()


def summarize_daily_frame(frame: pd.DataFrame) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for window in ("train", "validation"):
        subset = frame[frame["split_bucket"] == window].copy()
        result[window] = {
            "n_days": int(len(subset)),
            "daily_topk_realized_return_mean_distribution": summarize_numeric(
                subset["topk_realized_return_mean"].dropna().astype(float).tolist()
            ),
            "daily_topk_positive_rate_distribution": summarize_numeric(
                subset["topk_positive_rate"].dropna().astype(float).tolist()
            ),
            "daily_topk_tail_loss_share_5pct_distribution": summarize_numeric(
                subset["topk_tail_loss_share_5pct"].dropna().astype(float).tolist()
            ),
        }
    return result


def evaluate_metric_state(
    frame: pd.DataFrame,
    metric_name: str,
) -> dict[str, Any]:
    train = frame[(frame["split_bucket"] == "train") & frame[metric_name].notna()].copy()
    validation = frame[(frame["split_bucket"] == "validation") & frame[metric_name].notna()].copy()
    if train.empty:
        return {
            "metric_name": metric_name,
            "available": False,
            "reason": "train window missing",
        }

    q25 = float(train[metric_name].quantile(0.25))
    q75 = float(train[metric_name].quantile(0.75))
    low_train = train[train[metric_name] <= q25]
    high_train = train[train[metric_name] >= q75]
    low_train_mean = float(low_train["topk_realized_return_mean"].mean())
    high_train_mean = float(high_train["topk_realized_return_mean"].mean())
    weak_side = "low" if low_train_mean < high_train_mean else "high"

    if weak_side == "low":
        weak_train = low_train
        strong_train = high_train
        weak_validation = validation[validation[metric_name] <= q25]
        other_validation = validation[validation[metric_name] > q25]
    else:
        weak_train = high_train
        strong_train = low_train
        weak_validation = validation[validation[metric_name] >= q75]
        other_validation = validation[validation[metric_name] < q75]

    train_delta = float(weak_train["topk_realized_return_mean"].mean() - strong_train["topk_realized_return_mean"].mean())
    validation_other_mean = (
        float(other_validation["topk_realized_return_mean"].mean()) if not other_validation.empty else None
    )
    validation_weak_mean = (
        float(weak_validation["topk_realized_return_mean"].mean()) if not weak_validation.empty else None
    )
    validation_delta = (
        float(validation_weak_mean - validation_other_mean)
        if validation_weak_mean is not None and validation_other_mean is not None
        else None
    )
    train_spearman = train[[metric_name, "topk_realized_return_mean"]].corr(method="spearman").iloc[0, 1]
    validation_spearman = (
        validation[[metric_name, "topk_realized_return_mean"]].corr(method="spearman").iloc[0, 1]
        if not validation.empty
        else None
    )

    direction_consistent = bool(
        train_delta < 0
        and validation_delta is not None
        and validation_delta < 0
    )

    return {
        "metric_name": metric_name,
        "available": True,
        "train_threshold_q25": q25,
        "train_threshold_q75": q75,
        "weak_side": weak_side,
        "train_low_state_mean_return": low_train_mean,
        "train_high_state_mean_return": high_train_mean,
        "train_delta_weak_minus_strong": train_delta,
        "validation_delta_weak_minus_other": validation_delta,
        "train_weak_state_days": int(len(weak_train)),
        "validation_weak_state_days": int(len(weak_validation)),
        "train_weak_state_mean_return": float(weak_train["topk_realized_return_mean"].mean()),
        "validation_weak_state_mean_return": validation_weak_mean,
        "validation_other_state_mean_return": validation_other_mean,
        "train_weak_state_non_positive_rate": float((weak_train["topk_realized_return_mean"] <= 0).mean()),
        "validation_weak_state_non_positive_rate": (
            float((weak_validation["topk_realized_return_mean"] <= 0).mean()) if not weak_validation.empty else None
        ),
        "train_spearman": (float(train_spearman) if not pd.isna(train_spearman) else None),
        "validation_spearman": (
            float(validation_spearman) if validation_spearman is not None and not pd.isna(validation_spearman) else None
        ),
        "direction_consistent_train_validation": direction_consistent,
    }


def analyze_candidate(
    candidate_name: str,
    frame: pd.DataFrame,
) -> dict[str, Any]:
    metric_analysis: dict[str, Any] = {}
    consistent_conditions: list[dict[str, Any]] = []
    for spec in METRIC_SPECS:
        payload = evaluate_metric_state(frame, spec["name"])
        payload["label"] = spec["label"]
        payload["family"] = spec["family"]
        metric_analysis[spec["name"]] = payload
        if payload.get("direction_consistent_train_validation"):
            consistent_conditions.append(
                {
                    "metric_name": spec["name"],
                    "label": spec["label"],
                    "family": spec["family"],
                    "weak_side": payload["weak_side"],
                    "train_delta_weak_minus_strong": payload["train_delta_weak_minus_strong"],
                    "validation_delta_weak_minus_other": payload["validation_delta_weak_minus_other"],
                    "validation_weak_state_days": payload["validation_weak_state_days"],
                }
            )

    consistent_conditions.sort(
        key=lambda item: (
            item["validation_delta_weak_minus_other"],
            item["train_delta_weak_minus_strong"],
        )
    )
    return {
        "candidate_name": candidate_name,
        "daily_summary": summarize_daily_frame(frame),
        "metric_state_analysis": metric_analysis,
        "consistent_weak_head_conditions": consistent_conditions,
    }


def find_shared_conditions(candidates: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    nonlinear_keys = ("confirmed5", "v2")
    key_sets = []
    for key in nonlinear_keys:
        rows = candidates[key]["consistent_weak_head_conditions"]
        key_sets.append({(row["metric_name"], row["weak_side"]) for row in rows})
    shared = set.intersection(*key_sets) if key_sets else set()
    result: list[dict[str, Any]] = []
    for metric_name, weak_side in sorted(shared):
        spec = next(spec for spec in METRIC_SPECS if spec["name"] == metric_name)
        baseline_row = candidates["baseline"]["metric_state_analysis"][metric_name]
        result.append(
            {
                "metric_name": metric_name,
                "label": spec["label"],
                "family": spec["family"],
                "weak_side": weak_side,
                "baseline_direction_consistent": bool(baseline_row.get("direction_consistent_train_validation")),
                "baseline_weak_side": baseline_row.get("weak_side"),
            }
        )
    return result


def infer_conclusion(candidates: dict[str, dict[str, Any]]) -> dict[str, Any]:
    baseline_consistent = candidates["baseline"]["consistent_weak_head_conditions"]
    confirmed5_consistent = candidates["confirmed5"]["consistent_weak_head_conditions"]
    v2_consistent = candidates["v2"]["consistent_weak_head_conditions"]
    shared_conditions = find_shared_conditions(candidates)
    shared_score_shape_conditions = [row for row in shared_conditions if row["family"] == "score_shape"]
    score_shape_evidence_stable_enough = bool(shared_score_shape_conditions)
    low_degree_gate_supported = bool(shared_conditions) and score_shape_evidence_stable_enough
    if low_degree_gate_supported:
        recommendation = "存在可继续审计的低自由度 gate 证据，但仍只应进入新的 diagnostic-only preregistration，不得直接进入 v4。"
    else:
        recommendation = "不建议进入 gate challenger。当前证据更多是 candidate-specific 弱状态，而不是能跨 confirmed5 / v2 稳定复用的低自由度 gate 规则。"

    baseline_notes = []
    if baseline_consistent:
        baseline_notes.append("baseline 自身也存在少量弱 head 状态，但与 nonlinear challengers 并未收敛到同一条共享 gate 规则。")
    else:
        baseline_notes.append("baseline 未表现出足够稳定、可复用的弱 head score-shape 条件。")

    nonlinear_notes = []
    if confirmed5_consistent:
        nonlinear_notes.append("confirmed5 的一致弱状态主要来自暴露侧，而不是稳定的 score separation 侧。")
    if v2_consistent:
        nonlinear_notes.append("v2 的一致弱状态更像过度保守后的低波动 / 低换手头部，而不是简单的弱 score dispersion。")
    if not nonlinear_notes:
        nonlinear_notes.append("confirmed5 与 v2 都没有形成足够稳定的弱 head 条件。")

    return {
        "checked_d0_visible_metrics": [spec["name"] for spec in METRIC_SPECS],
        "baseline_consistent_conditions": baseline_consistent,
        "confirmed5_consistent_conditions": confirmed5_consistent,
        "v2_consistent_conditions": v2_consistent,
        "shared_low_degree_conditions_across_failed_nonlinear_candidates": shared_conditions,
        "shared_score_shape_conditions_across_failed_nonlinear_candidates": shared_score_shape_conditions,
        "score_shape_evidence_stable_enough": score_shape_evidence_stable_enough,
        "low_degree_gate_evidence_supported": low_degree_gate_supported,
        "baseline_explanation_notes": baseline_notes,
        "nonlinear_explanation_notes": nonlinear_notes,
        "recommend_gate_challenger": low_degree_gate_supported,
        "recommendation": recommendation,
    }


def build_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# TopK Head Quality Gate Diagnosis",
        "",
        "## Scope",
        "",
        "本文档只使用 trainval 诊断输入，检查 D0 可见、低自由度、可审计的 TopK head quality gate 证据。本文档不训练，不跑 portfolio，不生成 metrics/readout，不读取 frozen test，不设计 v4 参数，不把 trainval diagnosis 当 OOS。",
        "",
        "## Checked D0-Visible Metrics",
        "",
    ]
    for spec in METRIC_SPECS:
        lines.append(f"- `{spec['name']}`: {spec['label']}")

    lines.extend(["", "## Candidate Diagnosis", ""])
    for key in ("baseline", "confirmed5", "v2"):
        candidate = payload["candidates"][key]
        summary = candidate["daily_summary"]
        consistent = candidate["consistent_weak_head_conditions"]
        lines.append(f"### {key}")
        lines.append("")
        lines.append(
            f"- train days `{summary['train']['n_days']}`, validation days `{summary['validation']['n_days']}`"
        )
        lines.append(
            f"- train daily TopK realized return mean `{summary['train']['daily_topk_realized_return_mean_distribution']['mean']:.4%}`"
            if summary["train"]["daily_topk_realized_return_mean_distribution"]["mean"] is not None
            else "- train daily TopK realized return mean `N/A`"
        )
        lines.append(
            f"- validation daily TopK realized return mean `{summary['validation']['daily_topk_realized_return_mean_distribution']['mean']:.4%}`"
            if summary["validation"]["daily_topk_realized_return_mean_distribution"]["mean"] is not None
            else "- validation daily TopK realized return mean `N/A`"
        )
        if consistent:
            lines.append("- direction-consistent weak head conditions:")
            for row in consistent:
                lines.append(
                    f"  - `{row['metric_name']}` / `{row['weak_side']}`: "
                    f"train delta `{row['train_delta_weak_minus_strong']:.4%}`, "
                    f"validation delta `{row['validation_delta_weak_minus_other']:.4%}`, "
                    f"validation weak days `{row['validation_weak_state_days']}`"
                )
        else:
            lines.append("- direction-consistent weak head conditions: none")
        lines.append("")

    conclusion = payload["conclusion"]
    lines.extend(["## Conclusion", ""])
    lines.append(
        f"- shared low-degree conditions across failed nonlinear candidates: `{len(conclusion['shared_low_degree_conditions_across_failed_nonlinear_candidates'])}`"
    )
    lines.append(
        f"- score-shape evidence stable enough: `{conclusion['score_shape_evidence_stable_enough']}`"
    )
    lines.append(
        f"- low-degree gate evidence supported: `{conclusion['low_degree_gate_evidence_supported']}`"
    )
    for note in conclusion["baseline_explanation_notes"]:
        lines.append(f"- {note}")
    for note in conclusion["nonlinear_explanation_notes"]:
        lines.append(f"- {note}")
    lines.append(f"- recommendation: {conclusion['recommendation']}")
    if not conclusion["recommend_gate_challenger"]:
        lines.append("- 不建议进入 gate challenger")

    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    required_paths = {
        "source_db": args.source_db,
        "split_panel": args.split_panel,
        "execution_panel": args.execution_panel,
        "baseline_scores": args.baseline_scores,
        "confirmed5_scores": args.confirmed5_scores,
        "v2_scores": args.v2_scores,
    }
    for label, path in required_paths.items():
        ensure_exists(path, label)
    if args.include_v3_reference:
        ensure_exists(args.v3_scores, "v3_scores")

    con = duckdb.connect()
    try:
        con.execute(f"ATTACH '{sql_path(args.source_db)}' AS wh (READ_ONLY)")
        con.execute(
            f"""
            CREATE OR REPLACE VIEW split_days AS
            SELECT DISTINCT signal_date, split_bucket
            FROM read_parquet('{sql_path(args.split_panel)}')
            WHERE split_bucket IN ('train', 'validation')
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW execution_panel AS
            SELECT snapshot_id, instrument, signal_date, execution_delayed_realized_return
            FROM read_parquet('{sql_path(args.execution_panel)}')
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW source_features AS
            SELECT
                snapshot_id,
                ts_code AS instrument,
                trade_date AS signal_date,
                amount,
                total_mv,
                turnover_rate,
                STDDEV_SAMP(pct_chg) OVER (
                    PARTITION BY ts_code
                    ORDER BY trade_date
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                ) AS volatility_20d
            FROM wh.serving.vw_bars_daily
            """
        )

        candidate_frames = {
            "baseline": build_daily_head_frame(con, args.baseline_scores, view_name="baseline_scores", topk=args.topk),
            "confirmed5": build_daily_head_frame(
                con, args.confirmed5_scores, view_name="confirmed5_scores", topk=args.topk
            ),
            "v2": build_daily_head_frame(con, args.v2_scores, view_name="v2_scores", topk=args.topk),
        }
        if args.include_v3_reference and args.v3_scores.exists():
            candidate_frames["v3_rejected_reference"] = build_daily_head_frame(
                con, args.v3_scores, view_name="v3_scores", topk=args.topk
            )
    finally:
        con.close()

    candidates = {
        name: analyze_candidate(name, frame)
        for name, frame in candidate_frames.items()
        if name in {"baseline", "confirmed5", "v2"}
    }
    conclusion = infer_conclusion(candidates)

    payload: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "diagnostic_only": True,
        "trainval_only": True,
        "frozen_test_read": False,
        "portfolio_run_executed": False,
        "metrics_readout_generated": False,
        "topk": int(args.topk),
        "checked_d0_visible_metrics": [spec["name"] for spec in METRIC_SPECS],
        "candidates": candidates,
        "conclusion": conclusion,
    }
    if "v3_rejected_reference" in candidate_frames:
        payload["v3_rejected_reference"] = {
            "included": True,
            "purpose": "rejected_reference_only",
            "daily_summary": summarize_daily_frame(candidate_frames["v3_rejected_reference"]),
        }
    else:
        payload["v3_rejected_reference"] = {
            "included": False,
            "purpose": "not_needed_for_gate_conclusion",
        }

    write_json(args.output_json, payload)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(build_markdown(payload), encoding="utf-8")


if __name__ == "__main__":
    main()
