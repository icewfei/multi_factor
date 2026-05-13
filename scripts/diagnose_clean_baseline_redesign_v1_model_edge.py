#!/usr/bin/env python3
"""
Diagnose clean baseline redesign round v1 model-layer behavior only.

This script reads score artifacts and train/validation labels for diagnosis. It
does not train, does not run portfolio, does not generate formal readouts, and
does not read frozen test data.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


ROOT = Path("/Users/wy/MiscProject/multi_factor")
DEFAULT_MANIFEST = ROOT / "configs" / "clean_baselines" / "redesign_round_v1" / "clean_baseline_redesign_manifest.json"
DEFAULT_REDESIGN_SCORES_ROOT = Path("/private/tmp/clean_baseline_redesign_round_v1/scores")
DEFAULT_OLD_FAMILY_ROOT = Path("/private/tmp/clean_baseline_family_score_gate_20260513")
DEFAULT_LABEL_PANEL = ROOT / "artifacts" / "run_state" / "project_panels_research_trainval_20211231_20260429" / "project_label_panel.parquet"
DEFAULT_SPLIT_PANEL = ROOT / "artifacts" / "run_state" / "project_panels_research_trainval_20211231_20260429" / "dataset_split_daily.parquet"
DEFAULT_P98_SCORES = ROOT / "artifacts" / "run_state" / "confirmatory_reversal_p98_trainval_20260506" / "model_scores_D0.parquet"
DEFAULT_MULTI_EQUAL_SCORES = ROOT / "artifacts" / "run_state" / "exploratory_multi_signal_composite_v1" / "model_scores_D0_multi.parquet"
DEFAULT_OUTPUT_JSON = Path("/private/tmp/clean_baseline_redesign_round_v1/model_edge_diagnosis.json")
DEFAULT_OUTPUT_MD = Path("/private/tmp/clean_baseline_redesign_round_v1/model_edge_diagnosis.md")

OLD_CLEAN_BASELINES = [
    "no_p98_reversal_baseline_v1",
    "clean_momentum_20d_baseline_v1",
    "clean_liquidity_adjusted_reversal_baseline_v1",
    "clean_equal_weight_random_eligible_baseline_v1",
]
REFERENCE_MODELS = {
    "p98_conditional_reference": {
        "candidate_scheme_id": "reversal_tail_exclude_p98_v1",
        "label": "p98 conditional baseline",
        "score_path_attr": "p98_scores",
        "effective_expression": "model_score_D0",
        "has_snapshot_id": True,
        "status": "conditional_reference_only",
    },
    "multi_equal_weight_v1_conditional_reference": {
        "candidate_scheme_id": "multi_equal_weight_v1",
        "label": "multi_equal_weight_v1 conditional baseline",
        "score_path_attr": "multi_equal_scores",
        "effective_expression": "model_score_D0",
        "has_snapshot_id": False,
        "status": "conditional_reference_only",
    },
}


class DiagnosisError(Exception):
    """Raised when diagnosis cannot be completed safely."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose clean baseline redesign round v1 model-layer edge.")
    parser.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--redesign-scores-root", type=Path, default=DEFAULT_REDESIGN_SCORES_ROOT)
    parser.add_argument("--old-family-root", type=Path, default=DEFAULT_OLD_FAMILY_ROOT)
    parser.add_argument("--label-panel", type=Path, default=DEFAULT_LABEL_PANEL)
    parser.add_argument("--split-panel", type=Path, default=DEFAULT_SPLIT_PANEL)
    parser.add_argument("--p98-scores", type=Path, default=DEFAULT_P98_SCORES)
    parser.add_argument("--multi-equal-scores", type=Path, default=DEFAULT_MULTI_EQUAL_SCORES)
    parser.add_argument("--topk", type=int, default=30)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def ensure_exists(path: Path, label: str) -> None:
    if not path.exists():
        raise DiagnosisError(f"{label} not found: {path}")


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
    if std_value in (None, 0.0):
        return mean_value, std_value, None
    return mean_value, std_value, float(mean_value / (std_value / math.sqrt(len(clean))))


