#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Run the CORD30 turnover-control-only family seed on the trainval-only snapshot.

This seed freezes the CORD30 score body and changes only the portfolio refresh
rule to refresh_hysteresis15: retain incumbents if rank_position <= 15,
refill remaining TopK=10 slots from highest-ranked non-held eligible names.

Comparison references:
  - Primary: standalone cord30 (baseline_reference)
  - External anchor: v18 (external_anchor)
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

ROUND_ID = "rr_confirmatory_alpha158_cord30_turnover_control_seed_20260430"
ROUND_DIR = REGISTRY_DIR / "research_rounds" / ROUND_ID
CONTRACT_PATH = ROOT / "contracts" / "run_input_contract.research_trainval_20211231.json"
BASE_PANELS_RUN_ID = "project_panels_research_trainval_20211231_20260429"
BASE_PANELS_DIR = RUN_STATE_DIR / BASE_PANELS_RUN_ID
VALIDATION_START = "20190101"
VALIDATION_END = "20211231"

# Challenger (this seed)
CANDIDATE_SCHEME_ID = "confirmatory_alpha158_cord30_seed_refresh_hysteresis15_v1"
FEATURE_NAME = "CORD30"
RUN_ID = "confirmatory_cord30_seed_refresh_hysteresis15_trainval_20260430"
FIXED_TEST_RUN_ID = "confirmatory_fixed_test_cord30_seed_refresh_hysteresis15_trainval_20260430"

# Primary reference: standalone CORD30
REFERENCE_CANDIDATE_ID = "price_volume_single_signal_alpha158_cord30_v1"
REFERENCE_RUN_ID = "confirmatory_cord30_trainval_20260430"
REFERENCE_FIXED_TEST_DIR = FIXED_TEST_DIR / REFERENCE_RUN_ID

# External anchor: v18
ANCHOR_CANDIDATE_ID = "price_volume_v18_refresh_hysteresis"
ANCHOR_FIXED_TEST_DIR = FIXED_TEST_DIR / "confirmatory_reference_v18_trainval_20260429"

