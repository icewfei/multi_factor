#!/opt/anaconda3/envs/quant_trade/bin/python
"""
MODEL EDGE DIAGNOSIS ONLY — NOT A BACKTEST — NOT A PORTFOLIO READOUT

Compare nonlinear challenger v2 adjusted scores against:
- confirmed5 raw model scores
- baseline multi_equal_weight_v1 exact scores

This script:
- does NOT read frozen test
- does NOT generate holdings, portfolio, or backtest artifacts
- does NOT produce formal metrics/readout
- writes local diagnosis JSON/MD only
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd


ROOT = Path("/Users/wy/MiscProject/multi_factor")
DEFAULT_V2_SCORES = Path(
    "/private/tmp/local_nlc_v2_confirmed5_locked_cs_volatility_discount_20260509/model_scores_D0.parquet"
)
DEFAULT_V2_AUDIT = Path(
    "/private/tmp/local_nlc_v2_confirmed5_locked_cs_volatility_discount_20260509/score_transform_audit.json"
)
DEFAULT_CONFIRMED5_SCORES = ROOT / "artifacts/run_state/confirmatory_reversal_p98_trainval_20260506/model_scores_D0.parquet"
DEFAULT_BASELINE_SCORES = ROOT / "artifacts/run_state/exploratory_multi_signal_composite_v1/model_scores_D0_multi.parquet"
DEFAULT_LABEL_PANEL = ROOT / "artifacts/run_state/project_panels_research_trainval_20211231_20260429/project_label_panel.parquet"
DEFAULT_SPLIT_PANEL = ROOT / "artifacts/run_state/project_panels_research_trainval_20211231_20260429/dataset_split_daily.parquet"
DEFAULT_OUTPUT_JSON = Path("/private/tmp/nonlinear_challenger_v2_model_edge_diagnosis.json")
DEFAULT_OUTPUT_MD = Path("/private/tmp/nonlinear_challenger_v2_model_edge_diagnosis.md")

EXPECTED_V2_CANDIDATE = "nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42"
EXPECTED_CONFIRMED5_CANDIDATE = "reversal_tail_exclude_p98_v1"
EXPECTED_BASELINE_CANDIDATE = "multi_equal_weight_v1"
DIAGNOSIS_LABEL = (
    "MODEL EDGE DIAGNOSIS ONLY — NOT A BACKTEST — "
    "NOT A PORTFOLIO READOUT — DO NOT INTERPRET AS STRATEGY PERFORMANCE"
)

VALIDATION_RANKIC_DAMAGE_THRESHOLD = -0.005
VALIDATION_ICIR_DAMAGE_THRESHOLD = -0.05


class DiagnosisError(Exception):
    """Raised when the model-edge diagnosis cannot be completed safely."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose nonlinear challenger v2 model-layer edge only.")
    parser.add_argument("--v2-scores", type=Path, default=DEFAULT_V2_SCORES, help="Path to v2 transformed scores parquet.")
    parser.add_argument("--v2-audit", type=Path, default=DEFAULT_V2_AUDIT, help="Path to v2 score_transform_audit.json.")
    parser.add_argument(
        "--confirmed5-scores",
        type=Path,
        default=DEFAULT_CONFIRMED5_SCORES,
        help="Path to confirmed5 raw model scores parquet.",
    )
    parser.add_argument(
        "--baseline-scores",
        type=Path,
        default=DEFAULT_BASELINE_SCORES,
        help="Path to exact baseline multi_score parquet containing multi_equal_weight_v1.",
    )
    parser.add_argument("--label-panel", type=Path, default=DEFAULT_LABEL_PANEL, help="Path to project_label_panel.parquet.")
    parser.add_argument("--split-panel", type=Path, default=DEFAULT_SPLIT_PANEL, help="Path to dataset_split_daily.parquet.")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON, help="Output diagnosis JSON path.")
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD, help="Output diagnosis Markdown path.")
    return parser.parse_args()


def ensure_exists(path: Path, label: str) -> None:
    if not path.exists():
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


