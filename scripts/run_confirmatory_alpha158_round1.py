#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Run the first confirmatory Alpha158 standalone shortlist round on the trainval-only
snapshot and project panels.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import hashlib
from datetime import datetime
from pathlib import Path


ROOT = Path("/Users/wy/MiscProject/multi_factor")
PYTHON = "/opt/anaconda3/envs/quant_trade/bin/python"
SCRIPTS_DIR = ROOT / "scripts"
RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
FIXED_TEST_DIR = ROOT / "artifacts" / "fixed_test"
REGISTRY_DIR = ROOT / "artifacts" / "research_registry"
ROUND_ID = "rr_confirmatory_alpha158_standalone_shortlist_round1_20260429"
ROUND_DIR = REGISTRY_DIR / "research_rounds" / ROUND_ID
CONTRACT_PATH = ROOT / "contracts" / "run_input_contract.research_trainval_20211231.json"
BASE_PANELS_RUN_ID = "project_panels_research_trainval_20211231_20260429"
BASE_PANELS_DIR = RUN_STATE_DIR / BASE_PANELS_RUN_ID
VALIDATION_START = "20190101"
VALIDATION_END = "20211231"
REFERENCE_CANDIDATE_ID = "price_volume_v18_refresh_hysteresis"
REFERENCE_RUN_ID = "confirmatory_reference_v18_trainval_20260429"
REFERENCE_FIXED_TEST_RUN_ID = "confirmatory_fixed_test_reference_v18_trainval_20260429"
SHORTLIST = [
    {
        "candidate_scheme_id": "price_volume_single_signal_alpha158_cord30_v1",
        "feature_name": "CORD30",
        "mechanism": "price_volume_change_corr",
    },
    {
        "candidate_scheme_id": "price_volume_single_signal_alpha158_vsumd60_v1",
        "feature_name": "VSUMD60",
        "mechanism": "volume_expansion_balance",
    },
    {
        "candidate_scheme_id": "price_volume_single_signal_alpha158_imxd5_v1",
        "feature_name": "IMXD5",
        "mechanism": "path_ordering_breakout",
    },
]
CODE_HASH_FILES = [
    SCRIPTS_DIR / "run_confirmatory_alpha158_round1.py",
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
        hasher.update(path.name.encode("utf-8"))
        hasher.update(path.read_bytes())
    return hasher.hexdigest()


def build_reference() -> dict:
    run_dir = RUN_STATE_DIR / REFERENCE_RUN_ID
    run_dir.mkdir(parents=True, exist_ok=True)
    stage_panels(run_dir)

    run_cmd(
        [
            PYTHON,
            str(SCRIPTS_DIR / "build_baseline_model_scores.py"),
            "--run-id",
            REFERENCE_RUN_ID,
            "--candidate-scheme-id",
            REFERENCE_CANDIDATE_ID,
            "--feature-preset",
            "price_volume_v16_remove_trend_consistency",
            "--min-feature-count",
            "2",
            "--run-input-contract",
            str(CONTRACT_PATH),
        ]
    )
    run_cmd(
        [
            PYTHON,
            str(SCRIPTS_DIR / "build_run_state_skeleton.py"),
            "--run-id",
            REFERENCE_RUN_ID,
            "--run-type",
            "confirmatory_reference",
            "--candidate-scheme-id",
            REFERENCE_CANDIDATE_ID,
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
            REFERENCE_RUN_ID,
            "--attempt-id",
            attempt_id,
        ]
    )
    run_cmd(
        [
            PYTHON,
            str(SCRIPTS_DIR / "build_fixed_test_minimal.py"),
            "--run-id",
            REFERENCE_RUN_ID,
            "--attempt-id",
            attempt_id,
            "--fixed-test-run-id",
            REFERENCE_FIXED_TEST_RUN_ID,
            "--run-input-contract",
            str(CONTRACT_PATH),
        ]
    )
    fixed_test_dir = FIXED_TEST_DIR / REFERENCE_RUN_ID
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
    return load_json(validation_output)


def run_candidate(candidate: dict) -> dict:
    run_id = f"confirmatory_{candidate['feature_name'].lower()}_trainval_20260429"
    fixed_test_run_id = f"confirmatory_fixed_test_{candidate['feature_name'].lower()}_trainval_20260429"
    run_dir = RUN_STATE_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    stage_panels(run_dir)

    run_cmd(
        [
            PYTHON,
            str(SCRIPTS_DIR / "build_alpha158_standalone_model_scores.py"),
            "--run-id",
            run_id,
            "--feature-name",
            candidate["feature_name"],
            "--candidate-scheme-id",
            candidate["candidate_scheme_id"],
            "--run-input-contract",
            str(CONTRACT_PATH),
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
            candidate["candidate_scheme_id"],
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
            "--fixed-test-run-id",
            fixed_test_run_id,
            "--run-input-contract",
            str(CONTRACT_PATH),
        ]
    )
    fixed_test_dir = FIXED_TEST_DIR / run_id
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
    payload["run_id"] = run_id
    payload["fixed_test_run_id"] = fixed_test_run_id
    payload["mechanism"] = candidate["mechanism"]
    return payload


def decide(reference: dict, payload: dict) -> dict:
    annual_relative_return_delta = None
    relative_ir_delta = None
    max_drawdown_delta = None
    avg_turnover_daily_delta = None
    if reference.get("annual_relative_return") is not None and payload.get("annual_relative_return") is not None:
        annual_relative_return_delta = payload["annual_relative_return"] - reference["annual_relative_return"]
    if reference.get("relative_ir") is not None and payload.get("relative_ir") is not None:
        relative_ir_delta = payload["relative_ir"] - reference["relative_ir"]
    if reference.get("max_drawdown") is not None and payload.get("max_drawdown") is not None:
        max_drawdown_delta = payload["max_drawdown"] - reference["max_drawdown"]
    if reference.get("avg_turnover_daily") is not None and payload.get("avg_turnover_daily") is not None:
        avg_turnover_daily_delta = payload["avg_turnover_daily"] - reference["avg_turnover_daily"]

    pass_boolean = bool(
        annual_relative_return_delta is not None
        and annual_relative_return_delta > 0.005
        and relative_ir_delta is not None
        and relative_ir_delta > 0.05
        and max_drawdown_delta is not None
        and max_drawdown_delta >= -0.05
        and avg_turnover_daily_delta is not None
        and avg_turnover_daily_delta <= 0.02
        and payload.get("avg_invested_weight", 0.0) >= 0.15
    )
    return {
        "pass_boolean": pass_boolean,
        "annual_relative_return_delta": annual_relative_return_delta,
        "relative_ir_delta": relative_ir_delta,
        "max_drawdown_delta": max_drawdown_delta,
        "avg_turnover_daily_delta": avg_turnover_daily_delta,
        "boolean_expression": (
            "(validation_annual_relative_return - reference_validation_annual_relative_return > 0.005) "
            "AND (validation_relative_ir - reference_validation_relative_ir > 0.05) "
            "AND (validation_max_drawdown - reference_validation_max_drawdown >= -0.05) "
            "AND (validation_avg_turnover_daily - reference_validation_avg_turnover_daily <= 0.02) "
            "AND (validation_avg_invested_weight >= 0.15)"
        ),
    }


def main() -> None:
    if not BASE_PANELS_DIR.exists():
        raise FileNotFoundError(f"Missing required trainval panel base directory: {BASE_PANELS_DIR}")
    ROUND_DIR.mkdir(parents=True, exist_ok=True)

    reference = build_reference()
    results: list[dict] = []
    for candidate in SHORTLIST:
        payload = run_candidate(candidate)
        decision = decide(reference, payload)
        results.append({**candidate, **payload, **decision})

    passed = [row for row in results if row["pass_boolean"]]
    top_ranked = sorted(
        results,
        key=lambda row: (
            row["pass_boolean"],
            row["annual_relative_return_delta"] if row["annual_relative_return_delta"] is not None else -999.0,
            row["relative_ir_delta"] if row["relative_ir_delta"] is not None else -999.0,
            row["max_drawdown_delta"] if row["max_drawdown_delta"] is not None else -999.0,
        ),
        reverse=True,
    )
    round_decision = "KEEP" if passed else "REJECT"
    summary = {
        "research_round_id": ROUND_ID,
        "generated_at": now_iso(),
        "snapshot_id": load_json(CONTRACT_PATH)["snapshot_id"],
        "code_hash": compute_code_hash(),
        "reference_candidate_scheme_id": REFERENCE_CANDIDATE_ID,
        "reference_validation": reference,
        "results": results,
        "passed_candidates": [row["candidate_scheme_id"] for row in passed],
        "top_ranked_candidates": [row["candidate_scheme_id"] for row in top_ranked],
        "round_decision": round_decision,
        "winner_candidate_scheme_id": top_ranked[0]["candidate_scheme_id"] if top_ranked else None,
    }
    write_json(ROUND_DIR / "confirmatory_round1_results.json", summary)

    lines = [
        f"# {ROUND_ID} results",
        "",
        "## Round decision",
        "",
        f"- `round_decision(轮次结论) = {round_decision}`",
        f"- `winner_candidate_scheme_id(排序第一候选) = {summary['winner_candidate_scheme_id']}`",
        f"- `passed_candidate_count(通过候选数) = {len(passed)}`",
        "",
        "## Reference validation",
        "",
        f"- `annual_relative_return(年化超额收益) = {reference['annual_relative_return']:.6f}`" if reference.get("annual_relative_return") is not None else "- `annual_relative_return(年化超额收益) = null`",
        f"- `relative_ir(相对信息比率) = {reference['relative_ir']:.6f}`" if reference.get("relative_ir") is not None else "- `relative_ir(相对信息比率) = null`",
        f"- `max_drawdown(最大回撤) = {reference['max_drawdown']:.6f}`" if reference.get("max_drawdown") is not None else "- `max_drawdown(最大回撤) = null`",
        f"- `avg_turnover_daily(平均日换手) = {reference['avg_turnover_daily']:.6f}`" if reference.get("avg_turnover_daily") is not None else "- `avg_turnover_daily(平均日换手) = null`",
        "",
        "## Candidate results",
        "",
    ]
    for row in top_ranked:
        lines.extend(
            [
                f"- `{row['candidate_scheme_id']}`",
                f"  - `pass_boolean(布尔通过) = {str(row['pass_boolean']).lower()}`",
                f"  - `validation_annual_relative_return(验证期年化超额收益) = {row['annual_relative_return']:.6f}`" if row.get("annual_relative_return") is not None else "  - `validation_annual_relative_return(验证期年化超额收益) = null`",
                f"  - `validation_relative_ir(验证期相对信息比率) = {row['relative_ir']:.6f}`" if row.get("relative_ir") is not None else "  - `validation_relative_ir(验证期相对信息比率) = null`",
                f"  - `validation_max_drawdown(验证期最大回撤) = {row['max_drawdown']:.6f}`" if row.get("max_drawdown") is not None else "  - `validation_max_drawdown(验证期最大回撤) = null`",
                f"  - `validation_avg_turnover_daily(验证期平均日换手) = {row['avg_turnover_daily']:.6f}`" if row.get("avg_turnover_daily") is not None else "  - `validation_avg_turnover_daily(验证期平均日换手) = null`",
                f"  - `annual_relative_return_delta_vs_v18(相对v18验证期年化超额收益变化) = {row['annual_relative_return_delta']:.6f}`" if row.get("annual_relative_return_delta") is not None else "  - `annual_relative_return_delta_vs_v18(相对v18验证期年化超额收益变化) = null`",
                f"  - `relative_ir_delta_vs_v18(相对v18验证期相对信息比率变化) = {row['relative_ir_delta']:.6f}`" if row.get("relative_ir_delta") is not None else "  - `relative_ir_delta_vs_v18(相对v18验证期相对信息比率变化) = null`",
                f"  - `max_drawdown_delta_vs_v18(相对v18验证期最大回撤变化) = {row['max_drawdown_delta']:.6f}`" if row.get("max_drawdown_delta") is not None else "  - `max_drawdown_delta_vs_v18(相对v18验证期最大回撤变化) = null`",
                f"  - `avg_turnover_daily_delta_vs_v18(相对v18验证期平均日换手变化) = {row['avg_turnover_daily_delta']:.6f}`" if row.get("avg_turnover_daily_delta") is not None else "  - `avg_turnover_daily_delta_vs_v18(相对v18验证期平均日换手变化) = null`",
                "",
            ]
        )
    (ROUND_DIR / "confirmatory_round1_results.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
