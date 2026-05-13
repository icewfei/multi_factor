#!/opt/anaconda3/envs/quant_trade/bin/python
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
RESEARCH_REGISTRY_DIR = ROOT / "artifacts" / "research_registry"

DEFAULT_RUN_ID = "exploratory_cross_horizon_c1_reversal_only"
DEFAULT_RUN_DIR = RUN_STATE_DIR / DEFAULT_RUN_ID
DEFAULT_PROJECT_PANELS_DIR = RUN_STATE_DIR / "project_panels_research_trainval_20211231_20260429"
DEFAULT_RUN_INPUT_CONTRACT = ROOT / "contracts" / "run_input_contract.research_trainval_20211231.json"
DEFAULT_BUILD_SCRIPT = ROOT / "scripts" / "build_baseline_model_scores.py"
DEFAULT_C1_BUILDER = ROOT / "scripts" / "build_baseline_model_scores.py"
DEFAULT_P98_BUILDER = ROOT / "scripts" / "build_reversal_tail_composite_model_scores.py"
DEFAULT_CANDIDATE_REGISTRY = RESEARCH_REGISTRY_DIR / "candidate_scheme_registry.jsonl"
DEFAULT_C1_ROUND_PREREG = (
    RESEARCH_REGISTRY_DIR
    / "research_rounds"
    / "rr_exploratory_cross_horizon_reversal_momentum_20260501"
    / "preregistration.json"
)
DEFAULT_P98_TAIL_PREREG = (
    RESEARCH_REGISTRY_DIR
    / "research_rounds"
    / "rr_exploratory_reversal_tail_handling_20260502"
    / "preregistration.json"
)
DEFAULT_P98_SCORE_PATH = RUN_STATE_DIR / "confirmatory_reversal_p98_trainval_20260506" / "model_scores_D0.parquet"
DEFAULT_P98_AUDIT_PATH = RUN_STATE_DIR / "confirmatory_reversal_p98_trainval_20260506" / "model_scores_D0_audit.json"
DEFAULT_ATTEMPT_ID = "attempt_rebuild_source_chain_provenance"

TARGET_CANDIDATE_SCHEME_ID = "exploratory_cross_horizon_c1_reversal_only"
TARGET_FEATURE_PRESET = "single_signal_reversal_5d_v1"

