#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Run the single-candidate TopK=12 follow-up for the live p98 baseline.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path("/Users/wy/MiscProject/multi_factor")
PYTHON = "/opt/anaconda3/envs/quant_trade/bin/python"
SCRIPTS_DIR = ROOT / "scripts"
RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
FIXED_TEST_DIR = ROOT / "artifacts" / "fixed_test"
REGISTRY_DIR = ROOT / "artifacts" / "research_registry"
ROUND_ID = "rr_exploratory_reversal_p98_top12_20260506"
ROUND_DIR = REGISTRY_DIR / "research_rounds" / ROUND_ID
CONTRACT_PATH = ROOT / "contracts" / "run_input_contract.research_trainval_20211231.json"
BASE_PANELS_RUN_ID = "project_panels_research_trainval_20211231_20260429"
BASE_PANELS_DIR = RUN_STATE_DIR / BASE_PANELS_RUN_ID
VALIDATION_START = "20190101"
VALIDATION_END = "20211231"

BASELINE_FIXED_RUN_ID = "confirmatory_reversal_p98_trainval_20260506"
CHALLENGER_CANDIDATE_ID = "reversal_tail_exclude_p98_top12_v1"
CHALLENGER_RUN_ID = "exploratory_reversal_p98_top12_trainval_20260506"

CODE_HASH_FILES = [
    SCRIPTS_DIR / "run_reversal_p98_top12_round.py",
    SCRIPTS_DIR / "build_reversal_tail_composite_model_scores.py",
    SCRIPTS_DIR / "build_run_state_skeleton.py",
    SCRIPTS_DIR / "build_portfolio_artifacts.py",
    SCRIPTS_DIR / "build_fixed_test_minimal.py",
    SCRIPTS_DIR / "build_confirmatory_validation_readout.py",
]


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def ensure_symlink(src: Path, dst: Path) -> None:
    if dst.exists() or dst.is_symlink():
        return
    os.symlink(src, dst)


def stage_panels(run_dir: Path) -> None:
    for name in [
        "project_label_panel.parquet",
        "project_sample_panel.parquet",
        "project_execution_panel.parquet",
        "data_quality_audit.json",
    ]:
        ensure_symlink(BASE_PANELS_DIR / name, run_dir / name)


def run_cmd(args: list[str]) -> None:
    subprocess.run(args, check=True)


def compute_code_hash() -> str:
    hasher = hashlib.sha256()
    for path in CODE_HASH_FILES:
        hasher.update(path.name.encode("utf-8"))
        hasher.update(path.read_bytes())
    return hasher.hexdigest()


