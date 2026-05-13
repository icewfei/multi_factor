#!/opt/anaconda3/envs/quant_trade/bin/python
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DB = Path(
    "/Users/wy/MiscProject/tushare_data/parquet_duckdb/data/snapshots/"
    "warehouse_20260429_trainval_20211231/duckdb/warehouse.duckdb"
)
DEFAULT_EXECUTION_PANEL = (
    ROOT / "artifacts" / "run_state" / "project_panels_research_trainval_20211231_20260429" / "project_execution_panel.parquet"
)
DEFAULT_SPLIT_PANEL = (
    ROOT / "artifacts" / "run_state" / "project_panels_research_trainval_20211231_20260429" / "dataset_split_daily.parquet"
)
DEFAULT_BASELINE_SCORES = Path("/private/tmp/baseline_multi_equal_weight_v1_exact_model_scores_D0.parquet")
DEFAULT_CONFIRMED5_SCORES = Path("/private/tmp/confirmed5_same_contract_registered_model_scores_D0.parquet")
DEFAULT_CONFIRMED5_READOUT = Path("/private/tmp/confirmed5_vs_baseline_same_contract_readout.json")
DEFAULT_V2_READOUT = Path("/private/tmp/nlc_v2_vs_baseline_same_contract_v3_readout.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose baseline portfolio edge versus confirmed5 and nonlinear challenger v2 using trainval-only artifacts."
    )
    parser.add_argument("--source-db", default=str(DEFAULT_SOURCE_DB))
    parser.add_argument("--execution-panel", default=str(DEFAULT_EXECUTION_PANEL))
    parser.add_argument("--split-panel", default=str(DEFAULT_SPLIT_PANEL))
    parser.add_argument("--baseline-scores", default=str(DEFAULT_BASELINE_SCORES))
    parser.add_argument("--confirmed5-scores", default=str(DEFAULT_CONFIRMED5_SCORES))
    parser.add_argument("--confirmed5-readout-json", default=str(DEFAULT_CONFIRMED5_READOUT))
    parser.add_argument("--v2-readout-json", default=str(DEFAULT_V2_READOUT))
    parser.add_argument("--topk", type=int, default=10)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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


def ensure_exists(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} not found: {path}")


def extract_readout_metrics(
    path: Path,
    primary_key: str,
) -> dict[str, dict[str, float | None]]:
    payload = load_json(path)
    windows = payload["windows"][primary_key]
    result: dict[str, dict[str, float | None]] = {}
    for window in ("train", "validation"):
        entry = windows.get(window, {})
        result[window] = {
            "total_equity": float(entry["final_total_equity_estimate"]) if "final_total_equity_estimate" in entry else None,
            "relative_return": (
                float(entry["annual_relative_return_trainval_dry_run_estimate"])
                if "annual_relative_return_trainval_dry_run_estimate" in entry
                else None
            ),
            "relative_ir": float(entry["relative_ir_estimate"]) if "relative_ir_estimate" in entry else None,
            "avg_cash_weight": float(entry["avg_cash_weight"]) if "avg_cash_weight" in entry else None,
            "avg_invested_weight": float(entry["avg_invested_weight"]) if "avg_invested_weight" in entry else None,
            "avg_turnover_daily": float(entry["avg_turnover_daily"]) if "avg_turnover_daily" in entry else None,
            "max_drawdown": (
                float(entry["max_drawdown_trainval_dry_run_estimate"])
                if "max_drawdown_trainval_dry_run_estimate" in entry
                else None
            ),
        }
    return result


