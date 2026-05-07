#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Run the confirmatory promotion round for p98 tail-handled reversal vs the
reversal+cord30 equal-weight composite under the frozen trainval contract.
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
ROUND_ID = "rr_confirmatory_reversal_cord30_promotion_20260506"
ROUND_DIR = REGISTRY_DIR / "research_rounds" / ROUND_ID
CONTRACT_PATH = ROOT / "contracts" / "run_input_contract.research_trainval_20211231.json"
BASE_PANELS_RUN_ID = "project_panels_research_trainval_20211231_20260429"
BASE_PANELS_DIR = RUN_STATE_DIR / BASE_PANELS_RUN_ID
VALIDATION_START = "20190101"
VALIDATION_END = "20211231"

BASELINE_CANDIDATE_ID = "reversal_tail_exclude_p98_v1"
CANDIDATE_CANDIDATE_ID = "reversal_p98_cord30_ew_v1"
SECONDARY_REFERENCE_RUN_ID = "confirmatory_cord30_trainval_20260429"

BASELINE_RUN_ID = "confirmatory_reversal_p98_trainval_20260506"
CANDIDATE_RUN_ID = "confirmatory_reversal_p98_cord30_trainval_20260506"

CODE_HASH_FILES = [
    SCRIPTS_DIR / "run_confirmatory_reversal_cord30_promotion_round.py",
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


def perturbation_map(run_id: str) -> dict[int, dict]:
    payload = load_json(FIXED_TEST_DIR / run_id / "topk_perturbation_summary.json")
    return {int(row["topk"]): row for row in payload["perturbations"]}


def stage_and_run(run_id: str, candidate_scheme_id: str) -> dict:
    run_dir = RUN_STATE_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    stage_panels(run_dir)

    run_cmd(
        [
            PYTHON,
            str(SCRIPTS_DIR / "build_reversal_tail_composite_model_scores.py"),
            "--run-id",
            run_id,
            "--candidate-scheme-id",
            candidate_scheme_id,
        ]
    )
    run_cmd(
        [
            PYTHON,
            str(SCRIPTS_DIR / "build_run_state_skeleton.py"),
            "--run-id",
            run_id,
            "--run-type",
            "confirmatory",
            "--candidate-scheme-id",
            candidate_scheme_id,
            "--research-round-id",
            ROUND_ID,
            "--scores-path",
            str(run_dir / "model_scores_D0.parquet"),
            "--topk",
            "10",
        ]
    )
    attempt_id = load_json(run_dir / "run_state_latest_attempt.json")["attempt_id"]
    run_cmd(
        [
            PYTHON,
            str(SCRIPTS_DIR / "build_portfolio_artifacts.py"),
            "--run-id",
            run_id,
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
            run_id,
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
            str(FIXED_TEST_DIR / run_id),
            "--validation-start",
            VALIDATION_START,
            "--validation-end",
            VALIDATION_END,
            "--output-path",
            str(FIXED_TEST_DIR / run_id / "validation_readout.json"),
        ]
    )
    return load_json(FIXED_TEST_DIR / run_id / "validation_readout.json")


def main() -> None:
    ROUND_DIR.mkdir(parents=True, exist_ok=True)

    baseline_validation = stage_and_run(BASELINE_RUN_ID, BASELINE_CANDIDATE_ID)
    candidate_validation = stage_and_run(CANDIDATE_RUN_ID, CANDIDATE_CANDIDATE_ID)

    baseline_cost = load_json(FIXED_TEST_DIR / BASELINE_RUN_ID / "cost_stress_summary.json")
    candidate_cost = load_json(FIXED_TEST_DIR / CANDIDATE_RUN_ID / "cost_stress_summary.json")
    baseline_liq = load_json(FIXED_TEST_DIR / BASELINE_RUN_ID / "low_liquidity_exposure_summary.json")
    candidate_liq = load_json(FIXED_TEST_DIR / CANDIDATE_RUN_ID / "low_liquidity_exposure_summary.json")
    baseline_perturb = perturbation_map(BASELINE_RUN_ID)
    candidate_perturb = perturbation_map(CANDIDATE_RUN_ID)
    secondary_reference = load_json(FIXED_TEST_DIR / SECONDARY_REFERENCE_RUN_ID / "validation_readout.json")

    validation_annual_relative_return_delta = (
        candidate_validation["annual_relative_return"] - baseline_validation["annual_relative_return"]
    )
    validation_relative_ir_delta = candidate_validation["relative_ir"] - baseline_validation["relative_ir"]
    validation_max_drawdown_delta = candidate_validation["max_drawdown"] - baseline_validation["max_drawdown"]
    validation_avg_turnover_daily_delta = (
        candidate_validation["avg_turnover_daily"] - baseline_validation["avg_turnover_daily"]
    )
    cost_stress_annual_relative_return_delta = (
        candidate_cost["annual_relative_return"] - baseline_cost["annual_relative_return"]
    )
    low_liquidity_weight_share_delta = (
        candidate_liq["low_liquidity_weight_share"] - baseline_liq["low_liquidity_weight_share"]
    )
    topk8_delta = (
        candidate_perturb[8]["annual_relative_return"] - baseline_perturb[8]["annual_relative_return"]
    )
    topk12_delta = (
        candidate_perturb[12]["annual_relative_return"] - baseline_perturb[12]["annual_relative_return"]
    )

    passes = {
        "validation_annual_relative_return_delta_gt_0": validation_annual_relative_return_delta > 0.0,
        "validation_relative_ir_delta_gt_0": validation_relative_ir_delta > 0.0,
        "validation_max_drawdown_delta_ge_0": validation_max_drawdown_delta >= 0.0,
        "cost_stress_annual_relative_return_delta_ge_0": cost_stress_annual_relative_return_delta >= 0.0,
        "topk8_annual_relative_return_delta_gt_0": topk8_delta > 0.0,
        "topk12_annual_relative_return_delta_gt_0": topk12_delta > 0.0,
        "validation_avg_turnover_daily_delta_le_002": validation_avg_turnover_daily_delta <= 0.02,
        "low_liquidity_weight_share_delta_le_0": low_liquidity_weight_share_delta <= 0.0,
        "candidate_avg_invested_weight_ge_018": candidate_validation["avg_invested_weight"] >= 0.18,
    }
    all_pass = all(passes.values())

    result = {
        "research_round_id": ROUND_ID,
        "generated_at": now_iso(),
        "snapshot_id": baseline_validation["snapshot_id"],
        "code_hash": compute_code_hash(),
        "baseline": {
            "run_id": BASELINE_RUN_ID,
            "candidate_scheme_id": BASELINE_CANDIDATE_ID,
            "validation": baseline_validation,
            "cost_stress": baseline_cost,
            "low_liquidity": baseline_liq,
            "topk_perturbation": {
                "8": baseline_perturb[8],
                "12": baseline_perturb[12],
            },
        },
        "candidate": {
            "run_id": CANDIDATE_RUN_ID,
            "candidate_scheme_id": CANDIDATE_CANDIDATE_ID,
            "validation": candidate_validation,
            "cost_stress": candidate_cost,
            "low_liquidity": candidate_liq,
            "topk_perturbation": {
                "8": candidate_perturb[8],
                "12": candidate_perturb[12],
            },
        },
        "secondary_reference": {
            "run_id": SECONDARY_REFERENCE_RUN_ID,
            "validation": secondary_reference,
        },
        "deltas_vs_baseline": {
            "validation_annual_relative_return_delta": validation_annual_relative_return_delta,
            "validation_relative_ir_delta": validation_relative_ir_delta,
            "validation_max_drawdown_delta": validation_max_drawdown_delta,
            "validation_avg_turnover_daily_delta": validation_avg_turnover_daily_delta,
            "cost_stress_annual_relative_return_delta": cost_stress_annual_relative_return_delta,
            "low_liquidity_weight_share_delta": low_liquidity_weight_share_delta,
            "topk8_annual_relative_return_delta": topk8_delta,
            "topk12_annual_relative_return_delta": topk12_delta,
        },
        "evaluation": {
            **passes,
            "all_pass": all_pass,
        },
        "round_decision": "PROMOTE_COMPOSITE" if all_pass else "KEEP_P98_BASELINE",
        "verdict": "pass" if all_pass else "fail",
    }
    write_json(ROUND_DIR / "promotion_results.json", result)

    lines = [
        "# Reversal + Cord30 Promotion Results",
        "",
        f"- `research_round_id = {ROUND_ID}`",
        f"- `generated_at = {result['generated_at']}`",
        "",
        "## Candidate vs Baseline",
        "",
        f"- `baseline_candidate_scheme_id = {BASELINE_CANDIDATE_ID}`",
        f"- `candidate_scheme_id = {CANDIDATE_CANDIDATE_ID}`",
        "",
        "## Validation deltas vs baseline",
        "",
        f"- `validation_annual_relative_return_delta = {validation_annual_relative_return_delta:.6f}`",
        f"- `validation_relative_ir_delta = {validation_relative_ir_delta:.6f}`",
        f"- `validation_max_drawdown_delta = {validation_max_drawdown_delta:.6f}`",
        f"- `validation_avg_turnover_daily_delta = {validation_avg_turnover_daily_delta:.6f}`",
        f"- `cost_stress_annual_relative_return_delta = {cost_stress_annual_relative_return_delta:.6f}`",
        f"- `low_liquidity_weight_share_delta = {low_liquidity_weight_share_delta:.6f}`",
        f"- `topk8_annual_relative_return_delta = {topk8_delta:.6f}`",
        f"- `topk12_annual_relative_return_delta = {topk12_delta:.6f}`",
        "",
        "## Rule evaluation",
        "",
    ]
    for key, value in passes.items():
        lines.append(f"- `{key} = {str(value).lower()}`")
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- `round_decision = {result['round_decision']}`",
            f"- `verdict = {result['verdict']}`",
        ]
    )
    (ROUND_DIR / "promotion_results.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    timestamp = now_iso()
    append_jsonl(
        REGISTRY_DIR / "research_round_registry.jsonl",
        {
            "registered_at": "2026-05-06T11:50:00+08:00",
            "research_round_id": ROUND_ID,
            "research_tier": "confirmatory",
            "status": "completed_promotion_pass" if all_pass else "completed_promotion_fail",
            "round_type": "baseline_promotion_check",
            "research_question": load_json(ROUND_DIR / "preregistration.json")["research_question"],
            "allowed_core_dimension": "score family composition only",
            "changed_dimension": "score_family_composition",
            "change_control_rule": "single_dimension_only",
            "candidate_scheme_ids": [CANDIDATE_CANDIDATE_ID],
            "planned_candidate_scheme_ids": [CANDIDATE_CANDIDATE_ID],
            "baseline_reference_candidate_scheme_id": BASELINE_CANDIDATE_ID,
            "snapshot_id": load_json(CONTRACT_PATH)["snapshot_id"],
            "round_decision": result["round_decision"],
            "status_updated_at": timestamp,
            "notes": (
                "Promotion round completed. "
                f"validation_annual_relative_return_delta={validation_annual_relative_return_delta:.6f}, "
                f"validation_relative_ir_delta={validation_relative_ir_delta:.6f}, "
                f"cost_stress_annual_relative_return_delta={cost_stress_annual_relative_return_delta:.6f}."
            ),
        },
    )
    append_jsonl(
        REGISTRY_DIR / "candidate_scheme_registry.jsonl",
        {
            "registered_at": "2026-05-06T11:50:00+08:00",
            "candidate_scheme_id": CANDIDATE_CANDIDATE_ID,
            "scheme_family": "reversal_tail_handled_composite",
            "status": "confirmatory_promotion_passed" if all_pass else "confirmatory_promotion_rejected",
            "research_round_id": ROUND_ID,
            "research_tier": "confirmatory",
            "owner": "codex",
            "score_builder": "build_reversal_tail_composite_model_scores.py",
            "feature_source": "reversal_run_state + cord30_run_state",
            "feature_set": ["negated_reversal_p98_tail_handled", "alpha158_cord30"],
            "score_rule": "0.5 * percent_rank(p98_reversal_score) + 0.5 * percent_rank(cord30_score)",
            "baseline_reference_candidate_scheme_id": BASELINE_CANDIDATE_ID,
            "external_anchor_candidate_scheme_id": "price_volume_single_signal_alpha158_cord30_v1",
            "snapshot_id": load_json(CONTRACT_PATH)["snapshot_id"],
            "execution_logic_version": "warehouse_execution_v3",
            "changed_dimension": "score_family_composition",
            "validation_annual_relative_return_delta_vs_p98": validation_annual_relative_return_delta,
            "validation_relative_ir_delta_vs_p98": validation_relative_ir_delta,
            "validation_max_drawdown_delta_vs_p98": validation_max_drawdown_delta,
            "validation_avg_turnover_daily_delta_vs_p98": validation_avg_turnover_daily_delta,
            "cost_stress_annual_relative_return_delta_vs_p98": cost_stress_annual_relative_return_delta,
            "low_liquidity_weight_share_delta_vs_p98": low_liquidity_weight_share_delta,
            "topk8_annual_relative_return_delta_vs_p98": topk8_delta,
            "topk12_annual_relative_return_delta_vs_p98": topk12_delta,
            "avg_invested_weight": candidate_validation["avg_invested_weight"],
            "notes": "First full-chain promotion check for the p98 reversal + cord30 composite.",
            "status_updated_at": timestamp,
        },
    )


if __name__ == "__main__":
    main()
