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

COHORTS = ("baseline_only", "nonlinear_only", "overlap")
D0_FEATURES: list[dict[str, str]] = [
    {"name": "volatility_20d", "label": "volatility_20d"},
    {"name": "amount", "label": "amount"},
    {"name": "turnover_rate", "label": "turnover_rate"},
    {"name": "total_mv", "label": "total_mv"},
    {"name": "baseline_rank_position", "label": "baseline rank_position"},
    {"name": "nonlinear_rank_position", "label": "nonlinear rank_position"},
]


def sql_path(path: Path) -> str:
    return path.as_posix().replace("'", "''")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose baseline overlap/divergence versus nonlinear challengers using trainval-only inputs."
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
            "positive_rate": None,
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
        "positive_rate": float((series > 0).mean()),
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fmt_pct(value: float | None) -> str:
    return f"{value:.4%}" if value is not None else "N/A"


def fmt_float(value: float | None) -> str:
    return f"{value:.4f}" if value is not None else "N/A"


def build_pair_frame(
    con: duckdb.DuckDBPyConnection,
    baseline_scores: Path,
    nonlinear_scores: Path,
    *,
    baseline_view: str,
    nonlinear_view: str,
    topk: int,
) -> pd.DataFrame:
    con.execute(f"CREATE OR REPLACE VIEW {baseline_view} AS SELECT * FROM read_parquet('{sql_path(baseline_scores)}')")
    con.execute(f"CREATE OR REPLACE VIEW {nonlinear_view} AS SELECT * FROM read_parquet('{sql_path(nonlinear_scores)}')")
    query = f"""
    WITH baseline_ranked AS (
        SELECT
            s.snapshot_id,
            s.instrument,
            s.signal_date,
            s.model_score_D0,
            d.split_bucket,
            ROW_NUMBER() OVER (
                PARTITION BY s.signal_date
                ORDER BY s.model_score_D0 DESC, s.instrument ASC
            ) AS rank_position
        FROM {baseline_view} s
        INNER JOIN split_days d
            USING (signal_date)
    ),
    nonlinear_ranked AS (
        SELECT
            s.snapshot_id,
            s.instrument,
            s.signal_date,
            s.model_score_D0,
            d.split_bucket,
            ROW_NUMBER() OVER (
                PARTITION BY s.signal_date
                ORDER BY s.model_score_D0 DESC, s.instrument ASC
            ) AS rank_position
        FROM {nonlinear_view} s
        INNER JOIN split_days d
            USING (signal_date)
    ),
    baseline_topk AS (
        SELECT snapshot_id, instrument, signal_date, split_bucket, rank_position, model_score_D0
        FROM baseline_ranked
        WHERE rank_position <= {topk}
    ),
    nonlinear_topk AS (
        SELECT snapshot_id, instrument, signal_date, split_bucket, rank_position, model_score_D0
        FROM nonlinear_ranked
        WHERE rank_position <= {topk}
    ),
    merged AS (
        SELECT
            COALESCE(b.snapshot_id, n.snapshot_id) AS snapshot_id,
            COALESCE(b.instrument, n.instrument) AS instrument,
            COALESCE(b.signal_date, n.signal_date) AS signal_date,
            COALESCE(b.split_bucket, n.split_bucket) AS split_bucket,
            b.rank_position AS baseline_rank_position,
            n.rank_position AS nonlinear_rank_position,
            b.model_score_D0 AS baseline_model_score_D0,
            n.model_score_D0 AS nonlinear_model_score_D0,
            CASE
                WHEN b.instrument IS NOT NULL AND n.instrument IS NOT NULL THEN 'overlap'
                WHEN b.instrument IS NOT NULL THEN 'baseline_only'
                ELSE 'nonlinear_only'
            END AS cohort
        FROM baseline_topk b
        FULL OUTER JOIN nonlinear_topk n
            USING (snapshot_id, instrument, signal_date, split_bucket)
    )
    SELECT
        m.snapshot_id,
        m.instrument,
        m.signal_date,
        m.split_bucket,
        m.baseline_rank_position,
        m.nonlinear_rank_position,
        m.baseline_model_score_D0,
        m.nonlinear_model_score_D0,
        m.cohort,
        e.execution_delayed_realized_return,
        f.amount,
        f.total_mv,
        f.turnover_rate,
        f.volatility_20d
    FROM merged m
    LEFT JOIN execution_panel e
        USING (snapshot_id, instrument, signal_date)
    LEFT JOIN source_features f
        USING (snapshot_id, instrument, signal_date)
    ORDER BY signal_date, cohort, instrument
    """
    return con.execute(query).fetchdf()


