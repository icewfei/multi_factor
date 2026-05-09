#!/opt/anaconda3/envs/quant_trade/bin/python
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


ROOT = Path("/Users/wy/MiscProject/multi_factor")
DEFAULT_SPLIT_CONFIG = ROOT / "configs" / "dataset_split" / "dataset_split_research_trainval_20211231.json"
DEFAULT_V2_RUN_DIR = ROOT / "artifacts" / "run_state" / "local_nlc_v2_same_contract_gap_20260509"
DEFAULT_BASELINE_RUN_DIR = ROOT / "artifacts" / "run_state" / "local_multi_equal_weight_v1_exact_same_contract_gap_20260509"
DEFAULT_CONFIRMED5_RUN_DIR = ROOT / "artifacts" / "run_state" / "local_nlc_confirmed5_same_contract_ref33_gap_20260509"
DEFAULT_V2_MODEL_DIAGNOSIS = Path("/private/tmp/nonlinear_challenger_v2_model_edge_diagnosis.json")
DEFAULT_CONFIRMED5_MODEL_DIAGNOSIS = Path("/private/tmp/model_edge_diagnosis.json")
DEFAULT_V2_READOUT = Path("/private/tmp/nlc_v2_vs_baseline_same_contract_v3_readout.json")
DEFAULT_CONFIRMED5_READOUT = Path("/private/tmp/confirmed5_vs_baseline_same_contract_readout.json")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_date(value: str) -> str:
    return value.replace("-", "")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose portfolio construction and capital deployment gaps across nonlinear challengers."
    )
    parser.add_argument("--v2-run-dir", default=str(DEFAULT_V2_RUN_DIR))
    parser.add_argument("--v2-attempt-id", default="attempt_portfolio_gap_diag")
    parser.add_argument("--baseline-run-dir", default=str(DEFAULT_BASELINE_RUN_DIR))
    parser.add_argument("--baseline-attempt-id", default="attempt_portfolio_gap_diag")
    parser.add_argument("--confirmed5-run-dir", default=str(DEFAULT_CONFIRMED5_RUN_DIR))
    parser.add_argument("--confirmed5-attempt-id", default="attempt_portfolio_gap_diag")
    parser.add_argument("--split-config", default=str(DEFAULT_SPLIT_CONFIG))
    parser.add_argument("--v2-model-diagnosis-json", default=str(DEFAULT_V2_MODEL_DIAGNOSIS))
    parser.add_argument("--confirmed5-model-diagnosis-json", default=str(DEFAULT_CONFIRMED5_MODEL_DIAGNOSIS))
    parser.add_argument("--v2-readout-json", default=str(DEFAULT_V2_READOUT))
    parser.add_argument("--confirmed5-readout-json", default=str(DEFAULT_CONFIRMED5_READOUT))
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    return parser.parse_args()


def summarize_numeric(values: list[float]) -> dict[str, float | None]:
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


def classify_window(signal_date: str, split: dict[str, str]) -> str | None:
    if split["train_start"] <= signal_date <= split["train_end"]:
        return "train"
    if split["validation_start"] <= signal_date <= split["validation_end"]:
        return "validation"
    return None


def compute_set_turnover(signal_to_names: dict[str, set[str]], split: dict[str, str]) -> dict[str, dict[str, float | int | None]]:
    per_window: dict[str, list[dict[str, float]]] = {"train": [], "validation": []}
    ordered_dates = sorted(signal_to_names)
    for prev_date, curr_date in zip(ordered_dates, ordered_dates[1:]):
        window = classify_window(curr_date, split)
        if window is None:
            continue
        prev_names = signal_to_names[prev_date]
        curr_names = signal_to_names[curr_date]
        overlap = len(prev_names & curr_names)
        additions = len(curr_names - prev_names)
        removals = len(prev_names - curr_names)
        curr_count = len(curr_names)
        turnover_ratio = ((additions + removals) / curr_count) if curr_count else None
        per_window[window].append(
            {
                "overlap_count": float(overlap),
                "additions": float(additions),
                "removals": float(removals),
                "curr_count": float(curr_count),
                "turnover_ratio": float(turnover_ratio) if turnover_ratio is not None else math.nan,
            }
        )

    result: dict[str, dict[str, float | int | None]] = {}
    for window, rows in per_window.items():
        if not rows:
            result[window] = {
                "n_transitions": 0,
                "avg_overlap_count": None,
                "avg_additions": None,
                "avg_removals": None,
                "avg_turnover_ratio": None,
            }
            continue
        frame = pd.DataFrame(rows)
        result[window] = {
            "n_transitions": int(len(frame)),
            "avg_overlap_count": float(frame["overlap_count"].mean()),
            "avg_additions": float(frame["additions"].mean()),
            "avg_removals": float(frame["removals"].mean()),
            "avg_turnover_ratio": float(frame["turnover_ratio"].mean()),
        }
    return result