FUTURE_FIELD_TERMS = (
    "next_open",
    "next_close",
    "open_d1",
    "close_d1",
    "close_d5",
    "lead(",
    "following",
)
LABEL_OR_REALIZED_RETURN_TERMS = (
    "label_",
    "forward_label",
    "realized_return",
    "execution_delayed_realized_return",
    "actual_exit_date",
    "actual_sell_price",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rebuild baseline c1/p98 source-chain artifacts without running portfolio.")
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--project-panels-dir", type=Path, default=DEFAULT_PROJECT_PANELS_DIR)
    parser.add_argument("--run-input-contract", type=Path, default=DEFAULT_RUN_INPUT_CONTRACT)
    parser.add_argument("--build-script", type=Path, default=DEFAULT_BUILD_SCRIPT)
    parser.add_argument("--c1-builder", type=Path, default=DEFAULT_C1_BUILDER)
    parser.add_argument("--p98-builder", type=Path, default=DEFAULT_P98_BUILDER)
    parser.add_argument("--candidate-registry", type=Path, default=DEFAULT_CANDIDATE_REGISTRY)
    parser.add_argument("--c1-round-prereg", type=Path, default=DEFAULT_C1_ROUND_PREREG)
    parser.add_argument("--p98-tail-prereg", type=Path, default=DEFAULT_P98_TAIL_PREREG)
    parser.add_argument("--p98-score-path", type=Path, default=DEFAULT_P98_SCORE_PATH)
    parser.add_argument("--p98-audit-path", type=Path, default=DEFAULT_P98_AUDIT_PATH)
    parser.add_argument("--attempt-id", default=DEFAULT_ATTEMPT_ID)
    return parser


def read_text(path: Path, label: str) -> str:
    return path.read_text(encoding="utf-8")


def read_json(path: Path, label: str) -> dict[str, Any]:
    payload = json.loads(read_text(path, label))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return payload


def read_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"JSONL row must be object: {path}")
        rows.append(payload)
    return rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def collect_term_hits(text: str, terms: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    return [term for term in terms if term.lower() in lowered]


def parse_score_rule_direction(score_rule: str | None) -> str | None:
    if not score_rule:
        return None
    lowered = score_rule.lower()
    if "reversal_5d_raw asc" in lowered:
        return "ASC"
    if "reversal_5d_raw desc" in lowered:
        return "DESC"
    return None


def ensure_input_exists(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} not found: {path}")


def symlink_or_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        return
    try:
        dst.symlink_to(src)
    except OSError:
        if src.is_file():
            shutil.copy2(src, dst)
        else:
            raise


def stage_run_inputs(run_dir: Path, project_panels_dir: Path, attempt_dir: Path) -> None:
    for name in (
        "project_sample_panel.parquet",
        "project_label_panel.parquet",
        "project_execution_panel.parquet",
        "data_quality_audit.json",
    ):
        src = project_panels_dir / name
        ensure_input_exists(src, f"project panel input {name}")
        symlink_or_copy(src, run_dir / name)
        symlink_or_copy(src, attempt_dir / "inputs" / name)


def find_candidate_registry_row(path: Path) -> dict[str, Any]:
    rows = read_jsonl(path)
    for row in rows:
        if row.get("candidate_scheme_id") == TARGET_CANDIDATE_SCHEME_ID:
            return row
    raise ValueError(f"candidate registry row missing for {TARGET_CANDIDATE_SCHEME_ID}")


def inspect_c1_direction(builder_text: str, registry_row: dict[str, Any]) -> dict[str, Any]:
    metadata_score_rule = registry_row.get("score_rule")
    metadata_direction = parse_score_rule_direction(metadata_score_rule)

    preset_uses_reversal_rank = '("reversal_5d_raw", "reversal_rank")' in builder_text
    reversal_rank_direction = (
        "ASC" if "ORDER BY reversal_5d_raw ASC, instrument ASC" in builder_text else None
    )
    implementation_direction = "ASC" if preset_uses_reversal_rank and reversal_rank_direction == "ASC" else None

    return {
        "registry_score_rule": metadata_score_rule,
        "registry_direction": metadata_direction,
        "implementation_direction": implementation_direction,
        "metadata_matches_implementation": (
            metadata_direction == implementation_direction
            if metadata_direction is not None and implementation_direction is not None
            else None
        ),
    }


def inspect_d0_and_leakage(builder_text: str) -> dict[str, Any]:
    future_hits = collect_term_hits(builder_text, FUTURE_FIELD_TERMS)
    label_hits = collect_term_hits(builder_text, LABEL_OR_REALIZED_RETURN_TERMS)
    d0_checks = {
        "trade_date_as_signal_date": "trade_date AS signal_date" in builder_text,
        "reversal_uses_lag5": "(adj_close / LAG(adj_close, 5) OVER w - 1.0) AS reversal_5d_raw" in builder_text,
        "ranking_guard_present": "WHERE ranking_eligible_D0" in builder_text,
        "lead_absent": "LEAD(" not in builder_text,
        "following_absent": "FOLLOWING" not in builder_text,
    }
    return {
        "d0_visibility_checks": d0_checks,
        "d0_visibility_pass": all(d0_checks.values()),
        "future_field_hits": future_hits,
        "label_or_realized_return_hits": label_hits,
        "leakage_pass": not future_hits and not label_hits,
    }


def run_c1_build(args: argparse.Namespace) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(args.build_script),
        "--run-id",
        args.run_id,
        "--input-dir",
        str(args.run_dir),
        "--candidate-scheme-id",
        TARGET_CANDIDATE_SCHEME_ID,
        "--min-feature-count",
        "1",
        "--feature-preset",
        TARGET_FEATURE_PRESET,
        "--run-input-contract",
        str(args.run_input_contract),
    ]
    return subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def summarize_c1_scores(score_path: Path) -> dict[str, Any]:
    con = duckdb.connect()
    try:
        score_sql = score_path.resolve().as_posix()
        candidate_rows = con.execute(
            f"""
            SELECT
                candidate_scheme_id,
                COUNT(*) AS row_count,
                SUM(CASE WHEN model_score_D0 IS NULL THEN 1 ELSE 0 END) AS null_score_count,
                SUM(CASE WHEN model_score_D0 IS NOT NULL AND NOT isfinite(model_score_D0) THEN 1 ELSE 0 END) AS nonfinite_score_count,
                SUM(CASE WHEN model_score_D0 IS NOT NULL AND ABS(model_score_D0 - reversal_rank) < 1e-12 THEN 1 ELSE 0 END) AS matches_reversal_rank_count,
                SUM(CASE WHEN model_score_D0 IS NOT NULL AND ABS(model_score_D0 - reversal_followthrough_rank) < 1e-12 THEN 1 ELSE 0 END) AS matches_reversal_followthrough_count
            FROM read_parquet('{score_sql}')
            GROUP BY 1
            """
        ).fetchall()
        if len(candidate_rows) != 1:
            raise ValueError(f"Expected exactly one candidate_scheme_id in rebuilt c1 score file: {candidate_rows}")
        row = candidate_rows[0]
        return {
            "candidate_scheme_id": row[0],
            "row_count": int(row[1] or 0),
            "null_score_count": int(row[2] or 0),
            "nonfinite_score_count": int(row[3] or 0),
            "matches_reversal_rank_count": int(row[4] or 0),
            "matches_reversal_followthrough_count": int(row[5] or 0),
        }
    finally:
        con.close()