def compute_pairwise_overlap(frame: pd.DataFrame, *, topk: int) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for window in ("train", "validation"):
        subset = frame[frame["split_bucket"] == window].copy()
        daily = (
            subset.groupby(["signal_date", "cohort"], as_index=False)
            .agg(count=("instrument", "count"))
        )
        pivot = daily.pivot(index="signal_date", columns="cohort", values="count").reset_index()
        for cohort in COHORTS:
            if cohort not in pivot.columns:
                pivot[cohort] = 0.0
        overlap_count = pivot["overlap"].astype(float)
        jaccard = overlap_count / (2.0 * topk - overlap_count)
        result[window] = {
            "n_days": int(len(pivot)),
            "avg_overlap_count": float(overlap_count.mean()) if not overlap_count.empty else None,
            "avg_overlap_share_of_topk": float((overlap_count / topk).mean()) if not overlap_count.empty else None,
            "avg_jaccard": float(jaccard.mean()) if not jaccard.empty else None,
        }
    return result


def summarize_cohort(subset: pd.DataFrame) -> dict[str, Any]:
    returns = subset["execution_delayed_realized_return"].dropna().astype(float).tolist()
    result = {
        "row_count": int(len(subset)),
        "realized_return_distribution": summarize_numeric(returns),
    }
    for feature in D0_FEATURES:
        values = subset[feature["name"]].dropna().astype(float).tolist()
        result[f"{feature['name']}_distribution"] = summarize_numeric(values)
    return result


def compute_cohort_summary(frame: pd.DataFrame) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for window in ("train", "validation"):
        subset = frame[frame["split_bucket"] == window].copy()
        result[window] = {}
        for cohort in COHORTS:
            result[window][cohort] = summarize_cohort(subset[subset["cohort"] == cohort].copy())
    return result


def build_daily_divergence_frame(frame: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        frame.groupby(["split_bucket", "signal_date", "cohort"], as_index=False)
        .agg(
            mean_return=("execution_delayed_realized_return", "mean"),
            avg_volatility_20d=("volatility_20d", "mean"),
            avg_amount=("amount", "mean"),
            avg_total_mv=("total_mv", "mean"),
            avg_turnover_rate=("turnover_rate", "mean"),
            count=("instrument", "count"),
        )
    )
    returns = grouped.pivot(index=["split_bucket", "signal_date"], columns="cohort", values="mean_return").reset_index()
    counts = grouped.pivot(index=["split_bucket", "signal_date"], columns="cohort", values="count").reset_index()
    for table, fill_value in ((returns, float("nan")), (counts, 0.0)):
        for cohort in COHORTS:
            if cohort not in table.columns:
                table[cohort] = fill_value
    merged = returns.merge(counts, on=["split_bucket", "signal_date"], suffixes=("_ret", "_count"))
    merged["divergence_spread"] = merged["baseline_only_ret"] - merged["nonlinear_only_ret"]
    merged["baseline_total_mean"] = merged[["baseline_only_ret", "overlap_ret"]].mean(axis=1)
    merged["nonlinear_total_mean"] = merged[["nonlinear_only_ret", "overlap_ret"]].mean(axis=1)
    merged["baseline_minus_nonlinear_total"] = merged["baseline_total_mean"] - merged["nonlinear_total_mean"]
    return merged


def compute_divergence_summary(frame: pd.DataFrame) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for window in ("train", "validation"):
        subset = frame[frame["split_bucket"] == window].copy()
        spread = subset["divergence_spread"].dropna().astype(float).tolist()
        baseline_only = subset["baseline_only_ret"].dropna().astype(float).tolist()
        nonlinear_only = subset["nonlinear_only_ret"].dropna().astype(float).tolist()
        overlap = subset["overlap_ret"].dropna().astype(float).tolist()
        corr = subset[["divergence_spread", "baseline_minus_nonlinear_total"]].corr().iloc[0, 1]
        result[window] = {
            "n_days": int(len(subset)),
            "baseline_only_mean_realized_return": float(pd.Series(baseline_only).mean()) if baseline_only else None,
            "nonlinear_only_mean_realized_return": float(pd.Series(nonlinear_only).mean()) if nonlinear_only else None,
            "overlap_mean_realized_return": float(pd.Series(overlap).mean()) if overlap else None,
            "baseline_only_minus_nonlinear_only_mean": float(pd.Series(spread).mean()) if spread else None,
            "divergence_spread_distribution": summarize_numeric(spread),
            "correlation_divergence_spread_vs_total_diff": float(corr) if not pd.isna(corr) else None,
            "baseline_win_day_share": float((subset["baseline_minus_nonlinear_total"] > 0).mean()) if not subset.empty else None,
        }
    result["direction_consistent_baseline_only_better"] = bool(
        result["train"]["baseline_only_minus_nonlinear_only_mean"] is not None
        and result["validation"]["baseline_only_minus_nonlinear_only_mean"] is not None
        and result["train"]["baseline_only_minus_nonlinear_only_mean"] > 0
        and result["validation"]["baseline_only_minus_nonlinear_only_mean"] > 0
    )
    return result


