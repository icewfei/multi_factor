#!/opt/anaconda3/envs/quant_trade/bin/python
"""
MODEL EDGE DIAGNOSIS ONLY — NOT A BACKTEST — NOT A PORTFOLIO READOUT

Compare nonlinear challenger v3 adjusted scores against:
- manifest-bound confirmed5 raw scores
- nonlinear challenger v2 adjusted scores
- baseline multi_equal_weight_v1 scores

This script:
- does NOT read frozen test
- does NOT generate holdings, portfolio, backtest_daily, metrics, or readout
- does NOT modify any score formula or hyperparameter
- writes diagnosis JSON/MD only
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


ROOT = Path("/Users/wy/MiscProject/multi_factor")
DEFAULT_V3_SCORES = Path("/private/tmp/nlc_v3_real_trainval_score_gate_20260512/out/model_scores_D0.parquet")
DEFAULT_V3_AUDIT = Path("/private/tmp/nlc_v3_real_trainval_score_gate_20260512/out/score_builder_audit.json")
DEFAULT_V2_SCORES = Path(
    "/private/tmp/local_nlc_v2_confirmed5_locked_cs_volatility_discount_20260509/model_scores_D0.parquet"
)
DEFAULT_V2_AUDIT = Path(
    "/private/tmp/local_nlc_v2_confirmed5_locked_cs_volatility_discount_20260509/score_transform_audit.json"
)
DEFAULT_BASELINE_SCORES = ROOT / "artifacts/run_state/exploratory_multi_signal_composite_v1/model_scores_D0_multi.parquet"
DEFAULT_LABEL_PANEL = ROOT / "artifacts/run_state/project_panels_research_trainval_20211231_20260429/project_label_panel.parquet"
DEFAULT_SPLIT_PANEL = ROOT / "artifacts/run_state/project_panels_research_trainval_20211231_20260429/dataset_split_daily.parquet"
DEFAULT_SOURCE_BINDING = ROOT / "configs/nonlinear_challenger_v3/source_bindings/v3_score_source_binding.json"
DEFAULT_OUTPUT_JSON = Path("/private/tmp/nonlinear_challenger_v3_model_edge_diagnosis.json")
DEFAULT_OUTPUT_MD = Path("/private/tmp/nonlinear_challenger_v3_model_edge_diagnosis.md")

EXPECTED_V3_CANDIDATE = "nlc_v3_confirmed5_locked_topk_head_quality_conditioned_capital_deployment_lgbm_depth3_seed42"
EXPECTED_V2_CANDIDATE = "nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42"
EXPECTED_CONFIRMED5_CANDIDATE = "nlc_v1_confirmed5_lgbm_depth3_seed42"
EXPECTED_BASELINE_CANDIDATE = "multi_equal_weight_v1"
VALIDATION_RANKIC_DAMAGE_THRESHOLD = -0.005
VALIDATION_ICIR_DAMAGE_THRESHOLD = -0.05
DIAGNOSIS_LABEL = (
    "MODEL EDGE DIAGNOSIS ONLY — NOT A BACKTEST — "
    "NOT A PORTFOLIO READOUT — DO NOT INTERPRET AS STRATEGY EFFECTIVENESS"
)


class DiagnosisError(Exception):
    """Raised when the v3 model-edge diagnosis cannot be completed safely."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose nonlinear challenger v3 model-layer edge only.")
    parser.add_argument("--v3-scores", type=Path, default=DEFAULT_V3_SCORES, help="Path to v3 model_scores_D0 parquet.")
    parser.add_argument("--v3-audit", type=Path, default=DEFAULT_V3_AUDIT, help="Path to v3 score_builder_audit.json.")
    parser.add_argument(
        "--confirmed5-scores",
        type=Path,
        default=None,
        help="Optional override for confirmed5 raw score parquet. Defaults to v3_audit.base_score_input_path.",
    )
    parser.add_argument("--v2-scores", type=Path, default=DEFAULT_V2_SCORES, help="Path to v2 model_scores_D0 parquet.")
    parser.add_argument("--v2-audit", type=Path, default=DEFAULT_V2_AUDIT, help="Path to v2 score_transform_audit.json.")
    parser.add_argument(
        "--baseline-scores",
        type=Path,
        default=DEFAULT_BASELINE_SCORES,
        help="Path to baseline multi-score parquet containing multi_equal_weight_v1.",
    )
    parser.add_argument("--label-panel", type=Path, default=DEFAULT_LABEL_PANEL, help="Path to project_label_panel.parquet.")
    parser.add_argument("--split-panel", type=Path, default=DEFAULT_SPLIT_PANEL, help="Path to dataset_split_daily.parquet.")
    parser.add_argument(
        "--source-binding",
        type=Path,
        default=DEFAULT_SOURCE_BINDING,
        help="Path to the nonlinear challenger v3 source binding contract JSON.",
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON, help="Output diagnosis JSON path.")
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD, help="Output diagnosis Markdown path.")
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


def require_field(payload: dict[str, Any], field: str, label: str) -> Any:
    if field not in payload:
        raise DiagnosisError(f"{label} missing required field: {field}")
    return payload[field]


def sql_path(path: Path) -> str:
    return path.as_posix().replace("'", "''")