CODE_HASH_FILES = [
    SCRIPTS_DIR / "run_confirmatory_alpha158_cord30_seed_refresh_hysteresis15_v1.py",
    SCRIPTS_DIR / "build_alpha158_standalone_model_scores.py",
    SCRIPTS_DIR / "build_baseline_model_scores.py",
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
        if path.exists():
            hasher.update(path.name.encode("utf-8"))
            hasher.update(path.read_bytes())
    return hasher.hexdigest()


def load_validation_readout(fixed_test_dir: Path) -> dict:
    path = fixed_test_dir / "validation_readout.json"
    if not path.exists():
        raise FileNotFoundError(f"Reference validation readout not found: {path}")
    return load_json(path)


def compute_deltas(challenger: dict, reference: dict) -> dict:
    deltas = {}
    for key in ("annual_relative_return", "relative_ir", "max_drawdown", "avg_turnover_daily", "avg_invested_weight"):
        c_val = challenger.get(key)
        r_val = reference.get(key)
        if c_val is not None and r_val is not None:
            deltas[f"{key}_delta"] = c_val - r_val
        else:
            deltas[f"{key}_delta"] = None
    return deltas


def evaluate_decision(challenger: dict, reference: dict, anchor: dict) -> dict:
    """Evaluate the preregistered boolean decision rule."""
    deltas_vs_cord30 = compute_deltas(challenger, reference)
    deltas_vs_v18 = compute_deltas(challenger, anchor)

    vs_cord30_return = deltas_vs_cord30.get("annual_relative_return_delta")
    vs_cord30_ir = deltas_vs_cord30.get("relative_ir_delta")
    vs_cord30_dd = deltas_vs_cord30.get("max_drawdown_delta")
    vs_cord30_to = deltas_vs_cord30.get("avg_turnover_daily_delta")
    vs_cord30_cost = None  # cost stress not in simple diff; skip for now
    vs_cord30_lliq = None

    vs_v18_return = deltas_vs_v18.get("annual_relative_return_delta")
    vs_v18_ir = deltas_vs_v18.get("relative_ir_delta")
    vs_v18_dd = deltas_vs_v18.get("max_drawdown_delta")
    vs_v18_to = deltas_vs_v18.get("avg_turnover_daily_delta")

    avg_invested = challenger.get("avg_invested_weight", 0.0)

    pass_boolean = bool(
        # vs CORD30: turnover must drop, core metrics not materially hurt
        vs_cord30_to is not None and vs_cord30_to <= -0.01
        and vs_cord30_return is not None and vs_cord30_return >= -0.02
        and vs_cord30_ir is not None and vs_cord30_ir >= -0.10
        and vs_cord30_dd is not None and vs_cord30_dd >= -0.02
        # vs v18: must still beat v18 on strict gate
        and vs_v18_return is not None and vs_v18_return > 0.10
        and vs_v18_ir is not None and vs_v18_ir > 0.50
        and vs_v18_dd is not None and vs_v18_dd >= 0.10
        and vs_v18_to is not None and vs_v18_to <= 0.02
        and avg_invested >= 0.18
    )

    return {
        "pass_boolean": pass_boolean,
        "deltas_vs_cord30": deltas_vs_cord30,
        "deltas_vs_v18": deltas_vs_v18,
        "boolean_expression": (
            "(validation_avg_turnover_daily_delta_vs_cord30 <= -0.01) "
            "AND (validation_annual_relative_return_delta_vs_cord30 >= -0.02) "
            "AND (validation_relative_ir_delta_vs_cord30 >= -0.10) "
            "AND (validation_max_drawdown_delta_vs_cord30 >= -0.02) "
            "AND (validation_annual_relative_return_delta_vs_v18 > 0.10) "
            "AND (validation_relative_ir_delta_vs_v18 > 0.50) "
            "AND (validation_max_drawdown_delta_vs_v18 >= 0.10) "
            "AND (validation_avg_turnover_daily_delta_vs_v18 <= 0.02) "
            "AND (candidate_avg_invested_weight >= 0.18)"
        ),
    }


def load_or_build_reference(fixed_test_dir: Path) -> dict:
    return load_validation_readout(fixed_test_dir)


def build_seed() -> dict:
    run_dir = RUN_STATE_DIR / RUN_ID
    run_dir.mkdir(parents=True, exist_ok=True)
    stage_panels(run_dir)

    print(f"[{now_iso()}] Stage 1/4: Building model scores (CORD30 standalone, unchanged)...")
    run_cmd(
        [
            PYTHON,
            str(SCRIPTS_DIR / "build_alpha158_standalone_model_scores.py"),
            "--run-id", RUN_ID,
            "--feature-name", FEATURE_NAME,
            "--candidate-scheme-id", CANDIDATE_SCHEME_ID,
            "--run-input-contract", str(CONTRACT_PATH),
        ]
    )

    print(f"[{now_iso()}] Stage 2/4: Building run state skeleton...")
    run_cmd(
        [
            PYTHON,
            str(SCRIPTS_DIR / "build_run_state_skeleton.py"),
            "--run-id", RUN_ID,
            "--run-type", "confirmatory",
            "--candidate-scheme-id", CANDIDATE_SCHEME_ID,
            "--research-round-id", ROUND_ID,
            "--scores-path", str(run_dir / "model_scores_D0.parquet"),
            "--topk", "10",
        ]
    )

    attempt_id = load_json(run_dir / "run_state_latest_attempt.json")["attempt_id"]
    print(f"[{now_iso()}] Stage 3/4: Building portfolio artifacts (using refresh_hysteresis15)...")
    run_cmd(
        [
            PYTHON,
            str(SCRIPTS_DIR / "build_portfolio_artifacts.py"),
            "--run-id", RUN_ID,
            "--attempt-id", attempt_id,
            "--run-input-contract", str(CONTRACT_PATH),
        ]
    )

    print(f"[{now_iso()}] Stage 4/4: Building fixed test + validation readout...")
    run_cmd(
        [
            PYTHON,
            str(SCRIPTS_DIR / "build_fixed_test_minimal.py"),
            "--run-id", RUN_ID,
            "--attempt-id", attempt_id,
            "--fixed-test-run-id", FIXED_TEST_RUN_ID,
            "--run-input-contract", str(CONTRACT_PATH),
        ]
    )

    fixed_test_output_dir = FIXED_TEST_DIR / RUN_ID
    validation_output = fixed_test_output_dir / "validation_readout.json"
    run_cmd(
        [
            PYTHON,
            str(SCRIPTS_DIR / "build_confirmatory_validation_readout.py"),
            "--fixed-test-dir", str(fixed_test_output_dir),
            "--validation-start", VALIDATION_START,
            "--validation-end", VALIDATION_END,
            "--output-path", str(validation_output),
        ]
    )

    return load_json(validation_output)


def main() -> None:
    if not BASE_PANELS_DIR.exists():
        raise FileNotFoundError(f"Missing required trainval panel base directory: {BASE_PANELS_DIR}")
    ROUND_DIR.mkdir(parents=True, exist_ok=True)

    # Load both references
    print(f"[{now_iso()}] Loading reference: standalone CORD30...")
    reference = load_or_build_reference(REFERENCE_FIXED_TEST_DIR)
    print(f"[{now_iso()}] Loading reference: v18...")
    anchor = load_or_build_reference(ANCHOR_FIXED_TEST_DIR)

    # Build and run the seed
    print(f"[{now_iso()}] === Building seed: {CANDIDATE_SCHEME_ID} ===")
    challenger = build_seed()
    challenger["run_id"] = RUN_ID
    challenger["fixed_test_run_id"] = FIXED_TEST_RUN_ID

    # Evaluate
    decision = evaluate_decision(challenger, reference, anchor)

    # Write results
    summary = {
        "research_round_id": ROUND_ID,
        "generated_at": now_iso(),
        "code_hash": compute_code_hash(),
        "snapshot_id": load_json(CONTRACT_PATH)["snapshot_id"],
        "candidate_scheme_id": CANDIDATE_SCHEME_ID,
        "baseline_reference_candidate_scheme_id": REFERENCE_CANDIDATE_ID,
        "external_anchor_candidate_scheme_id": ANCHOR_CANDIDATE_ID,
        "challenger_validation": challenger,
        "reference_validation_cord30": reference,
        "reference_validation_v18": anchor,
        "deltas_vs_cord30": decision["deltas_vs_cord30"],
        "deltas_vs_v18": decision["deltas_vs_v18"],
        "pass_boolean": decision["pass_boolean"],
        "boolean_expression": decision["boolean_expression"],
    }
    write_json(ROUND_DIR / "challenger_vs_cord30_summary.json", summary)

    # Write markdown summary
    lines = [
        f"# CORD30 Turnover-Control Seed Results",
        "",
        f"生成时间: {now_iso()}",
        "",
        f"## 候选方案",
        "",
        f"- `candidate_scheme_id(候选方案ID) = {CANDIDATE_SCHEME_ID}`",
        f"- `changed_dimension(唯一变化维度) = portfolio_refresh_rule(组合刷新规则)`",
        f"- `refresh_rule(刷新规则) = refresh_hysteresis15(holder ≤ rank 15 保留, 空缺最高分补足到 10)`",
        "",
        f"## 布尔通过",
        "",
        f"- `pass_boolean(布尔通过结果) = {str(decision['pass_boolean']).lower()}`",
        "",
    ]

    # Helper to format number or "null"
    def fmt(val) -> str:
        if val is None:
            return "null"
        return f"{val:.6f}"

    # Challenger absolute metrics
    lines.extend([
        "## Challenger 验证期绝对指标",
        "",
        f"- `validation_annual_relative_return(验证期年化超额收益) = {fmt(challenger.get('annual_relative_return'))}`",
        f"- `validation_relative_ir(验证期相对信息比率) = {fmt(challenger.get('relative_ir'))}`",
        f"- `validation_max_drawdown(验证期最大回撤) = {fmt(challenger.get('max_drawdown'))}`",
        f"- `validation_avg_turnover_daily(验证期平均日换手) = {fmt(challenger.get('avg_turnover_daily'))}`",
        f"- `validation_avg_invested_weight(验证期平均投资仓位) = {fmt(challenger.get('avg_invested_weight'))}`",
        "",
        "## vs standalone CORD30",
        "",
    ])

    d_cord30 = decision["deltas_vs_cord30"]
    lines.extend([
        f"- `annual_relative_return_delta_vs_cord30 = {fmt(d_cord30.get('annual_relative_return_delta'))}`",
        f"- `relative_ir_delta_vs_cord30 = {fmt(d_cord30.get('relative_ir_delta'))}`",
        f"- `max_drawdown_delta_vs_cord30 = {fmt(d_cord30.get('max_drawdown_delta'))}`",
        f"- `avg_turnover_daily_delta_vs_cord30 = {fmt(d_cord30.get('avg_turnover_daily_delta'))}`",
        "",
        f"Reference cord30 annual_relative_return: {fmt(reference.get('annual_relative_return'))}",
        f"Reference cord30 avg_turnover_daily: {fmt(reference.get('avg_turnover_daily'))}",
        "",
        "## vs v18 (外部锚点)",
        "",
    ])

    d_v18 = decision["deltas_vs_v18"]
    lines.extend([
        f"- `annual_relative_return_delta_vs_v18 = {fmt(d_v18.get('annual_relative_return_delta'))}`",
        f"- `relative_ir_delta_vs_v18 = {fmt(d_v18.get('relative_ir_delta'))}`",
        f"- `max_drawdown_delta_vs_v18 = {fmt(d_v18.get('max_drawdown_delta'))}`",
        f"- `avg_turnover_daily_delta_vs_v18 = {fmt(d_v18.get('avg_turnover_daily_delta'))}`",
        "",
        f"Reference v18 annual_relative_return: {fmt(anchor.get('annual_relative_return'))}",
        f"Reference v18 avg_turnover_daily: {fmt(anchor.get('avg_turnover_daily'))}",
        "",
        "## 布尔条件逐项检查",
        "",
        f"- vs CORD30: avg_turnover_daily_delta <= -0.01 → {d_cord30.get('avg_turnover_daily_delta') is not None and d_cord30['avg_turnover_daily_delta'] <= -0.01}",
        f"- vs CORD30: annual_relative_return_delta >= -0.02 → {d_cord30.get('annual_relative_return_delta') is not None and d_cord30['annual_relative_return_delta'] >= -0.02}",
        f"- vs CORD30: relative_ir_delta >= -0.10 → {d_cord30.get('relative_ir_delta') is not None and d_cord30['relative_ir_delta'] >= -0.10}",
        f"- vs CORD30: max_drawdown_delta >= -0.02 → {d_cord30.get('max_drawdown_delta') is not None and d_cord30['max_drawdown_delta'] >= -0.02}",
        f"- vs v18: annual_relative_return_delta > 0.10 → {d_v18.get('annual_relative_return_delta') is not None and d_v18['annual_relative_return_delta'] > 0.10}",
        f"- vs v18: relative_ir_delta > 0.50 → {d_v18.get('relative_ir_delta') is not None and d_v18['relative_ir_delta'] > 0.50}",
        f"- vs v18: max_drawdown_delta >= 0.10 → {d_v18.get('max_drawdown_delta') is not None and d_v18['max_drawdown_delta'] >= 0.10}",
        f"- vs v18: avg_turnover_daily_delta <= 0.02 → {d_v18.get('avg_turnover_daily_delta') is not None and d_v18['avg_turnover_daily_delta'] <= 0.02}",
        f"- avg_invested_weight >= 0.18 → {challenger.get('avg_invested_weight', 0.0) >= 0.18}",
        "",
    ])
    (ROUND_DIR / "challenger_vs_cord30_summary.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    print(f"[{now_iso()}] === Seed round complete ===")
    print(f"pass_boolean: {decision['pass_boolean']}")
    print(f"Summary: {ROUND_DIR / 'challenger_vs_cord30_summary.md'}")


if __name__ == "__main__":
    main()
