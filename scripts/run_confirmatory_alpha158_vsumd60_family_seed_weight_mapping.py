#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Run the final restrained VSUMD60 family-seed confirmatory round.

The score stays fixed on standalone Alpha158 VSUMD60. This seed changes exactly one
core dimension: the weight mapping inside the frozen TopK becomes a mild liquidity-rank
tilt with same-date renormalization.
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

ROUND_ID = "rr_confirmatory_alpha158_vsumd60_family_seed_weight_mapping_20260430"
ROUND_DIR = REGISTRY_DIR / "research_rounds" / ROUND_ID
CONTRACT_PATH = ROOT / "contracts" / "run_input_contract.research_trainval_20211231.json"
BASE_PANELS_RUN_ID = "project_panels_research_trainval_20211231_20260429"
BASE_PANELS_DIR = RUN_STATE_DIR / BASE_PANELS_RUN_ID

REFERENCE_CANDIDATE_ID = "price_volume_single_signal_alpha158_vsumd60_v1"
REFERENCE_RUN_ID = "confirmatory_vsumd60_trainval_20260429"
REFERENCE_FIXED_TEST_RUN_ID = "confirmatory_fixed_test_vsumd60_trainval_20260429"
EXTERNAL_ANCHOR_CANDIDATE_ID = "price_volume_v18_refresh_hysteresis"
EXTERNAL_ANCHOR_RUN_ID = "confirmatory_reference_v18_trainval_20260429"

CHALLENGER_CANDIDATE_ID = "confirmatory_alpha158_vsumd60_seed_liquidity_rank_tilt_v1"
CHALLENGER_RUN_ID = "confirmatory_vsumd60_seed_liquidity_rank_tilt_trainval_20260430"
CHALLENGER_FIXED_TEST_RUN_ID = "confirmatory_fixed_test_vsumd60_seed_liquidity_rank_tilt_trainval_20260430"
FEATURE_NAME = "VSUMD60"
VALIDATION_START = "20190101"
VALIDATION_END = "20211231"