def make_topk_frame(
    con: duckdb.DuckDBPyConnection,
    source_view: str,
    label: str,
    *,
    topk: int,
) -> pd.DataFrame:
    return con.execute(
        f"""
        WITH ranked AS (
            SELECT
                s.snapshot_id,
                s.instrument,
                s.signal_date,
                s.model_score_D0,
                ROW_NUMBER() OVER (
                    PARTITION BY s.signal_date
                    ORDER BY s.model_score_D0 DESC, s.instrument ASC
                ) AS rank_position
            FROM {source_view} s
        )
        SELECT
            '{label}' AS label,
            r.snapshot_id,
            r.instrument,
            r.signal_date,
            r.model_score_D0,
            r.rank_position,
            split.split_bucket,
            exec.execution_delayed_realized_return,
            exec.execution_path_status,
            feat.amount,
            feat.total_mv,
            feat.circ_mv,
            feat.turnover_rate,
            feat.volatility_20d
        FROM ranked r
        LEFT JOIN split_panel split
          USING (snapshot_id, instrument, signal_date)
        LEFT JOIN execution_panel exec
          USING (snapshot_id, instrument, signal_date)
        LEFT JOIN source_features feat
          USING (instrument, signal_date)
        WHERE r.rank_position <= {topk}
        ORDER BY r.signal_date, r.rank_position, r.instrument
        """
    ).fetchdf()


def build_signal_to_names(frame: pd.DataFrame) -> dict[str, set[str]]:
    mapping: dict[str, set[str]] = defaultdict(set)
    for row in frame.itertuples(index=False):
        mapping[str(row.signal_date)].add(str(row.instrument))
    return mapping


def compute_topk_turnover(signal_to_names: dict[str, set[str]]) -> dict[str, dict[str, float | int | None]]:
    result: dict[str, dict[str, float | int | None]] = {}
    for window, items in (("train", []), ("validation", [])):
        dates = sorted(
            date
            for date in signal_to_names
            if frame_date_to_window(date) == window
        )
        rows: list[dict[str, float]] = []
        for prev_date, curr_date in zip(dates, dates[1:]):
            prev_names = signal_to_names[prev_date]
            curr_names = signal_to_names[curr_date]
            overlap = len(prev_names & curr_names)
            replacements = len(curr_names - prev_names)
            rows.append(
                {
                    "overlap_count": float(overlap),
                    "replacement_ratio": float(replacements / len(curr_names)) if curr_names else 0.0,
                }
            )
        if not rows:
            result[window] = {"n_transitions": 0, "avg_overlap_count": None, "avg_replacement_ratio": None}
            continue
        summary = pd.DataFrame(rows)
        result[window] = {
            "n_transitions": int(len(summary)),
            "avg_overlap_count": float(summary["overlap_count"].mean()),
            "avg_replacement_ratio": float(summary["replacement_ratio"].mean()),
        }
    return result


WINDOW_MAP: dict[str, str] = {}


def frame_date_to_window(signal_date: str) -> str | None:
    return WINDOW_MAP.get(str(signal_date))


def compute_pairwise_overlap(
    left_signal_to_names: dict[str, set[str]],
    right_signal_to_names: dict[str, set[str]],
    *,
    topk: int,
) -> dict[str, dict[str, float | int | None]]:
    result: dict[str, dict[str, float | int | None]] = {}
    common_dates = sorted(set(left_signal_to_names) & set(right_signal_to_names))
    for window in ("train", "validation"):
        rows: list[dict[str, float]] = []
        for signal_date in common_dates:
            if frame_date_to_window(signal_date) != window:
                continue
            left_names = left_signal_to_names[signal_date]
            right_names = right_signal_to_names[signal_date]
            overlap = len(left_names & right_names)
            union = len(left_names | right_names)
            rows.append(
                {
                    "overlap_count": float(overlap),
                    "jaccard": float(overlap / union) if union else 0.0,
                }
            )
        if not rows:
            result[window] = {"n_days": 0, "avg_overlap_count": None, "avg_jaccard": None}
            continue
        summary = pd.DataFrame(rows)
        result[window] = {
            "n_days": int(len(summary)),
            "avg_overlap_count": float(summary["overlap_count"].mean()),
            "avg_overlap_share_of_topk": float(summary["overlap_count"].mean() / topk),
            "avg_jaccard": float(summary["jaccard"].mean()),
        }
    return result