def compute_rank_ic(df: pd.DataFrame, score_col: str, label_col: str) -> pd.Series:
    valid = df[[score_col, label_col, "signal_date"]].dropna()
    if len(valid) == 0:
        return pd.Series(dtype=float)
    daily_ic = valid.groupby("signal_date").apply(
        lambda g: g[score_col].corr(g[label_col], method="spearman") if len(g) >= 10 else None
    )
    return daily_ic.dropna()


def compute_decile_returns(df: pd.DataFrame, score_col: str, label_col: str) -> list[dict[str, Any]]:
    valid = df[[score_col, label_col, "signal_date"]].dropna().copy()
    if len(valid) == 0:
        return []

    valid["decile"] = valid.groupby("signal_date")[score_col].transform(
        lambda x: pd.qcut(x, 10, labels=False, duplicates="drop") + 1
    )
    valid = valid.dropna(subset=["decile"])
    if len(valid) == 0:
        return []
    valid["decile"] = valid["decile"].astype(int)

    daily_decile = valid.groupby(["signal_date", "decile"])[label_col].mean().reset_index()
    avg_decile = daily_decile.groupby("decile")[label_col].agg(["mean", "std", "count"]).reset_index()
    rows: list[dict[str, Any]] = []
    for _, row in avg_decile.iterrows():
        t_stat = None
        if pd.notna(row["std"]) and row["std"] > 0 and row["count"] > 0:
            t_stat = float(row["mean"] / (row["std"] / np.sqrt(row["count"])))
        rows.append(
            {
                "decile": int(row["decile"]),
                "mean_forward_return": float(row["mean"]),
                "std_forward_return": float(row["std"]) if pd.notna(row["std"]) else None,
                "n_days": int(row["count"]),
                "t_stat": t_stat,
            }
        )
    return rows


def compute_top_bottom_spread(deciles: list[dict[str, Any]]) -> float | None:
    by_decile = {row["decile"]: row["mean_forward_return"] for row in deciles}
    if 1 not in by_decile or 10 not in by_decile:
        return None
    return float(by_decile[10] - by_decile[1])


def compute_yearly_stability(df: pd.DataFrame, score_col: str, label_col: str) -> list[dict[str, Any]]:
    valid = df[[score_col, label_col, "signal_date"]].dropna().copy()
    if len(valid) == 0:
        return []
    valid["year"] = valid["signal_date"].str[:4]
    output: list[dict[str, Any]] = []
    for year in sorted(valid["year"].unique()):
        year_df = valid[valid["year"] == year]
        daily_ic = compute_rank_ic(year_df, score_col, label_col)
        if len(daily_ic) == 0:
            continue
        ic_mean = float(daily_ic.mean())
        ic_std = float(daily_ic.std())
        output.append(
            {
                "year": int(year),
                "rank_ic_mean": ic_mean,
                "rank_ic_std": ic_std,
                "rank_ic_ir": float(ic_mean / ic_std) if ic_std > 0 else None,
                "n_days": int(len(daily_ic)),
                "positive_ic_pct": float((daily_ic > 0).mean()),
            }
        )
    return output