CODE_HASH_FILES = [
    SCRIPTS_DIR / "run_confirmatory_alpha158_vsumd60_family_seed_weight_mapping.py",
    SCRIPTS_DIR / "build_alpha158_standalone_model_scores.py",
    SCRIPTS_DIR / "alpha158_canonical_common.py",
    SCRIPTS_DIR / "single_signal_batch_common.py",
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


def ensure_validation_readout(run_id: str, fixed_test_run_id: str) -> dict:
    fixed_test_dir = FIXED_TEST_DIR / run_id
    validation_output = fixed_test_dir / "validation_readout.json"
    if validation_output.exists():
        return load_json(validation_output)
    run_cmd(
        [
            PYTHON,
            str(SCRIPTS_DIR / "build_confirmatory_validation_readout.py"),
            "--fixed-test-dir",
            str(fixed_test_dir),
            "--validation-start",
            VALIDATION_START,
            "--validation-end",
            VALIDATION_END,
            "--output-path",
            str(validation_output),
        ]
    )
    payload = load_json(validation_output)
    payload["fixed_test_run_id"] = fixed_test_run_id
    return payload


def run_challenger() -> dict:
    run_dir = RUN_STATE_DIR / CHALLENGER_RUN_ID
    run_dir.mkdir(parents=True, exist_ok=True)
    stage_panels(run_dir)

    run_cmd(
        [
            PYTHON,
            str(SCRIPTS_DIR / "build_alpha158_standalone_model_scores.py"),
            "--run-id",
            CHALLENGER_RUN_ID,
            "--feature-name",
            FEATURE_NAME,
            "--candidate-scheme-id",
            CHALLENGER_CANDIDATE_ID,
            "--run-input-contract",
            str(CONTRACT_PATH),
        ]
    )
    run_cmd(
        [
            PYTHON,
            str(SCRIPTS_DIR / "build_run_state_skeleton.py"),
            "--run-id",
            CHALLENGER_RUN_ID,
            "--run-type",
            "confirmatory_family_seed",
            "--candidate-scheme-id",
            CHALLENGER_CANDIDATE_ID,
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
            CHALLENGER_RUN_ID,
            "--attempt-id",
            attempt_id,
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
            "--fixed-test-run-id",
            CHALLENGER_FIXED_TEST_RUN_ID,
            "--run-input-contract",
            str(CONTRACT_PATH),
        ]
    )
    return ensure_validation_readout(CHALLENGER_RUN_ID, CHALLENGER_FIXED_TEST_RUN_ID)


def main() -> None:
    if not BASE_PANELS_DIR.exists():
        raise FileNotFoundError(f"Missing required trainval panel base directory: {BASE_PANELS_DIR}")
    ROUND_DIR.mkdir(parents=True, exist_ok=True)

    challenger_validation = run_challenger()
    reference_validation = ensure_validation_readout(REFERENCE_RUN_ID, REFERENCE_FIXED_TEST_RUN_ID)
    external_anchor_validation = ensure_validation_readout(EXTERNAL_ANCHOR_RUN_ID, EXTERNAL_ANCHOR_RUN_ID)

    challenger_liq = load_json(FIXED_TEST_DIR / CHALLENGER_RUN_ID / "low_liquidity_exposure_summary.json")
    reference_liq = load_json(FIXED_TEST_DIR / REFERENCE_RUN_ID / "low_liquidity_exposure_summary.json")
    challenger_cost = load_json(FIXED_TEST_DIR / CHALLENGER_RUN_ID / "cost_stress_summary.json")
    reference_cost = load_json(FIXED_TEST_DIR / REFERENCE_RUN_ID / "cost_stress_summary.json")
    challenger_perturb = load_json(FIXED_TEST_DIR / CHALLENGER_RUN_ID / "topk_perturbation_summary.json")
    reference_perturb = load_json(FIXED_TEST_DIR / REFERENCE_RUN_ID / "topk_perturbation_summary.json")

    validation_annual_relative_return_delta_vs_vsumd60 = (
        challenger_validation["annual_relative_return"] - reference_validation["annual_relative_return"]
    )
    validation_relative_ir_delta_vs_vsumd60 = (
        challenger_validation["relative_ir"] - reference_validation["relative_ir"]
    )
    validation_max_drawdown_delta_vs_vsumd60 = (
        challenger_validation["max_drawdown"] - reference_validation["max_drawdown"]
    )
    validation_avg_turnover_daily_delta_vs_vsumd60 = (
        challenger_validation["avg_turnover_daily"] - reference_validation["avg_turnover_daily"]
    )
    validation_low_liquidity_weight_share_delta_vs_vsumd60 = (
        challenger_liq["low_liquidity_weight_share"] - reference_liq["low_liquidity_weight_share"]
    )
    validation_cost_stress_annual_relative_return_delta_vs_vsumd60 = (
        challenger_cost["annual_relative_return"] - reference_cost["annual_relative_return"]
    )

    pass_boolean = bool(
        validation_annual_relative_return_delta_vs_vsumd60 >= 0.00
        and validation_relative_ir_delta_vs_vsumd60 >= 0.00
        and validation_max_drawdown_delta_vs_vsumd60 >= -0.02
        and validation_avg_turnover_daily_delta_vs_vsumd60 <= 0.01
        and validation_low_liquidity_weight_share_delta_vs_vsumd60 <= 0.00
        and validation_cost_stress_annual_relative_return_delta_vs_vsumd60 >= 0.00
    )

    summary = {
        "research_round_id": ROUND_ID,
        "generated_at": now_iso(),
        "snapshot_id": load_json(CONTRACT_PATH)["snapshot_id"],
        "code_hash": compute_code_hash(),
        "challenger_candidate_scheme_id": CHALLENGER_CANDIDATE_ID,
        "baseline_reference_candidate_scheme_id": REFERENCE_CANDIDATE_ID,
        "external_anchor_candidate_scheme_id": EXTERNAL_ANCHOR_CANDIDATE_ID,
        "challenger_validation": challenger_validation,
        "baseline_reference_validation": reference_validation,
        "external_anchor_validation": external_anchor_validation,
        "deltas_vs_vsumd60": {
            "annual_relative_return_delta": validation_annual_relative_return_delta_vs_vsumd60,
            "relative_ir_delta": validation_relative_ir_delta_vs_vsumd60,
            "max_drawdown_delta": validation_max_drawdown_delta_vs_vsumd60,
            "avg_turnover_daily_delta": validation_avg_turnover_daily_delta_vs_vsumd60,
            "low_liquidity_weight_share_delta": validation_low_liquidity_weight_share_delta_vs_vsumd60,
            "cost_stress_annual_relative_return_delta": validation_cost_stress_annual_relative_return_delta_vs_vsumd60,
        },
        "robustness": {
            "challenger_low_liquidity_weight_share": challenger_liq["low_liquidity_weight_share"],
            "reference_low_liquidity_weight_share": reference_liq["low_liquidity_weight_share"],
            "challenger_cost_stress_annual_relative_return": challenger_cost["annual_relative_return"],
            "reference_cost_stress_annual_relative_return": reference_cost["annual_relative_return"],
            "challenger_topk_perturbation": challenger_perturb["perturbations"],
            "reference_topk_perturbation": reference_perturb["perturbations"],
        },
        "decision_rule": "(validation_annual_relative_return_delta_vs_vsumd60 >= 0.00) AND (validation_relative_ir_delta_vs_vsumd60 >= 0.00) AND (validation_max_drawdown_delta_vs_vsumd60 >= -0.02) AND (validation_avg_turnover_daily_delta_vs_vsumd60 <= 0.01) AND (validation_low_liquidity_weight_share_delta_vs_vsumd60 <= 0.00) AND (validation_cost_stress_annual_relative_return_delta_vs_vsumd60 >= 0.00)",
        "pass_boolean": pass_boolean,
        "round_decision": "KEEP" if pass_boolean else "REJECT",
        "conclusion": (
            "The final VSUMD60 family seed improved internal weight mapping quality without giving back the confirmed standalone edge."
            if pass_boolean
            else "The final VSUMD60 family seed still failed to beat the standalone VSUMD60 reference under the preregistered gate."
        ),
    }
    write_json(ROUND_DIR / "challenger_vs_vsumd60_summary.json", summary)

    lines = [
        f"# {ROUND_ID} summary",
        "",
        f"- `round_decision(轮次结论) = {summary['round_decision']}`",
        f"- `pass_boolean(布尔通过) = {str(pass_boolean).lower()}`",
        f"- `challenger_candidate_scheme_id(挑战者候选方案ID) = {CHALLENGER_CANDIDATE_ID}`",
        f"- `baseline_reference_candidate_scheme_id(主参考候选方案ID) = {REFERENCE_CANDIDATE_ID}`",
        "",
        "## Validation Deltas Vs VSUMD60",
        "",
        f"- `annual_relative_return_delta(年化超额收益变化) = {validation_annual_relative_return_delta_vs_vsumd60:.6f}`",
        f"- `relative_ir_delta(相对信息比率变化) = {validation_relative_ir_delta_vs_vsumd60:.6f}`",
        f"- `max_drawdown_delta(最大回撤变化) = {validation_max_drawdown_delta_vs_vsumd60:.6f}`",
        f"- `avg_turnover_daily_delta(平均日换手变化) = {validation_avg_turnover_daily_delta_vs_vsumd60:.6f}`",
        f"- `low_liquidity_weight_share_delta(低流动性权重占比变化) = {validation_low_liquidity_weight_share_delta_vs_vsumd60:.6f}`",
        f"- `cost_stress_annual_relative_return_delta(成本压力年化超额收益变化) = {validation_cost_stress_annual_relative_return_delta_vs_vsumd60:.6f}`",
        "",
        "## Reference Levels",
        "",
        f"- `challenger_validation_annual_relative_return(挑战者验证期年化超额收益) = {challenger_validation['annual_relative_return']:.6f}`",
        f"- `reference_validation_annual_relative_return(参考验证期年化超额收益) = {reference_validation['annual_relative_return']:.6f}`",
        f"- `external_anchor_validation_annual_relative_return(外部锚验证期年化超额收益) = {external_anchor_validation['annual_relative_return']:.6f}`",
        "",
        "## Conclusion",
        "",
        f"- {summary['conclusion']}",
    ]
    (ROUND_DIR / "challenger_vs_vsumd60_summary.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