def summarize_p98_scores(score_path: Path) -> dict[str, Any]:
    con = duckdb.connect()
    try:
        score_sql = score_path.resolve().as_posix()
        rows = con.execute(
            f"""
            SELECT
                candidate_scheme_id,
                COUNT(*) AS row_count,
                SUM(CASE WHEN model_score_D0 IS NULL THEN 1 ELSE 0 END) AS null_score_count,
                SUM(CASE WHEN model_score_D0 IS NOT NULL AND NOT isfinite(model_score_D0) THEN 1 ELSE 0 END) AS nonfinite_score_count
            FROM read_parquet('{score_sql}')
            GROUP BY 1
            """
        ).fetchall()
        return [
            {
                "candidate_scheme_id": row[0],
                "row_count": int(row[1] or 0),
                "null_score_count": int(row[2] or 0),
                "nonfinite_score_count": int(row[3] or 0),
            }
            for row in rows
        ]
    finally:
        con.close()


def inspect_p98_feedback_risk(p98_tail_prereg: dict[str, Any], p98_audit: dict[str, Any] | None) -> dict[str, Any]:
    prereg_text = json.dumps(p98_tail_prereg, ensure_ascii=False)
    label_based = any(
        token in prereg_text
        for token in (
            "top10_avg_label",
            "top10_bot10_spread",
            "label_5d_next_open_close",
            "median_daily_ic",
        )
    )
    return {
        "label_based_learnability_diagnostics_detected": label_based,
        "fixed_test_reference_detected": "artifacts/fixed_test/" in prereg_text,
        "source_runs": p98_audit.get("source_runs") if p98_audit else None,
        "risk_status": "blocked" if label_based else "pass",
    }