def main() -> None:
    ROUND_DIR.mkdir(parents=True, exist_ok=True)

    run_dir = RUN_STATE_DIR / CHALLENGER_RUN_ID
    run_dir.mkdir(parents=True, exist_ok=True)
    stage_panels(run_dir)

    run_cmd(
        [
            PYTHON,
            str(SCRIPTS_DIR / "build_reversal_tail_composite_model_scores.py"),
            "--run-id",
            CHALLENGER_RUN_ID,
            "--candidate-scheme-id",
            CHALLENGER_CANDIDATE_ID,
        ]
    )
    run_cmd(
        [
            PYTHON,
            str(SCRIPTS_DIR / "build_run_state_skeleton.py"),
            "--run-id",
            CHALLENGER_RUN_ID,
            "--run-type",
            "exploratory",
            "--candidate-scheme-id",
            CHALLENGER_CANDIDATE_ID,
            "--research-round-id",
            ROUND_ID,
            "--scores-path",
            str(run_dir / "model_scores_D0.parquet"),
            "--topk",
            "12",
        ]
    )

    attempt_id = load_json(run_dir / "run_state_latest_attempt.json")["attempt_id"]
    run_cmd(
        [
            PYTHON,
            str(SCRIPTS_DIR / "build_portfolio_artifacts.py"),
            "--run-id",
            CHALLENGER_RUN_ID,
            "--attempt-id",
            attempt_id,
            "--run-input-contract",
            str(CONTRACT_PATH),
        ]
    )
    run_cmd(
        [
            PYTHON,
            str(SCRIPTS_DIR / "build_fixed_test_minimal.py"),
            "--run-id",
            CHALLENGER_RUN_ID,
            "--attempt-id",
            attempt_id,
            "--run-input-contract",
            str(CONTRACT_PATH),
        ]
    )
    run_cmd(
        [
            PYTHON,
            str(SCRIPTS_DIR / "build_confirmatory_validation_readout.py"),
            "--fixed-test-dir",
            str(FIXED_TEST_DIR / CHALLENGER_RUN_ID),
            "--validation-start",
            VALIDATION_START,
            "--validation-end",
            VALIDATION_END,
            "--output-path",
            str(FIXED_TEST_DIR / CHALLENGER_RUN_ID / "validation_readout.json"),
        ]
    )

    baseline_validation = load_json(FIXED_TEST_DIR / BASELINE_FIXED_RUN_ID / "validation_readout.json")
    baseline_cost = load_json(FIXED_TEST_DIR / BASELINE_FIXED_RUN_ID / "cost_stress_summary.json")
    baseline_liq = load_json(FIXED_TEST_DIR / BASELINE_FIXED_RUN_ID / "low_liquidity_exposure_summary.json")

    challenger_validation = load_json(FIXED_TEST_DIR / CHALLENGER_RUN_ID / "validation_readout.json")
    challenger_cost = load_json(FIXED_TEST_DIR / CHALLENGER_RUN_ID / "cost_stress_summary.json")
    challenger_liq = load_json(FIXED_TEST_DIR / CHALLENGER_RUN_ID / "low_liquidity_exposure_summary.json")

    validation_annual_relative_return_delta = (
        challenger_validation["annual_relative_return"] - baseline_validation["annual_relative_return"]
    )
    validation_relative_ir_delta = challenger_validation["relative_ir"] - baseline_validation["relative_ir"]
    validation_max_drawdown_delta = challenger_validation["max_drawdown"] - baseline_validation["max_drawdown"]
    validation_avg_turnover_daily_delta = (
        challenger_validation["avg_turnover_daily"] - baseline_validation["avg_turnover_daily"]
    )
    validation_avg_invested_weight_delta = (
        challenger_validation["avg_invested_weight"] - baseline_validation["avg_invested_weight"]
    )
    cost_stress_annual_relative_return_delta = (
        challenger_cost["annual_relative_return"] - baseline_cost["annual_relative_return"]
    )
    low_liquidity_weight_share_delta = (
        challenger_liq["low_liquidity_weight_share"] - baseline_liq["low_liquidity_weight_share"]
    )

    evaluation = {
        "validation_annual_relative_return_delta_gt_0": validation_annual_relative_return_delta > 0.0,
        "validation_relative_ir_delta_gt_0": validation_relative_ir_delta > 0.0,
        "validation_max_drawdown_delta_ge_0": validation_max_drawdown_delta >= 0.0,
        "cost_stress_annual_relative_return_delta_ge_0": cost_stress_annual_relative_return_delta >= 0.0,
        "low_liquidity_weight_share_delta_le_0": low_liquidity_weight_share_delta <= 0.0,
        "validation_avg_turnover_daily_delta_le_002": validation_avg_turnover_daily_delta <= 0.02,
        "validation_avg_invested_weight_delta_ge_0": validation_avg_invested_weight_delta >= 0.0,
    }
    evaluation["all_pass"] = all(evaluation.values())

    payload = {
        "research_round_id": ROUND_ID,
        "generated_at": now_iso(),
        "snapshot_id": challenger_validation["snapshot_id"],
        "code_hash": compute_code_hash(),
        "challenger": {
            "run_id": CHALLENGER_RUN_ID,
            "candidate_scheme_id": CHALLENGER_CANDIDATE_ID,
            "validation": challenger_validation,
            "cost_stress": challenger_cost,
            "low_liquidity": challenger_liq,
        },
        "deltas_vs_baseline": {
            "validation_annual_relative_return_delta": validation_annual_relative_return_delta,
            "validation_relative_ir_delta": validation_relative_ir_delta,
            "validation_max_drawdown_delta": validation_max_drawdown_delta,
            "validation_avg_turnover_daily_delta": validation_avg_turnover_daily_delta,
            "validation_avg_invested_weight_delta": validation_avg_invested_weight_delta,
            "cost_stress_annual_relative_return_delta": cost_stress_annual_relative_return_delta,
            "low_liquidity_weight_share_delta": low_liquidity_weight_share_delta,
        },
        "evaluation": evaluation,
        "round_decision": "TOP12_PASS" if evaluation["all_pass"] else "TOP12_FAIL",
    }
    write_json(ROUND_DIR / "top12_results.json", payload)

    lines = [
        "# Reversal P98 Top12 Results",
        "",
        f"- `research_round_id = {ROUND_ID}`",
        f"- `generated_at = {payload['generated_at']}`",
        "",
    ]
    for k, v in payload["deltas_vs_baseline"].items():
        lines.append(f"- `{k} = {v:.6f}`")
    lines.extend(["", "## Evaluation", ""])
    for k, v in evaluation.items():
        lines.append(f"- `{k} = {str(v).lower()}`")
    lines.extend(["", "## Decision", "", f"- `round_decision = {payload['round_decision']}`"])
    (ROUND_DIR / "top12_results.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    timestamp = now_iso()
    append_jsonl(
        REGISTRY_DIR / "research_round_registry.jsonl",
        {
            "registered_at": "2026-05-06T12:50:00+08:00",
            "research_round_id": ROUND_ID,
            "research_tier": "exploratory",
            "status": "completed_top12_pass" if evaluation["all_pass"] else "completed_top12_fail",
            "round_type": "portfolio_extraction_followup",
            "research_question": load_json(ROUND_DIR / "preregistration.json")["research_question"],
            "allowed_core_dimension": "topk parameter only",
            "changed_dimension": "topk_parameter",
            "change_control_rule": "single_dimension_only",
            "candidate_scheme_ids": [CHALLENGER_CANDIDATE_ID],
            "planned_candidate_scheme_ids": [CHALLENGER_CANDIDATE_ID],
            "baseline_reference_candidate_scheme_id": "reversal_tail_exclude_p98_v1",
            "snapshot_id": load_json(CONTRACT_PATH)["snapshot_id"],
            "round_decision": payload["round_decision"],
            "status_updated_at": timestamp,
            "notes": "Single-candidate TopK=12 follow-up after the liquidity-guard screen returned no clean candidate."
        }
    )
    append_jsonl(
        REGISTRY_DIR / "candidate_scheme_registry.jsonl",
        {
            "registered_at": "2026-05-06T12:50:00+08:00",
            "candidate_scheme_id": CHALLENGER_CANDIDATE_ID,
            "scheme_family": "reversal_tail_handled_extraction_variant",
            "status": "top12_passed" if evaluation["all_pass"] else "top12_failed",
            "research_round_id": ROUND_ID,
            "research_tier": "exploratory",
            "owner": "codex",
            "score_builder": "build_reversal_tail_composite_model_scores.py",
            "feature_source": "exploratory_cross_horizon_c1_reversal_only",
            "feature_set": ["negated_reversal_p98_tail_handled"],
            "score_rule": "same as reversal_tail_exclude_p98_v1; only TopK changes from 10 to 12",
            "baseline_reference_candidate_scheme_id": "reversal_tail_exclude_p98_v1",
            "snapshot_id": load_json(CONTRACT_PATH)["snapshot_id"],
            "execution_logic_version": "warehouse_execution_v3",
            "changed_dimension": "topk_parameter",
            "validation_annual_relative_return_delta_vs_p98_top10": validation_annual_relative_return_delta,
            "validation_relative_ir_delta_vs_p98_top10": validation_relative_ir_delta,
            "validation_max_drawdown_delta_vs_p98_top10": validation_max_drawdown_delta,
            "validation_avg_turnover_daily_delta_vs_p98_top10": validation_avg_turnover_daily_delta,
            "validation_avg_invested_weight_delta_vs_p98_top10": validation_avg_invested_weight_delta,
            "cost_stress_annual_relative_return_delta_vs_p98_top10": cost_stress_annual_relative_return_delta,
            "low_liquidity_weight_share_delta_vs_p98_top10": low_liquidity_weight_share_delta,
            "status_updated_at": timestamp,
            "notes": "TopK extraction follow-up for the live p98 baseline."
        }
    )


if __name__ == "__main__":
    main()