def resolve_confirmed5_scores_path(args: argparse.Namespace, v3_audit: dict[str, Any]) -> Path:
    if args.confirmed5_scores is not None:
        return args.confirmed5_scores
    path_value = require_field(v3_audit, "base_score_input_path", "v3_audit")
    confirmed5_path = Path(path_value)
    if not confirmed5_path.is_absolute():
        confirmed5_path = ROOT / confirmed5_path
    return confirmed5_path


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return float(value)


def mean_std_tstat(values: pd.Series) -> tuple[float | None, float | None, float | None]:
    clean = values.dropna()
    if clean.empty:
        return None, None, None
    mean_value = float(clean.mean())
    std_value = safe_float(clean.std())
    if std_value is None or std_value == 0.0:
        return mean_value, std_value, None
    t_stat = float(mean_value / (std_value / math.sqrt(len(clean))))
    return mean_value, std_value, t_stat


def build_views(
    con: duckdb.DuckDBPyConnection,
    *,
    v3_scores_path: Path,
    confirmed5_scores_path: Path,
    v2_scores_path: Path,
    baseline_scores_path: Path,
    label_panel_path: Path,
    split_panel_path: Path,
) -> None:
    con.execute(
        f"""
        CREATE OR REPLACE TEMP VIEW v3_t AS
        SELECT
            snapshot_id,
            instrument,
            signal_date,
            candidate_scheme_id,
            raw_score_D0,
            adjusted_score_D0,
            model_score_D0,
            provisional_topk_member
        FROM read_parquet('{sql_path(v3_scores_path)}')
        WHERE candidate_scheme_id = '{EXPECTED_V3_CANDIDATE}'
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TEMP VIEW confirmed5_t AS
        SELECT
            snapshot_id,
            instrument,
            signal_date,
            candidate_scheme_id,
            model_score_D0 AS confirmed5_raw_score
        FROM read_parquet('{sql_path(confirmed5_scores_path)}')
        WHERE candidate_scheme_id = '{EXPECTED_CONFIRMED5_CANDIDATE}'
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TEMP VIEW v2_t AS
        SELECT
            snapshot_id,
            instrument,
            signal_date,
            candidate_scheme_id,
            adjusted_score_D0 AS v2_adjusted_score
        FROM read_parquet('{sql_path(v2_scores_path)}')
        WHERE candidate_scheme_id = '{EXPECTED_V2_CANDIDATE}'
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TEMP VIEW baseline_t AS
        SELECT
            instrument,
            signal_date,
            candidate_scheme_id,
            model_score_D0 AS baseline_score
        FROM read_parquet('{sql_path(baseline_scores_path)}')
        WHERE candidate_scheme_id = '{EXPECTED_BASELINE_CANDIDATE}'
        """
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
        FROM read_parquet('{sql_path(label_panel_path)}')
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
        FROM read_parquet('{sql_path(split_panel_path)}')
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TEMP VIEW comparison_t AS
        SELECT
            l.snapshot_id,
            l.instrument,
            l.signal_date,
            l.forward_return_5d,
            s.split_bucket,
            s.train_flag,
            s.validation_flag,
            v3.raw_score_D0 AS v3_raw_score,
            v3.adjusted_score_D0 AS v3_adjusted_score,
            v3.model_score_D0 AS v3_model_score,
            v3.provisional_topk_member,
            c.confirmed5_raw_score,
            v2.v2_adjusted_score,
            b.baseline_score
        FROM label_t l
        INNER JOIN split_t s
            ON l.snapshot_id = s.snapshot_id
           AND l.instrument = s.instrument
           AND l.signal_date = s.signal_date
        LEFT JOIN v3_t v3
            ON l.snapshot_id = v3.snapshot_id
           AND l.instrument = v3.instrument
           AND l.signal_date = v3.signal_date
        LEFT JOIN confirmed5_t c
            ON l.snapshot_id = c.snapshot_id
           AND l.instrument = c.instrument
           AND l.signal_date = c.signal_date
        LEFT JOIN v2_t v2
            ON l.snapshot_id = v2.snapshot_id
           AND l.instrument = v2.instrument
           AND l.signal_date = v2.signal_date
        LEFT JOIN baseline_t b
            ON l.instrument = b.instrument
           AND l.signal_date = b.signal_date
        WHERE l.label_defined
          AND (s.train_flag OR s.validation_flag)
        """
    )


def fetch_daily_ic(
    con: duckdb.DuckDBPyConnection,
    *,
    split_flag: str,
    score_col: str,
) -> pd.DataFrame:
    return con.execute(
        f"""
        WITH ranked AS (
            SELECT
                signal_date,
                rank() OVER (PARTITION BY signal_date ORDER BY {score_col} ASC, instrument ASC) AS score_rank,
                rank() OVER (PARTITION BY signal_date ORDER BY forward_return_5d ASC, instrument ASC) AS label_rank
            FROM comparison_t
            WHERE {split_flag}
              AND {score_col} IS NOT NULL
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
    score_col: str,
) -> list[dict[str, Any]]:
    rows = con.execute(
        f"""
        WITH ranked AS (
            SELECT
                signal_date,
                ntile(10) OVER (PARTITION BY signal_date ORDER BY {score_col} DESC, instrument ASC) AS decile_desc,
                forward_return_5d
            FROM comparison_t
            WHERE {split_flag}
              AND {score_col} IS NOT NULL
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
    model_key: str,
    score_col: str,
    topk: int,
) -> dict[str, Any]:
    if model_key == "v3":
        daily = con.execute(
            f"""
            WITH ranked AS (
                SELECT
                    signal_date,
                    instrument,
                    forward_return_5d,
                    provisional_topk_member,
                    row_number() OVER (PARTITION BY signal_date ORDER BY v3_raw_score DESC, instrument ASC) AS raw_rank
                FROM comparison_t
                WHERE {split_flag}
                  AND v3_raw_score IS NOT NULL
            )
            SELECT
                signal_date,
                AVG(CASE WHEN provisional_topk_member THEN forward_return_5d END) AS topk_mean_return,
                AVG(CASE WHEN raw_rank BETWEEN {topk + 1} AND {2 * topk} THEN forward_return_5d END) AS nextk_mean_return,
                SUM(CASE WHEN provisional_topk_member THEN 1 ELSE 0 END) AS selected_topk_rows,
                SUM(CASE WHEN raw_rank BETWEEN {topk + 1} AND {2 * topk} THEN 1 ELSE 0 END) AS nextk_rows
            FROM ranked
            GROUP BY signal_date
            HAVING SUM(CASE WHEN provisional_topk_member THEN 1 ELSE 0 END) = {topk}
               AND SUM(CASE WHEN raw_rank BETWEEN {topk + 1} AND {2 * topk} THEN 1 ELSE 0 END) = {topk}
            ORDER BY signal_date
            """
        ).fetchdf()
        ranking_mode = "provisional_topk_member_with_raw_score_next_bucket"
    else:
        daily = con.execute(
            f"""
            WITH ranked AS (
                SELECT
                    signal_date,
                    instrument,
                    forward_return_5d,
                    row_number() OVER (PARTITION BY signal_date ORDER BY {score_col} DESC, instrument ASC) AS score_rank
                FROM comparison_t
                WHERE {split_flag}
                  AND {score_col} IS NOT NULL
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
        ranking_mode = "score_desc_topk_and_nextk"

    if daily.empty:
        return {
            "topk": topk,
            "ranking_mode": ranking_mode,
            "n_days": 0,
            "selected_topk_rows": 0,
            "mean_topk_forward_return": None,
            "std_topk_forward_return": None,
            "positive_day_pct": None,
            "mean_rank11_20_forward_return": None,
            "topk_minus_rank11_20": None,
            "topk_mean_t_stat": None,
            "topk_minus_rank11_20_t_stat": None,
        }

    topk_mean, topk_std, topk_t_stat = mean_std_tstat(daily["topk_mean_return"])
    spread_series = daily["topk_mean_return"] - daily["nextk_mean_return"]
    spread_mean, _, spread_t_stat = mean_std_tstat(spread_series)
    return {
        "topk": topk,
        "ranking_mode": ranking_mode,
        "n_days": int(len(daily)),
        "selected_topk_rows": int(daily["selected_topk_rows"].sum()),
        "mean_topk_forward_return": topk_mean,
        "std_topk_forward_return": topk_std,
        "positive_day_pct": float((daily["topk_mean_return"] > 0).mean()),
        "mean_rank11_20_forward_return": float(daily["nextk_mean_return"].mean()),
        "topk_minus_rank11_20": spread_mean,
        "topk_mean_t_stat": topk_t_stat,
        "topk_minus_rank11_20_t_stat": spread_t_stat,
    }


def compute_yearly_stability(daily_ic: pd.DataFrame) -> list[dict[str, Any]]:
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
                "rank_ic_ir": (mean_value / std_value) if mean_value is not None and std_value not in (None, 0.0) else None,
                "n_days": int(len(group)),
                "positive_ic_pct": float((group["rank_ic"] > 0).mean()),
            }
        )
    return output


def diagnose_model(
    con: duckdb.DuckDBPyConnection,
    *,
    model_key: str,
    model_label: str,
    split_name: str,
    split_flag: str,
    score_col: str,
    eligible_labeled_rows: int,
    topk: int,
) -> dict[str, Any]:
    summary_row = con.execute(
        f"""
        SELECT
            COUNT({score_col}) AS scored_rows,
            COUNT(DISTINCT CASE WHEN {score_col} IS NOT NULL THEN signal_date END) AS n_signal_dates,
            COUNT(DISTINCT CASE WHEN {score_col} IS NOT NULL THEN instrument END) AS n_instruments,
            AVG({score_col}) AS mean_score,
            STDDEV_SAMP({score_col}) AS std_score,
            MIN({score_col}) AS min_score,
            quantile_cont({score_col}, 0.25) AS p25_score,
            quantile_cont({score_col}, 0.50) AS p50_score,
            quantile_cont({score_col}, 0.75) AS p75_score,
            MAX({score_col}) AS max_score
        FROM comparison_t
        WHERE {split_flag}
          AND {score_col} IS NOT NULL
        """
    ).fetchone()
    scored_rows = int(summary_row[0] or 0)
    score_coverage = (scored_rows / eligible_labeled_rows) if eligible_labeled_rows > 0 else None
    if scored_rows == 0:
        return {
            "model_key": model_key,
            "model_label": model_label,
            "split": split_name,
            "row_count": 0,
            "scored_rows": 0,
            "eligible_labeled_rows": eligible_labeled_rows,
            "score_coverage": score_coverage,
            "error": "No scored rows for split",
        }

    daily_ic = fetch_daily_ic(con, split_flag=split_flag, score_col=score_col)
    rank_ic_mean, rank_ic_std, rank_ic_t_stat = mean_std_tstat(daily_ic["rank_ic"]) if not daily_ic.empty else (None, None, None)
    icir = (rank_ic_mean / rank_ic_std) if rank_ic_mean is not None and rank_ic_std not in (None, 0.0) else None
    deciles = fetch_decile_returns(con, split_flag=split_flag, score_col=score_col)
    top_decile = next((row["mean_forward_return"] for row in deciles if row["decile"] == 1), None)
    bottom_decile = next((row["mean_forward_return"] for row in deciles if row["decile"] == 10), None)
    top_bottom_spread = (
        float(top_decile - bottom_decile)
        if top_decile is not None and bottom_decile is not None
        else None
    )
    topk_proxy = fetch_topk_head_proxy(con, split_flag=split_flag, model_key=model_key, score_col=score_col, topk=topk)

    diagnosis: dict[str, Any] = {
        "model_key": model_key,
        "model_label": model_label,
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
    if model_key == "v3":
        provisional_topk_rows = con.execute(
            f"""
            SELECT SUM(CASE WHEN provisional_topk_member THEN 1 ELSE 0 END)
            FROM comparison_t
            WHERE {split_flag}
              AND v3_raw_score IS NOT NULL
            """
        ).fetchone()[0]
        diagnosis["provisional_topk_rows"] = int(provisional_topk_rows or 0)
    return diagnosis


def build_coverage_summary(
    con: duckdb.DuckDBPyConnection,
    *,
    split_name: str,
    split_flag: str,
    diagnoses: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    eligible_labeled_rows = int(con.execute(f"SELECT COUNT(*) FROM comparison_t WHERE {split_flag}").fetchone()[0])
    v3_cov = diagnoses[f"v3_{split_name}"]["score_coverage"]
    confirmed5_cov = diagnoses[f"confirmed5_{split_name}"]["score_coverage"]
    v2_cov = diagnoses[f"v2_{split_name}"]["score_coverage"]
    baseline_cov = diagnoses[f"baseline_{split_name}"]["score_coverage"]
    return {
        "eligible_labeled_rows": eligible_labeled_rows,
        "v3_scored_rows": diagnoses[f"v3_{split_name}"]["scored_rows"],
        "confirmed5_scored_rows": diagnoses[f"confirmed5_{split_name}"]["scored_rows"],
        "v2_scored_rows": diagnoses[f"v2_{split_name}"]["scored_rows"],
        "baseline_scored_rows": diagnoses[f"baseline_{split_name}"]["scored_rows"],
        "v3_score_coverage": v3_cov,
        "confirmed5_score_coverage": confirmed5_cov,
        "v2_score_coverage": v2_cov,
        "baseline_score_coverage": baseline_cov,
        "score_coverage_difference": {
            "v3_minus_confirmed5": (v3_cov - confirmed5_cov) if v3_cov is not None and confirmed5_cov is not None else None,
            "v3_minus_v2": (v3_cov - v2_cov) if v3_cov is not None and v2_cov is not None else None,
            "v3_minus_baseline": (v3_cov - baseline_cov) if v3_cov is not None and baseline_cov is not None else None,
        },
    }


def build_split_comparison(
    *,
    split_name: str,
    diagnoses: dict[str, dict[str, Any]],
    coverage_summary: dict[str, Any],
) -> dict[str, Any]:
    v3 = diagnoses[f"v3_{split_name}"]
    confirmed5 = diagnoses[f"confirmed5_{split_name}"]
    v2 = diagnoses[f"v2_{split_name}"]
    baseline = diagnoses[f"baseline_{split_name}"]

    def model_snapshot(diag: dict[str, Any]) -> dict[str, Any]:
        return {
            "rank_ic": diag["rank_ic"]["mean"],
            "icir": diag["icir"],
            "top_bottom_spread": diag["top_bottom_spread"],
            "topk_head_realized_return_proxy": diag["topk_head_realized_return_proxy"]["mean_topk_forward_return"],
            "topk_minus_rank11_20": diag["topk_head_realized_return_proxy"]["topk_minus_rank11_20"],
            "score_coverage": diag["score_coverage"],
        }

    def delta(base: dict[str, Any], ref: dict[str, Any]) -> dict[str, Any]:
        return {
            "rank_ic_delta": (
                base["rank_ic"]["mean"] - ref["rank_ic"]["mean"]
                if base["rank_ic"]["mean"] is not None and ref["rank_ic"]["mean"] is not None
                else None
            ),
            "icir_delta": (base["icir"] - ref["icir"]) if base["icir"] is not None and ref["icir"] is not None else None,
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
            "topk_minus_rank11_20_delta": (
                base["topk_head_realized_return_proxy"]["topk_minus_rank11_20"]
                - ref["topk_head_realized_return_proxy"]["topk_minus_rank11_20"]
                if base["topk_head_realized_return_proxy"]["topk_minus_rank11_20"] is not None
                and ref["topk_head_realized_return_proxy"]["topk_minus_rank11_20"] is not None
                else None
            ),
        }

    return {
        "models": {
            "v3": model_snapshot(v3),
            "confirmed5": model_snapshot(confirmed5),
            "v2": model_snapshot(v2),
            "baseline": model_snapshot(baseline),
        },
        "v3_vs_confirmed5": delta(v3, confirmed5),
        "v3_vs_v2": delta(v3, v2),
        "v3_vs_baseline": delta(v3, baseline),
        "score_coverage_difference": coverage_summary["score_coverage_difference"],
    }


def build_conclusion(
    *,
    split_comparisons: dict[str, dict[str, Any]],
    v3_audit: dict[str, Any],
    v2_audit: dict[str, Any],
    source_binding: dict[str, Any],
    temporary_conditioning_source: bool,
) -> dict[str, Any]:
    validation = split_comparisons["validation"]
    v3_vs_confirmed5 = validation["v3_vs_confirmed5"]
    v3_vs_v2 = validation["v3_vs_v2"]

    materially_worse_vs_confirmed5 = False
    materially_worse_vs_v2 = False
    evidence: list[str] = []

    if v3_vs_confirmed5["rank_ic_delta"] is not None and v3_vs_confirmed5["rank_ic_delta"] < VALIDATION_RANKIC_DAMAGE_THRESHOLD:
        materially_worse_vs_confirmed5 = True
        evidence.append(
            "v3 validation RankIC is materially below confirmed5: "
            f"delta={v3_vs_confirmed5['rank_ic_delta']:+.6f} < {VALIDATION_RANKIC_DAMAGE_THRESHOLD:+.6f}"
        )
    if v3_vs_confirmed5["icir_delta"] is not None and v3_vs_confirmed5["icir_delta"] < VALIDATION_ICIR_DAMAGE_THRESHOLD:
        materially_worse_vs_confirmed5 = True
        evidence.append(
            "v3 validation ICIR is materially below confirmed5: "
            f"delta={v3_vs_confirmed5['icir_delta']:+.6f} < {VALIDATION_ICIR_DAMAGE_THRESHOLD:+.6f}"
        )
    if v3_vs_v2["rank_ic_delta"] is not None and v3_vs_v2["rank_ic_delta"] < VALIDATION_RANKIC_DAMAGE_THRESHOLD:
        materially_worse_vs_v2 = True
        evidence.append(
            "v3 validation RankIC is materially below v2: "
            f"delta={v3_vs_v2['rank_ic_delta']:+.6f} < {VALIDATION_RANKIC_DAMAGE_THRESHOLD:+.6f}"
        )
    if v3_vs_v2["icir_delta"] is not None and v3_vs_v2["icir_delta"] < VALIDATION_ICIR_DAMAGE_THRESHOLD:
        materially_worse_vs_v2 = True
        evidence.append(
            "v3 validation ICIR is materially below v2: "
            f"delta={v3_vs_v2['icir_delta']:+.6f} < {VALIDATION_ICIR_DAMAGE_THRESHOLD:+.6f}"
        )

    coverage_delta = validation["score_coverage_difference"]["v3_minus_confirmed5"]
    if coverage_delta is not None:
        evidence.append(f"Validation score coverage delta vs confirmed5: {coverage_delta:+.6f}")

    head_proxy_delta_vs_confirmed5 = v3_vs_confirmed5["topk_head_realized_return_proxy_delta"]
    head_proxy_delta_vs_v2 = v3_vs_v2["topk_head_realized_return_proxy_delta"]
    head_proxy_delta_vs_baseline = validation["v3_vs_baseline"]["topk_head_realized_return_proxy_delta"]
    inherits_confirmed5_raw_head = v3_audit.get("base_score_source") == "confirmed5_raw_score_D0"

    if head_proxy_delta_vs_confirmed5 is not None:
        evidence.append(f"Validation TopK head proxy delta vs confirmed5: {head_proxy_delta_vs_confirmed5:+.6f}")
    if head_proxy_delta_vs_v2 is not None:
        evidence.append(f"Validation TopK head proxy delta vs v2: {head_proxy_delta_vs_v2:+.6f}")
    if head_proxy_delta_vs_baseline is not None:
        evidence.append(f"Validation TopK head proxy delta vs baseline: {head_proxy_delta_vs_baseline:+.6f}")

    materially_worse = materially_worse_vs_confirmed5 or materially_worse_vs_v2
    if inherits_confirmed5_raw_head:
        evidence.append(
            "v3 provisional TopK head inherits the manifest-bound confirmed5 raw ordering; "
            "any labeled-overlap proxy delta versus confirmed5 is not treated as substantive head-selection improvement."
        )

    if materially_worse:
        recommendation = "do_not_recommend_portfolio_dry_run"
        recommendation_text = (
            "v3 adjusted_score materially weakens validation model-layer edge versus confirmed5 and/or v2. "
            "Do not advance to portfolio dry-run from this score-layer package."
        )
    elif temporary_conditioning_source:
        recommendation = "conditional_portfolio_dry_run_only_after_formal_source_resolution"
        recommendation_text = (
            "v3 does not show material model-layer deterioration under the declared thresholds, but the conditioning source "
            "is still a temporary gate artifact. Portfolio dry-run should only be considered after the source is formalized "
            "or that temporary dependency is explicitly accepted for a one-off gate check."
        )
    else:
        recommendation = "eligible_for_portfolio_dry_run"
        recommendation_text = (
            "v3 does not show material model-layer deterioration under the declared thresholds. "
            "Portfolio dry-run may be considered next, subject to unchanged execution and portfolio guardrails."
        )

    return {
        "materially_worse_vs_confirmed5": materially_worse_vs_confirmed5,
        "materially_worse_vs_v2": materially_worse_vs_v2,
        "materially_worse_overall": materially_worse,
        "topk_head_quality_improved_vs_confirmed5": (
            False
            if inherits_confirmed5_raw_head
            else head_proxy_delta_vs_confirmed5 is not None and head_proxy_delta_vs_confirmed5 > 0
        ),
        "topk_head_quality_improved_vs_v2": head_proxy_delta_vs_v2 is not None and head_proxy_delta_vs_v2 > 0,
        "topk_head_quality_improved_vs_baseline": head_proxy_delta_vs_baseline is not None and head_proxy_delta_vs_baseline > 0,
        "inherits_confirmed5_raw_head": inherits_confirmed5_raw_head,
        "evaluation_thresholds": {
            "validation_rankic_damage_threshold": VALIDATION_RANKIC_DAMAGE_THRESHOLD,
            "validation_icir_damage_threshold": VALIDATION_ICIR_DAMAGE_THRESHOLD,
        },
        "v3_provisional_topk_rows_total": v3_audit.get("provisional_topk_rows"),
        "v2_raw_input_null_score_rows": v2_audit.get("raw_input_null_score_rows"),
        "temporary_conditioning_source": temporary_conditioning_source,
        "conditioning_source_path": v3_audit.get("conditioning_source_path"),
        "source_binding_id": source_binding.get("source_binding_id"),
        "evidence": evidence,
        "recommendation": recommendation,
        "recommendation_text": recommendation_text,
        "caveat": (
            "This is model-layer / score-layer diagnosis only. It is not a portfolio, holdings, backtest, OOS, or formal metrics/readout package."
        ),
    }


def render_diagnosis_section(diag: dict[str, Any]) -> list[str]:
    if "error" in diag:
        return [f"### {diag['model_label']} — {diag['split']}", "", f"- Error: {diag['error']}", ""]

    topk = diag["topk_head_realized_return_proxy"]
    lines = [
        f"### {diag['model_label']} — {diag['split']}",
        "",
        f"- Scored rows: `{diag['scored_rows']}`",
        f"- Eligible labeled rows: `{diag['eligible_labeled_rows']}`",
        f"- Score coverage: `{diag['score_coverage']:.6f}`",
        f"- Signal dates: `{diag['n_signal_dates']}`",
        f"- RankIC mean: `{diag['rank_ic']['mean']:.6f}`" if diag["rank_ic"]["mean"] is not None else "- RankIC mean: `null`",
        f"- ICIR: `{diag['icir']:.6f}`" if diag["icir"] is not None else "- ICIR: `null`",
        f"- Top-bottom spread (top decile minus bottom decile): `{diag['top_bottom_spread']:.6f}`"
        if diag["top_bottom_spread"] is not None
        else "- Top-bottom spread (top decile minus bottom decile): `null`",
        f"- TopK head realized return proxy mean: `{topk['mean_topk_forward_return']:.6f}`"
        if topk["mean_topk_forward_return"] is not None
        else "- TopK head realized return proxy mean: `null`",
        f"- TopK minus rank11_20: `{topk['topk_minus_rank11_20']:.6f}`"
        if topk["topk_minus_rank11_20"] is not None
        else "- TopK minus rank11_20: `null`",
    ]
    if "provisional_topk_rows" in diag:
        lines.append(f"- provisional_topk_rows: `{diag['provisional_topk_rows']}`")
    lines.extend(["", "**Decile Forward Returns (1=top, 10=bottom):**"])
    for row in diag["decile_forward_returns"]:
        lines.append(
            f"- Decile {row['decile']}: mean=`{row['mean_forward_return']:.6f}`, n_days=`{row['n_days']}`"
        )
    lines.extend(["", "**Yearly Stability:**"])
    for row in diag["yearly_stability"]:
        if row["rank_ic_ir"] is None:
            lines.append(f"- {row['year']}: RankIC=`{row['rank_ic_mean']:.6f}`, ICIR=`null`")
        else:
            lines.append(f"- {row['year']}: RankIC=`{row['rank_ic_mean']:.6f}`, ICIR=`{row['rank_ic_ir']:.6f}`")
    lines.append("")
    return lines


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fmt_num(value: float | None) -> str:
    return "null" if value is None else f"{value:.6f}"


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Nonlinear Challenger v3 Model Edge Diagnosis",
        "",
        f"> **{DIAGNOSIS_LABEL}**",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        "## 1. Scope",
        "",
        "- This is model-layer / score-layer diagnosis only.",
        "- This is not a portfolio or backtest.",
        "- This does not read frozen test.",
        "- conditioning source is still a temporary gate artifact, not a long-term formal source.",
        "",
        "## 2. Coverage Summary",
        "",
    ]
    for split_name in ["train", "validation"]:
        cov = payload["coverage_summary"][split_name]
        lines.extend(
            [
                f"### {split_name.title()}",
                "",
                f"- Eligible labeled rows: `{cov['eligible_labeled_rows']}`",
                f"- v3 scored rows: `{cov['v3_scored_rows']}`",
                f"- confirmed5 scored rows: `{cov['confirmed5_scored_rows']}`",
                f"- v2 scored rows: `{cov['v2_scored_rows']}`",
                f"- baseline scored rows: `{cov['baseline_scored_rows']}`",
                f"- v3 coverage: `{cov['v3_score_coverage']:.6f}`",
                f"- confirmed5 coverage: `{cov['confirmed5_score_coverage']:.6f}`",
                f"- v2 coverage: `{cov['v2_score_coverage']:.6f}`",
                f"- baseline coverage: `{cov['baseline_score_coverage']:.6f}`",
                f"- v3 minus confirmed5 coverage: `{cov['score_coverage_difference']['v3_minus_confirmed5']:+.6f}`",
                f"- v3 minus v2 coverage: `{cov['score_coverage_difference']['v3_minus_v2']:+.6f}`",
                f"- v3 minus baseline coverage: `{cov['score_coverage_difference']['v3_minus_baseline']:+.6f}`",
                "",
            ]
        )

    lines.extend(["## 3. Train Diagnostics", ""])
    for key in ["v3_train", "confirmed5_train", "v2_train", "baseline_train"]:
        lines.extend(render_diagnosis_section(payload["diagnostics"][key]))
    lines.extend(["## 4. Validation Diagnostics", ""])
    for key in ["v3_validation", "confirmed5_validation", "v2_validation", "baseline_validation"]:
        lines.extend(render_diagnosis_section(payload["diagnostics"][key]))

    lines.extend(
        [
            "## 5. Cross-Model Comparison",
            "",
            "| Split | Metric | v3 | confirmed5 | v2 | baseline |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for split_name in ["train", "validation"]:
        models = payload["cross_model_comparison"][split_name]["models"]
        lines.append(
            f"| {split_name} | RankIC | {fmt_num(models['v3']['rank_ic'])} | {fmt_num(models['confirmed5']['rank_ic'])} | {fmt_num(models['v2']['rank_ic'])} | {fmt_num(models['baseline']['rank_ic'])} |"
        )
        lines.append(
            f"| {split_name} | ICIR | {fmt_num(models['v3']['icir'])} | {fmt_num(models['confirmed5']['icir'])} | {fmt_num(models['v2']['icir'])} | {fmt_num(models['baseline']['icir'])} |"
        )
        lines.append(
            f"| {split_name} | Top-bottom spread | {fmt_num(models['v3']['top_bottom_spread'])} | {fmt_num(models['confirmed5']['top_bottom_spread'])} | {fmt_num(models['v2']['top_bottom_spread'])} | {fmt_num(models['baseline']['top_bottom_spread'])} |"
        )
        lines.append(
            f"| {split_name} | TopK head proxy | {fmt_num(models['v3']['topk_head_realized_return_proxy'])} | {fmt_num(models['confirmed5']['topk_head_realized_return_proxy'])} | {fmt_num(models['v2']['topk_head_realized_return_proxy'])} | {fmt_num(models['baseline']['topk_head_realized_return_proxy'])} |"
        )
        lines.append(
            f"| {split_name} | Coverage | {fmt_num(models['v3']['score_coverage'])} | {fmt_num(models['confirmed5']['score_coverage'])} | {fmt_num(models['v2']['score_coverage'])} | {fmt_num(models['baseline']['score_coverage'])} |"
        )

    conclusion = payload["conclusion"]
    lines.extend(
        [
            "",
            "## 6. Conclusion",
            "",
            f"- materially_worse_vs_confirmed5: `{conclusion['materially_worse_vs_confirmed5']}`",
            f"- materially_worse_vs_v2: `{conclusion['materially_worse_vs_v2']}`",
            f"- topk_head_quality_improved_vs_confirmed5: `{conclusion['topk_head_quality_improved_vs_confirmed5']}`",
            f"- topk_head_quality_improved_vs_v2: `{conclusion['topk_head_quality_improved_vs_v2']}`",
            f"- temporary_conditioning_source: `{conclusion['temporary_conditioning_source']}`",
            f"- recommendation: `{conclusion['recommendation']}`",
            "",
            conclusion["recommendation_text"],
            "",
            conclusion["caveat"],
            "",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_diagnosis(args: argparse.Namespace) -> dict[str, Any]:
    ensure_exists(args.v3_scores, "v3 scores")
    ensure_exists(args.v3_audit, "v3 audit")
    ensure_exists(args.v2_scores, "v2 scores")
    ensure_exists(args.v2_audit, "v2 audit")
    ensure_exists(args.baseline_scores, "baseline scores")
    ensure_exists(args.label_panel, "label panel")
    ensure_exists(args.split_panel, "split panel")
    ensure_exists(args.source_binding, "source binding")

    v3_audit = load_json(args.v3_audit, "v3_audit")
    v2_audit = load_json(args.v2_audit, "v2_audit")
    source_binding = load_json(args.source_binding, "source_binding")
    confirmed5_scores_path = resolve_confirmed5_scores_path(args, v3_audit)
    ensure_exists(confirmed5_scores_path, "confirmed5 scores")

    topk = int(require_field(v3_audit, "topk", "v3_audit"))
    conditioning_source_path = Path(require_field(v3_audit, "conditioning_source_path", "v3_audit"))
    prohibited_prefixes = source_binding["conditioning_source_binding"]["long_term_formal_source_must_not_use_path_prefixes"]
    temporary_conditioning_source = any(str(conditioning_source_path).startswith(prefix) for prefix in prohibited_prefixes)

    con = duckdb.connect()
    try:
        build_views(
            con,
            v3_scores_path=args.v3_scores,
            confirmed5_scores_path=confirmed5_scores_path,
            v2_scores_path=args.v2_scores,
            baseline_scores_path=args.baseline_scores,
            label_panel_path=args.label_panel,
            split_panel_path=args.split_panel,
        )

        diagnoses: dict[str, dict[str, Any]] = {}
        for split_name, split_flag in [("train", "train_flag"), ("validation", "validation_flag")]:
            eligible_labeled_rows = int(con.execute(f"SELECT COUNT(*) FROM comparison_t WHERE {split_flag}").fetchone()[0])
            diagnoses[f"v3_{split_name}"] = diagnose_model(
                con,
                model_key="v3",
                model_label="v3 adjusted_score_D0",
                split_name=split_name,
                split_flag=split_flag,
                score_col="v3_adjusted_score",
                eligible_labeled_rows=eligible_labeled_rows,
                topk=topk,
            )
            diagnoses[f"confirmed5_{split_name}"] = diagnose_model(
                con,
                model_key="confirmed5",
                model_label="confirmed5 raw score_D0",
                split_name=split_name,
                split_flag=split_flag,
                score_col="confirmed5_raw_score",
                eligible_labeled_rows=eligible_labeled_rows,
                topk=topk,
            )
            diagnoses[f"v2_{split_name}"] = diagnose_model(
                con,
                model_key="v2",
                model_label="v2 adjusted_score_D0",
                split_name=split_name,
                split_flag=split_flag,
                score_col="v2_adjusted_score",
                eligible_labeled_rows=eligible_labeled_rows,
                topk=topk,
            )
            diagnoses[f"baseline_{split_name}"] = diagnose_model(
                con,
                model_key="baseline",
                model_label="baseline multi_equal_weight_v1 score",
                split_name=split_name,
                split_flag=split_flag,
                score_col="baseline_score",
                eligible_labeled_rows=eligible_labeled_rows,
                topk=topk,
            )

        coverage_summary = {
            split_name: build_coverage_summary(con, split_name=split_name, split_flag=split_flag, diagnoses=diagnoses)
            for split_name, split_flag in [("train", "train_flag"), ("validation", "validation_flag")]
        }
        cross_model_comparison = {
            split_name: build_split_comparison(
                split_name=split_name,
                diagnoses=diagnoses,
                coverage_summary=coverage_summary[split_name],
            )
            for split_name in ["train", "validation"]
        }
    finally:
        con.close()

    conclusion = build_conclusion(
        split_comparisons=cross_model_comparison,
        v3_audit=v3_audit,
        v2_audit=v2_audit,
        source_binding=source_binding,
        temporary_conditioning_source=temporary_conditioning_source,
    )

    payload = {
        "diagnosis_label": DIAGNOSIS_LABEL,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "portfolio_run_executed": False,
        "formal_metrics_generated": False,
        "frozen_test_accessed": False,
        "comparison_scope": {
            "phase_statement": "This phase evaluates model-layer / score-layer only.",
            "portfolio_statement": "No holdings, backtest_daily, metrics, or readout are generated.",
            "formula_statement": "v3 formula, confirmed5, v2, and baseline are all treated as fixed inputs.",
            "temporary_conditioning_source_disclosure": (
                "conditioning source is a temporary gate artifact, not a formal long-term governed source"
            ),
        },
        "data_sources": {
            "v3_scores_path": str(args.v3_scores),
            "v3_audit_path": str(args.v3_audit),
            "confirmed5_scores_path": str(confirmed5_scores_path),
            "v2_scores_path": str(args.v2_scores),
            "v2_audit_path": str(args.v2_audit),
            "baseline_scores_path": str(args.baseline_scores),
            "label_panel_path": str(args.label_panel),
            "split_panel_path": str(args.split_panel),
            "source_binding_path": str(args.source_binding),
        },
        "v3_score_builder_audit": {
            "candidate_scheme_id": v3_audit.get("candidate_scheme_id"),
            "base_score_source": v3_audit.get("base_score_source"),
            "base_score_input_path": v3_audit.get("base_score_input_path"),
            "conditioning_source_path": v3_audit.get("conditioning_source_path"),
            "head_quality_conditioning_source": v3_audit.get("head_quality_conditioning_source"),
            "conditioning_policy_version": v3_audit.get("conditioning_policy_version"),
            "row_count": v3_audit.get("row_count"),
            "provisional_topk_rows": v3_audit.get("provisional_topk_rows"),
            "topk": v3_audit.get("topk"),
            "training_performed": v3_audit.get("training_performed"),
            "frozen_test_accessed": v3_audit.get("frozen_test_accessed"),
            "portfolio_outputs_generated": v3_audit.get("portfolio_outputs_generated"),
        },
        "v2_transform_input_audit": {
            "candidate_scheme_id": v2_audit.get("candidate_scheme_id"),
            "row_count": v2_audit.get("row_count"),
            "raw_input_null_score_rows": v2_audit.get("raw_input_null_score_rows"),
            "score_transform_policy_version": v2_audit.get("score_transform_policy_version"),
            "training_performed": v2_audit.get("training_performed"),
            "frozen_test_accessed": v2_audit.get("frozen_test_accessed"),
        },
        "source_binding_disclosure": {
            "source_binding_id": source_binding.get("source_binding_id"),
            "canonical_source_requirement": source_binding["conditioning_source_binding"]["canonical_source_requirement"],
            "binding_notes": source_binding.get("notes", []),
            "temporary_conditioning_source": temporary_conditioning_source,
        },
        "coverage_summary": coverage_summary,
        "diagnostics": diagnoses,
        "cross_model_comparison": cross_model_comparison,
        "conclusion": conclusion,
    }
    return payload


def main() -> int:
    args = parse_args()
    try:
        payload = run_diagnosis(args)
    except DiagnosisError as exc:
        print(f"[diagnose_nonlinear_challenger_v3_model_edge] {exc}", file=sys.stderr)
        return 1

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output_json, payload)
    write_markdown(args.output_md, payload)
    print(json.dumps({"output_json": str(args.output_json), "output_md": str(args.output_md)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