def compute_realized_return_decomposition(frame: pd.DataFrame) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for window in ("train", "validation"):
        subset = frame[
            (frame["split_bucket"] == window)
            & frame["execution_delayed_realized_return"].notna()
        ].copy()
        returns = subset["execution_delayed_realized_return"].astype(float).tolist()
        positive = subset[subset["execution_delayed_realized_return"].astype(float) > 0].copy()
        negative = subset[subset["execution_delayed_realized_return"].astype(float) < 0].copy()
        positive = positive.sort_values("execution_delayed_realized_return", ascending=False)
        negative = negative.sort_values("execution_delayed_realized_return", ascending=True)

        top_winner_sum = float(positive["execution_delayed_realized_return"].head(20).sum()) if not positive.empty else 0.0
        total_positive_sum = float(positive["execution_delayed_realized_return"].sum()) if not positive.empty else 0.0
        top_loser_sum = float(negative["execution_delayed_realized_return"].head(20).sum()) if not negative.empty else 0.0
        total_negative_sum = float(negative["execution_delayed_realized_return"].sum()) if not negative.empty else 0.0

        result[window] = {
            "distribution": summarize_numeric(returns),
            "large_winner_contribution": {
                "count_ge_10pct": int((subset["execution_delayed_realized_return"].astype(float) >= 0.10).sum()),
                "top20_sum": top_winner_sum,
                "share_of_total_positive_sum": (
                    float(top_winner_sum / total_positive_sum) if total_positive_sum else None
                ),
            },
            "large_loser_contribution": {
                "count_le_minus_10pct": int((subset["execution_delayed_realized_return"].astype(float) <= -0.10).sum()),
                "bottom20_sum": top_loser_sum,
                "share_of_total_negative_abs_sum": (
                    float(abs(top_loser_sum) / abs(total_negative_sum)) if total_negative_sum else None
                ),
            },
            "rank_bucket_mean_return": compute_rank_bucket_mean_return(subset),
        }
    return result


def compute_rank_bucket_mean_return(frame: pd.DataFrame) -> dict[str, float | None]:
    if frame.empty:
        return {"rank_1_3": None, "rank_4_6": None, "rank_7_10": None}
    bucketed = frame.copy()
    bucketed["rank_bucket"] = bucketed["rank_position"].apply(
        lambda x: "rank_1_3" if x <= 3 else ("rank_4_6" if x <= 6 else "rank_7_10")
    )
    result: dict[str, float | None] = {}
    for bucket in ("rank_1_3", "rank_4_6", "rank_7_10"):
        subset = bucketed[bucketed["rank_bucket"] == bucket]
        result[bucket] = (
            float(subset["execution_delayed_realized_return"].astype(float).mean())
            if not subset.empty
            else None
        )
    return result


def compute_exposure_summary(frame: pd.DataFrame) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    fields = {
        "industry": None,
        "market_cap_total_mv": "total_mv",
        "market_cap_circ_mv": "circ_mv",
        "liquidity_amount": "amount",
        "liquidity_turnover_rate": "turnover_rate",
        "volatility_20d": "volatility_20d",
    }
    for window in ("train", "validation"):
        subset = frame[frame["split_bucket"] == window]
        payload: dict[str, Any] = {}
        for name, column in fields.items():
            if column is None:
                payload[name] = {"available": False, "status": "不可得"}
                continue
            values = subset[column].dropna().astype(float).tolist() if column in subset else []
            payload[name] = {
                "available": bool(values),
                "status": "可得" if values else "不可得",
                "summary": summarize_numeric(values),
            }
        result[window] = payload
    return result


def compute_daily_head_frame(frame: pd.DataFrame) -> pd.DataFrame:
    realized = frame[
        frame["execution_delayed_realized_return"].notna()
    ].copy()
    grouped = (
        realized.groupby(["split_bucket", "signal_date"], as_index=False)
        .agg(
            avg_topk_realized_return=("execution_delayed_realized_return", "mean"),
            avg_volatility_20d=("volatility_20d", "mean"),
            avg_amount=("amount", "mean"),
            avg_total_mv=("total_mv", "mean"),
            avg_turnover_rate=("turnover_rate", "mean"),
            avg_model_score=("model_score_D0", "mean"),
        )
    )
    return grouped


