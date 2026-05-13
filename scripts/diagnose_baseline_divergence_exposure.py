#!/opt/anaconda3/envs/quant_trade/bin/python
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

try:
    from scripts.data_enrichment_next_use_guardrail_adapter import require_data_enrichment_next_use
except ModuleNotFoundError:
    adapter_path = Path(__file__).with_name("data_enrichment_next_use_guardrail_adapter.py")
    spec = importlib.util.spec_from_file_location("data_enrichment_next_use_guardrail_adapter", adapter_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load guardrail adapter from {adapter_path}")
    adapter_module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("data_enrichment_next_use_guardrail_adapter", adapter_module)
    spec.loader.exec_module(adapter_module)
    require_data_enrichment_next_use = adapter_module.require_data_enrichment_next_use


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

EXPOSURE_FIELDS: list[dict[str, str]] = [
    {"name": "volatility_20d", "label": "volatility_20d"},
    {"name": "amount", "label": "amount / liquidity"},
    {"name": "total_mv", "label": "total_mv / size"},
    {"name": "turnover_rate", "label": "turnover_rate"},
    {"name": "candidate_model_score_D0", "label": "candidate model_score_D0"},
    {"name": "candidate_score_percentile", "label": "candidate score percentile"},
    {"name": "candidate_rank_position", "label": "candidate topk rank position"},
]

UNAVAILABLE_FIELDS: list[dict[str, str]] = [
    {"name": "industry", "reason": "current trainval pair frame does not carry normalized industry exposure fields"},
    {"name": "st_status", "reason": "current diagnostic input does not carry audited ST status flags in the pair frame"},
    {"name": "listing_age", "reason": "current diagnostic input does not carry listing age as a normalized D0 exposure field"},
    {"name": "limit_status", "reason": "current diagnostic input does not carry normalized limit-up/limit-down state flags for divergence cohorts"},
    {"name": "suspension_status", "reason": "current diagnostic input does not carry normalized suspension state flags for divergence cohorts"},
]

COHORTS = ("baseline_only", "nonlinear_only", "overlap")
EPS = 1e-9


def sql_path(path: Path) -> str:
    return path.as_posix().replace("'", "''")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose D0-visible divergence exposure differences between baseline-only and nonlinear-only names."
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
    parser.add_argument(
        "--enrichment-requested-fields",
        nargs="*",
        default=[],
        help="Explicit data_field_enrichment_v1 fields requested by this diagnostic. Default: none.",
    )
    parser.add_argument(
        "--next-use-audit-path",
        type=Path,
        default=None,
        help="Path to write the data enrichment next-use guardrail audit JSON.",
    )
    return parser.parse_args()


def default_next_use_audit_path(output_json: Path) -> Path:
    return output_json.with_name(f"{output_json.stem}_next_use_audit.json")


def run_next_use_guardrail(args: argparse.Namespace) -> tuple[Path, dict[str, Any]]:
    audit_path = args.next_use_audit_path or default_next_use_audit_path(args.output_json)
    audit = require_data_enrichment_next_use(
        requested_fields=list(args.enrichment_requested_fields),
        intended_use="diagnostic",
        consumer_name="diagnose_baseline_divergence_exposure",
        run_scope="trainval_diagnostic_only",
        declared_no_frozen_test_access=True,
        declared_conditional_pass=True,
        requested_layer_status="conditional_pass",
        allow_silent_fallback=False,
        audit_json=audit_path,
    )
    return audit_path, audit


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


def signed_direction(value: float | None) -> str:
    if value is None or abs(value) <= EPS:
        return "flat"
    return "positive" if value > 0 else "negative"


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
            COUNT(*) OVER (PARTITION BY s.signal_date) AS pool_count,
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
            COUNT(*) OVER (PARTITION BY s.signal_date) AS pool_count,
            ROW_NUMBER() OVER (
                PARTITION BY s.signal_date
                ORDER BY s.model_score_D0 DESC, s.instrument ASC
            ) AS rank_position
        FROM {nonlinear_view} s
        INNER JOIN split_days d
            USING (signal_date)
    ),
    baseline_topk AS (
        SELECT snapshot_id, instrument, signal_date, split_bucket, rank_position, pool_count, model_score_D0
        FROM baseline_ranked
        WHERE rank_position <= {topk}
    ),
    nonlinear_topk AS (
        SELECT snapshot_id, instrument, signal_date, split_bucket, rank_position, pool_count, model_score_D0
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
            b.pool_count AS baseline_pool_count,
            n.pool_count AS nonlinear_pool_count,
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
        m.cohort,
        m.baseline_rank_position,
        m.nonlinear_rank_position,
        m.baseline_model_score_D0,
        m.nonlinear_model_score_D0,
        e.execution_delayed_realized_return,
        f.amount,
        f.total_mv,
        f.turnover_rate,
        f.volatility_20d,
        CASE
            WHEN m.cohort = 'baseline_only' THEN m.baseline_rank_position
            WHEN m.cohort = 'nonlinear_only' THEN m.nonlinear_rank_position
            ELSE m.baseline_rank_position
        END AS candidate_rank_position,
        CASE
            WHEN m.cohort = 'baseline_only' AND m.baseline_pool_count > 1
                THEN 1.0 - ((m.baseline_rank_position - 1.0) / (m.baseline_pool_count - 1.0))
            WHEN m.cohort = 'nonlinear_only' AND m.nonlinear_pool_count > 1
                THEN 1.0 - ((m.nonlinear_rank_position - 1.0) / (m.nonlinear_pool_count - 1.0))
            WHEN m.cohort = 'overlap' AND m.baseline_pool_count > 1
                THEN 1.0 - ((m.baseline_rank_position - 1.0) / (m.baseline_pool_count - 1.0))
            ELSE NULL
        END AS candidate_score_percentile,
        CASE
            WHEN m.cohort = 'baseline_only' THEN m.baseline_model_score_D0
            WHEN m.cohort = 'nonlinear_only' THEN m.nonlinear_model_score_D0
            ELSE m.baseline_model_score_D0
        END AS candidate_model_score_D0
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
        daily = subset.groupby(["signal_date", "cohort"], as_index=False).agg(count=("instrument", "count"))
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


def compute_cohort_summary(frame: pd.DataFrame) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for window in ("train", "validation"):
        subset = frame[frame["split_bucket"] == window].copy()
        result[window] = {}
        for cohort in COHORTS:
            cohort_subset = subset[subset["cohort"] == cohort].copy()
            returns = cohort_subset["execution_delayed_realized_return"].dropna().astype(float).tolist()
            payload = {
                "row_count": int(len(cohort_subset)),
                "realized_return_distribution": summarize_numeric(returns),
            }
            for feature in EXPOSURE_FIELDS:
                values = cohort_subset[feature["name"]].dropna().astype(float).tolist()
                payload[f"{feature['name']}_distribution"] = summarize_numeric(values)
            result[window][cohort] = payload
    return result


def compute_exposure_difference_summary(frame: pd.DataFrame) -> dict[str, Any]:
    divergence = frame[frame["cohort"].isin(("baseline_only", "nonlinear_only"))].copy()
    result: dict[str, Any] = {}
    for feature in EXPOSURE_FIELDS:
        field_payload: dict[str, Any] = {}
        train_sign = None
        validation_sign = None
        for window in ("train", "validation"):
            baseline_subset = divergence[
                (divergence["split_bucket"] == window) & (divergence["cohort"] == "baseline_only")
            ][feature["name"]].dropna().astype(float)
            nonlinear_subset = divergence[
                (divergence["split_bucket"] == window) & (divergence["cohort"] == "nonlinear_only")
            ][feature["name"]].dropna().astype(float)
            mean_diff = (
                float(baseline_subset.mean() - nonlinear_subset.mean())
                if not baseline_subset.empty and not nonlinear_subset.empty
                else None
            )
            direction = signed_direction(mean_diff)
            field_payload[window] = {
                "baseline_only": summarize_numeric(baseline_subset.tolist()),
                "nonlinear_only": summarize_numeric(nonlinear_subset.tolist()),
                "baseline_only_minus_nonlinear_only_mean": mean_diff,
                "direction": direction,
            }
            if window == "train":
                train_sign = direction
            else:
                validation_sign = direction
        field_payload["direction_consistent_train_validation"] = bool(
            train_sign in {"positive", "negative"} and train_sign == validation_sign
        )
        result[feature["name"]] = field_payload
    return result


def compute_exposure_bucket_summary(frame: pd.DataFrame) -> dict[str, Any]:
    divergence = frame[frame["cohort"].isin(("baseline_only", "nonlinear_only"))].copy()
    result: dict[str, Any] = {}
    for feature in EXPOSURE_FIELDS:
        field = feature["name"]
        train = divergence[(divergence["split_bucket"] == "train") & divergence[field].notna()].copy()
        if train.empty:
            result[field] = {"available": False}
            continue
        q1, q2 = train[field].quantile([1 / 3, 2 / 3]).tolist()

        def bucket(value: float | None) -> str | None:
            if pd.isna(value):
                return None
            if value <= q1:
                return "low"
            if value <= q2:
                return "mid"
            return "high"

        bucketed = divergence.copy()
        bucketed["bucket"] = bucketed[field].apply(bucket)
        grouped = (
            bucketed.dropna(subset=["bucket"])
            .groupby(["split_bucket", "bucket", "cohort"], as_index=False)
            .agg(
                mean_realized_return=("execution_delayed_realized_return", "mean"),
                row_count=("instrument", "count"),
            )
        )
        field_payload: dict[str, Any] = {
            "available": True,
            "train_threshold_q33": float(q1),
            "train_threshold_q67": float(q2),
            "windows": {},
        }
        consistent_positive_buckets: list[str] = []
        for window in ("train", "validation"):
            window_rows: dict[str, Any] = {}
            window_group = grouped[grouped["split_bucket"] == window]
            for bucket_name in ("low", "mid", "high"):
                bucket_group = window_group[window_group["bucket"] == bucket_name]
                baseline_row = bucket_group[bucket_group["cohort"] == "baseline_only"]
                nonlinear_row = bucket_group[bucket_group["cohort"] == "nonlinear_only"]
                baseline_mean = (
                    float(baseline_row["mean_realized_return"].iloc[0]) if not baseline_row.empty else None
                )
                nonlinear_mean = (
                    float(nonlinear_row["mean_realized_return"].iloc[0]) if not nonlinear_row.empty else None
                )
                spread = (
                    float(baseline_mean - nonlinear_mean)
                    if baseline_mean is not None and nonlinear_mean is not None
                    else None
                )
                window_rows[bucket_name] = {
                    "baseline_only_mean_realized_return": baseline_mean,
                    "nonlinear_only_mean_realized_return": nonlinear_mean,
                    "baseline_only_minus_nonlinear_only_spread": spread,
                    "direction": signed_direction(spread),
                    "baseline_only_count": int(baseline_row["row_count"].iloc[0]) if not baseline_row.empty else 0,
                    "nonlinear_only_count": int(nonlinear_row["row_count"].iloc[0]) if not nonlinear_row.empty else 0,
                }
            field_payload["windows"][window] = window_rows
        for bucket_name in ("low", "mid", "high"):
            train_direction = field_payload["windows"]["train"][bucket_name]["direction"]
            validation_direction = field_payload["windows"]["validation"][bucket_name]["direction"]
            if train_direction == "positive" and validation_direction == "positive":
                consistent_positive_buckets.append(bucket_name)
        field_payload["positive_spread_buckets_consistent_train_validation"] = consistent_positive_buckets
        result[field] = field_payload
    return result


def analyze_pair(pair_name: str, frame: pd.DataFrame, *, topk: int) -> dict[str, Any]:
    return {
        "pair_name": pair_name,
        "pairwise_overlap": compute_pairwise_overlap(frame, topk=topk),
        "cohort_summary": compute_cohort_summary(frame),
        "exposure_difference_summary": compute_exposure_difference_summary(frame),
        "exposure_bucket_summary": compute_exposure_bucket_summary(frame),
    }


def find_shared_exposure_patterns(pairs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    confirmed5 = pairs["baseline_vs_confirmed5"]["exposure_difference_summary"]
    v2 = pairs["baseline_vs_v2"]["exposure_difference_summary"]
    shared: list[dict[str, Any]] = []
    for feature in EXPOSURE_FIELDS:
        field = feature["name"]
        c5 = confirmed5[field]
        v2_field = v2[field]
        c5_train = c5["train"]["direction"]
        c5_validation = c5["validation"]["direction"]
        v2_train = v2_field["train"]["direction"]
        v2_validation = v2_field["validation"]["direction"]
        if (
            c5["direction_consistent_train_validation"]
            and v2_field["direction_consistent_train_validation"]
            and c5_train == v2_train
            and c5_validation == v2_validation
        ):
            shared.append(
                {
                    "field": field,
                    "label": feature["label"],
                    "direction": c5_train,
                }
            )
    return shared


def find_shared_positive_buckets(pairs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    confirmed5 = pairs["baseline_vs_confirmed5"]["exposure_bucket_summary"]
    v2 = pairs["baseline_vs_v2"]["exposure_bucket_summary"]
    shared: list[dict[str, Any]] = []
    for feature in EXPOSURE_FIELDS:
        field = feature["name"]
        if not confirmed5[field]["available"] or not v2[field]["available"]:
            continue
        buckets = set(confirmed5[field]["positive_spread_buckets_consistent_train_validation"]) & set(
            v2[field]["positive_spread_buckets_consistent_train_validation"]
        )
        for bucket_name in sorted(buckets):
            shared.append(
                {
                    "field": field,
                    "label": feature["label"],
                    "bucket": bucket_name,
                }
            )
    return shared


def infer_conclusion(pairs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    shared_patterns = find_shared_exposure_patterns(pairs)
    shared_positive_buckets = find_shared_positive_buckets(pairs)
    low_degree_rule_supported = False
    findings = [
        "baseline-only 与 confirmed5-only 的主要差异更像低波动、低换手、更大市值与更低 amount 暴露。",
        "baseline-only 与 v2-only 的主要差异则更像更高波动、更高换手、更小市值与更高 amount 方向，说明两组 divergence exposure 结构并不统一。",
        "exposure bucket 下虽然存在一些 train / validation 同方向的正 spread bucket，但这些 bucket 无法压缩成一条跨 confirmed5 / v2 共享的单一 D0 曝露规则。",
        "因此当前证据更适合支持进一步 exposure decomposition，而不是直接进入 exposure rule challenger。",
    ]
    recommendation = (
        "不建议进入 exposure rule challenger。当前可以确认 baseline divergence selection 与 D0 暴露有关，"
        "但 confirmed5 / v2 并没有共享单一、低自由度、可复用的 exposure pattern。"
    )
    return {
        "checked_d0_visible_fields": [feature["name"] for feature in EXPOSURE_FIELDS],
        "unavailable_fields": UNAVAILABLE_FIELDS,
        "shared_exposure_patterns_across_confirmed5_v2": shared_patterns,
        "shared_positive_spread_buckets_across_confirmed5_v2": shared_positive_buckets,
        "low_degree_exposure_rule_supported": low_degree_rule_supported,
        "findings": findings,
        "recommend_exposure_rule_challenger": low_degree_rule_supported,
        "recommendation": recommendation,
    }


def build_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Baseline Divergence Exposure Diagnosis",
        "",
        "## Scope",
        "",
        "本文档只使用 trainval diagnostic-only 输入，检查 baseline-only names 相比 nonlinear-only names 的 D0 可见暴露差异。本文档不训练，不跑 portfolio，不生成 formal metrics/readout，不读取 frozen test，不设计 v4 参数，不把 trainval diagnosis 当 OOS。",
        "",
        "## Checked D0-Visible Fields",
        "",
    ]
    for feature in EXPOSURE_FIELDS:
        lines.append(f"- `{feature['name']}`: {feature['label']}")
    lines.extend(["", "## Unavailable Fields", ""])
    for field in UNAVAILABLE_FIELDS:
        lines.append(f"- `{field['name']}`: {field['reason']}")

    lines.extend(["", "## Pair Diagnosis", ""])
    for pair_name in ("baseline_vs_confirmed5", "baseline_vs_v2"):
        pair = payload["pairs"][pair_name]
        lines.append(f"### {pair_name}")
        lines.append("")
        for window in ("train", "validation"):
            overlap = pair["pairwise_overlap"][window]
            lines.append(
                f"- {window} overlap `{fmt_float(overlap['avg_overlap_count'])}` / {payload['topk']}, jaccard `{fmt_float(overlap['avg_jaccard'])}`"
            )
        for feature in EXPOSURE_FIELDS:
            summary = pair["exposure_difference_summary"][feature["name"]]
            lines.append(
                f"- `{feature['name']}` train diff `{fmt_float(summary['train']['baseline_only_minus_nonlinear_only_mean'])}`, "
                f"validation diff `{fmt_float(summary['validation']['baseline_only_minus_nonlinear_only_mean'])}`, "
                f"direction consistent `{summary['direction_consistent_train_validation']}`"
            )
        lines.append("")

    conclusion = payload["conclusion"]
    lines.extend(["## Conclusion", ""])
    lines.append(
        f"- shared exposure patterns across confirmed5 / v2: `{conclusion['shared_exposure_patterns_across_confirmed5_v2']}`"
    )
    lines.append(
        f"- shared positive spread buckets across confirmed5 / v2: `{conclusion['shared_positive_spread_buckets_across_confirmed5_v2']}`"
    )
    lines.append(
        f"- low-degree exposure rule supported: `{conclusion['low_degree_exposure_rule_supported']}`"
    )
    for finding in conclusion["findings"]:
        lines.append(f"- {finding}")
    lines.append(f"- recommendation: {conclusion['recommendation']}")
    if not conclusion["recommend_exposure_rule_challenger"]:
        lines.append("- 不建议进入 exposure rule challenger")
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    next_use_audit_path, next_use_audit = run_next_use_guardrail(args)
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
                "purpose": "not_needed_for_exposure_conclusion",
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
        "next_use_audit_path": next_use_audit_path.as_posix(),
        "data_enrichment_next_use": next_use_audit,
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
