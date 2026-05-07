#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Run the first exploratory Alpha158 CORR30 + CORD30 dual-signal family on the
trainval-only snapshot.
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

ROUND_ID = "rr_alpha158_corr30_cord30_dual_signal_family_20260430"
ROUND_DIR = REGISTRY_DIR / "research_rounds" / ROUND_ID
CONTRACT_PATH = ROOT / "contracts" / "run_input_contract.research_trainval_20211231.json"
BASE_PANELS_RUN_ID = "project_panels_research_trainval_20211231_20260429"
BASE_PANELS_DIR = RUN_STATE_DIR / BASE_PANELS_RUN_ID
VALIDATION_START = "20190101"
VALIDATION_END = "20211231"

CANDIDATE_SCHEME_ID = "alpha158_corr30_cord30_dual_signal_family_v1"
RUN_ID = "exploratory_alpha158_corr30_cord30_dual_signal_family_trainval_20260430"
FIXED_TEST_RUN_ID = "exploratory_fixed_test_alpha158_corr30_cord30_dual_signal_family_trainval_20260430"
FEATURE_NAMES = "CORR30,CORD30"

REFERENCE_CORD30_CANDIDATE_ID = "price_volume_single_signal_alpha158_cord30_v1"
REFERENCE_CORD30_RUN_ID = "confirmatory_cord30_trainval_20260430"
REFERENCE_CORD30_FIXED_TEST_DIR = FIXED_TEST_DIR / REFERENCE_CORD30_RUN_ID

ANCHOR_V18_CANDIDATE_ID = "price_volume_v18_refresh_hysteresis"
ANCHOR_V18_RUN_ID = "confirmatory_reference_v18_trainval_20260429"
ANCHOR_V18_FIXED_TEST_DIR = FIXED_TEST_DIR / ANCHOR_V18_RUN_ID