def diagnose_model(
    df: pd.DataFrame,
    score_col: str,
    split_col: str,
    label_col: str,
    total_split_rows: int,
    label: str,
) -> dict[str, Any]:
    subset = df[df[split_col]].copy()
    scored = subset.dropna(subset=[score_col])
    score_count = int(scored[score_col].count())
    score_coverage = float(score_count / total_split_rows) if total_split_rows > 0 else None

    if score_count == 0:
        return {
            "label": label,
            "row_count": 0,
            "scored_rows": 0,
            "eligible_labeled_rows": total_split_rows,
            "score_coverage": score_coverage,
            "error": "No scored rows for split",
        }

    score_distribution = {
        "count": score_count,
        "mean": float(scored[score_col].mean()),
        "std": float(scored[score_col].std()),
        "min": float(scored[score_col].min()),
        "p25": float(scored[score_col].quantile(0.25)),
        "p50": float(scored[score_col].quantile(0.50)),
        "p75": float(scored[score_col].quantile(0.75)),
        "max": float(scored[score_col].max()),
    }

    daily_ic = compute_rank_ic(scored, score_col, label_col)
    rank_ic = {"error": "No valid IC days"}
    icir = None
    if len(daily_ic) > 0:
        ic_mean = float(daily_ic.mean())
        ic_std = float(daily_ic.std())
        rank_ic = {
            "mean": ic_mean,
            "std": ic_std,
            "n_days": int(len(daily_ic)),
            "positive_ic_pct": float((daily_ic > 0).mean()),
            "t_stat": float(ic_mean / (ic_std / np.sqrt(len(daily_ic)))) if ic_std > 0 else None,
        }
        icir = float(ic_mean / ic_std) if ic_std > 0 else None

    deciles = compute_decile_returns(scored, score_col, label_col)
    top_bottom_spread = compute_top_bottom_spread(deciles)
    yearly = compute_yearly_stability(scored, score_col, label_col)
    daily_mean_score = scored.groupby("signal_date")[score_col].mean().dropna()
    score_autocorr = float(daily_mean_score.autocorr(lag=1)) if len(daily_mean_score) > 1 else None

    return {
        "label": label,
        "row_count": score_count,
        "scored_rows": score_count,
        "eligible_labeled_rows": total_split_rows,
        "score_coverage": score_coverage,
        "n_signal_dates": int(scored["signal_date"].nunique()),
        "n_instruments": int(scored["instrument"].nunique()),
        "score_distribution": score_distribution,
        "rank_ic": rank_ic,
        "icir": icir,
        "decile_forward_returns": deciles,
        "top_bottom_spread": top_bottom_spread,
        "score_autocorr_lag1": score_autocorr,
        "yearly_stability": yearly,
    }


def load_comparison_frame(
    v2_scores_path: Path,
    confirmed5_scores_path: Path,
    baseline_scores_path: Path,
    label_panel_path: Path,
    split_panel_path: Path,
) -> pd.DataFrame:
    con = duckdb.connect()
    try:
        result = con.execute(
            f"""
            WITH v2_t AS (
                SELECT
                    snapshot_id,
                    instrument,
                    signal_date,
                    model_score_D0 AS v2_score
                FROM read_parquet('{v2_scores_path.as_posix()}')
                WHERE candidate_scheme_id = '{EXPECTED_V2_CANDIDATE}'
            ),
            confirmed5_t AS (
                SELECT
                    snapshot_id,
                    instrument,
                    signal_date,
                    model_score_D0 AS confirmed5_score
                FROM read_parquet('{confirmed5_scores_path.as_posix()}')
                WHERE candidate_scheme_id = '{EXPECTED_CONFIRMED5_CANDIDATE}'
            ),
            baseline_t AS (
                SELECT
                    instrument,
                    signal_date,
                    model_score_D0 AS baseline_score
                FROM read_parquet('{baseline_scores_path.as_posix()}')
                WHERE candidate_scheme_id = '{EXPECTED_BASELINE_CANDIDATE}'
            ),
            label_t AS (
                SELECT
                    snapshot_id,
                    instrument,
                    signal_date,
                    label_5d_next_open_close AS forward_return_5d,
                    label_defined
                FROM read_parquet('{label_panel_path.as_posix()}')
            ),
            split_t AS (
                SELECT
                    snapshot_id,
                    instrument,
                    signal_date,
                    train_flag,
                    validation_flag
                FROM read_parquet('{split_panel_path.as_posix()}')
            )
            SELECT
                l.snapshot_id,
                l.instrument,
                l.signal_date,
                v2.v2_score,
                c.confirmed5_score,
                b.baseline_score,
                l.forward_return_5d,
                s.train_flag,
                s.validation_flag
            FROM label_t l
            INNER JOIN split_t s
              ON l.snapshot_id = s.snapshot_id
             AND l.instrument = s.instrument
             AND l.signal_date = s.signal_date
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
            ORDER BY l.signal_date, l.instrument
            """
        ).fetchdf()
    finally:
        con.close()
    return result