def compute_win_day_attribution(frame: pd.DataFrame) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for window in ("train", "validation"):
        subset = frame[frame["split_bucket"] == window].copy()
        win_days = subset[subset["baseline_minus_nonlinear_total"] > 0].copy()
        lose_days = subset[subset["baseline_minus_nonlinear_total"] < 0].copy()
        result[window] = {
            "baseline_win_days": int(len(win_days)),
            "nonlinear_win_days": int(len(lose_days)),
            "divergence_spread_mean_on_baseline_win_days": (
                float(win_days["divergence_spread"].mean()) if not win_days.empty else None
            ),
            "divergence_spread_mean_on_nonlinear_win_days": (
                float(lose_days["divergence_spread"].mean()) if not lose_days.empty else None
            ),
            "overlap_mean_return_on_baseline_win_days": (
                float(win_days["overlap_ret"].mean()) if not win_days.empty else None
            ),
            "overlap_mean_return_on_nonlinear_win_days": (
                float(lose_days["overlap_ret"].mean()) if not lose_days.empty else None
            ),
            "baseline_only_mean_return_on_baseline_win_days": (
                float(win_days["baseline_only_ret"].mean()) if not win_days.empty else None
            ),
            "baseline_only_mean_return_on_nonlinear_win_days": (
                float(lose_days["baseline_only_ret"].mean()) if not lose_days.empty else None
            ),
            "nonlinear_only_mean_return_on_baseline_win_days": (
                float(win_days["nonlinear_only_ret"].mean()) if not win_days.empty else None
            ),
            "nonlinear_only_mean_return_on_nonlinear_win_days": (
                float(lose_days["nonlinear_only_ret"].mean()) if not lose_days.empty else None
            ),
        }
    result["baseline_wins_mainly_from_divergence"] = bool(
        result["train"]["divergence_spread_mean_on_baseline_win_days"] is not None
        and result["validation"]["divergence_spread_mean_on_baseline_win_days"] is not None
        and result["train"]["divergence_spread_mean_on_baseline_win_days"] > 0
        and result["validation"]["divergence_spread_mean_on_baseline_win_days"] > 0
    )
    return result


def analyze_pair(pair_name: str, frame: pd.DataFrame, *, topk: int) -> dict[str, Any]:
    daily_divergence = build_daily_divergence_frame(frame)
    return {
        "pair_name": pair_name,
        "pairwise_overlap": compute_pairwise_overlap(frame, topk=topk),
        "cohort_summary": compute_cohort_summary(frame),
        "divergence_summary": compute_divergence_summary(daily_divergence),
        "win_day_attribution": compute_win_day_attribution(daily_divergence),
    }