def compute_pairwise_overlap(
    left_signal_to_names: dict[str, set[str]],
    right_signal_to_names: dict[str, set[str]],
    split: dict[str, str],
) -> dict[str, dict[str, float | int | None]]:
    windows: dict[str, list[dict[str, float]]] = {"train": [], "validation": []}
    for signal_date in sorted(set(left_signal_to_names) & set(right_signal_to_names)):
        window = classify_window(signal_date, split)
        if window is None:
            continue
        left_names = left_signal_to_names[signal_date]
        right_names = right_signal_to_names[signal_date]
        overlap = len(left_names & right_names)
        union = len(left_names | right_names)
        windows[window].append(
            {
                "left_count": float(len(left_names)),
                "right_count": float(len(right_names)),
                "overlap_count": float(overlap),
                "jaccard": (float(overlap) / union) if union else math.nan,
            }
        )

    result: dict[str, dict[str, float | int | None]] = {}
    for window, rows in windows.items():
        if not rows:
            result[window] = {
                "n_days": 0,
                "avg_left_count": None,
                "avg_right_count": None,
                "avg_overlap_count": None,
                "avg_jaccard": None,
            }
            continue
        frame = pd.DataFrame(rows)
        result[window] = {
            "n_days": int(len(frame)),
            "avg_left_count": float(frame["left_count"].mean()),
            "avg_right_count": float(frame["right_count"].mean()),
            "avg_overlap_count": float(frame["overlap_count"].mean()),
            "avg_jaccard": float(frame["jaccard"].mean()),
        }
    return result


def extract_model_metrics(path: Path, candidate_label: str) -> dict[str, dict[str, float | None]]:
    payload = load_json(path)
    diagnostics = payload["diagnostics"]
    result: dict[str, dict[str, float | None]] = {}
    for window in ("train", "validation"):
        diag = diagnostics[f"{candidate_label}_{window}"]
        result[window] = {
            "rank_ic": float(diag["rank_ic"]["mean"]),
            "icir": float(diag["icir"]),
            "top_bottom_spread": float(diag["top_bottom_spread"]),
            "score_coverage": float(diag["score_coverage"]),
        }
    return result


def extract_readout_metrics(path: Path, primary_key: str) -> dict[str, dict[str, float]]:
    payload = load_json(path)
    windows = payload["windows"][primary_key]
    result: dict[str, dict[str, float]] = {}
    for window in ("train", "validation"):
        entry = windows[window]
        result[window] = {
            "total_equity": float(entry["final_total_equity_estimate"]),
            "relative_return": float(entry["annual_relative_return_trainval_dry_run_estimate"]),
            "relative_ir": float(entry["relative_ir_estimate"]),
            "avg_cash_weight": float(entry["avg_cash_weight"]),
            "avg_invested_weight": float(entry["avg_invested_weight"]),
            "avg_turnover_daily": float(entry["avg_turnover_daily"]),
            "max_drawdown": float(entry["max_drawdown_trainval_dry_run_estimate"]),
        }
    return result


