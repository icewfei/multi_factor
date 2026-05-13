#!/opt/anaconda3/envs/quant_trade/bin/python
"""
MODEL EDGE DIAGNOSIS ONLY — NOT A BACKTEST — NOT A PORTFOLIO READOUT

Compare no-p98 clean baseline score artifacts against:
- p98 conditional baseline
- current multi_equal_weight_v1 baseline
- confirmed5
- nonlinear challenger v2

This script:
- does NOT read frozen test
- does NOT generate holdings, backtest_daily, metrics, or readout
- does NOT modify any baseline or challenger logic
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
DEFAULT_NO_P98_SCORES = Path(
    "/private/tmp/no_p98_real_trainval_official_projection_20260513/out/model_scores_D0.parquet"
)
DEFAULT_NO_P98_AUDIT = Path(
    "/private/tmp/no_p98_real_trainval_official_projection_20260513/out/model_scores_D0_audit.json"
)
DEFAULT_P98_SCORES = ROOT / "artifacts" / "run_state" / "confirmatory_reversal_p98_trainval_20260506" / "model_scores_D0.parquet"
DEFAULT_CONFIRMED5_SCORES = Path("/private/tmp/confirmed5_same_contract_registered_model_scores_D0.parquet")
DEFAULT_V2_SCORES = Path(
    "/private/tmp/local_nlc_v2_confirmed5_locked_cs_volatility_discount_20260509/model_scores_D0.parquet"
)
DEFAULT_V3_SCORES = Path("/private/tmp/nlc_v3_real_trainval_score_gate_20260512/out/model_scores_D0.parquet")
DEFAULT_BASELINE_SCORES = ROOT / "artifacts" / "run_state" / "exploratory_multi_signal_composite_v1" / "model_scores_D0_multi.parquet"
DEFAULT_LABEL_PANEL = ROOT / "artifacts" / "run_state" / "project_panels_research_trainval_20211231_20260429" / "project_label_panel.parquet"
DEFAULT_SPLIT_PANEL = ROOT / "artifacts" / "run_state" / "project_panels_research_trainval_20211231_20260429" / "dataset_split_daily.parquet"
DEFAULT_OUTPUT_JSON = Path("/private/tmp/no_p98_clean_baseline_model_edge_diagnosis.json")
DEFAULT_OUTPUT_MD = Path("/private/tmp/no_p98_clean_baseline_model_edge_diagnosis.md")

EXPECTED_NO_P98_CANDIDATE = "no_p98_reversal_baseline_v1"
EXPECTED_P98_CANDIDATE = "reversal_tail_exclude_p98_v1"
EXPECTED_CONFIRMED5_CANDIDATE = "nlc_v1_confirmed5_lgbm_depth3_seed42"
EXPECTED_V2_CANDIDATE = "nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42"
EXPECTED_V3_CANDIDATE = "nlc_v3_confirmed5_locked_topk_head_quality_conditioned_capital_deployment_lgbm_depth3_seed42"
EXPECTED_BASELINE_CANDIDATE = "multi_equal_weight_v1"

TOPK_DEFAULT = 30
VALIDATION_RANKIC_LOSS_THRESHOLD = -0.005
VALIDATION_ICIR_LOSS_THRESHOLD = -0.05
DIAGNOSIS_LABEL = (
    "MODEL EDGE DIAGNOSIS ONLY — NOT A BACKTEST — "
    "NOT A PORTFOLIO READOUT — DO NOT INTERPRET AS STRATEGY EFFECTIVENESS"
)

MODEL_SPECS = {
    "no_p98": {
        "candidate_scheme_id": EXPECTED_NO_P98_CANDIDATE,
        "raw_score_column": "model_score_D0",
        "score_direction": "ASC / reversal_rank",
        "effective_score_expression": "-model_score_D0",
        "has_snapshot_id": True,
        "label": "no_p98 clean baseline",
    },
    "p98": {
        "candidate_scheme_id": EXPECTED_P98_CANDIDATE,
        "raw_score_column": "model_score_D0",
        "score_direction": "DESC / higher score better",
        "effective_score_expression": "model_score_D0",
        "has_snapshot_id": True,
        "label": "p98 conditional baseline",
    },
    "confirmed5": {
        "candidate_scheme_id": EXPECTED_CONFIRMED5_CANDIDATE,
        "raw_score_column": "model_score_D0",
        "score_direction": "DESC / higher score better",
        "effective_score_expression": "model_score_D0",
        "has_snapshot_id": True,
        "label": "confirmed5",
    },
    "v2": {
        "candidate_scheme_id": EXPECTED_V2_CANDIDATE,
        "raw_score_column": "model_score_D0",
        "score_direction": "DESC / higher score better",
        "effective_score_expression": "model_score_D0",
        "has_snapshot_id": True,
        "label": "v2",
    },
    "baseline": {
        "candidate_scheme_id": EXPECTED_BASELINE_CANDIDATE,
        "raw_score_column": "model_score_D0",
        "score_direction": "DESC / higher score better",
        "effective_score_expression": "model_score_D0",
        "has_snapshot_id": False,
        "label": "multi_equal_weight_v1",
    },
    "v3": {
        "candidate_scheme_id": EXPECTED_V3_CANDIDATE,
        "raw_score_column": "model_score_D0",
        "score_direction": "DESC / higher score better",
        "effective_score_expression": "model_score_D0",
        "has_snapshot_id": True,
        "label": "v3 rejected reference",
    },
}


class DiagnosisError(Exception):
    """Raised when the diagnosis cannot be completed safely."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose no-p98 clean baseline model-layer edge only.")
    parser.add_argument("--no-p98-scores", type=Path, default=DEFAULT_NO_P98_SCORES)
    parser.add_argument("--no-p98-audit", type=Path, default=DEFAULT_NO_P98_AUDIT)
    parser.add_argument("--p98-scores", type=Path, default=DEFAULT_P98_SCORES)
    parser.add_argument("--confirmed5-scores", type=Path, default=DEFAULT_CONFIRMED5_SCORES)
    parser.add_argument("--v2-scores", type=Path, default=DEFAULT_V2_SCORES)
    parser.add_argument("--v3-scores", type=Path, default=DEFAULT_V3_SCORES)
    parser.add_argument("--baseline-scores", type=Path, default=DEFAULT_BASELINE_SCORES)
    parser.add_argument("--label-panel", type=Path, default=DEFAULT_LABEL_PANEL)
    parser.add_argument("--split-panel", type=Path, default=DEFAULT_SPLIT_PANEL)
    parser.add_argument("--include-v3-reference", action="store_true")
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