def build_conclusion(results: dict[str, Any], v2_audit: dict[str, Any]) -> dict[str, Any]:
    validation_comp = results["cross_model_comparison"]["v2_vs_confirmed5"]["validation"]
    coverage_summary = results["coverage_summary"]
    val_rankic_delta = validation_comp.get("rank_ic_delta_vs_confirmed5")
    val_icir_delta = validation_comp.get("icir_delta_vs_confirmed5")

    materially_damaged = False
    reasons: list[str] = []
    if val_rankic_delta is not None and val_rankic_delta < VALIDATION_RANKIC_DAMAGE_THRESHOLD:
        materially_damaged = True
        reasons.append(
            "v2 validation RankIC is materially below confirmed5: "
            f"delta={val_rankic_delta:+.4f} < {VALIDATION_RANKIC_DAMAGE_THRESHOLD:+.4f}"
        )
    if val_icir_delta is not None and val_icir_delta < VALIDATION_ICIR_DAMAGE_THRESHOLD:
        materially_damaged = True
        reasons.append(
            "v2 validation ICIR is materially below confirmed5: "
            f"delta={val_icir_delta:+.4f} < {VALIDATION_ICIR_DAMAGE_THRESHOLD:+.4f}"
        )

    if coverage_summary["validation"]["coverage_diff_vs_confirmed5"] is not None:
        reasons.append(
            "Validation score coverage delta vs confirmed5: "
            f"{coverage_summary['validation']['coverage_diff_vs_confirmed5']:+.6f}"
        )

    if materially_damaged:
        recommendation = "stop_do_not_enter_portfolio"
        recommendation_text = (
            "v2 adjusted_score materially damages confirmed5 model-layer validation edge. "
            "Stop here and do not enter portfolio dry-run."
        )
    else:
        recommendation = "eligible_for_portfolio_dry_run"
        recommendation_text = (
            "v2 adjusted_score is close to confirmed5 or not materially worse on validation model-layer edge. "
            "Portfolio dry-run may be considered next, subject to unchanged execution and portfolio guardrails."
        )

    return {
        "materially_damages_confirmed5_model_edge": materially_damaged,
        "evaluation_thresholds": {
            "validation_rankic_damage_threshold": VALIDATION_RANKIC_DAMAGE_THRESHOLD,
            "validation_icir_damage_threshold": VALIDATION_ICIR_DAMAGE_THRESHOLD,
        },
        "evidence": reasons,
        "v2_row_count": v2_audit.get("row_count"),
        "v2_raw_input_null_score_rows": v2_audit.get("raw_input_null_score_rows"),
        "recommendation": recommendation,
        "recommendation_text": recommendation_text,
        "caveat": (
            "This is a MODEL-LAYER diagnosis only. It is not a portfolio, backtest, OOS, or formal metrics/readout."
        ),
    }