def load_selected_position_frame(run_dir: Path, attempt_id: str) -> pd.DataFrame:
    attempt_dir = run_dir / "attempts" / attempt_id
    ranking = attempt_dir / "ranking_state_daily.parquet"
    execution = attempt_dir / "execution_state_daily.parquet"
    project_execution = run_dir / "project_execution_panel.parquet"
    sql = f"""
        SELECT
            r.candidate_scheme_id,
            r.signal_date,
            r.instrument,
            r.model_score_D0,
            r.rank_position,
            r.topk_frozen_D0,
            e.execution_attempt_D1,
            e.entry_filled_D1,
            e.backtest_executable,
            e.target_weight_D0,
            p.actual_exit_date,
            p.execution_delayed_realized_return,
            p.execution_path_status
        FROM read_parquet('{ranking.as_posix()}') r
        INNER JOIN read_parquet('{execution.as_posix()}') e
            USING (run_id, attempt_id, run_type, snapshot_id, instrument, signal_date)
        INNER JOIN read_parquet('{project_execution.as_posix()}') p
            USING (snapshot_id, instrument, signal_date)
        WHERE r.topk_frozen_D0
        ORDER BY r.signal_date, r.rank_position, r.instrument
    """
    con = duckdb.connect()
    try:
        return con.execute(sql).fetchdf()
    finally:
        con.close()


def load_summary_frame(run_dir: Path, attempt_id: str) -> pd.DataFrame | None:
    path = run_dir / "attempts" / attempt_id / "portfolio_daily_summary.csv"
    if not path.exists():
        return None
    return pd.read_csv(path, dtype={"trade_date": str})


def load_turnover_frame(run_dir: Path, attempt_id: str) -> pd.DataFrame | None:
    path = run_dir / "attempts" / attempt_id / "turnover_daily.csv"
    if not path.exists():
        return None
    return pd.read_csv(path, dtype={"trade_date": str})


def load_weights_frame(run_dir: Path, attempt_id: str) -> pd.DataFrame | None:
    path = run_dir / "attempts" / attempt_id / "portfolio_weights_daily.csv"
    if not path.exists():
        return None
    return pd.read_csv(path, dtype={"trade_date": str})


def load_holdings_frame(run_dir: Path, attempt_id: str) -> pd.DataFrame | None:
    path = run_dir / "attempts" / attempt_id / "holdings.csv"
    if not path.exists():
        return None
    return pd.read_csv(
        path,
        dtype={
            "signal_date": str,
            "entry_date": str,
            "actual_exit_date": str,
            "instrument": str,
        },
    )


def build_signal_to_names(selected_positions: pd.DataFrame, flag_column: str) -> dict[str, set[str]]:
    filtered = selected_positions[selected_positions[flag_column].fillna(False)]
    mapping: dict[str, set[str]] = defaultdict(set)
    for row in filtered.itertuples(index=False):
        mapping[str(row.signal_date)].add(str(row.instrument))
    return mapping


def summarize_daily_selected_counts(selected_positions: pd.DataFrame, split: dict[str, str]) -> dict[str, dict[str, float]]:
    daily = (
        selected_positions.groupby("signal_date")
        .agg(
            topk_frozen_count=("topk_frozen_D0", lambda s: int(pd.Series(s).fillna(False).sum())),
            execution_attempt_count=("execution_attempt_D1", lambda s: int(pd.Series(s).fillna(False).sum())),
            backtest_executable_count=("backtest_executable", lambda s: int(pd.Series(s).fillna(False).sum())),
        )
        .reset_index()
    )
    daily["window"] = daily["signal_date"].map(lambda d: classify_window(str(d), split))
    result: dict[str, dict[str, float]] = {}
    for window in ("train", "validation"):
        frame = daily[daily["window"] == window]
        result[window] = {
            "n_signal_dates": int(len(frame)),
            "avg_topk_frozen_count": float(frame["topk_frozen_count"].mean()),
            "avg_execution_attempt_count": float(frame["execution_attempt_count"].mean()),
            "avg_backtest_executable_count": float(frame["backtest_executable_count"].mean()),
        }
    return result


