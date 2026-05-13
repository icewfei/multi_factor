#!/usr/bin/env python3
"""
MODEL EDGE DIAGNOSIS ONLY — NOT A BACKTEST — NOT A PORTFOLIO READOUT

Diagnose clean baseline family score-layer / model-layer behavior on real trainval.

This script:
- does NOT read frozen test
- does NOT generate holdings, backtest_daily, metrics, or readout
- does NOT modify any baseline definition
- writes diagnosis JSON/MD only
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
SCORE_GATE_ROOT = Path("/private/tmp/clean_baseline_family_score_gate_20260513")
DEFAULT_OUTPUT_JSON = Path("/private/tmp/clean_baseline_family_model_edge_diagnosis.json")
DEFAULT_OUTPUT_MD = Path("/private/tmp/clean_baseline_family_model_edge_diagnosis.md")
DEFAULT_LABEL_PANEL = (
    ROOT
    / "artifacts"
    / "run_state"
    / "project_panels_research_trainval_20211231_20260429"
    / "project_label_panel.parquet"
)
DEFAULT_SPLIT_PANEL = (
    ROOT
    / "artifacts"
    / "run_state"
    / "project_panels_research_trainval_20211231_20260429"
    / "dataset_split_daily.parquet"
)
DEFAULT_P98_SCORES = (
    ROOT
    / "artifacts"
    / "run_state"
    / "confirmatory_reversal_p98_trainval_20260506"
    / "model_scores_D0.parquet"
)
DEFAULT_MULTI_EQUAL_SCORES = (
    ROOT
    / "artifacts"
    / "run_state"
    / "exploratory_multi_signal_composite_v1"
    / "model_scores_D0_multi.parquet"
)

TOPK_DEFAULT = 30
DIAGNOSIS_LABEL = (
    "MODEL EDGE DIAGNOSIS ONLY — NOT A BACKTEST — "
    "NOT A PORTFOLIO READOUT — DO NOT INTERPRET AS STRATEGY EFFECTIVENESS"
)
EXPECTED_P98_CANDIDATE = "reversal_tail_exclude_p98_v1"
EXPECTED_MULTI_EQUAL_CANDIDATE = "multi_equal_weight_v1"

MODEL_SPECS: dict[str, dict[str, Any]] = {
    "no_p98_reversal_baseline_v1": {
        "candidate_scheme_id": "no_p98_reversal_baseline_v1",
        "raw_score_column": "model_score_D0",
        "score_direction": "ASC / reversal_rank",
        "effective_score_expression": "-model_score_D0",
        "has_snapshot_id": True,
        "label": "no_p98_reversal_baseline_v1",
        "status": "clean_baseline_candidate",
        "conditional_reference": False,
        "audit_required": True,
    },
    "clean_momentum_20d_baseline_v1": {
        "candidate_scheme_id": "clean_momentum_20d_baseline_v1",
        "raw_score_column": "model_score_D0",
        "score_direction": "descending 20d cumulative return / stronger momentum first",
        "effective_score_expression": "-model_score_D0",
        "has_snapshot_id": True,
        "label": "clean_momentum_20d_baseline_v1",
        "status": "clean_baseline_candidate",
        "conditional_reference": False,
        "audit_required": True,
    },
    "clean_liquidity_adjusted_reversal_baseline_v1": {
        "candidate_scheme_id": "clean_liquidity_adjusted_reversal_baseline_v1",
        "raw_score_column": "model_score_D0",
        "score_direction": "ascending 1d return first, descending liquidity tiebreak",
        "effective_score_expression": "-model_score_D0",
        "has_snapshot_id": True,
        "label": "clean_liquidity_adjusted_reversal_baseline_v1",
        "status": "clean_baseline_candidate",
        "conditional_reference": False,
        "audit_required": True,
    },
    "clean_equal_weight_random_eligible_baseline_v1": {
        "candidate_scheme_id": "clean_equal_weight_random_eligible_baseline_v1",
        "raw_score_column": "model_score_D0",
        "score_direction": "ascending deterministic hash / pseudo-random but reproducible order",
        "effective_score_expression": "-model_score_D0",
        "has_snapshot_id": True,
        "label": "clean_equal_weight_random_eligible_baseline_v1",
        "status": "clean_baseline_candidate",
        "conditional_reference": False,
        "audit_required": True,
    },
    "p98_conditional_reference": {
        "candidate_scheme_id": EXPECTED_P98_CANDIDATE,
        "raw_score_column": "model_score_D0",
        "score_direction": "DESC / higher score better",
        "effective_score_expression": "model_score_D0",
        "has_snapshot_id": True,
        "label": "p98 conditional baseline",
        "status": "conditional_reference_only",
        "conditional_reference": True,
        "audit_required": False,
    },
    "multi_equal_weight_v1_conditional_reference": {
        "candidate_scheme_id": EXPECTED_MULTI_EQUAL_CANDIDATE,
        "raw_score_column": "model_score_D0",
        "score_direction": "DESC / higher score better",
        "effective_score_expression": "model_score_D0",
        "has_snapshot_id": False,
        "label": "multi_equal_weight_v1 conditional baseline",
        "status": "conditional_reference_only",
        "conditional_reference": True,
        "audit_required": False,
    },
}
REQUIRED_CLEAN_MODEL_KEYS = [
    "no_p98_reversal_baseline_v1",
    "clean_momentum_20d_baseline_v1",
    "clean_liquidity_adjusted_reversal_baseline_v1",
    "clean_equal_weight_random_eligible_baseline_v1",
]
CONDITIONAL_REFERENCE_KEYS = [
    "p98_conditional_reference",
    "multi_equal_weight_v1_conditional_reference",
]


class DiagnosisError(Exception):
    """Raised when the diagnosis cannot be completed safely."""


def default_score_path(baseline_id: str) -> Path:
    return SCORE_GATE_ROOT / baseline_id / "model_scores_D0.parquet"


def default_audit_path(baseline_id: str) -> Path:
    return SCORE_GATE_ROOT / baseline_id / "model_scores_D0_audit.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose clean baseline family model-layer edge only."
    )
    parser.add_argument(
        "--no-p98-scores",
        type=Path,
        default=default_score_path("no_p98_reversal_baseline_v1"),
    )
    parser.add_argument(
        "--no-p98-audit",
        type=Path,
        default=default_audit_path("no_p98_reversal_baseline_v1"),
    )
    parser.add_argument(
        "--momentum-scores",
        type=Path,
        default=default_score_path("clean_momentum_20d_baseline_v1"),
    )
    parser.add_argument(
        "--momentum-audit",
        type=Path,
        default=default_audit_path("clean_momentum_20d_baseline_v1"),
    )
    parser.add_argument(
        "--liquidity-scores",
        type=Path,
        default=default_score_path("clean_liquidity_adjusted_reversal_baseline_v1"),
    )
    parser.add_argument(
        "--liquidity-audit",
        type=Path,
        default=default_audit_path("clean_liquidity_adjusted_reversal_baseline_v1"),
    )
    parser.add_argument(
        "--random-scores",
        type=Path,
        default=default_score_path("clean_equal_weight_random_eligible_baseline_v1"),
    )
    parser.add_argument(
        "--random-audit",
        type=Path,
        default=default_audit_path("clean_equal_weight_random_eligible_baseline_v1"),
    )
    parser.add_argument("--p98-scores", type=Path, default=DEFAULT_P98_SCORES)
    parser.add_argument("--multi-equal-scores", type=Path, default=DEFAULT_MULTI_EQUAL_SCORES)
    parser.add_argument("--label-panel", type=Path, default=DEFAULT_LABEL_PANEL)
    parser.add_argument("--split-panel", type=Path, default=DEFAULT_SPLIT_PANEL)
    parser.add_argument("--topk", type=int, default=TOPK_DEFAULT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def ensure_exists(path: Path | None, label: str) -> None:
    if path is None or not path.exists():
        raise DiagnosisError(f"{label} not found: {path}")


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DiagnosisError(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DiagnosisError(f"{label} is not valid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise DiagnosisError(f"{label} must be a JSON object: {path}")
    return payload


def sql_path(path: Path) -> str:
    return path.as_posix().replace("'", "''")


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return float(value)


def mean_std_tstat(values) -> tuple[float | None, float | None, float | None]:
    clean = values.dropna()
    if clean.empty:
        return None, None, None
    mean_value = float(clean.mean())
    std_value = safe_float(clean.std())
    if std_value in (None, 0.0):
        return mean_value, std_value, None
    t_stat = float(mean_value / (std_value / math.sqrt(len(clean))))
    return mean_value, std_value, t_stat


def extract_summary_count(audit: dict[str, Any], name: str) -> Any:
    if name in audit:
        return audit[name]
    return audit.get("summary_counts", {}).get(name)


def ensure_clean_audit_passes(audit: dict[str, Any], baseline_id: str) -> None:
    if audit.get("candidate_scheme_id") != baseline_id:
        raise DiagnosisError(f"{baseline_id} audit candidate_scheme_id mismatch")
    if audit.get("baseline_id") != baseline_id:
        raise DiagnosisError(f"{baseline_id} audit baseline_id mismatch")
    if audit.get("frozen_test_accessed") is not False:
        raise DiagnosisError(f"{baseline_id} audit indicates frozen_test_accessed is not false")
    if audit.get("p98_used") is not False:
        raise DiagnosisError(f"{baseline_id} audit indicates p98_used is not false")
    if audit.get("label_diagnostics_used") is not False:
        raise DiagnosisError(f"{baseline_id} audit indicates label_diagnostics_used is not false")
    if audit.get("d0_visibility_audit", {}).get("pass") is not True:
        raise DiagnosisError(f"{baseline_id} audit indicates D0 visibility audit failed")
    if audit.get("leakage_audit", {}).get("pass") is not True:
        raise DiagnosisError(f"{baseline_id} audit indicates leakage audit failed")


def build_score_inputs(args: argparse.Namespace) -> dict[str, dict[str, Path | None]]:
    return {
        "no_p98_reversal_baseline_v1": {
            "scores": args.no_p98_scores,
            "audit": args.no_p98_audit,
        },
        "clean_momentum_20d_baseline_v1": {
            "scores": args.momentum_scores,
            "audit": args.momentum_audit,
        },
        "clean_liquidity_adjusted_reversal_baseline_v1": {
            "scores": args.liquidity_scores,
            "audit": args.liquidity_audit,
        },
        "clean_equal_weight_random_eligible_baseline_v1": {
            "scores": args.random_scores,
            "audit": args.random_audit,
        },
        "p98_conditional_reference": {
            "scores": args.p98_scores,
            "audit": None,
        },
        "multi_equal_weight_v1_conditional_reference": {
            "scores": args.multi_equal_scores,
            "audit": None,
        },
    }


def register_score_view(
    con: duckdb.DuckDBPyConnection,
    *,
    view_name: str,
    path: Path,
    candidate_scheme_id: str,
    raw_score_column: str,
    effective_score_expression: str,
) -> None:
    con.execute(
        f"""
        CREATE OR REPLACE TEMP VIEW {view_name} AS
        SELECT
            *,
            {raw_score_column} AS raw_score,
            {effective_score_expression} AS effective_score
        FROM read_parquet('{sql_path(path)}')
        WHERE candidate_scheme_id = '{candidate_scheme_id}'
        """
    )


def build_views(
    con: duckdb.DuckDBPyConnection,
    *,
    score_inputs: dict[str, dict[str, Path | None]],
    args: argparse.Namespace,
) -> None:
    for model_key, spec in MODEL_SPECS.items():
        register_score_view(
            con,
            view_name=f"{model_key}_t",
            path=score_inputs[model_key]["scores"],  # type: ignore[arg-type]
            candidate_scheme_id=spec["candidate_scheme_id"],
            raw_score_column=spec["raw_score_column"],
            effective_score_expression=spec["effective_score_expression"],
        )

    con.execute(
        f"""
        CREATE OR REPLACE TEMP VIEW label_t AS
        SELECT
            snapshot_id,
            instrument,
            signal_date,
            label_5d_next_open_close AS forward_return_5d,
            label_defined
        FROM read_parquet('{sql_path(args.label_panel)}')
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TEMP VIEW split_t AS
        SELECT
            snapshot_id,
            instrument,
            signal_date,
            split_bucket,
            train_flag,
            validation_flag
        FROM read_parquet('{sql_path(args.split_panel)}')
        """
    )

    comparison_sql = """
        CREATE OR REPLACE TEMP VIEW comparison_t AS
        SELECT
            l.snapshot_id,
            l.instrument,
            l.signal_date,
            l.forward_return_5d,
            s.split_bucket,
            s.train_flag,
            s.validation_flag
    """
    for model_key in MODEL_SPECS:
        comparison_sql += f"""
            ,
            {model_key}_t.raw_score AS {model_key}_raw_score,
            {model_key}_t.effective_score AS {model_key}_effective_score
        """
    comparison_sql += """
        FROM label_t l
        INNER JOIN split_t s
            ON l.snapshot_id = s.snapshot_id
           AND l.instrument = s.instrument
           AND l.signal_date = s.signal_date
    """
    for model_key, spec in MODEL_SPECS.items():
        if spec["has_snapshot_id"]:
            comparison_sql += f"""
        LEFT JOIN {model_key}_t
            ON l.snapshot_id = {model_key}_t.snapshot_id
           AND l.instrument = {model_key}_t.instrument
           AND l.signal_date = {model_key}_t.signal_date
            """
        else:
            comparison_sql += f"""
        LEFT JOIN {model_key}_t
            ON l.instrument = {model_key}_t.instrument
           AND l.signal_date = {model_key}_t.signal_date
            """
    comparison_sql += """
        WHERE l.label_defined
          AND (s.train_flag OR s.validation_flag)
    """
    con.execute(comparison_sql)


def fetch_daily_ic(
    con: duckdb.DuckDBPyConnection,
    *,
    split_flag: str,
    effective_score_col: str,
) -> Any:
    return con.execute(
        f"""
        WITH ranked AS (
            SELECT
                signal_date,
                rank() OVER (
                    PARTITION BY signal_date
                    ORDER BY {effective_score_col} ASC, instrument ASC
                ) AS score_rank,
                rank() OVER (
                    PARTITION BY signal_date
                    ORDER BY forward_return_5d ASC, instrument ASC
                ) AS label_rank
            FROM comparison_t
            WHERE {split_flag}
              AND {effective_score_col} IS NOT NULL
        )
        SELECT
            signal_date,
            corr(score_rank::DOUBLE, label_rank::DOUBLE) AS rank_ic
        FROM ranked
        GROUP BY signal_date
        HAVING COUNT(*) >= 10
        ORDER BY signal_date
        """
    ).fetchdf()


def fetch_decile_returns(
    con: duckdb.DuckDBPyConnection,
    *,
    split_flag: str,
    effective_score_col: str,
) -> list[dict[str, Any]]:
    rows = con.execute(
        f"""
        WITH ranked AS (
            SELECT
                signal_date,
                ntile(10) OVER (
                    PARTITION BY signal_date
                    ORDER BY {effective_score_col} DESC, instrument ASC
                ) AS decile_desc,
                forward_return_5d
            FROM comparison_t
            WHERE {split_flag}
              AND {effective_score_col} IS NOT NULL
        ),
        daily_decile AS (
            SELECT
                signal_date,
                decile_desc,
                AVG(forward_return_5d) AS decile_return
            FROM ranked
            GROUP BY signal_date, decile_desc
        )
        SELECT
            decile_desc,
            AVG(decile_return) AS mean_forward_return,
            STDDEV_SAMP(decile_return) AS std_forward_return,
            COUNT(*) AS n_days
        FROM daily_decile
        GROUP BY decile_desc
        ORDER BY decile_desc
        """
    ).fetchall()
    output: list[dict[str, Any]] = []
    for decile_desc, mean_forward_return, std_forward_return, n_days in rows:
        t_stat = None
        if std_forward_return is not None and std_forward_return > 0 and n_days > 0:
            t_stat = float(mean_forward_return / (std_forward_return / math.sqrt(n_days)))
        output.append(
            {
                "decile": int(decile_desc),
                "decile_order": "1_is_top_10pct__10_is_bottom_10pct",
                "mean_forward_return": float(mean_forward_return),
                "std_forward_return": safe_float(std_forward_return),
                "n_days": int(n_days),
                "t_stat": t_stat,
            }
        )
    return output


def fetch_topk_head_proxy(
    con: duckdb.DuckDBPyConnection,
    *,
    split_flag: str,
    effective_score_col: str,
    topk: int,
) -> dict[str, Any]:
    daily = con.execute(
        f"""
        WITH ranked AS (
            SELECT
                signal_date,
                instrument,
                forward_return_5d,
                row_number() OVER (
                    PARTITION BY signal_date
                    ORDER BY {effective_score_col} DESC, instrument ASC
                ) AS score_rank
            FROM comparison_t
            WHERE {split_flag}
              AND {effective_score_col} IS NOT NULL
        )
        SELECT
            signal_date,
            AVG(CASE WHEN score_rank <= {topk} THEN forward_return_5d END) AS topk_mean_return,
            AVG(CASE WHEN score_rank BETWEEN {topk + 1} AND {2 * topk} THEN forward_return_5d END) AS nextk_mean_return,
            SUM(CASE WHEN score_rank <= {topk} THEN 1 ELSE 0 END) AS selected_topk_rows,
            SUM(CASE WHEN score_rank BETWEEN {topk + 1} AND {2 * topk} THEN 1 ELSE 0 END) AS nextk_rows
        FROM ranked
        GROUP BY signal_date
        HAVING SUM(CASE WHEN score_rank <= {topk} THEN 1 ELSE 0 END) = {topk}
           AND SUM(CASE WHEN score_rank BETWEEN {topk + 1} AND {2 * topk} THEN 1 ELSE 0 END) = {topk}
        ORDER BY signal_date
        """
    ).fetchdf()
    if daily.empty:
        return {
            "topk": topk,
            "ranking_mode": "effective_score_desc_topk_and_nextk",
            "n_days": 0,
            "selected_topk_rows": 0,
            "mean_topk_forward_return": None,
            "std_topk_forward_return": None,
            "positive_day_pct": None,
            "mean_nextk_forward_return": None,
            "topk_minus_nextk": None,
            "topk_mean_t_stat": None,
            "topk_minus_nextk_t_stat": None,
        }

    topk_mean, topk_std, topk_t_stat = mean_std_tstat(daily["topk_mean_return"])
    spread_series = daily["topk_mean_return"] - daily["nextk_mean_return"]
    spread_mean, _, spread_t_stat = mean_std_tstat(spread_series)
    return {
        "topk": topk,
        "ranking_mode": "effective_score_desc_topk_and_nextk",
        "n_days": int(len(daily)),
        "selected_topk_rows": int(daily["selected_topk_rows"].sum()),
        "mean_topk_forward_return": topk_mean,
        "std_topk_forward_return": topk_std,
        "positive_day_pct": float((daily["topk_mean_return"] > 0).mean()),
        "mean_nextk_forward_return": float(daily["nextk_mean_return"].mean()),
        "topk_minus_nextk": spread_mean,
        "topk_mean_t_stat": topk_t_stat,
        "topk_minus_nextk_t_stat": spread_t_stat,
    }


def compute_yearly_stability(daily_ic) -> list[dict[str, Any]]:
    if daily_ic.empty:
        return []
    ic_frame = daily_ic.copy()
    ic_frame["year"] = ic_frame["signal_date"].str[:4].astype(int)
    output: list[dict[str, Any]] = []
    for year, group in ic_frame.groupby("year", sort=True):
        mean_value, std_value, _ = mean_std_tstat(group["rank_ic"])
        output.append(
            {
                "year": int(year),
                "rank_ic_mean": mean_value,
                "rank_ic_std": std_value,
                "rank_ic_ir": (
                    mean_value / std_value
                    if mean_value is not None and std_value not in (None, 0.0)
                    else None
                ),
                "n_days": int(len(group)),
                "positive_ic_pct": float((group["rank_ic"] > 0).mean()),
            }
        )
    return output


def diagnose_model(
    con: duckdb.DuckDBPyConnection,
    *,
    model_key: str,
    split_name: str,
    split_flag: str,
    raw_score_col: str,
    effective_score_col: str,
    eligible_labeled_rows: int,
    topk: int,
) -> dict[str, Any]:
    summary_row = con.execute(
        f"""
        SELECT
            COUNT({raw_score_col}) AS scored_rows,
            COUNT(DISTINCT CASE WHEN {raw_score_col} IS NOT NULL THEN signal_date END) AS n_signal_dates,
            COUNT(DISTINCT CASE WHEN {raw_score_col} IS NOT NULL THEN instrument END) AS n_instruments,
            AVG({raw_score_col}) AS mean_score,
            STDDEV_SAMP({raw_score_col}) AS std_score,
            MIN({raw_score_col}) AS min_score,
            quantile_cont({raw_score_col}, 0.25) AS p25_score,
            quantile_cont({raw_score_col}, 0.50) AS p50_score,
            quantile_cont({raw_score_col}, 0.75) AS p75_score,
            MAX({raw_score_col}) AS max_score
        FROM comparison_t
        WHERE {split_flag}
          AND {raw_score_col} IS NOT NULL
        """
    ).fetchone()

    scored_rows = int(summary_row[0] or 0)
    score_coverage = (scored_rows / eligible_labeled_rows) if eligible_labeled_rows > 0 else None
    if scored_rows == 0:
        return {
            "model_key": model_key,
            "model_label": MODEL_SPECS[model_key]["label"],
            "candidate_scheme_id": MODEL_SPECS[model_key]["candidate_scheme_id"],
            "score_direction": MODEL_SPECS[model_key]["score_direction"],
            "split": split_name,
            "row_count": 0,
            "scored_rows": 0,
            "eligible_labeled_rows": eligible_labeled_rows,
            "score_coverage": score_coverage,
            "error": "No scored rows for split",
        }

    daily_ic = fetch_daily_ic(con, split_flag=split_flag, effective_score_col=effective_score_col)
    rank_ic_mean, rank_ic_std, rank_ic_t_stat = (
        mean_std_tstat(daily_ic["rank_ic"]) if not daily_ic.empty else (None, None, None)
    )
    icir = (
        rank_ic_mean / rank_ic_std
        if rank_ic_mean is not None and rank_ic_std not in (None, 0.0)
        else None
    )
    deciles = fetch_decile_returns(con, split_flag=split_flag, effective_score_col=effective_score_col)
    top_decile = next((row["mean_forward_return"] for row in deciles if row["decile"] == 1), None)
    bottom_decile = next((row["mean_forward_return"] for row in deciles if row["decile"] == 10), None)
    top_bottom_spread = (
        float(top_decile - bottom_decile)
        if top_decile is not None and bottom_decile is not None
        else None
    )
    topk_proxy = fetch_topk_head_proxy(
        con,
        split_flag=split_flag,
        effective_score_col=effective_score_col,
        topk=topk,
    )
    return {
        "model_key": model_key,
        "model_label": MODEL_SPECS[model_key]["label"],
        "candidate_scheme_id": MODEL_SPECS[model_key]["candidate_scheme_id"],
        "score_direction": MODEL_SPECS[model_key]["score_direction"],
        "status": MODEL_SPECS[model_key]["status"],
        "conditional_reference": MODEL_SPECS[model_key]["conditional_reference"],
        "split": split_name,
        "row_count": scored_rows,
        "scored_rows": scored_rows,
        "eligible_labeled_rows": eligible_labeled_rows,
        "score_coverage": score_coverage,
        "n_signal_dates": int(summary_row[1] or 0),
        "n_instruments": int(summary_row[2] or 0),
        "score_distribution": {
            "count": scored_rows,
            "mean": float(summary_row[3]),
            "std": safe_float(summary_row[4]),
            "min": float(summary_row[5]),
            "p25": float(summary_row[6]),
            "p50": float(summary_row[7]),
            "p75": float(summary_row[8]),
            "max": float(summary_row[9]),
        },
        "rank_ic": {
            "mean": rank_ic_mean,
            "std": rank_ic_std,
            "n_days": int(len(daily_ic)),
            "positive_ic_pct": float((daily_ic["rank_ic"] > 0).mean()) if not daily_ic.empty else None,
            "t_stat": rank_ic_t_stat,
        },
        "icir": icir,
        "decile_forward_returns": deciles,
        "top_bottom_spread": top_bottom_spread,
        "yearly_stability": compute_yearly_stability(daily_ic),
        "topk_head_realized_return_proxy": topk_proxy,
    }


def build_cross_split_summary(
    *,
    clean_model_keys: list[str],
    diagnoses: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for model_key in clean_model_keys:
        train_diag = diagnoses[f"{model_key}_train"]
        validation_diag = diagnoses[f"{model_key}_validation"]
        train_cov = train_diag.get("score_coverage")
        validation_cov = validation_diag.get("score_coverage")
        output[model_key] = {
            "train_score_coverage": train_cov,
            "validation_score_coverage": validation_cov,
            "score_coverage_difference_validation_minus_train": (
                validation_cov - train_cov
                if train_cov is not None and validation_cov is not None
                else None
            ),
        }
    return output


def model_snapshot(diag: dict[str, Any]) -> dict[str, Any]:
    return {
        "rank_ic": diag["rank_ic"]["mean"],
        "icir": diag["icir"],
        "top_bottom_spread": diag["top_bottom_spread"],
        "topk_head_realized_return_proxy": diag["topk_head_realized_return_proxy"][
            "mean_topk_forward_return"
        ],
        "topk_minus_nextk": diag["topk_head_realized_return_proxy"]["topk_minus_nextk"],
        "score_coverage": diag["score_coverage"],
    }


def delta(base: dict[str, Any], ref: dict[str, Any]) -> dict[str, Any]:
    return {
        "rank_ic_delta": (
            base["rank_ic"]["mean"] - ref["rank_ic"]["mean"]
            if base["rank_ic"]["mean"] is not None and ref["rank_ic"]["mean"] is not None
            else None
        ),
        "icir_delta": (
            base["icir"] - ref["icir"]
            if base["icir"] is not None and ref["icir"] is not None
            else None
        ),
        "top_bottom_spread_delta": (
            base["top_bottom_spread"] - ref["top_bottom_spread"]
            if base["top_bottom_spread"] is not None and ref["top_bottom_spread"] is not None
            else None
        ),
        "topk_head_realized_return_proxy_delta": (
            base["topk_head_realized_return_proxy"]["mean_topk_forward_return"]
            - ref["topk_head_realized_return_proxy"]["mean_topk_forward_return"]
            if base["topk_head_realized_return_proxy"]["mean_topk_forward_return"] is not None
            and ref["topk_head_realized_return_proxy"]["mean_topk_forward_return"] is not None
            else None
        ),
        "topk_minus_nextk_delta": (
            base["topk_head_realized_return_proxy"]["topk_minus_nextk"]
            - ref["topk_head_realized_return_proxy"]["topk_minus_nextk"]
            if base["topk_head_realized_return_proxy"]["topk_minus_nextk"] is not None
            and ref["topk_head_realized_return_proxy"]["topk_minus_nextk"] is not None
            else None
        ),
        "score_coverage_delta": (
            base["score_coverage"] - ref["score_coverage"]
            if base["score_coverage"] is not None and ref["score_coverage"] is not None
            else None
        ),
    }


def build_split_comparison(
    *,
    split_name: str,
    diagnoses: dict[str, dict[str, Any]],
    model_keys: list[str],
    reference_key: str,
) -> dict[str, Any]:
    models = {model_key: model_snapshot(diagnoses[f"{model_key}_{split_name}"]) for model_key in model_keys}
    output = {"models": models}
    for model_key in model_keys:
        if model_key == reference_key:
            continue
        output[f"{model_key}_vs_{reference_key}"] = delta(
            diagnoses[f"{model_key}_{split_name}"],
            diagnoses[f"{reference_key}_{split_name}"],
        )
    return output


def clean_has_model_layer_edge(train_diag: dict[str, Any], validation_diag: dict[str, Any]) -> bool:
    def rankic_icir_pass(diag: dict[str, Any]) -> bool:
        rank_ic_mean = diag["rank_ic"]["mean"]
        icir = diag["icir"]
        rank_ic_std = diag["rank_ic"]["std"]
        if rank_ic_mean is None or rank_ic_mean <= 0:
            return False
        if icir is not None:
            return icir > 0
        return rank_ic_std in (None, 0.0)

    return (
        rankic_icir_pass(train_diag)
        and rankic_icir_pass(validation_diag)
        and validation_diag["top_bottom_spread"] is not None
        and validation_diag["top_bottom_spread"] > 0
    )


def clean_has_topk_head_quality(validation_diag: dict[str, Any]) -> bool:
    topk = validation_diag["topk_head_realized_return_proxy"]
    return (
        topk["mean_topk_forward_return"] is not None
        and topk["mean_topk_forward_return"] > 0
        and topk["topk_minus_nextk"] is not None
        and topk["topk_minus_nextk"] > 0
    )


def build_conclusion(
    *,
    diagnoses: dict[str, dict[str, Any]],
    cross_split_summary: dict[str, Any],
) -> dict[str, Any]:
    clean_results: dict[str, Any] = {}
    recommended_for_dry_run: list[str] = []
    for model_key in REQUIRED_CLEAN_MODEL_KEYS:
        train_diag = diagnoses[f"{model_key}_train"]
        validation_diag = diagnoses[f"{model_key}_validation"]
        has_edge = clean_has_model_layer_edge(train_diag, validation_diag)
        has_head_quality = clean_has_topk_head_quality(validation_diag)
        recommend_dry_run = has_edge and has_head_quality
        if recommend_dry_run:
            recommended_for_dry_run.append(model_key)
        clean_results[model_key] = {
            "has_model_layer_edge": has_edge,
            "has_topk_head_quality": has_head_quality,
            "recommend_same_contract_portfolio_dry_run_preparation": recommend_dry_run,
            "score_coverage_difference_validation_minus_train": cross_split_summary[model_key][
                "score_coverage_difference_validation_minus_train"
            ],
        }

    p98_validation = diagnoses["p98_conditional_reference_validation"]
    best_clean_key = max(
        REQUIRED_CLEAN_MODEL_KEYS,
        key=lambda key: (
            diagnoses[f"{key}_validation"]["rank_ic"]["mean"]
            if diagnoses[f"{key}_validation"]["rank_ic"]["mean"] is not None
            else float("-inf")
        ),
    )
    best_clean_validation = diagnoses[f"{best_clean_key}_validation"]

    can_replace_p98 = (
        clean_results[best_clean_key]["recommend_same_contract_portfolio_dry_run_preparation"]
        and best_clean_validation["rank_ic"]["mean"] is not None
        and p98_validation["rank_ic"]["mean"] is not None
        and best_clean_validation["rank_ic"]["mean"] >= p98_validation["rank_ic"]["mean"]
        and best_clean_validation["topk_head_realized_return_proxy"]["mean_topk_forward_return"] is not None
        and p98_validation["topk_head_realized_return_proxy"]["mean_topk_forward_return"] is not None
        and best_clean_validation["topk_head_realized_return_proxy"]["mean_topk_forward_return"]
        >= p98_validation["topk_head_realized_return_proxy"]["mean_topk_forward_return"]
        and best_clean_validation["topk_head_realized_return_proxy"]["topk_minus_nextk"] is not None
        and p98_validation["topk_head_realized_return_proxy"]["topk_minus_nextk"] is not None
        and best_clean_validation["topk_head_realized_return_proxy"]["topk_minus_nextk"]
        >= p98_validation["topk_head_realized_return_proxy"]["topk_minus_nextk"]
    )
    can_parallel_p98 = bool(recommended_for_dry_run)

    if can_replace_p98:
        family_position = "replace_or_parallel_p98_conditional_baseline"
    elif can_parallel_p98:
        family_position = "parallel_only_to_p98_conditional_baseline"
    else:
        family_position = "not_ready_to_replace_or_parallel_p98_conditional_baseline"

    if recommended_for_dry_run:
        recommendation = "prepare_same_contract_portfolio_dry_run_for_selected_clean_baselines_only"
        recommendation_text = (
            "At least one clean baseline retains train/validation model-layer edge and positive validation TopK head quality. "
            "Those clean baselines may proceed to same-contract portfolio dry-run preparation only as clean candidates."
        )
    else:
        recommendation = "do_not_prepare_same_contract_portfolio_dry_run_yet"
        recommendation_text = (
            "No clean baseline clears both validation model-layer edge and validation TopK head quality at the same time. "
            "Do not prepare same-contract portfolio dry-run yet."
        )

    return {
        "clean_baseline_results": clean_results,
        "recommended_same_contract_portfolio_dry_run_candidates": recommended_for_dry_run,
        "best_clean_validation_rankic_candidate": best_clean_key,
        "can_replace_p98_conditional_baseline": can_replace_p98,
        "can_parallel_p98_conditional_baseline": can_parallel_p98,
        "clean_baseline_family_position_vs_p98_conditional_baseline": family_position,
        "conditional_reference_disclosure": {
            "p98_conditional_reference_status": "conditional_reference_only",
            "multi_equal_weight_v1_conditional_reference_status": "conditional_reference_only",
        },
        "recommendation": recommendation,
        "recommendation_text": recommendation_text,
        "caveat": (
            "This is model-layer / score-layer diagnosis only. It is not a portfolio, holdings, backtest, OOS, "
            "or formal metrics/readout package, and it is not a strategy-effectiveness conclusion."
        ),
    }


def build_score_layer_inputs(
    *,
    score_inputs: dict[str, dict[str, Path | None]],
    clean_audits: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for model_key, spec in MODEL_SPECS.items():
        entry: dict[str, Any] = {
            "candidate_scheme_id": spec["candidate_scheme_id"],
            "status": spec["status"],
            "conditional_reference": spec["conditional_reference"],
            "score_direction": spec["score_direction"],
            "score_path": score_inputs[model_key]["scores"].as_posix(),  # type: ignore[union-attr]
        }
        if spec["audit_required"]:
            audit = clean_audits[model_key]
            entry.update(
                {
                    "audit_path": score_inputs[model_key]["audit"].as_posix(),  # type: ignore[union-attr]
                    "row_count": extract_summary_count(audit, "row_count"),
                    "null_score_count": extract_summary_count(audit, "null_score_count"),
                    "nonfinite_score_count": extract_summary_count(audit, "nonfinite_score_count"),
                    "p98_used": audit.get("p98_used"),
                    "label_diagnostics_used": audit.get("label_diagnostics_used"),
                    "frozen_test_accessed": audit.get("frozen_test_accessed"),
                    "d0_visibility_audit": audit.get("d0_visibility_audit"),
                    "leakage_audit": audit.get("leakage_audit"),
                    "liquidity_field_used": audit.get("liquidity_field_used"),
                    "volume_field_source": audit.get("volume_field_source"),
                    "amount_field_source": audit.get("amount_field_source"),
                }
            )
        output[model_key] = entry
    return output


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fmt_num(value: float | None) -> str:
    return "null" if value is None else f"{value:.6f}"


def render_model_section(diag: dict[str, Any], coverage_diff: float | None) -> list[str]:
    topk = diag["topk_head_realized_return_proxy"]
    lines = [
        f"### {diag['model_label']} — {diag['split']}",
        "",
        f"- Candidate: `{diag['candidate_scheme_id']}`",
        f"- Status: `{diag['status']}`",
        f"- Conditional reference: `{diag['conditional_reference']}`",
        f"- Score direction: `{diag['score_direction']}`",
        f"- Coverage: `{diag['score_coverage']:.6f}`",
        f"- Coverage difference vs opposite split: `{fmt_num(coverage_diff)}`",
        f"- RankIC: `{fmt_num(diag['rank_ic']['mean'])}`",
        f"- ICIR: `{fmt_num(diag['icir'])}`",
        f"- Top-bottom spread: `{fmt_num(diag['top_bottom_spread'])}`",
        f"- TopK head realized return proxy: `{fmt_num(topk['mean_topk_forward_return'])}`",
        f"- TopK minus nextK: `{fmt_num(topk['topk_minus_nextk'])}`",
        "",
        "**Decile Forward Returns (1=top, 10=bottom):**",
    ]
    for row in diag["decile_forward_returns"]:
        lines.append(
            f"- Decile {row['decile']}: mean=`{fmt_num(row['mean_forward_return'])}`, n_days=`{row['n_days']}`"
        )
    lines.extend(["", "**Yearly Stability:**"])
    for row in diag["yearly_stability"]:
        lines.append(
            f"- {row['year']}: RankIC=`{fmt_num(row['rank_ic_mean'])}`, ICIR=`{fmt_num(row['rank_ic_ir'])}`, n_days=`{row['n_days']}`"
        )
    lines.append("")
    return lines


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# clean baseline family model edge diagnosis",
        "",
        f"> **{DIAGNOSIS_LABEL}**",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        "## 1. Scope",
        "",
        "- This is score-layer / model-layer diagnosis only.",
        "- This is not a portfolio, holdings, backtest, or formal metrics/readout package.",
        "- This does not read frozen test.",
        "- This does not claim strategy effectiveness.",
        "",
        "## 2. Score-Layer Inputs",
        "",
    ]
    for model_key in REQUIRED_CLEAN_MODEL_KEYS:
        meta = payload["score_layer_inputs"][model_key]
        lines.extend(
            [
                f"### {model_key}",
                "",
                f"- score path: `{meta['score_path']}`",
                f"- audit path: `{meta['audit_path']}`",
                f"- row_count: `{meta['row_count']}`",
                f"- null_score_count: `{meta['null_score_count']}`",
                f"- nonfinite_score_count: `{meta['nonfinite_score_count']}`",
                f"- p98_used: `{meta['p98_used']}`",
                f"- label_diagnostics_used: `{meta['label_diagnostics_used']}`",
                f"- frozen_test_accessed: `{meta['frozen_test_accessed']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## 3. Conditional References",
            "",
            "- `p98 conditional baseline` is included as `conditional_reference_only`.",
            "- `multi_equal_weight_v1 conditional baseline` is included as `conditional_reference_only`.",
            "",
            "## 4. Train Diagnostics",
            "",
        ]
    )
    for model_key in REQUIRED_CLEAN_MODEL_KEYS + CONDITIONAL_REFERENCE_KEYS:
        coverage_diff = payload["cross_split_summary"].get(model_key, {}).get(
            "score_coverage_difference_validation_minus_train"
        )
        lines.extend(render_model_section(payload["diagnostics"][f"{model_key}_train"], coverage_diff))
    lines.extend(["## 5. Validation Diagnostics", ""])
    for model_key in REQUIRED_CLEAN_MODEL_KEYS + CONDITIONAL_REFERENCE_KEYS:
        coverage_diff = payload["cross_split_summary"].get(model_key, {}).get(
            "score_coverage_difference_validation_minus_train"
        )
        lines.extend(
            render_model_section(payload["diagnostics"][f"{model_key}_validation"], coverage_diff)
        )
    lines.extend(
        [
            "## 6. Conclusion",
            "",
            f"- recommendation: `{payload['conclusion']['recommendation']}`",
            f"- recommended_same_contract_portfolio_dry_run_candidates: `{payload['conclusion']['recommended_same_contract_portfolio_dry_run_candidates']}`",
            f"- can_replace_p98_conditional_baseline: `{payload['conclusion']['can_replace_p98_conditional_baseline']}`",
            f"- can_parallel_p98_conditional_baseline: `{payload['conclusion']['can_parallel_p98_conditional_baseline']}`",
            f"- clean_baseline_family_position_vs_p98_conditional_baseline: `{payload['conclusion']['clean_baseline_family_position_vs_p98_conditional_baseline']}`",
            "",
            payload["conclusion"]["recommendation_text"],
            "",
            payload["conclusion"]["caveat"],
            "",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_diagnosis(args: argparse.Namespace) -> dict[str, Any]:
    score_inputs = build_score_inputs(args)
    for model_key, paths in score_inputs.items():
        ensure_exists(paths["scores"], f"{model_key} scores")
        if MODEL_SPECS[model_key]["audit_required"]:
            ensure_exists(paths["audit"], f"{model_key} audit")
    ensure_exists(args.label_panel, "label panel")
    ensure_exists(args.split_panel, "split panel")

    clean_audits: dict[str, dict[str, Any]] = {}
    for model_key in REQUIRED_CLEAN_MODEL_KEYS:
        audit = load_json(score_inputs[model_key]["audit"], f"{model_key} audit")  # type: ignore[arg-type]
        ensure_clean_audit_passes(audit, model_key)
        clean_audits[model_key] = audit

    con = duckdb.connect()
    try:
        build_views(con, score_inputs=score_inputs, args=args)
        model_keys = REQUIRED_CLEAN_MODEL_KEYS + CONDITIONAL_REFERENCE_KEYS
        diagnoses: dict[str, dict[str, Any]] = {}
        for split_name, split_flag in [("train", "train_flag"), ("validation", "validation_flag")]:
            eligible_labeled_rows = int(
                con.execute(f"SELECT COUNT(*) FROM comparison_t WHERE {split_flag}").fetchone()[0]
            )
            for model_key in model_keys:
                diagnoses[f"{model_key}_{split_name}"] = diagnose_model(
                    con,
                    model_key=model_key,
                    split_name=split_name,
                    split_flag=split_flag,
                    raw_score_col=f"{model_key}_raw_score",
                    effective_score_col=f"{model_key}_effective_score",
                    eligible_labeled_rows=eligible_labeled_rows,
                    topk=args.topk,
                )
    finally:
        con.close()

    cross_split_summary = build_cross_split_summary(
        clean_model_keys=REQUIRED_CLEAN_MODEL_KEYS,
        diagnoses=diagnoses,
    )
    cross_model_comparison = {
        split_name: build_split_comparison(
            split_name=split_name,
            diagnoses=diagnoses,
            model_keys=REQUIRED_CLEAN_MODEL_KEYS + CONDITIONAL_REFERENCE_KEYS,
            reference_key="p98_conditional_reference",
        )
        for split_name in ("train", "validation")
    }
    conclusion = build_conclusion(
        diagnoses=diagnoses,
        cross_split_summary=cross_split_summary,
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "diagnosis_label": DIAGNOSIS_LABEL,
        "diagnostic_only": True,
        "training_performed": False,
        "portfolio_run_executed": False,
        "formal_metrics_generated": False,
        "frozen_test_accessed": False,
        "topk": args.topk,
        "inputs": {
            model_key: {
                "score_path": score_inputs[model_key]["scores"].as_posix(),  # type: ignore[union-attr]
                "audit_path": (
                    score_inputs[model_key]["audit"].as_posix()  # type: ignore[union-attr]
                    if score_inputs[model_key]["audit"] is not None
                    else None
                ),
            }
            for model_key in MODEL_SPECS
        }
        | {
            "label_panel": args.label_panel.as_posix(),
            "split_panel": args.split_panel.as_posix(),
        },
        "score_layer_inputs": build_score_layer_inputs(
            score_inputs=score_inputs,
            clean_audits=clean_audits,
        ),
        "models_compared": MODEL_SPECS,
        "diagnostics": diagnoses,
        "cross_split_summary": cross_split_summary,
        "cross_model_comparison": cross_model_comparison,
        "conclusion": conclusion,
    }


def main() -> None:
    args = parse_args()
    payload = run_diagnosis(args)
    write_json(args.output_json, payload)
    write_markdown(args.output_md, payload)


if __name__ == "__main__":
    main()