CODE_HASH_FILES = [
    SCRIPTS_DIR / "run_alpha158_corr30_cord30_dual_signal_family_v1.py",
    SCRIPTS_DIR / "build_alpha158_head_extraction_dual_signal_family_scores.py",
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
        raise FileNotFoundError(f"Required validation readout not found: {path}")
    return load_json(path)


def load_optional_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return load_json(path)


def build_family() -> dict:
    run_dir = RUN_STATE_DIR / RUN_ID
    run_dir.mkdir(parents=True, exist_ok=True)
    stage_panels(run_dir)

    print(f"[{now_iso()}] Stage 1/4: Building dual-signal family model scores...")
    run_cmd(
        [
            PYTHON,
            str(SCRIPTS_DIR / "build_alpha158_head_extraction_dual_signal_family_scores.py"),
            "--run-id",
            RUN_ID,
            "--candidate-scheme-id",
            CANDIDATE_SCHEME_ID,
            "--feature-names",
            FEATURE_NAMES,
            "--run-input-contract",
            str(CONTRACT_PATH),
        ]
    )

    print(f"[{now_iso()}] Stage 2/4: Building run state skeleton...")
    run_cmd(
        [
            PYTHON,
            str(SCRIPTS_DIR / "build_run_state_skeleton.py"),
            "--run-id",
            RUN_ID,
            "--run-type",
            "exploratory",
            "--candidate-scheme-id",
            CANDIDATE_SCHEME_ID,
            "--research-round-id",
            ROUND_ID,
            "--scores-path",
            str(run_dir / "model_scores_D0.parquet"),
            "--topk",
            "10",
        ]
    )

    attempt_id = load_json(run_dir / "run_state_latest_attempt.json")["attempt_id"]

    print(f"[{now_iso()}] Stage 3/4: Building portfolio artifacts...")
    run_cmd(
        [
            PYTHON,
            str(SCRIPTS_DIR / "build_portfolio_artifacts.py"),
            "--run-id",
            RUN_ID,
            "--attempt-id",
            attempt_id,
            "--run-input-contract",
            str(CONTRACT_PATH),
        ]
    )

    print(f"[{now_iso()}] Stage 4/4: Building fixed test + validation readout...")
    run_cmd(
        [
            PYTHON,
            str(SCRIPTS_DIR / "build_fixed_test_minimal.py"),
            "--run-id",
            RUN_ID,
            "--attempt-id",
            attempt_id,
            "--fixed-test-run-id",
            FIXED_TEST_RUN_ID,
            "--run-input-contract",
            str(CONTRACT_PATH),
        ]
    )

    fixed_test_dir = FIXED_TEST_DIR / RUN_ID
    validation_output = fixed_test_dir / "validation_readout.json"
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
    payload["run_id"] = RUN_ID
    payload["fixed_test_run_id"] = FIXED_TEST_RUN_ID
    return payload


def compute_deltas(challenger: dict, reference: dict) -> dict:
    result = {}
    for key in (
        "annual_relative_return",
        "relative_ir",
        "max_drawdown",
        "avg_turnover_daily",
        "avg_invested_weight",
        "avg_cash_weight",
    ):
        c_val = challenger.get(key)
        r_val = reference.get(key)
        result[f"{key}_delta"] = (c_val - r_val) if (c_val is not None and r_val is not None) else None
    return result


def topk_pass(summary: dict | None) -> bool | None:
    if not summary:
        return None
    perturbations = summary.get("perturbations")
    if not isinstance(perturbations, list) or not perturbations:
        return None
    for row in perturbations:
        if row.get("annual_relative_return") is None or row.get("annual_relative_return") <= 0:
            return False
    return True


def cost_stress_pass(summary: dict | None) -> bool | None:
    if not summary:
        return None
    return bool(summary.get("pass_cost_stress_relative_return_floor"))


def low_liquidity_share(summary: dict | None) -> float | None:
    if not summary:
        return None
    for key in ("avg_low_liquidity_weight_share", "low_liquidity_weight_share", "average_low_liquidity_weight_share"):
        value = summary.get(key)
        if value is not None:
            return value
    return None


def assess_round(challenger: dict, ref_cord30: dict, ref_v18: dict, topk_ok: bool | None, cost_ok: bool | None) -> dict:
    deltas_vs_cord30 = compute_deltas(challenger, ref_cord30)
    deltas_vs_v18 = compute_deltas(challenger, ref_v18)
    keep = bool(
        deltas_vs_cord30.get("avg_turnover_daily_delta") is not None
        and deltas_vs_cord30["avg_turnover_daily_delta"] < 0
        and deltas_vs_v18.get("annual_relative_return_delta") is not None
        and deltas_vs_v18["annual_relative_return_delta"] > 0
        and deltas_vs_v18.get("relative_ir_delta") is not None
        and deltas_vs_v18["relative_ir_delta"] > 0
        and deltas_vs_v18.get("max_drawdown_delta") is not None
        and deltas_vs_v18["max_drawdown_delta"] > 0
        and challenger.get("avg_invested_weight", 0.0) >= 0.18
    )
    if topk_ok is False or cost_ok is False:
        keep = False
    return {
        "round_decision": "KEEP" if keep else "REJECT",
        "status_for_registry": "exploratory_family_candidate" if keep else "weak_candidate",
        "deltas_vs_cord30": deltas_vs_cord30,
        "deltas_vs_v18": deltas_vs_v18,
    }


def append_jsonl(path: Path, row: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    if not BASE_PANELS_DIR.exists():
        raise FileNotFoundError(f"Missing required trainval panel base directory: {BASE_PANELS_DIR}")
    ROUND_DIR.mkdir(parents=True, exist_ok=True)

    reference_cord30 = load_validation_readout(REFERENCE_CORD30_FIXED_TEST_DIR)
    reference_v18 = load_validation_readout(ANCHOR_V18_FIXED_TEST_DIR)

    challenger = build_family()

    challenger_fixed_test_dir = FIXED_TEST_DIR / RUN_ID
    topk_summary = load_optional_json(challenger_fixed_test_dir / "topk_perturbation_summary.json")
    cost_summary = load_optional_json(challenger_fixed_test_dir / "cost_stress_summary.json")
    low_liquidity_summary = load_optional_json(challenger_fixed_test_dir / "low_liquidity_exposure_summary.json")

    topk_ok = topk_pass(topk_summary)
    cost_ok = cost_stress_pass(cost_summary)
    challenger_low_liquidity = low_liquidity_share(low_liquidity_summary)
    reference_cord30_low_liquidity = low_liquidity_share(
        load_optional_json(REFERENCE_CORD30_FIXED_TEST_DIR / "low_liquidity_exposure_summary.json")
    )
    reference_v18_low_liquidity = low_liquidity_share(
        load_optional_json(ANCHOR_V18_FIXED_TEST_DIR / "low_liquidity_exposure_summary.json")
    )

    assessment = assess_round(challenger, reference_cord30, reference_v18, topk_ok, cost_ok)
    summary = {
        "research_round_id": ROUND_ID,
        "generated_at": now_iso(),
        "snapshot_id": load_json(CONTRACT_PATH)["snapshot_id"],
        "code_hash": compute_code_hash(),
        "candidate_scheme_id": CANDIDATE_SCHEME_ID,
        "baseline_reference_candidate_scheme_id": REFERENCE_CORD30_CANDIDATE_ID,
        "external_anchor_candidate_scheme_id": ANCHOR_V18_CANDIDATE_ID,
        "challenger_validation": challenger,
        "reference_validation_cord30": reference_cord30,
        "reference_validation_v18": reference_v18,
        "challenger_topk_perturbation": topk_summary,
        "challenger_cost_stress": cost_summary,
        "challenger_low_liquidity_exposure": low_liquidity_summary,
        "challenger_topk_pass": topk_ok,
        "challenger_cost_stress_pass": cost_ok,
        "challenger_low_liquidity_weight_share": challenger_low_liquidity,
        "reference_cord30_low_liquidity_weight_share": reference_cord30_low_liquidity,
        "reference_v18_low_liquidity_weight_share": reference_v18_low_liquidity,
        "deltas_vs_cord30": assessment["deltas_vs_cord30"],
        "deltas_vs_v18": assessment["deltas_vs_v18"],
        "round_decision": assessment["round_decision"],
    }
    write_json(ROUND_DIR / "challenger_vs_cord30_summary.json", summary)

    def fmt(value: float | None) -> str:
        return "null" if value is None else f"{value:.6f}"

    lines = [
        "# Alpha158 CORR30 + CORD30 Dual-Signal Family Results",
        "",
        f"生成时间: {summary['generated_at']}",
        "",
        "## 轮次结论",
        "",
        f"- `round_decision(轮次结论) = {assessment['round_decision']}`",
        f"- `candidate_scheme_id(候选方案ID) = {CANDIDATE_SCHEME_ID}`",
        "",
        "## Challenger 验证期绝对指标",
        "",
        f"- `annual_relative_return(年化超额收益) = {fmt(challenger.get('annual_relative_return'))}`",
        f"- `relative_ir(相对信息比率) = {fmt(challenger.get('relative_ir'))}`",
        f"- `max_drawdown(最大回撤) = {fmt(challenger.get('max_drawdown'))}`",
        f"- `avg_turnover_daily(平均日换手) = {fmt(challenger.get('avg_turnover_daily'))}`",
        f"- `avg_invested_weight(平均投资仓位) = {fmt(challenger.get('avg_invested_weight'))}`",
        f"- `avg_cash_weight(平均现金仓位) = {fmt(challenger.get('avg_cash_weight'))}`",
        "",
        "## vs standalone CORD30",
        "",
        f"- `annual_relative_return_delta(年化超额收益变化) = {fmt(assessment['deltas_vs_cord30'].get('annual_relative_return_delta'))}`",
        f"- `relative_ir_delta(相对信息比率变化) = {fmt(assessment['deltas_vs_cord30'].get('relative_ir_delta'))}`",
        f"- `max_drawdown_delta(最大回撤变化) = {fmt(assessment['deltas_vs_cord30'].get('max_drawdown_delta'))}`",
        f"- `avg_turnover_daily_delta(平均日换手变化) = {fmt(assessment['deltas_vs_cord30'].get('avg_turnover_daily_delta'))}`",
        f"- `avg_invested_weight_delta(平均投资仓位变化) = {fmt(assessment['deltas_vs_cord30'].get('avg_invested_weight_delta'))}`",
        "",
        "## vs v18",
        "",
        f"- `annual_relative_return_delta(年化超额收益变化) = {fmt(assessment['deltas_vs_v18'].get('annual_relative_return_delta'))}`",
        f"- `relative_ir_delta(相对信息比率变化) = {fmt(assessment['deltas_vs_v18'].get('relative_ir_delta'))}`",
        f"- `max_drawdown_delta(最大回撤变化) = {fmt(assessment['deltas_vs_v18'].get('max_drawdown_delta'))}`",
        f"- `avg_turnover_daily_delta(平均日换手变化) = {fmt(assessment['deltas_vs_v18'].get('avg_turnover_daily_delta'))}`",
        f"- `avg_invested_weight_delta(平均投资仓位变化) = {fmt(assessment['deltas_vs_v18'].get('avg_invested_weight_delta'))}`",
        "",
        "## 审计补充",
        "",
        f"- `topk_perturbation_pass(TopK扰动通过) = {str(topk_ok).lower() if topk_ok is not None else 'null'}`",
        f"- `cost_stress_pass(成本压力通过) = {str(cost_ok).lower() if cost_ok is not None else 'null'}`",
        f"- `low_liquidity_weight_share(低流动性权重占比) = {fmt(challenger_low_liquidity)}`",
        "",
    ]
    (ROUND_DIR / "challenger_vs_cord30_summary.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )

    closeout_lines = [
        "# Alpha158 CORR30 + CORD30 Dual-Signal Family — Closeout",
        "",
        f"日期: {datetime.now().date().isoformat()}",
        "",
        "## 结论",
        "",
        f"**`round_decision = {assessment['round_decision']}`**",
        "",
        "## 解释",
        "",
        "这轮只测试一个结构性问题：双信号融合本身能否在不引入 refresh / extraction / weight-tilt 干预的情况下，缓解单信号 `TopK + 等权 + 全刷新` 的结构性换手。",
        "",
        f"- 相对 `cord30` 的 `avg_turnover_daily(平均日换手)` 变化 = {fmt(assessment['deltas_vs_cord30'].get('avg_turnover_daily_delta'))}",
        f"- 相对 `v18` 的 `avg_turnover_daily(平均日换手)` 变化 = {fmt(assessment['deltas_vs_v18'].get('avg_turnover_daily_delta'))}",
        f"- `topk_perturbation_pass(TopK扰动通过) = {str(topk_ok).lower() if topk_ok is not None else 'null'}`",
        f"- `cost_stress_pass(成本压力通过) = {str(cost_ok).lower() if cost_ok is not None else 'null'}`",
    ]
    (ROUND_DIR / "closeout.md").write_text("\n".join(closeout_lines).rstrip() + "\n", encoding="utf-8")

    timestamp = now_iso()
    append_jsonl(
        REGISTRY_DIR / "research_round_registry.jsonl",
        {
            "registered_at": "2026-04-30T17:17:11+08:00",
            "research_round_id": ROUND_ID,
            "status": "completed_exploratory_family_seed",
            "research_tier": "exploratory",
            "run_type": "exploratory_family_seed",
            "research_question": load_json(ROUND_DIR / "preregistration.json")["research_question"],
            "allowed_core_dimension": "score family only",
            "changed_dimension": "score_family",
            "change_control_rule": "single_dimension_only",
            "candidate_scheme_ids": [CANDIDATE_SCHEME_ID],
            "planned_candidate_scheme_ids": [CANDIDATE_SCHEME_ID],
            "baseline_reference_candidate_scheme_id": REFERENCE_CORD30_CANDIDATE_ID,
            "external_anchor_candidate_scheme_id": ANCHOR_V18_CANDIDATE_ID,
            "snapshot_id": load_json(CONTRACT_PATH)["snapshot_id"],
            "round_decision": assessment["round_decision"],
            "status_updated_at": timestamp,
            "notes": f"Exploratory dual-signal family completed. topk_perturbation_pass={str(topk_ok).lower() if topk_ok is not None else 'null'}, cost_stress_pass={str(cost_ok).lower() if cost_ok is not None else 'null'}.",
        },
    )
    append_jsonl(
        REGISTRY_DIR / "candidate_scheme_registry.jsonl",
        {
            "registered_at": "2026-04-30T17:17:11+08:00",
            "candidate_scheme_id": CANDIDATE_SCHEME_ID,
            "scheme_family": "alpha158_reserve_dual_signal_family",
            "status": assessment["status_for_registry"],
            "research_round_id": ROUND_ID,
            "research_tier": "exploratory",
            "owner": "codex",
            "score_builder": "build_alpha158_head_extraction_dual_signal_family_scores.py",
            "feature_source": "bars_daily_derived",
            "feature_set": ["alpha158_corr30_raw", "alpha158_cord30_raw"],
            "score_rule": "mean(percentile_rank(alpha158_corr30_raw DESC), percentile_rank(alpha158_cord30_raw DESC)); require min_feature_count >= 2",
            "baseline_reference_candidate_scheme_id": REFERENCE_CORD30_CANDIDATE_ID,
            "external_anchor_candidate_scheme_id": ANCHOR_V18_CANDIDATE_ID,
            "snapshot_id": load_json(CONTRACT_PATH)["snapshot_id"],
            "execution_logic_version": "warehouse_execution_v3",
            "changed_dimension": "score_family",
            "annual_relative_return_delta_vs_cord30": assessment["deltas_vs_cord30"].get("annual_relative_return_delta"),
            "relative_ir_delta_vs_cord30": assessment["deltas_vs_cord30"].get("relative_ir_delta"),
            "max_drawdown_delta_vs_cord30": assessment["deltas_vs_cord30"].get("max_drawdown_delta"),
            "avg_turnover_daily_delta_vs_cord30": assessment["deltas_vs_cord30"].get("avg_turnover_daily_delta"),
            "annual_relative_return_delta_vs_v18": assessment["deltas_vs_v18"].get("annual_relative_return_delta"),
            "relative_ir_delta_vs_v18": assessment["deltas_vs_v18"].get("relative_ir_delta"),
            "max_drawdown_delta_vs_v18": assessment["deltas_vs_v18"].get("max_drawdown_delta"),
            "avg_turnover_daily_delta_vs_v18": assessment["deltas_vs_v18"].get("avg_turnover_daily_delta"),
            "avg_invested_weight": challenger.get("avg_invested_weight"),
            "topk_perturbation_pass": topk_ok,
            "cost_stress_pass": cost_ok,
            "status_updated_at": timestamp,
            "notes": "First exploratory dual-signal family from reserve head-extraction cards corr30 and cord30. This result answers whether score smoothing alone can reduce structural single-signal turnover under a frozen simple operating contract.",
            "weakness_reason": None if assessment["status_for_registry"] != "weak_candidate" else "The dual-signal family did not clear the exploratory keep threshold after full-chain evaluation.",
        },
    )


if __name__ == "__main__":
    main()