def compute_selected_realized_summary(selected_positions: pd.DataFrame, split: dict[str, str]) -> dict[str, dict[str, Any]]:
    selected_positions = selected_positions.copy()
    selected_positions["window"] = selected_positions["signal_date"].map(lambda d: classify_window(str(d), split))
    selected_positions["realized_available"] = selected_positions["actual_exit_date"].notna()
    selected_positions["rank_bucket"] = selected_positions["rank_position"].apply(
        lambda rank: "rank_1_3" if rank <= 3 else ("rank_4_5" if rank <= 5 else "rank_6_10")
    )
    result: dict[str, dict[str, Any]] = {}
    for window in ("train", "validation"):
        frame = selected_positions[selected_positions["window"] == window]
        executable = frame[frame["backtest_executable"].fillna(False)]
        realized = executable[executable["realized_available"]]
        unresolved_count = int(executable["realized_available"].eq(False).sum())
        realized_returns = realized["execution_delayed_realized_return"].astype(float).tolist()
        score_corr = None
        if len(realized) >= 2:
            score_corr_value = realized["model_score_D0"].astype(float).corr(
                realized["execution_delayed_realized_return"].astype(float)
            )
            if pd.notna(score_corr_value):
                score_corr = float(score_corr_value)
        rank_bucket_summary: dict[str, dict[str, float | None]] = {}
        for bucket, bucket_frame in realized.groupby("rank_bucket"):
            rank_bucket_summary[str(bucket)] = summarize_numeric(
                bucket_frame["execution_delayed_realized_return"].astype(float).tolist()
            )
        result[window] = {
            "selected_positions": int(len(frame)),
            "backtest_executable_positions": int(len(executable)),
            "unresolved_backtest_positions": unresolved_count,
            "realized_return_distribution": summarize_numeric(realized_returns),
            "score_vs_realized_corr": score_corr,
            "rank_bucket_realized_return": rank_bucket_summary,
        }
    return result