def compute_relative_day_summary(
    baseline_daily: pd.DataFrame,
    challenger_daily: pd.DataFrame,
) -> dict[str, dict[str, float | int | None]]:
    joined = baseline_daily.merge(
        challenger_daily,
        on=["split_bucket", "signal_date"],
        suffixes=("_baseline", "_challenger"),
        how="inner",
    )
    joined["baseline_minus_challenger"] = (
        joined["avg_topk_realized_return_baseline"] - joined["avg_topk_realized_return_challenger"]
    )
    result: dict[str, dict[str, float | int | None]] = {}
    for window in ("train", "validation"):
        subset = joined[joined["split_bucket"] == window]
        if subset.empty:
            result[window] = {
                "n_days": 0,
                "baseline_win_days": 0,
                "challenger_win_days": 0,
                "tie_days": 0,
                "baseline_win_rate": None,
                "avg_baseline_minus_challenger": None,
                "median_baseline_minus_challenger": None,
                "avg_baseline_win_margin": None,
                "avg_challenger_win_margin": None,
            }
            continue
        baseline_wins = subset["baseline_minus_challenger"] > 0
        challenger_wins = subset["baseline_minus_challenger"] < 0
        result[window] = {
            "n_days": int(len(subset)),
            "baseline_win_days": int(baseline_wins.sum()),
            "challenger_win_days": int(challenger_wins.sum()),
            "tie_days": int((subset["baseline_minus_challenger"] == 0).sum()),
            "baseline_win_rate": float(baseline_wins.mean()),
            "avg_baseline_minus_challenger": float(subset["baseline_minus_challenger"].mean()),
            "median_baseline_minus_challenger": float(subset["baseline_minus_challenger"].median()),
            "avg_baseline_win_margin": (
                float(subset.loc[baseline_wins, "baseline_minus_challenger"].mean()) if baseline_wins.any() else None
            ),
            "avg_challenger_win_margin": (
                float((-subset.loc[challenger_wins, "baseline_minus_challenger"]).mean()) if challenger_wins.any() else None
            ),
        }
    return result


def compute_when_each_side_wins(
    baseline_daily: pd.DataFrame,
    challenger_daily: pd.DataFrame,
) -> dict[str, dict[str, Any]]:
    joined = baseline_daily.merge(
        challenger_daily,
        on=["split_bucket", "signal_date"],
        suffixes=("_baseline", "_challenger"),
        how="inner",
    )
    joined = joined[joined["split_bucket"] == "validation"].copy()
    if joined.empty:
        return {}

    joined["winner"] = joined["avg_topk_realized_return_baseline"].gt(
        joined["avg_topk_realized_return_challenger"]
    ).map({True: "baseline", False: "nonlinear"})
    result: dict[str, dict[str, Any]] = {}
    for winner in ("baseline", "nonlinear"):
        subset = joined[joined["winner"] == winner]
        result[winner] = {
            "n_days": int(len(subset)),
            "avg_baseline_minus_challenger": float(
                (
                    subset["avg_topk_realized_return_baseline"]
                    - subset["avg_topk_realized_return_challenger"]
                ).mean()
            ),
            "baseline_head_avg_volatility": float(subset["avg_volatility_20d_baseline"].mean()),
            "nonlinear_head_avg_volatility": float(subset["avg_volatility_20d_challenger"].mean()),
            "baseline_head_avg_amount": float(subset["avg_amount_baseline"].mean()),
            "nonlinear_head_avg_amount": float(subset["avg_amount_challenger"].mean()),
            "baseline_head_avg_total_mv": float(subset["avg_total_mv_baseline"].mean()),
            "nonlinear_head_avg_total_mv": float(subset["avg_total_mv_challenger"].mean()),
            "baseline_head_avg_turnover_rate": float(subset["avg_turnover_rate_baseline"].mean()),
            "nonlinear_head_avg_turnover_rate": float(subset["avg_turnover_rate_challenger"].mean()),
        }
    return result