def ensure_no_frozen_test_access(no_p98_audit: dict[str, Any]) -> None:
    if no_p98_audit.get("frozen_test_accessed") is not False:
        raise DiagnosisError("no_p98 audit indicates frozen_test_accessed is not false")
    if no_p98_audit.get("p98_used") is not False:
        raise DiagnosisError("no_p98 audit indicates p98_used is not false")
    if no_p98_audit.get("label_diagnostics_used") is not False:
        raise DiagnosisError("no_p98 audit indicates label_diagnostics_used is not false")


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
    args: argparse.Namespace,
) -> None:
    register_score_view(
        con,
        view_name="no_p98_t",
        path=args.no_p98_scores,
        candidate_scheme_id=EXPECTED_NO_P98_CANDIDATE,
        raw_score_column=MODEL_SPECS["no_p98"]["raw_score_column"],
        effective_score_expression=MODEL_SPECS["no_p98"]["effective_score_expression"],
    )
    register_score_view(
        con,
        view_name="p98_t",
        path=args.p98_scores,
        candidate_scheme_id=EXPECTED_P98_CANDIDATE,
        raw_score_column=MODEL_SPECS["p98"]["raw_score_column"],
        effective_score_expression=MODEL_SPECS["p98"]["effective_score_expression"],
    )
    register_score_view(
        con,
        view_name="confirmed5_t",
        path=args.confirmed5_scores,
        candidate_scheme_id=EXPECTED_CONFIRMED5_CANDIDATE,
        raw_score_column=MODEL_SPECS["confirmed5"]["raw_score_column"],
        effective_score_expression=MODEL_SPECS["confirmed5"]["effective_score_expression"],
    )
    register_score_view(
        con,
        view_name="v2_t",
        path=args.v2_scores,
        candidate_scheme_id=EXPECTED_V2_CANDIDATE,
        raw_score_column=MODEL_SPECS["v2"]["raw_score_column"],
        effective_score_expression=MODEL_SPECS["v2"]["effective_score_expression"],
    )
    register_score_view(
        con,
        view_name="baseline_t",
        path=args.baseline_scores,
        candidate_scheme_id=EXPECTED_BASELINE_CANDIDATE,
        raw_score_column=MODEL_SPECS["baseline"]["raw_score_column"],
        effective_score_expression=MODEL_SPECS["baseline"]["effective_score_expression"],
    )
    if args.include_v3_reference:
        register_score_view(
            con,
            view_name="v3_t",
            path=args.v3_scores,
            candidate_scheme_id=EXPECTED_V3_CANDIDATE,
            raw_score_column=MODEL_SPECS["v3"]["raw_score_column"],
            effective_score_expression=MODEL_SPECS["v3"]["effective_score_expression"],
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
            s.validation_flag,
            n.raw_score AS no_p98_raw_score,
            n.effective_score AS no_p98_effective_score,
            p.raw_score AS p98_raw_score,
            p.effective_score AS p98_effective_score,
            c.raw_score AS confirmed5_raw_score,
            c.effective_score AS confirmed5_effective_score,
            v2.raw_score AS v2_raw_score,
            v2.effective_score AS v2_effective_score,
            b.raw_score AS baseline_raw_score,
            b.effective_score AS baseline_effective_score
    """
    if args.include_v3_reference:
        comparison_sql += """
            ,
            v3.raw_score AS v3_raw_score,
            v3.effective_score AS v3_effective_score
        """
    comparison_sql += """
        FROM label_t l
        INNER JOIN split_t s
            ON l.snapshot_id = s.snapshot_id
           AND l.instrument = s.instrument
           AND l.signal_date = s.signal_date
        LEFT JOIN no_p98_t n
            ON l.snapshot_id = n.snapshot_id
           AND l.instrument = n.instrument
           AND l.signal_date = n.signal_date
        LEFT JOIN p98_t p
            ON l.snapshot_id = p.snapshot_id
           AND l.instrument = p.instrument
           AND l.signal_date = p.signal_date
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
    """
    if args.include_v3_reference:
        comparison_sql += """
        LEFT JOIN v3_t v3
            ON l.snapshot_id = v3.snapshot_id
           AND l.instrument = v3.instrument
           AND l.signal_date = v3.signal_date
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
    icir = (rank_ic_mean / rank_ic_std) if rank_ic_mean is not None and rank_ic_std not in (None, 0.0) else None
    deciles = fetch_decile_returns(con, split_flag=split_flag, effective_score_col=effective_score_col)
    top_decile = next((row["mean_forward_return"] for row in deciles if row["decile"] == 1), None)
    bottom_decile = next((row["mean_forward_return"] for row in deciles if row["decile"] == 10), None)
    top_bottom_spread = (
        float(top_decile - bottom_decile)
        if top_decile is not None and bottom_decile is not None
        else None
    )
    topk_proxy = fetch_topk_head_proxy(con, split_flag=split_flag, effective_score_col=effective_score_col, topk=topk)

    return {
        "model_key": model_key,
        "model_label": MODEL_SPECS[model_key]["label"],
        "candidate_scheme_id": MODEL_SPECS[model_key]["candidate_scheme_id"],
        "score_direction": MODEL_SPECS[model_key]["score_direction"],
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


def build_coverage_summary(
    con: duckdb.DuckDBPyConnection,
    *,
    split_name: str,
    split_flag: str,
    diagnoses: dict[str, dict[str, Any]],
    model_keys: list[str],
) -> dict[str, Any]:
    eligible_labeled_rows = int(con.execute(f"SELECT COUNT(*) FROM comparison_t WHERE {split_flag}").fetchone()[0])
    summary: dict[str, Any] = {"eligible_labeled_rows": eligible_labeled_rows}
    for model_key in model_keys:
        diag = diagnoses[f"{model_key}_{split_name}"]
        summary[f"{model_key}_scored_rows"] = diag["scored_rows"]
        summary[f"{model_key}_score_coverage"] = diag["score_coverage"]
    return summary


def model_snapshot(diag: dict[str, Any]) -> dict[str, Any]:
    return {
        "rank_ic": diag["rank_ic"]["mean"],
        "icir": diag["icir"],
        "top_bottom_spread": diag["top_bottom_spread"],
        "topk_head_realized_return_proxy": diag["topk_head_realized_return_proxy"]["mean_topk_forward_return"],
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
) -> dict[str, Any]:
    models = {model_key: model_snapshot(diagnoses[f"{model_key}_{split_name}"]) for model_key in model_keys}
    output = {"models": models}
    for ref_key in model_keys:
        if ref_key == "no_p98":
            continue
        output[f"no_p98_vs_{ref_key}"] = delta(
            diagnoses[f"no_p98_{split_name}"],
            diagnoses[f"{ref_key}_{split_name}"],
        )
    return output


def build_conclusion(
    *,
    diagnoses: dict[str, dict[str, Any]],
    cross_model_comparison: dict[str, dict[str, Any]],
    include_v3_reference: bool,
) -> dict[str, Any]:
    train_no_p98 = diagnoses["no_p98_train"]
    validation_no_p98 = diagnoses["no_p98_validation"]
    validation_vs_p98 = cross_model_comparison["validation"]["no_p98_vs_p98"]
    validation_vs_baseline = cross_model_comparison["validation"]["no_p98_vs_baseline"]

    retains_model_edge = all(
        metric is not None and metric > 0
        for metric in (
            train_no_p98["rank_ic"]["mean"],
            train_no_p98["icir"],
            validation_no_p98["rank_ic"]["mean"],
            validation_no_p98["icir"],
        )
    )
    validation_head_proxy_positive = (
        validation_no_p98["topk_head_realized_return_proxy"]["mean_topk_forward_return"] is not None
        and validation_no_p98["topk_head_realized_return_proxy"]["mean_topk_forward_return"] > 0
    )
    validation_head_proxy_beats_nextk = (
        validation_no_p98["topk_head_realized_return_proxy"]["topk_minus_nextk"] is not None
        and validation_no_p98["topk_head_realized_return_proxy"]["topk_minus_nextk"] > 0
    )

    p98_mainly_contributes_model_edge = (
        validation_vs_p98["rank_ic_delta"] is not None
        and validation_vs_p98["rank_ic_delta"] <= VALIDATION_RANKIC_LOSS_THRESHOLD
        and validation_vs_p98["icir_delta"] is not None
        and validation_vs_p98["icir_delta"] <= VALIDATION_ICIR_LOSS_THRESHOLD
        and validation_vs_p98["topk_head_realized_return_proxy_delta"] is not None
        and validation_vs_p98["topk_head_realized_return_proxy_delta"] < 0
        and validation_head_proxy_positive is False
    )

    recommend_same_contract_portfolio_dry_run_preparation = (
        retains_model_edge and validation_head_proxy_positive and validation_head_proxy_beats_nextk
    )
    if recommend_same_contract_portfolio_dry_run_preparation:
        recommendation = "prepare_same_contract_portfolio_dry_run"
        recommendation_text = (
            "no_p98 retains positive train/validation model-layer edge and its validation TopK head proxy is not negative. "
            "It may proceed to same-contract portfolio dry-run preparation as a clean baseline candidate only."
        )
    else:
        recommendation = "do_not_prepare_same_contract_portfolio_dry_run_yet"
        recommendation_text = (
            "no_p98 retains some full-cross-section model-layer edge, but the validation TopK head realized return proxy "
            "is not strong enough to support same-contract portfolio dry-run preparation yet."
        )

    evidence = [
        f"validation RankIC delta vs p98: {validation_vs_p98['rank_ic_delta']:+.6f}"
        if validation_vs_p98["rank_ic_delta"] is not None
        else "validation RankIC delta vs p98: null",
        f"validation ICIR delta vs p98: {validation_vs_p98['icir_delta']:+.6f}"
        if validation_vs_p98["icir_delta"] is not None
        else "validation ICIR delta vs p98: null",
        f"validation top-bottom spread delta vs p98: {validation_vs_p98['top_bottom_spread_delta']:+.6f}"
        if validation_vs_p98["top_bottom_spread_delta"] is not None
        else "validation top-bottom spread delta vs p98: null",
        f"validation TopK head proxy delta vs p98: {validation_vs_p98['topk_head_realized_return_proxy_delta']:+.6f}"
        if validation_vs_p98["topk_head_realized_return_proxy_delta"] is not None
        else "validation TopK head proxy delta vs p98: null",
        f"validation TopK head proxy delta vs baseline: {validation_vs_baseline['topk_head_realized_return_proxy_delta']:+.6f}"
        if validation_vs_baseline["topk_head_realized_return_proxy_delta"] is not None
        else "validation TopK head proxy delta vs baseline: null",
    ]
    if include_v3_reference:
        evidence.append("v3 is included only as a rejected reference, not as a new approval target.")

    return {
        "no_p98_retains_model_layer_edge": retains_model_edge,
        "validation_topk_head_proxy_positive": validation_head_proxy_positive,
        "validation_topk_head_proxy_beats_nextk": validation_head_proxy_beats_nextk,
        "p98_mainly_contributes_model_edge": p98_mainly_contributes_model_edge,
        "recommend_same_contract_portfolio_dry_run_preparation": recommend_same_contract_portfolio_dry_run_preparation,
        "recommendation": recommendation,
        "recommendation_text": recommendation_text,
        "loss_thresholds_vs_p98": {
            "validation_rankic_loss_threshold": VALIDATION_RANKIC_LOSS_THRESHOLD,
            "validation_icir_loss_threshold": VALIDATION_ICIR_LOSS_THRESHOLD,
        },
        "evidence": evidence,
        "caveat": (
            "This is model-layer / score-layer diagnosis only. It is not a portfolio, holdings, backtest, OOS, "
            "or formal metrics/readout package, and it is not a strategy-effectiveness conclusion."
        ),
    }


def fmt_num(value: float | None) -> str:
    return "null" if value is None else f"{value:.6f}"


def render_diagnosis_section(diag: dict[str, Any]) -> list[str]:
    if "error" in diag:
        return [f"### {diag['model_label']} — {diag['split']}", "", f"- Error: {diag['error']}", ""]

    topk = diag["topk_head_realized_return_proxy"]
    lines = [
        f"### {diag['model_label']} — {diag['split']}",
        "",
        f"- Candidate: `{diag['candidate_scheme_id']}`",
        f"- Score direction: `{diag['score_direction']}`",
        f"- Scored rows: `{diag['scored_rows']}`",
        f"- Eligible labeled rows: `{diag['eligible_labeled_rows']}`",
        f"- Coverage: `{diag['score_coverage']:.6f}`",
        f"- RankIC: `{diag['rank_ic']['mean']:.6f}`" if diag["rank_ic"]["mean"] is not None else "- RankIC: `null`",
        f"- ICIR: `{diag['icir']:.6f}`" if diag["icir"] is not None else "- ICIR: `null`",
        f"- Top-bottom spread: `{diag['top_bottom_spread']:.6f}`"
        if diag["top_bottom_spread"] is not None
        else "- Top-bottom spread: `null`",
        f"- TopK head realized return proxy mean: `{topk['mean_topk_forward_return']:.6f}`"
        if topk["mean_topk_forward_return"] is not None
        else "- TopK head realized return proxy mean: `null`",
        f"- TopK minus nextK: `{topk['topk_minus_nextk']:.6f}`"
        if topk["topk_minus_nextk"] is not None
        else "- TopK minus nextK: `null`",
        "",
        "**Decile Forward Returns (1=top, 10=bottom):**",
    ]
    for row in diag["decile_forward_returns"]:
        lines.append(
            f"- Decile {row['decile']}: mean=`{row['mean_forward_return']:.6f}`, n_days=`{row['n_days']}`"
        )
    lines.extend(["", "**Yearly Stability:**"])
    for row in diag["yearly_stability"]:
        lines.append(
            f"- {row['year']}: RankIC=`{row['rank_ic_mean']:.6f}`, ICIR=`{fmt_num(row['rank_ic_ir'])}`"
        )
    lines.append("")
    return lines


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, payload: dict[str, Any], model_keys: list[str]) -> None:
    lines = [
        "# no-p98 clean baseline model edge diagnosis",
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
        "## 2. no-p98 Score-Layer Preconditions",
        "",
        f"- score_direction: `{payload['no_p98_score_layer_metadata']['score_direction']}`",
        f"- p98_used: `{payload['no_p98_score_layer_metadata']['p98_used']}`",
        f"- label_diagnostics_used: `{payload['no_p98_score_layer_metadata']['label_diagnostics_used']}`",
        f"- frozen_test_accessed: `{payload['no_p98_score_layer_metadata']['frozen_test_accessed']}`",
        "",
        "## 3. Coverage Summary",
        "",
    ]
    for split_name in ("train", "validation"):
        cov = payload["coverage_summary"][split_name]
        lines.extend(
            [
                f"### {split_name.title()}",
                "",
                f"- Eligible labeled rows: `{cov['eligible_labeled_rows']}`",
            ]
        )
        for model_key in model_keys:
            lines.append(f"- {model_key} scored rows: `{cov[f'{model_key}_scored_rows']}`")
            lines.append(f"- {model_key} coverage: `{cov[f'{model_key}_score_coverage']:.6f}`")
        lines.append("")

    lines.extend(["## 4. Train Diagnostics", ""])
    for model_key in model_keys:
        lines.extend(render_diagnosis_section(payload["diagnostics"][f"{model_key}_train"]))
    lines.extend(["## 5. Validation Diagnostics", ""])
    for model_key in model_keys:
        lines.extend(render_diagnosis_section(payload["diagnostics"][f"{model_key}_validation"]))

    lines.extend(
        [
            "## 6. Cross-Model Comparison",
            "",
            "| Split | Metric | no_p98 | p98 | baseline | confirmed5 | v2 |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for split_name in ("train", "validation"):
        models = payload["cross_model_comparison"][split_name]["models"]
        lines.append(
            f"| {split_name} | RankIC | {fmt_num(models['no_p98']['rank_ic'])} | {fmt_num(models['p98']['rank_ic'])} | {fmt_num(models['baseline']['rank_ic'])} | {fmt_num(models['confirmed5']['rank_ic'])} | {fmt_num(models['v2']['rank_ic'])} |"
        )
        lines.append(
            f"| {split_name} | ICIR | {fmt_num(models['no_p98']['icir'])} | {fmt_num(models['p98']['icir'])} | {fmt_num(models['baseline']['icir'])} | {fmt_num(models['confirmed5']['icir'])} | {fmt_num(models['v2']['icir'])} |"
        )
        lines.append(
            f"| {split_name} | Top-bottom spread | {fmt_num(models['no_p98']['top_bottom_spread'])} | {fmt_num(models['p98']['top_bottom_spread'])} | {fmt_num(models['baseline']['top_bottom_spread'])} | {fmt_num(models['confirmed5']['top_bottom_spread'])} | {fmt_num(models['v2']['top_bottom_spread'])} |"
        )
        lines.append(
            f"| {split_name} | TopK head proxy | {fmt_num(models['no_p98']['topk_head_realized_return_proxy'])} | {fmt_num(models['p98']['topk_head_realized_return_proxy'])} | {fmt_num(models['baseline']['topk_head_realized_return_proxy'])} | {fmt_num(models['confirmed5']['topk_head_realized_return_proxy'])} | {fmt_num(models['v2']['topk_head_realized_return_proxy'])} |"
        )
        lines.append(
            f"| {split_name} | Coverage | {fmt_num(models['no_p98']['score_coverage'])} | {fmt_num(models['p98']['score_coverage'])} | {fmt_num(models['baseline']['score_coverage'])} | {fmt_num(models['confirmed5']['score_coverage'])} | {fmt_num(models['v2']['score_coverage'])} |"
        )

    conclusion = payload["conclusion"]
    lines.extend(
        [
            "",
            "## 7. Conclusion",
            "",
            f"- no_p98_retains_model_layer_edge: `{conclusion['no_p98_retains_model_layer_edge']}`",
            f"- validation_topk_head_proxy_positive: `{conclusion['validation_topk_head_proxy_positive']}`",
            f"- validation_topk_head_proxy_beats_nextk: `{conclusion['validation_topk_head_proxy_beats_nextk']}`",
            f"- p98_mainly_contributes_model_edge: `{conclusion['p98_mainly_contributes_model_edge']}`",
            f"- recommend_same_contract_portfolio_dry_run_preparation: `{conclusion['recommend_same_contract_portfolio_dry_run_preparation']}`",
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
    ensure_exists(args.no_p98_scores, "no_p98 scores")
    ensure_exists(args.no_p98_audit, "no_p98 audit")
    ensure_exists(args.p98_scores, "p98 scores")
    ensure_exists(args.confirmed5_scores, "confirmed5 scores")
    ensure_exists(args.v2_scores, "v2 scores")
    ensure_exists(args.baseline_scores, "baseline scores")
    ensure_exists(args.label_panel, "label panel")
    ensure_exists(args.split_panel, "split panel")
    if args.include_v3_reference:
        ensure_exists(args.v3_scores, "v3 scores")

    no_p98_audit = load_json(args.no_p98_audit, "no_p98 audit")
    ensure_no_frozen_test_access(no_p98_audit)

    model_keys = ["no_p98", "p98", "baseline", "confirmed5", "v2"]
    if args.include_v3_reference:
        model_keys.append("v3")

    con = duckdb.connect()
    try:
        build_views(con, args=args)

        diagnoses: dict[str, dict[str, Any]] = {}
        for split_name, split_flag in [("train", "train_flag"), ("validation", "validation_flag")]:
            eligible_labeled_rows = int(con.execute(f"SELECT COUNT(*) FROM comparison_t WHERE {split_flag}").fetchone()[0])
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

        coverage_summary = {
            split_name: build_coverage_summary(
                con,
                split_name=split_name,
                split_flag=split_flag,
                diagnoses=diagnoses,
                model_keys=model_keys,
            )
            for split_name, split_flag in [("train", "train_flag"), ("validation", "validation_flag")]
        }
    finally:
        con.close()

    cross_model_comparison = {
        split_name: build_split_comparison(split_name=split_name, diagnoses=diagnoses, model_keys=model_keys)
        for split_name in ("train", "validation")
    }
    conclusion = build_conclusion(
        diagnoses=diagnoses,
        cross_model_comparison=cross_model_comparison,
        include_v3_reference=args.include_v3_reference,
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
            "no_p98_scores": args.no_p98_scores.as_posix(),
            "no_p98_audit": args.no_p98_audit.as_posix(),
            "p98_scores": args.p98_scores.as_posix(),
            "confirmed5_scores": args.confirmed5_scores.as_posix(),
            "v2_scores": args.v2_scores.as_posix(),
            "baseline_scores": args.baseline_scores.as_posix(),
            "label_panel": args.label_panel.as_posix(),
            "split_panel": args.split_panel.as_posix(),
            "include_v3_reference": args.include_v3_reference,
            "v3_scores": args.v3_scores.as_posix() if args.include_v3_reference else None,
        },
        "no_p98_score_layer_metadata": {
            "candidate_scheme_id": no_p98_audit.get("candidate_scheme_id"),
            "baseline_id": no_p98_audit.get("baseline_id"),
            "score_direction": no_p98_audit.get("score_direction"),
            "p98_used": no_p98_audit.get("p98_used"),
            "label_diagnostics_used": no_p98_audit.get("label_diagnostics_used"),
            "frozen_test_accessed": no_p98_audit.get("frozen_test_accessed"),
            "d0_visibility_audit": no_p98_audit.get("d0_visibility_audit"),
            "leakage_audit": no_p98_audit.get("leakage_audit"),
        },
        "models_compared": {model_key: MODEL_SPECS[model_key] for model_key in model_keys},
        "coverage_summary": coverage_summary,
        "diagnostics": diagnoses,
        "cross_model_comparison": cross_model_comparison,
        "conclusion": conclusion,
    }


def main() -> None:
    args = parse_args()
    payload = run_diagnosis(args)
    write_json(args.output_json, payload)
    write_markdown(args.output_md, payload, list(payload["models_compared"].keys()))


if __name__ == "__main__":
    main()