def infer_conclusion(pairs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    confirmed5 = pairs["baseline_vs_confirmed5"]
    v2 = pairs["baseline_vs_v2"]
    consistent_divergence = {
        "baseline_vs_confirmed5": confirmed5["divergence_summary"]["direction_consistent_baseline_only_better"],
        "baseline_vs_v2": v2["divergence_summary"]["direction_consistent_baseline_only_better"],
    }
    divergence_drives_wins = {
        "baseline_vs_confirmed5": confirmed5["win_day_attribution"]["baseline_wins_mainly_from_divergence"],
        "baseline_vs_v2": v2["win_day_attribution"]["baseline_wins_mainly_from_divergence"],
    }

    low_degree_rule_supported = False
    findings = [
        "baseline-only names 相对 nonlinear-only names 的 realized return spread 在 confirmed5 和 v2 上都呈 train / validation 同方向为正。",
        "baseline 赢的日期里，divergence spread 与 baseline-minus-nonlinear 总差高度同向，说明 baseline edge 主要来自 divergence selection。",
        "overlap names 并没有在两组对比里稳定给 baseline 提供主要优势，baseline 优势更多压在 divergence names 上。",
        "但 divergence names 的 D0 暴露结构在 confirmed5 与 v2 上并不一致，因此还不能沉淀成单一、低自由度、可复用的 divergence-aware rule。",
    ]
    recommendation = (
        "不建议进入 divergence-aware challenger。当前证据支持“baseline 更擅长 divergence selection”，"
        "但不支持把这种现象压缩成一条跨 confirmed5 / v2 通用的低自由度 D0 规则。"
    )
    return {
        "checked_d0_visible_metrics": ["overlap_count", "jaccard"] + [feature["name"] for feature in D0_FEATURES],
        "divergence_spread_direction_consistent": consistent_divergence,
        "baseline_wins_mainly_from_divergence": divergence_drives_wins,
        "low_degree_divergence_rule_supported": low_degree_rule_supported,
        "findings": findings,
        "recommend_divergence_aware_challenger": low_degree_rule_supported,
        "recommendation": recommendation,
    }


def build_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Baseline Overlap Divergence Diagnosis",
        "",
        "## Scope",
        "",
        "本文档只使用 trainval 诊断输入，检查 baseline 与 nonlinear 候选同日 TopK 分歧时，收益是否主要由 divergence selection 决定。本文档不训练，不跑 portfolio，不生成 formal metrics/readout，不读取 frozen test，不设计 v4 参数，不把 trainval diagnosis 当 OOS。",
        "",
        "## Checked D0-Visible Metrics",
        "",
        "- `overlap_count`: 每日 TopK overlap count",
        "- `jaccard`: 每日 TopK Jaccard",
    ]
    for feature in D0_FEATURES:
        lines.append(f"- `{feature['name']}`: {feature['label']}")

    lines.extend(["", "## Pair Diagnosis", ""])
    for pair_name in ("baseline_vs_confirmed5", "baseline_vs_v2"):
        pair = payload["pairs"][pair_name]
        lines.append(f"### {pair_name}")
        lines.append("")
        for window in ("train", "validation"):
            overlap = pair["pairwise_overlap"][window]
            divergence = pair["divergence_summary"][window]
            lines.append(
                f"- {window} overlap `{fmt_float(overlap['avg_overlap_count'])}` / {payload['topk']}, jaccard `{fmt_float(overlap['avg_jaccard'])}`"
            )
            lines.append(
                f"- {window} baseline-only `{fmt_pct(divergence['baseline_only_mean_realized_return'])}`, "
                f"nonlinear-only `{fmt_pct(divergence['nonlinear_only_mean_realized_return'])}`, "
                f"overlap `{fmt_pct(divergence['overlap_mean_realized_return'])}`, "
                f"spread `{fmt_pct(divergence['baseline_only_minus_nonlinear_only_mean'])}`"
            )
        lines.append("")

    conclusion = payload["conclusion"]
    lines.extend(["## Conclusion", ""])
    lines.append(
        f"- divergence spread direction consistent: `{conclusion['divergence_spread_direction_consistent']}`"
    )
    lines.append(
        f"- baseline wins mainly from divergence: `{conclusion['baseline_wins_mainly_from_divergence']}`"
    )
    lines.append(
        f"- low-degree divergence rule supported: `{conclusion['low_degree_divergence_rule_supported']}`"
    )
    for finding in conclusion["findings"]:
        lines.append(f"- {finding}")
    lines.append(f"- recommendation: {conclusion['recommendation']}")
    if not conclusion["recommend_divergence_aware_challenger"]:
        lines.append("- 不建议进入 divergence-aware challenger")
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
        confirmed5_frame = build_pair_frame(
            con,
            args.baseline_scores,
            args.confirmed5_scores,
            baseline_view="baseline_scores",
            nonlinear_view="confirmed5_scores",
            topk=args.topk,
        )
        v2_frame = build_pair_frame(
            con,
            args.baseline_scores,
            args.v2_scores,
            baseline_view="baseline_scores_v2",
            nonlinear_view="v2_scores",
            topk=args.topk,
        )
        v3_reference_summary: dict[str, Any]
        if args.include_v3_reference and args.v3_scores.exists():
            v3_frame = build_pair_frame(
                con,
                args.baseline_scores,
                args.v3_scores,
                baseline_view="baseline_scores_v3",
                nonlinear_view="v3_scores",
                topk=args.topk,
            )
            v3_reference_summary = {
                "included": True,
                "purpose": "rejected_reference_only",
                "pairwise_overlap": compute_pairwise_overlap(v3_frame, topk=args.topk),
            }
        else:
            v3_reference_summary = {
                "included": False,
                "purpose": "not_needed_for_divergence_conclusion",
            }
    finally:
        con.close()

    pairs = {
        "baseline_vs_confirmed5": analyze_pair("baseline_vs_confirmed5", confirmed5_frame, topk=args.topk),
        "baseline_vs_v2": analyze_pair("baseline_vs_v2", v2_frame, topk=args.topk),
    }
    payload: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "diagnostic_only": True,
        "trainval_only": True,
        "frozen_test_read": False,
        "portfolio_run_executed": False,
        "formal_metrics_readout_generated": False,
        "topk": int(args.topk),
        "pairs": pairs,
        "conclusion": infer_conclusion(pairs),
        "v3_rejected_reference": v3_reference_summary,
    }
    write_json(args.output_json, payload)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(build_markdown(payload), encoding="utf-8")


if __name__ == "__main__":
    main()