def build_model_specs(args: argparse.Namespace, manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    specs: dict[str, dict[str, Any]] = {}
    for candidate in manifest["candidates"]:
        baseline_id = candidate["baseline_id"]
        specs[baseline_id] = {
            "candidate_scheme_id": baseline_id,
            "label": baseline_id,
            "score_path": args.redesign_scores_root / baseline_id / "model_scores_D0.parquet",
            "audit_path": args.redesign_scores_root / baseline_id / "model_scores_D0_audit.json",
            "effective_expression": "-model_score_D0",
            "has_snapshot_id": True,
            "status": "redesign_clean_candidate",
        }
    for baseline_id in OLD_CLEAN_BASELINES:
        specs[baseline_id] = {
            "candidate_scheme_id": baseline_id,
            "label": baseline_id,
            "score_path": args.old_family_root / baseline_id / "model_scores_D0.parquet",
            "audit_path": args.old_family_root / baseline_id / "model_scores_D0_audit.json",
            "effective_expression": "-model_score_D0",
            "has_snapshot_id": True,
            "status": "old_clean_baseline",
        }
    for key, spec in REFERENCE_MODELS.items():
        specs[key] = {
            **spec,
            "score_path": getattr(args, spec["score_path_attr"]),
            "audit_path": None,
        }
    return specs


def validate_clean_audits(specs: dict[str, dict[str, Any]]) -> None:
    for key, spec in specs.items():
        audit_path = spec.get("audit_path")
        if not audit_path:
            continue
        ensure_exists(audit_path, f"{key} audit")
        audit = load_json(audit_path)
        if audit.get("frozen_test_accessed") is not False:
            raise DiagnosisError(f"{key} audit indicates frozen_test_accessed is not false")
        if audit.get("p98_used") is not False:
            raise DiagnosisError(f"{key} audit indicates p98_used is not false")
        if audit.get("label_diagnostics_used") is not False:
            raise DiagnosisError(f"{key} audit indicates label_diagnostics_used is not false")


def register_views(con: duckdb.DuckDBPyConnection, specs: dict[str, dict[str, Any]], args: argparse.Namespace) -> None:
    con.execute(
        f"""
        CREATE OR REPLACE TEMP VIEW label_t AS
        SELECT snapshot_id, instrument, signal_date, label_5d_next_open_close AS forward_return_5d
        FROM read_parquet('{sql_path(args.label_panel)}')
        WHERE label_defined
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TEMP VIEW split_t AS
        SELECT snapshot_id, instrument, signal_date, split_bucket, train_flag, validation_flag
        FROM read_parquet('{sql_path(args.split_panel)}')
        WHERE train_flag OR validation_flag
        """
    )
    for key, spec in specs.items():
        ensure_exists(spec["score_path"], f"{key} scores")
        con.execute(
            f"""
            CREATE OR REPLACE TEMP VIEW {key}_score_t AS
            SELECT
                {'CAST(snapshot_id AS VARCHAR)' if spec['has_snapshot_id'] else 'NULL'} AS snapshot_id,
                instrument,
                signal_date,
                model_score_D0 AS raw_score,
                {spec['effective_expression']} AS effective_score
            FROM read_parquet('{sql_path(spec['score_path'])}')
            WHERE candidate_scheme_id = '{spec['candidate_scheme_id']}'
            """
        )


def fetch_joined_model_frame(
    con: duckdb.DuckDBPyConnection,
    *,
    model_key: str,
    has_snapshot_id: bool,
) -> pd.DataFrame:
    join_clause = (
        f"l.snapshot_id = m.snapshot_id AND l.instrument = m.instrument AND l.signal_date = m.signal_date"
        if has_snapshot_id
        else "l.instrument = m.instrument AND l.signal_date = m.signal_date"
    )
    return con.execute(
        f"""
        SELECT
            l.snapshot_id,
            l.instrument,
            l.signal_date,
            l.forward_return_5d,
            s.split_bucket,
            s.train_flag,
            s.validation_flag,
            m.raw_score,
            m.effective_score
        FROM label_t l
        INNER JOIN split_t s
          ON l.snapshot_id = s.snapshot_id
         AND l.instrument = s.instrument
         AND l.signal_date = s.signal_date
        LEFT JOIN {model_key}_score_t m
          ON {join_clause}
        """
    ).df()


def compute_deciles(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    rows: list[dict[str, Any]] = []
    work = frame.dropna(subset=["effective_score", "forward_return_5d"]).copy()
    if work.empty:
        return []
    work["decile"] = work.groupby("signal_date")["effective_score"].rank(method="first", ascending=False)
    counts = work.groupby("signal_date")["instrument"].transform("count")
    work["decile"] = ((work["decile"] - 1) / counts * 10).astype(int).clip(0, 9) + 1
    for decile, group in work.groupby("decile", sort=True):
        rows.append(
            {
                "decile": int(decile),
                "mean_forward_return": float(group["forward_return_5d"].mean()),
                "row_count": int(len(group)),
            }
        )
    return rows


def split_metrics(frame: pd.DataFrame, *, topk: int) -> dict[str, Any]:
    scored = frame.dropna(subset=["effective_score", "forward_return_5d"]).copy()
    eligible_rows = int(len(frame))
    scored_rows = int(len(scored))
    if scored.empty:
        return {
            "coverage": {"eligible_rows": eligible_rows, "scored_rows": 0, "score_coverage": 0.0},
            "rank_ic": {"mean": None, "std": None, "t_stat": None, "daily_count": 0},
            "icir": None,
            "top_bottom_spread": None,
            "decile_forward_return": [],
            "yearly_stability": [],
            "topk_head_proxy": {"topk": topk, "mean_topk_forward_return": None, "topk_minus_nextk": None},
            "score_coverage_difference": None,
        }
    daily_ics: list[dict[str, Any]] = []
    topk_rows: list[dict[str, Any]] = []
    deciles = compute_deciles(scored)
    for signal_date, day in scored.groupby("signal_date"):
        if day["effective_score"].nunique() >= 2 and day["forward_return_5d"].nunique() >= 2:
            daily_ics.append(
                {
                    "signal_date": str(signal_date),
                    "rank_ic": float(day["effective_score"].corr(day["forward_return_5d"], method="spearman")),
                }
            )
        ordered = day.sort_values(["effective_score", "instrument"], ascending=[False, True])
        if len(ordered) >= topk * 2:
            top = ordered.head(topk)["forward_return_5d"].mean()
            nextk = ordered.iloc[topk : topk * 2]["forward_return_5d"].mean()
            topk_rows.append({"signal_date": str(signal_date), "topk": float(top), "nextk": float(nextk), "spread": float(top - nextk)})
    ic_frame = pd.DataFrame(daily_ics)
    topk_frame = pd.DataFrame(topk_rows)
    rank_ic_mean, rank_ic_std, rank_ic_t = (
        mean_std_tstat(ic_frame["rank_ic"]) if not ic_frame.empty else (None, None, None)
    )
    yearly: list[dict[str, Any]] = []
    if not ic_frame.empty:
        ic_frame["year"] = ic_frame["signal_date"].str[:4]
        for year, group in ic_frame.groupby("year", sort=True):
            year_mean, year_std, _ = mean_std_tstat(group["rank_ic"])
            yearly.append({"year": str(year), "rank_ic_mean": year_mean, "rank_ic_std": year_std, "n_days": int(len(group))})
    top_decile = next((row["mean_forward_return"] for row in deciles if row["decile"] == 1), None)
    bottom_decile = next((row["mean_forward_return"] for row in deciles if row["decile"] == 10), None)
    topk_mean, _, topk_t = (
        mean_std_tstat(topk_frame["topk"]) if not topk_frame.empty else (None, None, None)
    )
    spread_mean, _, spread_t = (
        mean_std_tstat(topk_frame["spread"]) if not topk_frame.empty else (None, None, None)
    )
    return {
        "coverage": {
            "eligible_rows": eligible_rows,
            "scored_rows": scored_rows,
            "score_coverage": scored_rows / eligible_rows if eligible_rows else None,
            "signal_dates": int(scored["signal_date"].nunique()),
            "instruments": int(scored["instrument"].nunique()),
        },
        "rank_ic": {
            "mean": rank_ic_mean,
            "std": rank_ic_std,
            "t_stat": rank_ic_t,
            "daily_count": int(len(ic_frame)),
        },
        "icir": rank_ic_mean / rank_ic_std if rank_ic_mean is not None and rank_ic_std not in (None, 0.0) else None,
        "top_bottom_spread": top_decile - bottom_decile if top_decile is not None and bottom_decile is not None else None,
        "decile_forward_return": deciles,
        "yearly_stability": yearly,
        "topk_head_proxy": {
            "topk": topk,
            "n_days": int(len(topk_frame)),
            "mean_topk_forward_return": topk_mean,
            "topk_mean_t_stat": topk_t,
            "topk_minus_nextk": spread_mean,
            "topk_minus_nextk_t_stat": spread_t,
        },
        "score_coverage_difference": None,
    }


def diagnose_model(frame: pd.DataFrame, *, topk: int) -> dict[str, Any]:
    return {
        "train": split_metrics(frame[frame["train_flag"]], topk=topk),
        "validation": split_metrics(frame[frame["validation_flag"]], topk=topk),
    }


def build_conclusion(diagnostics: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    no_p98_val = diagnostics["no_p98_reversal_baseline_v1"]["validation"]
    no_p98_rankic = no_p98_val["rank_ic"]["mean"]
    no_p98_topk = no_p98_val["topk_head_proxy"]["mean_topk_forward_return"]
    no_p98_spread = no_p98_val["topk_head_proxy"]["topk_minus_nextk"]
    clean_candidate_ids = [candidate["baseline_id"] for candidate in manifest["candidates"]]
    candidate_results: dict[str, Any] = {}
    recommended: list[str] = []
    for baseline_id in clean_candidate_ids:
        val = diagnostics[baseline_id]["validation"]
        rankic = val["rank_ic"]["mean"]
        topk = val["topk_head_proxy"]["mean_topk_forward_return"]
        spread = val["topk_head_proxy"]["topk_minus_nextk"]
        rankic_beats_no_p98 = (
            rankic is not None and no_p98_rankic is not None and rankic > no_p98_rankic + 0.005
        )
        topk_positive = topk is not None and topk > 0
        spread_positive = spread is not None and spread > 0
        recommend = bool(rankic_beats_no_p98 and topk_positive and spread_positive)
        if recommend:
            recommended.append(baseline_id)
        candidate_results[baseline_id] = {
            "validation_rankic": rankic,
            "validation_rankic_beats_no_p98": rankic_beats_no_p98,
            "validation_topk_head_proxy": topk,
            "validation_topk_head_proxy_positive": topk_positive,
            "validation_topk_minus_nextk": spread,
            "validation_topk_minus_nextk_positive": spread_positive,
            "recommend_same_contract_portfolio_dry_run_preparation": recommend,
        }
    return {
        "no_p98_validation_rankic": no_p98_rankic,
        "no_p98_validation_topk_head_proxy": no_p98_topk,
        "no_p98_validation_topk_minus_nextk": no_p98_spread,
        "candidate_results": candidate_results,
        "recommended_for_same_contract_portfolio_dry_run_preparation": recommended,
        "any_candidate_recommended": bool(recommended),
        "can_replace_p98_conditional_baseline": False,
        "can_parallel_p98_conditional_baseline": bool(recommended),
        "interpretation": (
            "At least one clean redesign candidate clears the model-layer preparation screen."
            if recommended
            else "No clean redesign candidate clears RankIC plus TopK head plus TopK-minus-nextK requirements; continue not running portfolio."
        ),
    }


def build_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Clean Baseline Redesign Round V1 Model-Layer Diagnosis",
        "",
        "Trainval model-layer diagnosis only. Not OOS, not strategy approval, not portfolio, not a formal metrics/readout.",
        "",
        "## Candidate Summary",
        "",
    ]
    for baseline_id, result in payload["conclusion"]["candidate_results"].items():
        lines.append(
            f"- `{baseline_id}`: validation RankIC `{result['validation_rankic']}`, "
            f"TopK `{result['validation_topk_head_proxy']}`, "
            f"TopK-minus-nextK `{result['validation_topk_minus_nextk']}`, "
            f"recommend `{result['recommend_same_contract_portfolio_dry_run_preparation']}`"
        )
    lines.extend(
        [
            "",
            "## Conclusion",
            "",
            f"- recommended candidates: `{payload['conclusion']['recommended_for_same_contract_portfolio_dry_run_preparation']}`",
            f"- can replace p98 conditional baseline: `{payload['conclusion']['can_replace_p98_conditional_baseline']}`",
            f"- can parallel p98 conditional baseline: `{payload['conclusion']['can_parallel_p98_conditional_baseline']}`",
            f"- interpretation: {payload['conclusion']['interpretation']}",
        ]
    )
    return "\n".join(lines) + "\n"


def run_diagnosis(args: argparse.Namespace) -> dict[str, Any]:
    for path, label in [
        (args.manifest_json, "manifest"),
        (args.label_panel, "label panel"),
        (args.split_panel, "split panel"),
        (args.p98_scores, "p98 conditional scores"),
        (args.multi_equal_scores, "multi_equal conditional scores"),
    ]:
        ensure_exists(path, label)
    manifest = load_json(args.manifest_json)
    specs = build_model_specs(args, manifest)
    validate_clean_audits(specs)

    con = duckdb.connect()
    try:
        register_views(con, specs, args)
        diagnostics = {
            key: diagnose_model(
                fetch_joined_model_frame(con, model_key=key, has_snapshot_id=spec["has_snapshot_id"]),
                topk=args.topk,
            )
            | {
                "candidate_scheme_id": spec["candidate_scheme_id"],
                "status": spec["status"],
                "label": spec["label"],
            }
            for key, spec in specs.items()
        }
    finally:
        con.close()

    # Fill score coverage differences relative to no_p98 for each split.
    for split in ("train", "validation"):
        base_cov = diagnostics["no_p98_reversal_baseline_v1"][split]["coverage"]["score_coverage"]
        for item in diagnostics.values():
            cov = item[split]["coverage"]["score_coverage"]
            item[split]["score_coverage_difference"] = (
                cov - base_cov if cov is not None and base_cov is not None else None
            )

    return {
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "round_id": "clean_baseline_redesign_round_v1",
        "diagnosis_label": "MODEL_LAYER_DIAGNOSIS_ONLY_NOT_PORTFOLIO_NOT_OOS",
        "training_performed": False,
        "portfolio_run_executed": False,
        "formal_metrics_generated": False,
        "frozen_test_accessed": False,
        "p98_reference_status": "conditional_reference_only",
        "multi_equal_weight_v1_reference_status": "conditional_reference_only",
        "topk": args.topk,
        "diagnostics": diagnostics,
        "conclusion": build_conclusion(diagnostics, manifest),
    }


def main() -> None:
    args = parse_args()
    payload = run_diagnosis(args)
    write_json(args.output_json, payload)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(build_markdown(payload), encoding="utf-8")


if __name__ == "__main__":
    main()