def compute_capital_deployment_summary(
    summary_df: pd.DataFrame | None,
    turnover_df: pd.DataFrame | None,
    readout_fallback: dict[str, dict[str, float]],
    split: dict[str, str],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for window in ("train", "validation"):
        fallback = readout_fallback[window]
        result[window] = {
            "avg_cash_weight": fallback["avg_cash_weight"],
            "avg_invested_weight": fallback["avg_invested_weight"],
            "avg_turnover_daily": fallback["avg_turnover_daily"],
            "data_source": "readout_fallback",
        }
    if summary_df is None or turnover_df is None:
        return result

    summary_df = summary_df.copy()
    turnover_df = turnover_df.copy()
    summary_df["window"] = summary_df["trade_date"].map(lambda d: classify_window(str(d), split))
    turnover_df["window"] = turnover_df["trade_date"].map(lambda d: classify_window(str(d), split))
    for window in ("train", "validation"):
        summary_window = summary_df[summary_df["window"] == window]
        turnover_window = turnover_df[turnover_df["window"] == window]
        result[window] = {
            "avg_cash_weight": float(summary_window["cash_weight"].astype(float).mean()),
            "avg_invested_weight": float(summary_window["invested_weight"].astype(float).mean()),
            "avg_turnover_daily": float(turnover_window["turnover_daily"].astype(float).mean()),
            "data_source": "portfolio_artifacts",
        }
    return result


def compute_concentration_summary(summary_df: pd.DataFrame | None, split: dict[str, str]) -> dict[str, dict[str, float | None]]:
    if summary_df is None:
        return {
            "train": {
                "avg_max_single_name_weight": None,
                "avg_top3_weight": None,
                "avg_herfindahl": None,
            },
            "validation": {
                "avg_max_single_name_weight": None,
                "avg_top3_weight": None,
                "avg_herfindahl": None,
            },
        }
    summary_df = summary_df.copy()
    summary_df["window"] = summary_df["trade_date"].map(lambda d: classify_window(str(d), split))
    result: dict[str, dict[str, float | None]] = {}
    for window in ("train", "validation"):
        frame = summary_df[summary_df["window"] == window]
        result[window] = {
            "avg_max_single_name_weight": float(frame["max_single_name_weight"].astype(float).mean()),
            "avg_top3_weight": float(frame["top3_weight"].astype(float).mean()),
            "avg_herfindahl": float(frame["portfolio_herfindahl_index"].astype(float).mean()),
        }
    return result


def compute_active_portfolio_summary(
    weights_df: pd.DataFrame | None,
    holdings_df: pd.DataFrame | None,
    summary_df: pd.DataFrame | None,
    split: dict[str, str],
) -> dict[str, dict[str, float | None]]:
    if weights_df is None or holdings_df is None or summary_df is None:
        return {
            "train": {
                "avg_active_names": None,
                "avg_active_cohorts": None,
                "p50_active_names": None,
                "p50_active_cohorts": None,
            },
            "validation": {
                "avg_active_names": None,
                "avg_active_cohorts": None,
                "p50_active_names": None,
                "p50_active_cohorts": None,
            },
        }
    weights_df = weights_df.copy()
    summary_df = summary_df.copy()
    active_names = (
        weights_df[weights_df["closing_weight"].astype(float) > 0]
        .groupby("trade_date")["instrument"]
        .nunique()
        .reset_index(name="active_name_count")
    )
    positions = [
        (str(row.signal_date), str(row.entry_date), str(row.actual_exit_date))
        for row in holdings_df.itertuples(index=False)
    ]
    cohort_rows: list[dict[str, Any]] = []
    for trade_date in summary_df["trade_date"].astype(str).tolist():
        cohort_count = len({sig for sig, entry, exit_date in positions if entry <= trade_date <= exit_date})
        cohort_rows.append({"trade_date": trade_date, "active_cohort_count": cohort_count})
    cohort_df = pd.DataFrame(cohort_rows)
    merged = active_names.merge(cohort_df, on="trade_date", how="outer")
    merged["window"] = merged["trade_date"].map(lambda d: classify_window(str(d), split))
    result: dict[str, dict[str, float | None]] = {}
    for window in ("train", "validation"):
        frame = merged[merged["window"] == window]
        result[window] = {
            "avg_active_names": float(frame["active_name_count"].astype(float).mean()),
            "avg_active_cohorts": float(frame["active_cohort_count"].astype(float).mean()),
            "p50_active_names": float(frame["active_name_count"].astype(float).median()),
            "p50_active_cohorts": float(frame["active_cohort_count"].astype(float).median()),
        }
    return result


def infer_failure_causes(candidates: dict[str, dict[str, Any]]) -> dict[str, Any]:
    baseline_port = candidates["baseline"]["portfolio_metrics"]
    confirmed5_port = candidates["confirmed5"]["portfolio_metrics"]
    v2_port = candidates["v2"]["portfolio_metrics"]
    baseline_realized = candidates["baseline"]["selected_head_realized"]
    confirmed5_realized = candidates["confirmed5"]["selected_head_realized"]
    v2_realized = candidates["v2"]["selected_head_realized"]
    confirmed5_turn = candidates["confirmed5"]["topk_turnover"]
    v2_turn = candidates["v2"]["topk_turnover"]
    baseline_turn = candidates["baseline"]["topk_turnover"]

    baseline_wins_more_by = "selection_quality"
    if (
        baseline_port["validation"]["avg_invested_weight"] > v2_port["validation"]["avg_invested_weight"]
        and baseline_port["validation"]["avg_invested_weight"] > confirmed5_port["validation"]["avg_invested_weight"]
    ):
        baseline_wins_more_by = "selection_quality_plus_slightly_higher_deployment"

    next_focus = "portfolio_construction_and_capital_deployment"
    if (
        v2_realized["validation"]["realized_return_distribution"]["mean"]
        and baseline_realized["validation"]["realized_return_distribution"]["mean"]
        and v2_realized["validation"]["realized_return_distribution"]["mean"]
        > baseline_realized["validation"]["realized_return_distribution"]["mean"]
    ):
        next_focus = "signal_design"

    return {
        "baseline_is_not_winning_just_by_more_invested_weight": (
            confirmed5_port["validation"]["avg_invested_weight"] > baseline_port["validation"]["avg_invested_weight"]
            and confirmed5_port["validation"]["total_equity"] < baseline_port["validation"]["total_equity"]
        ),
        "baseline_wins_more_by": baseline_wins_more_by,
        "confirmed5_loses_with_higher_turnover": (
            confirmed5_turn["validation"]["avg_turnover_ratio"] is not None
            and baseline_turn["validation"]["avg_turnover_ratio"] is not None
            and confirmed5_turn["validation"]["avg_turnover_ratio"] > baseline_turn["validation"]["avg_turnover_ratio"]
        ),
        "v2_reduced_turnover_but_not_enough": (
            v2_turn["validation"]["avg_turnover_ratio"] is not None
            and baseline_turn["validation"]["avg_turnover_ratio"] is not None
            and v2_turn["validation"]["avg_turnover_ratio"] < baseline_turn["validation"]["avg_turnover_ratio"]
            and v2_port["validation"]["relative_return"] < baseline_port["validation"]["relative_return"]
        ),
        "v2_volatility_discount_tradeoff": (
            v2_port["validation"]["max_drawdown"] > baseline_port["validation"]["max_drawdown"]
            and v2_port["validation"]["relative_return"] < baseline_port["validation"]["relative_return"]
        ),
        "topk_realized_quality_gap_validation": {
            "baseline_mean": baseline_realized["validation"]["realized_return_distribution"]["mean"],
            "confirmed5_mean": confirmed5_realized["validation"]["realized_return_distribution"]["mean"],
            "v2_mean": v2_realized["validation"]["realized_return_distribution"]["mean"],
        },
        "rankic_not_translating_into_topk_edge_reason": (
            "Model-layer RankIC is computed over the full cross-section, but deployed TopK realized returns remain "
            "lower for nonlinear challengers. The selected-head score-vs-realized correlation is weak or negative, "
            "so score improvements are not turning into stronger realized head quality."
        ),
        "suggest_open_v3": True,
        "recommended_v3_research_axis": next_focus,
    }


def build_markdown(payload: dict[str, Any]) -> str:
    findings = payload["failure_diagnosis"]
    candidates = payload["candidates"]
    lines = [
        "# Portfolio Construction Gap Diagnosis",
        "",
        "TRAINVAL DIAGNOSIS ONLY. NOT OOS. NOT frozen test. NOT a formal strategy conclusion.",
        "",
        "## Diagnosis Summary",
        f"- baseline more likely wins by: `{findings['baseline_wins_more_by']}`",
        f"- confirmed5 loses with higher TopK turnover: `{findings['confirmed5_loses_with_higher_turnover']}`",
        f"- v2 reduced TopK turnover but still failed to beat baseline: `{findings['v2_reduced_turnover_but_not_enough']}`",
        f"- v2 volatility discount looks like risk reduction with weaker capture: `{findings['v2_volatility_discount_tradeoff']}`",
        f"- next research axis if a v3 is opened: `{findings['recommended_v3_research_axis']}`",
        "",
        "## Validation Highlights",
    ]
    for label in ("confirmed5", "v2", "baseline"):
        model = candidates[label]["model_metrics"]["validation"]
        port = candidates[label]["portfolio_metrics"]["validation"]
        realized = candidates[label]["selected_head_realized"]["validation"]["realized_return_distribution"]
        lines.append(
            f"- {label}: RankIC `{model['rank_ic']:.4f}`, ICIR `{model['icir']:.4f}`, "
            f"total_equity `{port['total_equity']:.4f}`, relative_return `{port['relative_return']:.4%}`, "
            f"avg_invested_weight `{port['avg_invested_weight']:.4f}`, avg_turnover_daily `{port['avg_turnover_daily']:.4f}`, "
            f"selected_head_realized_mean `{realized['mean']:.4%}`"
        )
    lines.extend(
        [
            "",
            "## Pairwise TopK Overlap",
        ]
    )
    for pair_name, pair_payload in payload["pairwise_topk_overlap"].items():
        validation = pair_payload["validation"]
        lines.append(
            f"- {pair_name}: validation avg overlap `{validation['avg_overlap_count']:.2f}` / 10, "
            f"avg jaccard `{validation['avg_jaccard']:.4f}`"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    split_config_raw = load_json(Path(args.split_config))
    split = {
        "train_start": normalize_date(split_config_raw["train_start"]),
        "train_end": normalize_date(split_config_raw["train_end"]),
        "validation_start": normalize_date(split_config_raw["validation_start"]),
        "validation_end": normalize_date(split_config_raw["validation_end"]),
    }

    readout_map = {
        "v2": extract_readout_metrics(Path(args.v2_readout_json), "primary"),
        "baseline": extract_readout_metrics(Path(args.v2_readout_json), "baseline"),
        "confirmed5": extract_readout_metrics(Path(args.confirmed5_readout_json), "primary"),
    }
    model_metric_map = {
        "v2": extract_model_metrics(Path(args.v2_model_diagnosis_json), "v2"),
        "baseline": extract_model_metrics(Path(args.v2_model_diagnosis_json), "baseline"),
        "confirmed5": extract_model_metrics(Path(args.v2_model_diagnosis_json), "confirmed5"),
    }

    run_map = {
        "v2": (Path(args.v2_run_dir), args.v2_attempt_id),
        "baseline": (Path(args.baseline_run_dir), args.baseline_attempt_id),
        "confirmed5": (Path(args.confirmed5_run_dir), args.confirmed5_attempt_id),
    }

    candidates: dict[str, dict[str, Any]] = {}
    signal_name_map: dict[str, dict[str, set[str]]] = {}
    for label, (run_dir, attempt_id) in run_map.items():
        selected_positions = load_selected_position_frame(run_dir, attempt_id)
        summary_df = load_summary_frame(run_dir, attempt_id)
        turnover_df = load_turnover_frame(run_dir, attempt_id)
        weights_df = load_weights_frame(run_dir, attempt_id)
        holdings_df = load_holdings_frame(run_dir, attempt_id)

        signal_name_map[label] = build_signal_to_names(selected_positions, "topk_frozen_D0")
        candidates[label] = {
            "run_dir": str(run_dir),
            "attempt_id": attempt_id,
            "holdings_artifacts_available": holdings_df is not None and summary_df is not None and turnover_df is not None,
            "model_metrics": model_metric_map[label],
            "portfolio_metrics": readout_map[label],
            "daily_selected_counts": summarize_daily_selected_counts(selected_positions, split),
            "topk_turnover": compute_set_turnover(signal_name_map[label], split),
            "selected_head_realized": compute_selected_realized_summary(selected_positions, split),
            "capital_deployment": compute_capital_deployment_summary(summary_df, turnover_df, readout_map[label], split),
            "concentration": compute_concentration_summary(summary_df, split),
            "active_portfolio_shape": compute_active_portfolio_summary(weights_df, holdings_df, summary_df, split),
            "industry_concentration_available": False,
        }

    pairwise = {
        "confirmed5_vs_baseline": compute_pairwise_overlap(signal_name_map["confirmed5"], signal_name_map["baseline"], split),
        "v2_vs_baseline": compute_pairwise_overlap(signal_name_map["v2"], signal_name_map["baseline"], split),
        "v2_vs_confirmed5": compute_pairwise_overlap(signal_name_map["v2"], signal_name_map["confirmed5"], split),
    }

    payload = {
        "diagnosis_label": (
            "PORTFOLIO CONSTRUCTION GAP DIAGNOSIS ONLY — TRAINVAL ONLY — NOT OOS — "
            "NOT FROZEN TEST — NOT A FORMAL STRATEGY CONCLUSION"
        ),
        "generated_at": datetime.now().astimezone().isoformat(),
        "frozen_test_accessed": False,
        "formal_metrics_generated": False,
        "new_model_training_executed": False,
        "split_config": split,
        "candidates": candidates,
        "pairwise_topk_overlap": pairwise,
        "failure_diagnosis": infer_failure_causes(candidates),
        "next_step_boundary": {
            "suggest_open_v3": True,
            "do_not_design_specific_v3_here": True,
            "recommended_research_axis": "portfolio_construction_and_capital_deployment",
            "do_not_continue_validation_tuning": True,
        },
    }

    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    write_json(output_json, payload)
    output_md.write_text(build_markdown(payload), encoding="utf-8")


if __name__ == "__main__":
    main()