def render_diagnosis_section(model_name: str, split_name: str, diag: dict[str, Any]) -> list[str]:
    if "error" in diag:
        return [f"### {model_name} — {split_name}", "", f"- Error: {diag['error']}", ""]

    lines = [
        f"### {model_name} — {split_name}",
        "",
        f"- Scored rows: `{diag['scored_rows']}`",
        f"- Eligible labeled rows: `{diag['eligible_labeled_rows']}`",
        f"- Score coverage: `{diag['score_coverage']:.6f}`",
        f"- Signal dates: `{diag['n_signal_dates']}`",
        "",
        "**RankIC:**",
        f"- Mean: `{diag['rank_ic']['mean']:.6f}`",
        f"- Std: `{diag['rank_ic']['std']:.6f}`",
        f"- Positive IC %: `{diag['rank_ic']['positive_ic_pct']:.6f}`",
        f"- ICIR: `{diag['icir']:.6f}`" if diag["icir"] is not None else "- ICIR: `null`",
        f"- Top-bottom spread: `{diag['top_bottom_spread']:.6f}`" if diag["top_bottom_spread"] is not None else "- Top-bottom spread: `null`",
        "",
        "**Decile Forward Returns:**",
    ]
    for row in diag["decile_forward_returns"]:
        lines.append(
            f"- Decile {row['decile']}: mean=`{row['mean_forward_return']:.6f}`, n_days=`{row['n_days']}`"
        )
    lines.extend(["", "**Yearly Stability:**"])
    for row in diag["yearly_stability"]:
        lines.append(
            f"- {row['year']}: RankIC=`{row['rank_ic_mean']:.6f}`, ICIR=`{row['rank_ic_ir']:.6f}`"
            if row["rank_ic_ir"] is not None
            else f"- {row['year']}: RankIC=`{row['rank_ic_mean']:.6f}`, ICIR=`null`"
        )
    lines.append("")
    return lines


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, results: dict[str, Any]) -> None:
    lines = [
        "# Nonlinear Challenger v2 Model Edge Diagnosis",
        "",
        f"> **{DIAGNOSIS_LABEL}**",
        "",
        f"Generated: {results['generated_at']}",
        "",
        "## 1. Scope",
        "",
        "- This is model-layer diagnosis only.",
        "- This is not a portfolio or backtest.",
        "- This does not read frozen test.",
        "",
        "## 2. Coverage Summary",
        "",
    ]
    for split_name in ["train", "validation"]:
        cov = results["coverage_summary"][split_name]
        lines.extend(
            [
                f"### {split_name.title()}",
                "",
                f"- Eligible labeled rows: `{cov['eligible_labeled_rows']}`",
                f"- v2 scored rows: `{cov['v2_scored_rows']}`",
                f"- confirmed5 scored rows: `{cov['confirmed5_scored_rows']}`",
                f"- baseline scored rows: `{cov['baseline_scored_rows']}`",
                f"- v2 coverage: `{cov['v2_score_coverage']:.6f}`",
                f"- confirmed5 coverage: `{cov['confirmed5_score_coverage']:.6f}`",
                f"- coverage diff vs confirmed5: `{cov['coverage_diff_vs_confirmed5']:+.6f}`",
                "",
            ]
        )

    lines.extend(["## 3. Train Diagnostics", ""])
    for key, name in [("v2_train", "v2"), ("confirmed5_train", "confirmed5"), ("baseline_train", "baseline")]:
        lines.extend(render_diagnosis_section(name, "train", results["diagnostics"][key]))
    lines.extend(["## 4. Validation Diagnostics", ""])
    for key, name in [("v2_validation", "v2"), ("confirmed5_validation", "confirmed5"), ("baseline_validation", "baseline")]:
        lines.extend(render_diagnosis_section(name, "validation", results["diagnostics"][key]))

    lines.extend(
        [
            "## 5. Cross-Model Comparison",
            "",
            "| Split | Metric | v2 | confirmed5 | baseline |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for split_name in ["train", "validation"]:
        v2c = results["cross_model_comparison"]["v2_vs_confirmed5"][split_name]
        baseline = results["cross_model_comparison"]["v2_vs_baseline"][split_name]
        if v2c.get("v2_rank_ic") is not None:
            lines.append(
                f"| {split_name} | RankIC | {v2c['v2_rank_ic']:.6f} | {v2c['confirmed5_rank_ic']:.6f} | {baseline['baseline_rank_ic']:.6f} |"
            )
        if v2c.get("v2_icir") is not None:
            lines.append(
                f"| {split_name} | ICIR | {v2c['v2_icir']:.6f} | {v2c['confirmed5_icir']:.6f} | {baseline['baseline_icir']:.6f} |"
            )
        if v2c.get("v2_top_bottom_spread") is not None:
            lines.append(
                f"| {split_name} | Top-bottom spread | {v2c['v2_top_bottom_spread']:.6f} | {v2c['confirmed5_top_bottom_spread']:.6f} | {baseline['baseline_top_bottom_spread']:.6f} |"
            )

    conc = results["conclusion"]
    lines.extend(
        [
            "",
            "## 6. Conclusion",
            "",
            f"- materially_damages_confirmed5_model_edge: `{conc['materially_damages_confirmed5_model_edge']}`",
            f"- recommendation: `{conc['recommendation']}`",
            f"- v2_row_count: `{conc['v2_row_count']}`",
            f"- v2_raw_input_null_score_rows: `{conc['v2_raw_input_null_score_rows']}`",
            "",
            conc["recommendation_text"],
            "",
            conc["caveat"],
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    for path, label in [
        (args.v2_scores, "v2 scores"),
        (args.v2_audit, "v2 audit"),
        (args.confirmed5_scores, "confirmed5 scores"),
        (args.baseline_scores, "baseline scores"),
        (args.label_panel, "label panel"),
        (args.split_panel, "split panel"),
    ]:
        ensure_exists(path, label)

    v2_audit = load_json(args.v2_audit, "v2 audit")
    if require_field(v2_audit, "candidate_scheme_id", "v2 audit") != EXPECTED_V2_CANDIDATE:
        raise DiagnosisError("v2 audit candidate_scheme_id mismatch")
    if require_field(v2_audit, "training_performed", "v2 audit") is not False:
        raise DiagnosisError("v2 audit must state training_performed=false")
    if require_field(v2_audit, "frozen_test_accessed", "v2 audit") is not False:
        raise DiagnosisError("v2 audit must state frozen_test_accessed=false")

    df = load_comparison_frame(
        args.v2_scores,
        args.confirmed5_scores,
        args.baseline_scores,
        args.label_panel,
        args.split_panel,
    )
    if len(df) == 0:
        raise DiagnosisError("diagnosis frame is empty")

    train_total = int((df["train_flag"] == True).sum())
    validation_total = int((df["validation_flag"] == True).sum())
    coverage_summary = {
        "train": {
            "eligible_labeled_rows": train_total,
            "v2_scored_rows": int(((df["train_flag"] == True) & df["v2_score"].notna()).sum()),
            "confirmed5_scored_rows": int(((df["train_flag"] == True) & df["confirmed5_score"].notna()).sum()),
            "baseline_scored_rows": int(((df["train_flag"] == True) & df["baseline_score"].notna()).sum()),
        },
        "validation": {
            "eligible_labeled_rows": validation_total,
            "v2_scored_rows": int(((df["validation_flag"] == True) & df["v2_score"].notna()).sum()),
            "confirmed5_scored_rows": int(((df["validation_flag"] == True) & df["confirmed5_score"].notna()).sum()),
            "baseline_scored_rows": int(((df["validation_flag"] == True) & df["baseline_score"].notna()).sum()),
        },
    }
    for split_name in ["train", "validation"]:
        cov = coverage_summary[split_name]
        total_rows = cov["eligible_labeled_rows"]
        cov["v2_score_coverage"] = float(cov["v2_scored_rows"] / total_rows) if total_rows > 0 else None
        cov["confirmed5_score_coverage"] = (
            float(cov["confirmed5_scored_rows"] / total_rows) if total_rows > 0 else None
        )
        cov["baseline_score_coverage"] = float(cov["baseline_scored_rows"] / total_rows) if total_rows > 0 else None
        cov["coverage_diff_vs_confirmed5"] = (
            cov["v2_score_coverage"] - cov["confirmed5_score_coverage"]
            if cov["v2_score_coverage"] is not None and cov["confirmed5_score_coverage"] is not None
            else None
        )

    diagnostics = {
        "v2_train": diagnose_model(df, "v2_score", "train_flag", "forward_return_5d", train_total, "v2_train"),
        "v2_validation": diagnose_model(
            df, "v2_score", "validation_flag", "forward_return_5d", validation_total, "v2_validation"
        ),
        "confirmed5_train": diagnose_model(
            df, "confirmed5_score", "train_flag", "forward_return_5d", train_total, "confirmed5_train"
        ),
        "confirmed5_validation": diagnose_model(
            df,
            "confirmed5_score",
            "validation_flag",
            "forward_return_5d",
            validation_total,
            "confirmed5_validation",
        ),
        "baseline_train": diagnose_model(
            df, "baseline_score", "train_flag", "forward_return_5d", train_total, "baseline_train"
        ),
        "baseline_validation": diagnose_model(
            df, "baseline_score", "validation_flag", "forward_return_5d", validation_total, "baseline_validation"
        ),
    }

    cross_model = {"v2_vs_confirmed5": {}, "v2_vs_baseline": {}}
    for split_name in ["train", "validation"]:
        v2_diag = diagnostics[f"v2_{split_name}"]
        confirmed5_diag = diagnostics[f"confirmed5_{split_name}"]
        baseline_diag = diagnostics[f"baseline_{split_name}"]

        def rank_mean(diag: dict[str, Any]) -> float | None:
            return diag["rank_ic"]["mean"] if isinstance(diag.get("rank_ic"), dict) and "mean" in diag["rank_ic"] else None

        v2_rank_ic = rank_mean(v2_diag)
        c5_rank_ic = rank_mean(confirmed5_diag)
        bl_rank_ic = rank_mean(baseline_diag)

        cross_model["v2_vs_confirmed5"][split_name] = {
            "v2_rank_ic": v2_rank_ic,
            "confirmed5_rank_ic": c5_rank_ic,
            "rank_ic_delta_vs_confirmed5": (v2_rank_ic - c5_rank_ic) if v2_rank_ic is not None and c5_rank_ic is not None else None,
            "v2_icir": v2_diag.get("icir"),
            "confirmed5_icir": confirmed5_diag.get("icir"),
            "icir_delta_vs_confirmed5": (
                v2_diag.get("icir") - confirmed5_diag.get("icir")
                if v2_diag.get("icir") is not None and confirmed5_diag.get("icir") is not None
                else None
            ),
            "v2_top_bottom_spread": v2_diag.get("top_bottom_spread"),
            "confirmed5_top_bottom_spread": confirmed5_diag.get("top_bottom_spread"),
            "top_bottom_spread_delta_vs_confirmed5": (
                v2_diag.get("top_bottom_spread") - confirmed5_diag.get("top_bottom_spread")
                if v2_diag.get("top_bottom_spread") is not None and confirmed5_diag.get("top_bottom_spread") is not None
                else None
            ),
        }
        cross_model["v2_vs_baseline"][split_name] = {
            "v2_rank_ic": v2_rank_ic,
            "baseline_rank_ic": bl_rank_ic,
            "rank_ic_delta_vs_baseline": (v2_rank_ic - bl_rank_ic) if v2_rank_ic is not None and bl_rank_ic is not None else None,
            "v2_icir": v2_diag.get("icir"),
            "baseline_icir": baseline_diag.get("icir"),
            "icir_delta_vs_baseline": (
                v2_diag.get("icir") - baseline_diag.get("icir")
                if v2_diag.get("icir") is not None and baseline_diag.get("icir") is not None
                else None
            ),
            "v2_top_bottom_spread": v2_diag.get("top_bottom_spread"),
            "baseline_top_bottom_spread": baseline_diag.get("top_bottom_spread"),
            "top_bottom_spread_delta_vs_baseline": (
                v2_diag.get("top_bottom_spread") - baseline_diag.get("top_bottom_spread")
                if v2_diag.get("top_bottom_spread") is not None and baseline_diag.get("top_bottom_spread") is not None
                else None
            ),
        }

    results = {
        "diagnosis_label": DIAGNOSIS_LABEL,
        "generated_at": datetime.now().astimezone().isoformat(),
        "frozen_test_accessed": False,
        "formal_metrics_generated": False,
        "portfolio_run_executed": False,
        "models_compared": {
            "v2": {
                "candidate_scheme_id": EXPECTED_V2_CANDIDATE,
                "source": str(args.v2_scores),
                "description": "confirmed5 raw score transformed by fixed cross-sectional volatility discount",
            },
            "confirmed5": {
                "candidate_scheme_id": EXPECTED_CONFIRMED5_CANDIDATE,
                "source": str(args.confirmed5_scores),
                "description": "confirmed5 raw model_score_D0 without retraining changes",
            },
            "baseline": {
                "candidate_scheme_id": EXPECTED_BASELINE_CANDIDATE,
                "source": str(args.baseline_scores),
                "description": "exact baseline multi_equal_weight_v1 scores",
            },
        },
        "v2_transform_input_audit": {
            "row_count": v2_audit.get("row_count"),
            "raw_input_null_score_rows": v2_audit.get("raw_input_null_score_rows"),
            "score_transform_policy_version": v2_audit.get("score_transform_policy_version"),
        },
        "coverage_summary": coverage_summary,
        "diagnostics": diagnostics,
        "cross_model_comparison": cross_model,
    }
    results["conclusion"] = build_conclusion(results, v2_audit)
    return results


def main() -> int:
    args = parse_args()
    try:
        results = run(args)
    except DiagnosisError as exc:
        print(f"diagnosis failed: {exc}")
        return 1

    write_json(args.output_json, results)
    write_markdown(args.output_md, results)
    print(f"Diagnosis JSON written to {args.output_json}")
    print(f"Diagnosis Markdown written to {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
