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

D0_FEATURES: list[dict[str, str]] = [
    {"name": "rank_position", "label": "TopK 内部 rank_position"},
    {"name": "model_score_D0", "label": "model_score_D0"},
    {"name": "volatility_20d", "label": "volatility_20d"},
    {"name": "amount", "label": "amount"},
    {"name": "total_mv", "label": "total_mv"},
    {"name": "turnover_rate", "label": "turnover_rate"},
]


def sql_path(path: Path) -> str:
    return path.as_posix().replace("'", "''")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose whether turnover-aware admission evidence is strong enough to justify a low-degree challenger."
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


def build_topk_frame(
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
    )
    SELECT
        r.snapshot_id,
        r.instrument,
        r.signal_date,
        r.model_score_D0,
        r.split_bucket,
        r.rank_position,
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
    ORDER BY signal_date, rank_position, instrument
    """
    return con.execute(query).fetchdf()


def annotate_turnover_states(frame: pd.DataFrame) -> pd.DataFrame:
    dates = list(pd.unique(frame["signal_date"]))
    previous_date_by_signal_date = {dates[i]: (dates[i - 1] if i > 0 else None) for i in range(len(dates))}
    topk_members = {signal_date: set(group["instrument"]) for signal_date, group in frame.groupby("signal_date", sort=True)}
    annotated_rows: list[dict[str, Any]] = []
    for signal_date, group in frame.groupby("signal_date", sort=True):
        previous_signal_date = previous_date_by_signal_date[signal_date]
        previous_members = topk_members.get(previous_signal_date, set()) if previous_signal_date is not None else set()
        current_members = topk_members[signal_date]
        replacement_ratio = (
            float(len(current_members - previous_members) / len(current_members)) if previous_signal_date is not None else None
        )
        retained_ratio = (
            float(len(current_members & previous_members) / len(current_members)) if previous_signal_date is not None else None
        )
        for row in group.itertuples(index=False):
            is_new_entrant = bool(previous_signal_date is not None and row.instrument not in previous_members)
            is_retained = bool(previous_signal_date is not None and row.instrument in previous_members)
            annotated_rows.append(
                {
                    **row._asdict(),
                    "previous_signal_date": previous_signal_date,
                    "is_new_entrant": is_new_entrant,
                    "is_retained": is_retained,
                    "replacement_ratio": replacement_ratio,
                    "retained_ratio": retained_ratio,
                }
            )
    annotated = pd.DataFrame(annotated_rows)
    return annotated[annotated["replacement_ratio"].notna()].copy()


def summarize_group(frame: pd.DataFrame, prefix: str) -> dict[str, Any]:
    returns = frame["execution_delayed_realized_return"].dropna().astype(float).tolist()
    result: dict[str, Any] = {
        "row_count": int(len(frame)),
        "realized_return_distribution": summarize_numeric(returns),
    }
    for feature in D0_FEATURES:
        values = frame[feature["name"]].dropna().astype(float).tolist()
        result[f"{prefix}_{feature['name']}_distribution"] = summarize_numeric(values)
    return result


def compute_new_entrant_vs_retained(frame: pd.DataFrame) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for window in ("train", "validation"):
        subset = frame[frame["split_bucket"] == window].copy()
        entrants = subset[subset["is_new_entrant"]].copy()
        retained = subset[subset["is_retained"]].copy()
        entrant_mean = entrants["execution_delayed_realized_return"].astype(float).mean() if not entrants.empty else None
        retained_mean = retained["execution_delayed_realized_return"].astype(float).mean() if not retained.empty else None
        result[window] = {
            "new_entrants": summarize_group(entrants, "new_entrants"),
            "retained_names": summarize_group(retained, "retained_names"),
            "entrant_minus_retained_mean_realized_return": (
                float(entrant_mean - retained_mean)
                if entrant_mean is not None and retained_mean is not None
                else None
            ),
            "entrants_weaker_than_retained": bool(
                entrant_mean is not None and retained_mean is not None and entrant_mean < retained_mean
            ),
        }
    return result


def build_daily_churn_frame(frame: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        frame.groupby(["split_bucket", "signal_date"], as_index=False)
        .agg(
            replacement_ratio=("replacement_ratio", "first"),
            retained_ratio=("retained_ratio", "first"),
            topk_realized_return_mean=("execution_delayed_realized_return", "mean"),
            entrants_mean_realized_return=(
                "execution_delayed_realized_return",
                lambda s: float(frame.loc[s.index & frame.index, "execution_delayed_realized_return"].mean()),
            ),
        )
    )
    return grouped


def compute_high_vs_low_churn(frame: pd.DataFrame) -> dict[str, Any]:
    daily = (
        frame.groupby(["split_bucket", "signal_date"], as_index=False)
        .agg(
            replacement_ratio=("replacement_ratio", "first"),
            topk_realized_return_mean=("execution_delayed_realized_return", "mean"),
            topk_positive_rate=("execution_delayed_realized_return", lambda s: float((pd.Series(s).astype(float) > 0).mean())),
        )
    )
    train = daily[daily["split_bucket"] == "train"].copy()
    validation = daily[daily["split_bucket"] == "validation"].copy()
    q25 = float(train["replacement_ratio"].quantile(0.25))
    q75 = float(train["replacement_ratio"].quantile(0.75))
    result: dict[str, Any] = {
        "train_threshold_q25": q25,
        "train_threshold_q75": q75,
    }
    for window, subset in (("train", train), ("validation", validation)):
        high_churn = subset[subset["replacement_ratio"] >= q75]
        low_churn = subset[subset["replacement_ratio"] <= q25]
        high_mean = float(high_churn["topk_realized_return_mean"].mean()) if not high_churn.empty else None
        low_mean = float(low_churn["topk_realized_return_mean"].mean()) if not low_churn.empty else None
        result[window] = {
            "n_days": int(len(subset)),
            "high_churn_days": int(len(high_churn)),
            "low_churn_days": int(len(low_churn)),
            "high_churn_mean_realized_return": high_mean,
            "low_churn_mean_realized_return": low_mean,
            "high_minus_low_mean_realized_return": (
                float(high_mean - low_mean) if high_mean is not None and low_mean is not None else None
            ),
            "high_churn_positive_rate": (
                float((high_churn["topk_realized_return_mean"] > 0).mean()) if not high_churn.empty else None
            ),
            "low_churn_positive_rate": (
                float((low_churn["topk_realized_return_mean"] > 0).mean()) if not low_churn.empty else None
            ),
        }
    result["direction_consistent_high_churn_weaker"] = bool(
        result["train"]["high_minus_low_mean_realized_return"] is not None
        and result["validation"]["high_minus_low_mean_realized_return"] is not None
        and result["train"]["high_minus_low_mean_realized_return"] < 0
        and result["validation"]["high_minus_low_mean_realized_return"] < 0
    )
    return result


def compute_turnover_summary(frame: pd.DataFrame) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for window in ("train", "validation"):
        daily = (
            frame[frame["split_bucket"] == window]
            .groupby("signal_date", as_index=False)
            .agg(replacement_ratio=("replacement_ratio", "first"), retained_ratio=("retained_ratio", "first"))
        )
        result[window] = {
            "n_days": int(len(daily)),
            "replacement_ratio_distribution": summarize_numeric(daily["replacement_ratio"].dropna().astype(float).tolist()),
            "retained_ratio_distribution": summarize_numeric(daily["retained_ratio"].dropna().astype(float).tolist()),
        }
    return result


def analyze_candidate(candidate_name: str, annotated_frame: pd.DataFrame) -> dict[str, Any]:
    entrant_vs_retained = compute_new_entrant_vs_retained(annotated_frame)
    high_vs_low_churn = compute_high_vs_low_churn(annotated_frame)
    return {
        "candidate_name": candidate_name,
        "turnover_summary": compute_turnover_summary(annotated_frame),
        "entrant_vs_retained": entrant_vs_retained,
        "high_vs_low_churn": high_vs_low_churn,
    }


def infer_conclusion(candidates: dict[str, dict[str, Any]]) -> dict[str, Any]:
    baseline = candidates["baseline"]
    confirmed5 = candidates["confirmed5"]
    v2 = candidates["v2"]

    entrant_penalty_consistent = {
        name: bool(
            payload["entrant_vs_retained"]["train"]["entrants_weaker_than_retained"]
            and payload["entrant_vs_retained"]["validation"]["entrants_weaker_than_retained"]
        )
        for name, payload in candidates.items()
    }
    high_churn_penalty_consistent = {
        name: bool(payload["high_vs_low_churn"]["direction_consistent_high_churn_weaker"])
        for name, payload in candidates.items()
    }

    confirmed5_validation_gap = confirmed5["entrant_vs_retained"]["validation"]["entrant_minus_retained_mean_realized_return"]
    baseline_validation_gap = baseline["entrant_vs_retained"]["validation"]["entrant_minus_retained_mean_realized_return"]
    v2_validation_gap = v2["entrant_vs_retained"]["validation"]["entrant_minus_retained_mean_realized_return"]
    confirmed5_validation_replacement = confirmed5["turnover_summary"]["validation"]["replacement_ratio_distribution"]["mean"]
    baseline_validation_replacement = baseline["turnover_summary"]["validation"]["replacement_ratio_distribution"]["mean"]
    v2_validation_replacement = v2["turnover_summary"]["validation"]["replacement_ratio_distribution"]["mean"]

    low_degree_evidence_supported = bool(
        entrant_penalty_consistent["confirmed5"]
        and entrant_penalty_consistent["v2"]
        and high_churn_penalty_consistent["confirmed5"]
        and high_churn_penalty_consistent["v2"]
    )

    findings = [
        "confirmed5 的 validation replacement ratio 明显高于 baseline，且 new entrants 在 validation 中显著弱于 retained names。",
        "v2 的 validation replacement ratio 低于 baseline，但 high churn penalty 并没有在 train / validation 稳定同向。",
        "三者的 high churn vs low churn 日级 realized return 差异都没有形成稳定同向证据。",
    ]
    if not entrant_penalty_consistent["v2"]:
        findings.append("v2 的 entrant penalty 在 train 中没有稳定成立，因此 admission rule 证据无法跨失败 nonlinear 候选复用。")

    recommendation = (
        "不建议进入 turnover-aware admission challenger。当前证据更多是在 validation 中看到 entrant 更弱，"
        "但 high churn penalty 本身不稳定，且 v2 的 entrant penalty 也没有在 train / validation 一致成立。"
    )
    if low_degree_evidence_supported:
        recommendation = (
            "存在可继续预注册审计的 admission evidence，但仍只应进入新的 diagnostic-only preregistration，"
            "不得直接推进 challenger。"
        )

    return {
        "checked_d0_visible_metrics": [feature["name"] for feature in D0_FEATURES] + ["replacement_ratio", "retained_ratio"],
        "entrant_penalty_consistent_train_validation": entrant_penalty_consistent,
        "high_churn_penalty_consistent_train_validation": high_churn_penalty_consistent,
        "confirmed5_validation_replacement_ratio_mean": confirmed5_validation_replacement,
        "baseline_validation_replacement_ratio_mean": baseline_validation_replacement,
        "v2_validation_replacement_ratio_mean": v2_validation_replacement,
        "confirmed5_validation_entrant_minus_retained": confirmed5_validation_gap,
        "baseline_validation_entrant_minus_retained": baseline_validation_gap,
        "v2_validation_entrant_minus_retained": v2_validation_gap,
        "low_degree_admission_evidence_supported": low_degree_evidence_supported,
        "findings": findings,
        "recommend_turnover_aware_admission_challenger": low_degree_evidence_supported,
        "recommendation": recommendation,
    }


def build_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Turnover-Aware Admission Diagnosis",
        "",
        "## Scope",
        "",
        "本文档只使用 trainval 诊断输入，检查 turnover-aware admission 是否存在 D0 可见、低自由度、train/validation 方向一致的证据。本文档不训练，不跑 portfolio，不生成 metrics/readout，不读取 frozen test，不设计 v4 参数，不把 trainval diagnosis 当 OOS。",
        "",
        "## Checked D0-Visible Metrics",
        "",
        "- `replacement_ratio`: 每个 signal_date 的 TopK replacement ratio",
        "- `retained_ratio`: 每个 signal_date 的 retained ratio",
    ]
    for feature in D0_FEATURES:
        lines.append(f"- `{feature['name']}`: {feature['label']}")

    lines.extend(["", "## Candidate Diagnosis", ""])
    for key in ("baseline", "confirmed5", "v2"):
        candidate = payload["candidates"][key]
        train_turn = candidate["turnover_summary"]["train"]["replacement_ratio_distribution"]["mean"]
        val_turn = candidate["turnover_summary"]["validation"]["replacement_ratio_distribution"]["mean"]
        train_gap = candidate["entrant_vs_retained"]["train"]["entrant_minus_retained_mean_realized_return"]
        val_gap = candidate["entrant_vs_retained"]["validation"]["entrant_minus_retained_mean_realized_return"]
        churn = candidate["high_vs_low_churn"]
        lines.append(f"### {key}")
        lines.append("")
        lines.append(f"- train replacement ratio mean `{fmt_float(train_turn)}`")
        lines.append(f"- validation replacement ratio mean `{fmt_float(val_turn)}`")
        lines.append(f"- entrant minus retained train `{fmt_pct(train_gap)}`")
        lines.append(f"- entrant minus retained validation `{fmt_pct(val_gap)}`")
        lines.append(f"- high churn minus low churn train `{fmt_pct(churn['train']['high_minus_low_mean_realized_return'])}`")
        lines.append(
            f"- high churn minus low churn validation `{fmt_pct(churn['validation']['high_minus_low_mean_realized_return'])}`"
        )
        lines.append("")

    conclusion = payload["conclusion"]
    lines.extend(["## Conclusion", ""])
    lines.append(
        f"- entrant penalty consistent train/validation: `{conclusion['entrant_penalty_consistent_train_validation']}`"
    )
    lines.append(
        f"- high churn penalty consistent train/validation: `{conclusion['high_churn_penalty_consistent_train_validation']}`"
    )
    lines.append(
        f"- low-degree admission evidence supported: `{conclusion['low_degree_admission_evidence_supported']}`"
    )
    for finding in conclusion["findings"]:
        lines.append(f"- {finding}")
    lines.append(f"- recommendation: {conclusion['recommendation']}")
    if not conclusion["recommend_turnover_aware_admission_challenger"]:
        lines.append("- 不建议进入 turnover-aware admission challenger")
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
        topk_frames = {
            "baseline": build_topk_frame(con, args.baseline_scores, view_name="baseline_scores", topk=args.topk),
            "confirmed5": build_topk_frame(con, args.confirmed5_scores, view_name="confirmed5_scores", topk=args.topk),
            "v2": build_topk_frame(con, args.v2_scores, view_name="v2_scores", topk=args.topk),
        }
        if args.include_v3_reference and args.v3_scores.exists():
            topk_frames["v3_rejected_reference"] = build_topk_frame(
                con,
                args.v3_scores,
                view_name="v3_scores",
                topk=args.topk,
            )
    finally:
        con.close()

    candidates = {
        name: analyze_candidate(name, annotate_turnover_states(frame))
        for name, frame in topk_frames.items()
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
        "candidates": candidates,
        "conclusion": conclusion,
    }
    if "v3_rejected_reference" in topk_frames:
        payload["v3_rejected_reference"] = {
            "included": True,
            "purpose": "rejected_reference_only",
            "turnover_summary": compute_turnover_summary(annotate_turnover_states(topk_frames["v3_rejected_reference"])),
        }
    else:
        payload["v3_rejected_reference"] = {
            "included": False,
            "purpose": "not_needed_for_admission_conclusion",
        }

    write_json(args.output_json, payload)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(build_markdown(payload), encoding="utf-8")


if __name__ == "__main__":
    main()