def build_attempt_manifest(
    *,
    args: argparse.Namespace,
    attempt_dir: Path,
    run_dir: Path,
    source_chain_status: str,
) -> dict[str, Any]:
    return {
        "run_id": args.run_id,
        "attempt_id": args.attempt_id,
        "run_type": "source_chain_rebuild",
        "status": source_chain_status,
        "started_at": datetime.now().astimezone().isoformat(),
        "attempt_dir": attempt_dir.as_posix(),
        "input_paths": {
            "project_sample_panel": (attempt_dir / "inputs" / "project_sample_panel.parquet").as_posix(),
            "project_label_panel": (attempt_dir / "inputs" / "project_label_panel.parquet").as_posix(),
            "project_execution_panel": (attempt_dir / "inputs" / "project_execution_panel.parquet").as_posix(),
            "base_data_quality_audit": (attempt_dir / "inputs" / "data_quality_audit.json").as_posix(),
        },
        "source_input_paths": {
            "project_sample_panel": (run_dir / "project_sample_panel.parquet").as_posix(),
            "project_label_panel": (run_dir / "project_label_panel.parquet").as_posix(),
            "project_execution_panel": (run_dir / "project_execution_panel.parquet").as_posix(),
            "base_data_quality_audit": (run_dir / "data_quality_audit.json").as_posix(),
        },
        "output_paths": {
            "model_scores_D0": (run_dir / "model_scores_D0.parquet").as_posix(),
            "model_scores_D0_audit": (run_dir / "model_scores_D0_audit.json").as_posix(),
            "data_quality_audit": (attempt_dir / "data_quality_audit.json").as_posix(),
            "source_chain_audit": (run_dir / "source_chain_audit.json").as_posix(),
        },
        "parameters": {
            "candidate_scheme_id": TARGET_CANDIDATE_SCHEME_ID,
            "feature_preset": TARGET_FEATURE_PRESET,
            "min_feature_count": 1,
            "portfolio_ran": False,
            "frozen_test_accessed": False,
        },
        "notes": [
            "Controlled source-chain rebuild only.",
            "No portfolio ranking/execution/backtest outputs were produced.",
            "No frozen test access.",
        ],
    }


def build_data_quality_audit(
    *,
    args: argparse.Namespace,
    c1_summary: dict[str, Any],
    d0_and_leakage: dict[str, Any],
    direction_audit: dict[str, Any],
) -> dict[str, Any]:
    warnings: list[str] = []
    if direction_audit["metadata_matches_implementation"] is False:
        warnings.append("registry score_rule direction does not match implementation direction")
    return {
        "run_id": args.run_id,
        "attempt_id": args.attempt_id,
        "run_type": "source_chain_rebuild",
        "candidate_scheme_id": TARGET_CANDIDATE_SCHEME_ID,
        "summary_counts": {
            "row_count": c1_summary["row_count"],
            "null_score_count": c1_summary["null_score_count"],
            "nonfinite_score_count": c1_summary["nonfinite_score_count"],
        },
        "direction_audit": {
            "registry_direction": direction_audit["registry_direction"],
            "implementation_direction": direction_audit["implementation_direction"],
            "matches_reversal_rank_count": c1_summary["matches_reversal_rank_count"],
            "matches_reversal_followthrough_count": c1_summary["matches_reversal_followthrough_count"],
        },
        "d0_visibility_pass": d0_and_leakage["d0_visibility_pass"],
        "leakage_pass": d0_and_leakage["leakage_pass"],
        "fatal_blockers": [],
        "warnings": warnings,
        "notes": [
            "Project-side source-chain rebuild only.",
            "No portfolio or formal readout outputs were produced.",
        ],
    }


def build_source_chain_audit(
    *,
    args: argparse.Namespace,
    source_chain_status: str,
    c1_summary: dict[str, Any] | None,
    direction_audit: dict[str, Any],
    d0_and_leakage: dict[str, Any],
    p98_feedback_audit: dict[str, Any],
    p98_score_summary: list[dict[str, Any]] | None,
    blocker_messages: list[str],
) -> dict[str, Any]:
    return {
        "run_id": args.run_id,
        "attempt_id": args.attempt_id,
        "source_chain_status": source_chain_status,
        "baseline_status_recommendation": (
            "continue_conditional_baseline"
            if source_chain_status != "pass"
            else "eligible_for_reaudit"
        ),
        "c1_rebuild": {
            "candidate_scheme_id": TARGET_CANDIDATE_SCHEME_ID,
            "feature_preset": TARGET_FEATURE_PRESET,
            "row_count": c1_summary["row_count"] if c1_summary else None,
            "null_score_count": c1_summary["null_score_count"] if c1_summary else None,
            "nonfinite_score_count": c1_summary["nonfinite_score_count"] if c1_summary else None,
        },
        "d0_visibility_audit": {
            "pass": d0_and_leakage["d0_visibility_pass"],
            "checks": d0_and_leakage["d0_visibility_checks"],
        },
        "leakage_audit": {
            "pass": d0_and_leakage["leakage_pass"],
            "future_field_hits": d0_and_leakage["future_field_hits"],
            "label_or_realized_return_hits": d0_and_leakage["label_or_realized_return_hits"],
        },
        "score_direction_audit": {
            **direction_audit,
            "rebuilt_score_matches_reversal_rank_count": (
                c1_summary["matches_reversal_rank_count"] if c1_summary else None
            ),
            "rebuilt_score_matches_reversal_followthrough_count": (
                c1_summary["matches_reversal_followthrough_count"] if c1_summary else None
            ),
            "recommended_action": (
                "keep blocker until registry or executed lineage is reconciled"
                if direction_audit["metadata_matches_implementation"] is False
                else "no direction blocker from accessible evidence"
            ),
        },
        "p98_provenance_audit": {
            **p98_feedback_audit,
            "score_summary": p98_score_summary,
        },
        "blockers": blocker_messages,
        "notes": [
            "This rebuild does not run portfolio ranking/execution.",
            "No frozen test access.",
            "No baseline logic was changed.",
        ],
    }