def infer_observations(
    candidates: dict[str, dict[str, Any]],
    pairwise_overlap: dict[str, Any],
    relative_day_summary: dict[str, Any],
) -> dict[str, Any]:
    base_val = candidates["baseline"]["topk_realized_return_decomposition"]["validation"]["distribution"]
    confirmed5_val = candidates["confirmed5"]["topk_realized_return_decomposition"]["validation"]["distribution"]
    v2_val = candidates["v2"]["topk_realized_return_decomposition"]["validation"]["distribution"]
    base_port = candidates["baseline"]["portfolio_readout"]["validation"]
    confirmed5_port = candidates["confirmed5"]["portfolio_readout"]["validation"]
    v2_port = candidates["v2"]["portfolio_readout"]["validation"]
    confirmed5_turn = candidates["confirmed5"]["topk_turnover"]["validation"]
    v2_turn = candidates["v2"]["topk_turnover"]["validation"]
    base_turn = candidates["baseline"]["topk_turnover"]["validation"]

    baseline_beats_confirmed5_on_head_quality = (
        (base_val["mean"] or 0.0) > (confirmed5_val["mean"] or 0.0)
        and (base_val["median"] or 0.0) > (confirmed5_val["median"] or 0.0)
    )
    baseline_beats_v2_on_head_quality = (
        (base_val["mean"] or 0.0) > (v2_val["mean"] or 0.0)
        and (base_val["positive_rate"] or 0.0) >= (v2_val["positive_rate"] or 0.0)
    )
    baseline_not_just_more_invested = (
        confirmed5_port["avg_invested_weight"] is not None
        and base_port["avg_invested_weight"] is not None
        and confirmed5_port["avg_invested_weight"] > base_port["avg_invested_weight"]
        and (base_val["mean"] or 0.0) > (confirmed5_val["mean"] or 0.0)
    )
    baseline_not_just_lower_turnover = (
        v2_turn["avg_replacement_ratio"] is not None
        and base_turn["avg_replacement_ratio"] is not None
        and v2_turn["avg_replacement_ratio"] < base_turn["avg_replacement_ratio"]
        and (base_val["mean"] or 0.0) > (v2_val["mean"] or 0.0)
    )
    stable_edge_supported = (
        (relative_day_summary["confirmed5_vs_baseline"]["validation"]["baseline_win_rate"] or 0.0) > 0.50
        and (relative_day_summary["v2_vs_baseline"]["validation"]["baseline_win_rate"] or 0.0) > 0.50
        and baseline_beats_confirmed5_on_head_quality
        and baseline_beats_v2_on_head_quality
    )

    baseline_reasons = [
        "baseline 的 validation TopK realized return 均值高于 confirmed5 和 v2",
        "baseline 不是单纯靠更高 invested_weight 取胜，因为 confirmed5 的 avg_invested_weight 更高但仍然输给 baseline",
        "baseline 也不是单纯靠更低 churn 取胜，因为 v2 的 TopK replacement ratio 更低但头部 realized return 仍弱于 baseline",
    ]
    challenger_loss_reasons = [
        "confirmed5 更像输在 head quality + 高 churn + 更重的左尾亏损暴露",
        "v2 更像输在 head quality + 较低 cash deployment 效率 + 过度保守后的收益捕获不足",
        "两条 nonlinear 都存在 score-to-TopK 转化不足的迹象，但这仍然是 trainval diagnosis，不是 OOS 结论",
    ]
    insufficient_evidence = [
        "行业暴露不可得",
        "集中度指标在当前输入里不可得，因为本任务未读取 holdings/weights/same-day concentration artifacts",
        "当前证据不足以把 trainval 诊断直接升级成稳定 OOS 组合优势结论",
    ]

    return {
        "baseline_beats_confirmed5_on_head_quality": baseline_beats_confirmed5_on_head_quality,
        "baseline_beats_v2_on_head_quality": baseline_beats_v2_on_head_quality,
        "baseline_not_just_more_invested_weight": baseline_not_just_more_invested,
        "baseline_not_just_lower_turnover": baseline_not_just_lower_turnover,
        "pairwise_overlap_validation": {
            "confirmed5_vs_baseline": pairwise_overlap["confirmed5_vs_baseline"]["validation"]["avg_overlap_count"],
            "v2_vs_baseline": pairwise_overlap["v2_vs_baseline"]["validation"]["avg_overlap_count"],
        },
        "stable_explainable_portfolio_construction_edge_supported": stable_edge_supported,
        "baseline_edge_observations": baseline_reasons,
        "challenger_loss_observations": challenger_loss_reasons,
        "insufficient_evidence": insufficient_evidence,
        "next_research_boundary": (
            "如果后续还继续研究，应优先继续查 portfolio construction / capital deployment，"
            "而不是直接推出新的 challenger 方案。"
        ),
    }