def build_markdown(audit: dict[str, Any], run_dir: Path) -> list[str]:
    return [
        "# baseline c1 p98 source-chain rebuild",
        "",
        "## Scope",
        "",
        "- Controlled source-chain rebuild only.",
        "- No ML training, no portfolio run, no formal metrics/readout, no frozen-test access.",
        "",
        "## Outputs",
        "",
        f"- `{(run_dir / 'model_scores_D0.parquet').as_posix()}`",
        f"- `{(run_dir / 'attempts' / audit['attempt_id'] / 'run_state_attempt_manifest.json').as_posix()}`",
        f"- `{(run_dir / 'attempts' / audit['attempt_id'] / 'data_quality_audit.json').as_posix()}`",
        f"- `{(run_dir / 'source_chain_audit.json').as_posix()}`",
        "",
        "## Result",
        "",
        f"- source_chain_status: `{audit['source_chain_status']}`",
        f"- baseline_status_recommendation: `{audit['baseline_status_recommendation']}`",
        f"- c1 row_count: `{audit['c1_rebuild']['row_count']}`",
        f"- c1 null_score_count: `{audit['c1_rebuild']['null_score_count']}`",
        f"- c1 nonfinite_score_count: `{audit['c1_rebuild']['nonfinite_score_count']}`",
        f"- D0 visibility pass: `{audit['d0_visibility_audit']['pass']}`",
        f"- leakage pass: `{audit['leakage_audit']['pass']}`",
        f"- registry direction: `{audit['score_direction_audit']['registry_direction']}`",
        f"- implementation direction: `{audit['score_direction_audit']['implementation_direction']}`",
        f"- p98 feedback risk status: `{audit['p98_provenance_audit']['risk_status']}`",
        "",
        "## Blockers",
        "",
    ] + [f"- {item}" for item in audit["blockers"]]


def run_rebuild(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = args.run_dir
    attempt_dir = run_dir / "attempts" / args.attempt_id
    run_dir.mkdir(parents=True, exist_ok=True)
    attempt_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = attempt_dir / "run_state_attempt_manifest.json"
    attempt_audit_path = attempt_dir / "data_quality_audit.json"
    source_chain_audit_path = run_dir / "source_chain_audit.json"
    latest_attempt_path = run_dir / "run_state_latest_attempt.json"

    blocker_messages: list[str] = []

    c1_builder_text = read_text(args.c1_builder, "c1 builder")
    p98_builder_text = read_text(args.p98_builder, "p98 builder")
    registry_row = find_candidate_registry_row(args.candidate_registry)
    direction_audit = inspect_c1_direction(c1_builder_text, registry_row)
    d0_and_leakage = inspect_d0_and_leakage(c1_builder_text)

    p98_tail_prereg = read_json(args.p98_tail_prereg, "p98 tail preregistration")
    p98_audit = read_optional_json(args.p98_audit_path)
    p98_feedback_audit = inspect_p98_feedback_risk(p98_tail_prereg, p98_audit)

    try:
        ensure_input_exists(args.project_panels_dir, "project panels directory")
        ensure_input_exists(args.run_input_contract, "run input contract")
        run_input_contract = read_json(args.run_input_contract, "run input contract")
        source_db = Path(run_input_contract["source_root"]["snapshot_path"]) / "duckdb" / "warehouse.duckdb"
        ensure_input_exists(source_db, "shared warehouse DB")
        ensure_input_exists(args.build_script, "build script")
        ensure_input_exists(args.p98_score_path, "p98 score parquet")

        stage_run_inputs(run_dir, args.project_panels_dir, attempt_dir)

        result = run_c1_build(args)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "c1 rebuild subprocess failed")

        c1_score_path = run_dir / "model_scores_D0.parquet"
        c1_score_audit_path = run_dir / "model_scores_D0_audit.json"
        ensure_input_exists(c1_score_path, "rebuilt c1 model_scores_D0.parquet")
        ensure_input_exists(c1_score_audit_path, "rebuilt c1 model_scores_D0_audit.json")

        c1_summary = summarize_c1_scores(c1_score_path)
        p98_score_summary = summarize_p98_scores(args.p98_score_path)

        if direction_audit["metadata_matches_implementation"] is False:
            blocker_messages.append("registry score_rule direction mismatch remains unresolved after rebuild")
        if p98_feedback_audit["risk_status"] == "blocked":
            blocker_messages.append("p98 tail-handling still depends on label-based learnability diagnostics")
        if not d0_and_leakage["d0_visibility_pass"]:
            blocker_messages.append("c1 D0 visibility audit failed")
        if not d0_and_leakage["leakage_pass"]:
            blocker_messages.append("c1 leakage audit failed")

        source_chain_status = "pass" if not blocker_messages else "conditional_pass"

        manifest = build_attempt_manifest(
            args=args,
            attempt_dir=attempt_dir,
            run_dir=run_dir,
            source_chain_status=source_chain_status,
        )
        data_quality_audit = build_data_quality_audit(
            args=args,
            c1_summary=c1_summary,
            d0_and_leakage=d0_and_leakage,
            direction_audit=direction_audit,
        )
        source_chain_audit = build_source_chain_audit(
            args=args,
            source_chain_status=source_chain_status,
            c1_summary=c1_summary,
            direction_audit=direction_audit,
            d0_and_leakage=d0_and_leakage,
            p98_feedback_audit=p98_feedback_audit,
            p98_score_summary=p98_score_summary,
            blocker_messages=blocker_messages,
        )
    except Exception as exc:
        blocker_messages.append(str(exc))
        source_chain_status = "blocked"
        manifest = build_attempt_manifest(
            args=args,
            attempt_dir=attempt_dir,
            run_dir=run_dir,
            source_chain_status=source_chain_status,
        )
        data_quality_audit = {
            "run_id": args.run_id,
            "attempt_id": args.attempt_id,
            "run_type": "source_chain_rebuild",
            "candidate_scheme_id": TARGET_CANDIDATE_SCHEME_ID,
            "fatal_blockers": blocker_messages,
            "warnings": [],
            "notes": [
                "Controlled source-chain rebuild failed before score artifact generation.",
                "No portfolio or frozen-test outputs were produced.",
            ],
        }
        source_chain_audit = build_source_chain_audit(
            args=args,
            source_chain_status=source_chain_status,
            c1_summary=None,
            direction_audit=direction_audit,
            d0_and_leakage=d0_and_leakage,
            p98_feedback_audit=p98_feedback_audit,
            p98_score_summary=None,
            blocker_messages=blocker_messages,
        )

    write_json(manifest_path, manifest)
    write_json(attempt_audit_path, data_quality_audit)
    write_json(source_chain_audit_path, source_chain_audit)
    write_json(
        latest_attempt_path,
        {
            "run_id": args.run_id,
            "attempt_id": args.attempt_id,
            "status": source_chain_status,
            "attempt_dir": attempt_dir.as_posix(),
            "updated_at": datetime.now().astimezone().isoformat(),
        },
    )
    write_markdown(run_dir / "source_chain_audit.md", build_markdown(source_chain_audit, run_dir))
    return source_chain_audit


def main() -> None:
    args = build_parser().parse_args()
    run_rebuild(args)


if __name__ == "__main__":
    main()