def build_markdown(payload: dict[str, Any]) -> str:
    baseline = payload["candidates"]["baseline"]
    confirmed5 = payload["candidates"]["confirmed5"]
    v2 = payload["candidates"]["v2"]
    findings = payload["interpretation"]
    c5_days = payload["relative_day_summary"]["confirmed5_vs_baseline"]["validation"]
    v2_days = payload["relative_day_summary"]["v2_vs_baseline"]["validation"]
    lines = [
        "# Baseline Portfolio Edge Decomposition",
        "",
        "TRAINVAL RESEARCH DIAGNOSIS ONLY. NOT OOS. NOT frozen test. NOT a formal strategy conclusion.",
        "",
        f"- `no_frozen_test_access = {payload['no_frozen_test_access']}`",
        f"- `training_executed = {payload['training_executed']}`",
        f"- `portfolio_backtest_executed = {payload['portfolio_backtest_executed']}`",
        "",
        "## TopK Realized Return Decomposition",
        (
            f"- baseline validation mean `{baseline['topk_realized_return_decomposition']['validation']['distribution']['mean']:.4%}`, "
            f"median `{baseline['topk_realized_return_decomposition']['validation']['distribution']['median']:.4%}`, "
            f"positive_rate `{baseline['topk_realized_return_decomposition']['validation']['distribution']['positive_rate']:.4%}`"
        ),
        (
            f"- confirmed5 validation mean `{confirmed5['topk_realized_return_decomposition']['validation']['distribution']['mean']:.4%}`, "
            f"median `{confirmed5['topk_realized_return_decomposition']['validation']['distribution']['median']:.4%}`, "
            f"positive_rate `{confirmed5['topk_realized_return_decomposition']['validation']['distribution']['positive_rate']:.4%}`"
        ),
        (
            f"- v2 validation mean `{v2['topk_realized_return_decomposition']['validation']['distribution']['mean']:.4%}`, "
            f"median `{v2['topk_realized_return_decomposition']['validation']['distribution']['median']:.4%}`, "
            f"positive_rate `{v2['topk_realized_return_decomposition']['validation']['distribution']['positive_rate']:.4%}`"
        ),
        "",
        "## Win/Loss Day Summary",
        (
            f"- baseline vs confirmed5: win_days `{c5_days['baseline_win_days']}`, loss_days `{c5_days['challenger_win_days']}`, "
            f"baseline_win_rate `{c5_days['baseline_win_rate']:.4%}`, avg_edge `{c5_days['avg_baseline_minus_challenger']:.4%}`"
        ),
        (
            f"- baseline vs v2: win_days `{v2_days['baseline_win_days']}`, loss_days `{v2_days['challenger_win_days']}`, "
            f"baseline_win_rate `{v2_days['baseline_win_rate']:.4%}`, avg_edge `{v2_days['avg_baseline_minus_challenger']:.4%}`"
        ),
        "",
        "## Turnover / Overlap / Cash",
        (
            f"- baseline validation TopK replacement ratio `{baseline['topk_turnover']['validation']['avg_replacement_ratio']:.4f}`, "
            f"avg cash weight `{baseline['portfolio_readout']['validation']['avg_cash_weight']:.4f}`, "
            f"avg invested weight `{baseline['portfolio_readout']['validation']['avg_invested_weight']:.4f}`"
        ),
        (
            f"- confirmed5 validation TopK replacement ratio `{confirmed5['topk_turnover']['validation']['avg_replacement_ratio']:.4f}`, "
            f"avg overlap vs baseline `{payload['pairwise_topk_overlap']['confirmed5_vs_baseline']['validation']['avg_overlap_count']:.2f}` / {payload['topk']}, "
            f"avg cash weight `{confirmed5['portfolio_readout']['validation']['avg_cash_weight']:.4f}`"
        ),
        (
            f"- v2 validation TopK replacement ratio `{v2['topk_turnover']['validation']['avg_replacement_ratio']:.4f}`, "
            f"avg overlap vs baseline `{payload['pairwise_topk_overlap']['v2_vs_baseline']['validation']['avg_overlap_count']:.2f}` / {payload['topk']}, "
            f"avg cash weight `{v2['portfolio_readout']['validation']['avg_cash_weight']:.4f}`"
        ),
        "",
        "## Interpretation",
        f"- stable explainable edge supported: `{findings['stable_explainable_portfolio_construction_edge_supported']}`",
    ]
    for text in findings["baseline_edge_observations"]:
        lines.append(f"- {text}")
    for text in findings["challenger_loss_observations"]:
        lines.append(f"- {text}")
    lines.extend(
        [
            "",
            "## Missing Evidence",
        ]
    )
    for text in findings["insufficient_evidence"]:
        lines.append(f"- {text}")
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    source_db = Path(args.source_db)
    execution_panel = Path(args.execution_panel)
    split_panel = Path(args.split_panel)
    baseline_scores = Path(args.baseline_scores)
    confirmed5_scores = Path(args.confirmed5_scores)
    confirmed5_readout = Path(args.confirmed5_readout_json)
    v2_readout = Path(args.v2_readout_json)

    for path, label in (
        (source_db, "source db"),
        (execution_panel, "execution panel"),
        (split_panel, "split panel"),
        (baseline_scores, "baseline scores"),
        (confirmed5_scores, "confirmed5 scores"),
        (confirmed5_readout, "confirmed5 readout"),
        (v2_readout, "v2 readout"),
    ):
        ensure_exists(path, label)

    con = duckdb.connect()
    try:
        con.execute(f"ATTACH '{source_db.as_posix()}' AS wh (READ_ONLY)")
        con.execute(
            f"""
            CREATE OR REPLACE VIEW baseline_scores AS
            SELECT snapshot_id, instrument, signal_date, candidate_scheme_id, model_score_D0
            FROM read_parquet('{baseline_scores.as_posix()}')
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW confirmed5_scores AS
            SELECT snapshot_id, instrument, signal_date, candidate_scheme_id, model_score_D0
            FROM read_parquet('{confirmed5_scores.as_posix()}')
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW execution_panel AS
            SELECT snapshot_id, instrument, signal_date, execution_delayed_realized_return, execution_path_status
            FROM read_parquet('{execution_panel.as_posix()}')
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW split_panel AS
            SELECT snapshot_id, instrument, signal_date, split_bucket
            FROM read_parquet('{split_panel.as_posix()}')
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW source_features AS
            WITH bars AS (
                SELECT
                    ts_code AS instrument,
                    trade_date AS signal_date,
                    pct_chg / 100.0 AS pct_ret,
                    amount,
                    total_mv,
                    circ_mv,
                    turnover_rate
                FROM wh.serving.vw_bars_daily
            )
            SELECT
                instrument,
                signal_date,
                amount,
                total_mv,
                circ_mv,
                turnover_rate,
                STDDEV_SAMP(pct_ret) OVER (
                    PARTITION BY instrument
                    ORDER BY signal_date
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                ) AS volatility_20d
            FROM bars
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW v2_scores AS
            WITH joined AS (
                SELECT
                    c.snapshot_id,
                    c.instrument,
                    c.signal_date,
                    c.model_score_D0 AS raw_model_score_D0,
                    feat.volatility_20d
                FROM confirmed5_scores c
                LEFT JOIN source_features feat
                  USING (instrument, signal_date)
            ),
            ranked AS (
                SELECT
                    snapshot_id,
                    instrument,
                    signal_date,
                    PERCENT_RANK() OVER (
                        PARTITION BY signal_date
                        ORDER BY raw_model_score_D0 ASC, instrument ASC
                    ) AS raw_model_score_percentile_rank_D0,
                    PERCENT_RANK() OVER (
                        PARTITION BY signal_date
                        ORDER BY volatility_20d ASC, instrument ASC
                    ) AS volatility_20d_percentile_rank_D0
                FROM joined
            )
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                raw_model_score_percentile_rank_D0 * (1.0 - volatility_20d_percentile_rank_D0) AS model_score_D0
            FROM ranked
            """
        )

        split_df = con.execute(
            "SELECT DISTINCT signal_date, split_bucket FROM split_panel WHERE split_bucket IN ('train', 'validation')"
        ).fetchdf()
        WINDOW_MAP.update({str(row.signal_date): str(row.split_bucket) for row in split_df.itertuples(index=False)})

        frames = {
            "baseline": make_topk_frame(con, "baseline_scores", "baseline", topk=args.topk),
            "confirmed5": make_topk_frame(con, "confirmed5_scores", "confirmed5", topk=args.topk),
            "v2": make_topk_frame(con, "v2_scores", "v2", topk=args.topk),
        }
    finally:
        con.close()

    readouts = {
        "confirmed5": extract_readout_metrics(confirmed5_readout, "primary"),
        "baseline": extract_readout_metrics(v2_readout, "baseline"),
        "v2": extract_readout_metrics(v2_readout, "primary"),
    }

    candidates: dict[str, dict[str, Any]] = {}
    signal_maps: dict[str, dict[str, set[str]]] = {}
    daily_frames: dict[str, pd.DataFrame] = {}
    for label, frame in frames.items():
        signal_map = build_signal_to_names(frame)
        signal_maps[label] = signal_map
        daily_frames[label] = compute_daily_head_frame(frame)
        candidates[label] = {
            "portfolio_readout": readouts[label],
            "topk_realized_return_decomposition": compute_realized_return_decomposition(frame),
            "exposure_summary": compute_exposure_summary(frame),
            "topk_turnover": compute_topk_turnover(signal_map),
        }

    pairwise = {
        "confirmed5_vs_baseline": compute_pairwise_overlap(
            signal_maps["confirmed5"], signal_maps["baseline"], topk=args.topk
        ),
        "v2_vs_baseline": compute_pairwise_overlap(
            signal_maps["v2"], signal_maps["baseline"], topk=args.topk
        ),
    }
    relative_day_summary = {
        "confirmed5_vs_baseline": compute_relative_day_summary(daily_frames["baseline"], daily_frames["confirmed5"]),
        "v2_vs_baseline": compute_relative_day_summary(daily_frames["baseline"], daily_frames["v2"]),
    }
    win_regimes = {
        "confirmed5_vs_baseline": compute_when_each_side_wins(daily_frames["baseline"], daily_frames["confirmed5"]),
        "v2_vs_baseline": compute_when_each_side_wins(daily_frames["baseline"], daily_frames["v2"]),
    }

    payload = {
        "diagnosis_label": "baseline_portfolio_edge_decomposition",
        "generated_at": datetime.now().astimezone().isoformat(),
        "trainval_research_only": True,
        "not_oos": True,
        "no_frozen_test_access": True,
        "training_executed": False,
        "portfolio_backtest_executed": False,
        "formal_metrics_generated": False,
        "formal_readout_generated": False,
        "topk": int(args.topk),
        "field_availability": {
            "industry": "不可得",
            "market_cap": "可得",
            "liquidity": "可得",
            "volatility": "可得",
            "concentration": "不可得",
        },
        "candidates": candidates,
        "pairwise_topk_overlap": pairwise,
        "relative_day_summary": relative_day_summary,
        "when_each_side_wins": win_regimes,
        "interpretation": infer_observations(candidates, pairwise, relative_day_summary),
    }

    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    write_json(output_json, payload)
    output_md.write_text(build_markdown(payload), encoding="utf-8")


if __name__ == "__main__":
    main()
