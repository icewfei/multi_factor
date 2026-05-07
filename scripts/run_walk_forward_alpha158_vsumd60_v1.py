#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Run walk-forward v1 for the standalone confirmatory Alpha158 VSUMD60 winner.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
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
WALK_FORWARD_DIR = ROOT / "artifacts" / "walk_forward"
CONTRACT_PATH = ROOT / "contracts" / "run_input_contract.walk_forward_20260418_181408.json"

ROUND_ID = "rr_walk_forward_alpha158_vsumd60_v1_20260430"
ROUND_DIR = REGISTRY_DIR / "research_rounds" / ROUND_ID
PANEL_RUN_ID = "project_panels_walk_forward_full_20260418_181408_20260430"
PANEL_DIR = RUN_STATE_DIR / PANEL_RUN_ID
RUN_ID = "walk_forward_alpha158_vsumd60_v1_full_20260430"
FIXED_TEST_RUN_ID = "walk_forward_fixed_test_alpha158_vsumd60_v1_full_20260430"
WALK_FORWARD_RUN_ID = "wf_alpha158_vsumd60_v1_20260430"
WF_DIR = WALK_FORWARD_DIR / WALK_FORWARD_RUN_ID

CANDIDATE_SCHEME_ID = "price_volume_single_signal_alpha158_vsumd60_v1"
FEATURE_NAME = "VSUMD60"
REFERENCE_CANDIDATE_ID = "price_volume_v18_refresh_hysteresis"

WINDOWS = [
    {
        "window_id": "wf_2022",
        "train_start": "20100101",
        "train_end": "20181231",
        "valid_start": "20190101",
        "valid_end": "20211231",
        "test_start": "20220101",
        "test_end": "20221231",
    },
    {
        "window_id": "wf_2023",
        "train_start": "20100101",
        "train_end": "20191231",
        "valid_start": "20200101",
        "valid_end": "20221231",
        "test_start": "20230101",
        "test_end": "20231231",
    },
    {
        "window_id": "wf_2024",
        "train_start": "20100101",
        "train_end": "20201231",
        "valid_start": "20210101",
        "valid_end": "20231231",
        "test_start": "20240101",
        "test_end": "20241231",
    },
    {
        "window_id": "wf_2025",
        "train_start": "20100101",
        "train_end": "20211231",
        "valid_start": "20220101",
        "valid_end": "20241231",
        "test_start": "20250101",
        "test_end": "20251231",
    },
]

CODE_HASH_FILES = [
    SCRIPTS_DIR / "run_walk_forward_alpha158_vsumd60_v1.py",
    SCRIPTS_DIR / "build_project_panels.py",
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


def run_cmd(args: list[str]) -> None:
    subprocess.run(args, check=True)


def read_backtest_max_trade_date(backtest_path: Path) -> int | None:
    if not backtest_path.exists():
        return None
    max_trade_date: int | None = None
    with backtest_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            value = row.get("trade_date")
            if not value:
                continue
            trade_date = int(value)
            if max_trade_date is None or trade_date > max_trade_date:
                max_trade_date = trade_date
    return max_trade_date


def compute_code_hash() -> str:
    hasher = hashlib.sha256()
    for path in CODE_HASH_FILES:
        hasher.update(path.name.encode("utf-8"))
        hasher.update(path.read_bytes())
    return hasher.hexdigest()


def ensure_panels() -> None:
    if PANEL_DIR.exists() and (PANEL_DIR / "project_sample_panel.parquet").exists():
        return
    run_cmd(
        [
            PYTHON,
            str(SCRIPTS_DIR / "build_project_panels.py"),
            "--run-id",
            PANEL_RUN_ID,
            "--run-input-contract",
            str(CONTRACT_PATH),
        ]
    )


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
        ensure_symlink(PANEL_DIR / name, run_dir / name)


def ensure_full_run() -> None:
    run_dir = RUN_STATE_DIR / RUN_ID
    existing_backtest = FIXED_TEST_DIR / RUN_ID / "backtest_daily.csv"
    existing_max_trade_date = read_backtest_max_trade_date(existing_backtest)
    if existing_max_trade_date is not None and existing_max_trade_date >= 20251231:
        return
    run_dir.mkdir(parents=True, exist_ok=True)
    stage_panels(run_dir)
    run_cmd(
        [
            PYTHON,
            str(SCRIPTS_DIR / "build_alpha158_standalone_model_scores.py"),
            "--run-id",
            RUN_ID,
            "--feature-name",
            FEATURE_NAME,
            "--candidate-scheme-id",
            CANDIDATE_SCHEME_ID,
            "--run-input-contract",
            str(CONTRACT_PATH),
        ]
    )
    run_cmd(
        [
            PYTHON,
            str(SCRIPTS_DIR / "build_run_state_skeleton.py"),
            "--run-id",
            RUN_ID,
            "--run-type",
            "walk_forward",
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


def build_window_validation(window: dict) -> dict:
    output_path = WF_DIR / f"{window['window_id']}_validation_readout.json"
    run_cmd(
        [
            PYTHON,
            str(SCRIPTS_DIR / "build_confirmatory_validation_readout.py"),
            "--fixed-test-dir",
            str(FIXED_TEST_DIR / RUN_ID),
            "--validation-start",
            window["test_start"],
            "--validation-end",
            window["test_end"],
            "--output-path",
            str(output_path),
        ]
    )
    payload = load_json(output_path)
    payload.update(
        {
            "window_id": window["window_id"],
            "train_start": window["train_start"],
            "train_end": window["train_end"],
            "valid_start": window["valid_start"],
            "valid_end": window["valid_end"],
            "test_start": window["test_start"],
            "test_end": window["test_end"],
        }
    )
    write_json(output_path, payload)
    return payload


def build_stitched_backtest() -> dict:
    source_path = FIXED_TEST_DIR / RUN_ID / "backtest_daily.csv"
    stitched_path = WF_DIR / "stitched_backtest_daily.csv"
    rows: list[dict] = []
    with source_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames or []
        for row in reader:
            trade_date = row["trade_date"]
            if "20220101" <= trade_date <= "20251231":
                rows.append(row)
    if not rows:
        raise ValueError("No stitched walk-forward rows found in 2022-2025.")
    with stitched_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    effective = [
        row for row in rows
        if row.get("benchmark_return_daily") not in ("", None)
        and row.get("relative_return_daily") not in ("", None)
        and row["benchmark_return_daily"].lower() != "nan"
        and row["relative_return_daily"].lower() != "nan"
    ]
    relative_daily = [float(row["relative_return_daily"]) for row in effective]
    relative_nav = 1.0
    benchmark_nav = 1.0
    total_equities = [float(row["total_equity"]) for row in rows]
    running_peak = -1.0
    max_drawdown = 0.0
    for equity in total_equities:
        running_peak = max(running_peak, equity)
        if running_peak > 0:
            max_drawdown = min(max_drawdown, (equity / running_peak) - 1.0)
    for row in effective:
        portfolio_ret = float(row["portfolio_daily_return"])
        benchmark_ret = float(row["benchmark_return_daily"])
        relative_nav *= (1.0 + portfolio_ret) / (1.0 + benchmark_ret)
        benchmark_nav *= 1.0 + benchmark_ret
    n_effective = len(effective)
    n_days = len(rows)
    avg_relative = sum(relative_daily) / n_effective if n_effective else 0.0
    if n_effective > 1:
        variance = sum((x - avg_relative) ** 2 for x in relative_daily) / (n_effective - 1)
        std_relative = math.sqrt(variance)
    else:
        std_relative = 0.0
    if n_effective > 0 and relative_nav > 0:
        annual_relative_return = math.pow(relative_nav, 252.0 / n_effective) - 1.0
    else:
        annual_relative_return = None
    relative_ir = avg_relative / std_relative * math.sqrt(252.0) if std_relative > 0 else None
    return {
        "stitched_backtest_path": str(stitched_path),
        "stitched_days": n_days,
        "effective_relative_days": n_effective,
        "stitched_annual_relative_return": annual_relative_return,
        "stitched_relative_ir": relative_ir,
        "stitched_benchmark_total_return": benchmark_nav - 1.0 if n_effective else None,
        "stitched_max_drawdown": max_drawdown,
        "monthly_positive_ratio": None,
        "return_concentration_ratio": None,
    }


def compute_monthly_stability() -> dict:
    source_path = WF_DIR / "stitched_backtest_daily.csv"
    monthly: dict[str, float] = {}
    with source_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rr = row.get("relative_return_daily")
            br = row.get("benchmark_return_daily")
            if rr in ("", None) or br in ("", None) or rr.lower() == "nan" or br.lower() == "nan":
                continue
            month = row["trade_date"][:6]
            monthly.setdefault(month, 1.0)
            monthly[month] *= 1.0 + float(rr)
    monthly_relative = {k: v - 1.0 for k, v in monthly.items()}
    if not monthly_relative:
        return {"monthly_positive_ratio": None, "return_concentration_ratio": None}
    positives = [v for v in monthly_relative.values() if v > 0]
    monthly_positive_ratio = len(positives) / len(monthly_relative)
    total_positive = sum(positives)
    if total_positive > 0:
        top3 = sorted(positives, reverse=True)[:3]
        return_concentration_ratio = sum(top3) / total_positive
    else:
        return_concentration_ratio = None
    return {
        "monthly_positive_ratio": monthly_positive_ratio,
        "return_concentration_ratio": return_concentration_ratio,
    }


def main() -> None:
    ROUND_DIR.mkdir(parents=True, exist_ok=True)
    WF_DIR.mkdir(parents=True, exist_ok=True)

    ensure_panels()
    ensure_full_run()

    window_results = [build_window_validation(window) for window in WINDOWS]
    stitched = build_stitched_backtest()
    stitched.update(compute_monthly_stability())

    positive_windows = sum(
        1 for row in window_results
        if row.get("annual_relative_return") is not None and row["annual_relative_return"] > 0
    )
    total_windows = len(window_results)
    walk_forward_positive_window_ratio = positive_windows / total_windows if total_windows else None
    walk_forward_ir = stitched["stitched_relative_ir"]
    stitched_annual_relative_return = stitched["stitched_annual_relative_return"]
    continuation_pass = bool(
        walk_forward_positive_window_ratio is not None
        and walk_forward_ir is not None
        and stitched_annual_relative_return is not None
        and walk_forward_positive_window_ratio >= 0.50
        and walk_forward_ir >= 0.00
        and stitched_annual_relative_return >= 0.00
    )
    framework_pass = bool(
        walk_forward_positive_window_ratio is not None
        and walk_forward_ir is not None
        and walk_forward_positive_window_ratio >= 0.75
        and walk_forward_ir >= 0.30
    )

    summary = {
        "research_round_id": ROUND_ID,
        "generated_at": now_iso(),
        "snapshot_id": load_json(CONTRACT_PATH)["snapshot_id"],
        "code_hash": compute_code_hash(),
        "candidate_scheme_id": CANDIDATE_SCHEME_ID,
        "baseline_reference_candidate_scheme_id": REFERENCE_CANDIDATE_ID,
        "walk_forward_protocol": "walk_forward_v1",
        "full_run_id": RUN_ID,
        "fixed_test_run_id": FIXED_TEST_RUN_ID,
        "window_results": window_results,
        "stitched_summary": stitched,
        "aggregates": {
            "positive_window_count": positive_windows,
            "window_count": total_windows,
            "walk_forward_positive_window_ratio": walk_forward_positive_window_ratio,
            "walk_forward_ir": walk_forward_ir,
            "stitched_annual_relative_return": stitched_annual_relative_return,
        },
        "continuation_gate": {
            "decision_rule": "(walk_forward_positive_window_ratio >= 0.50) AND (walk_forward_ir >= 0.00) AND (stitched_annual_relative_return >= 0.00)",
            "pass_boolean": continuation_pass
        },
        "framework_reference_gate": {
            "decision_rule": "(walk_forward_positive_window_ratio >= 0.75) AND (walk_forward_ir >= 0.30)",
            "pass_boolean": framework_pass
        },
        "round_decision": "CONTINUE" if continuation_pass else "STOP",
        "conclusion": (
            "Standalone VSUMD60 retains enough walk-forward deployment quality to justify continued research investment."
            if continuation_pass
            else "Standalone VSUMD60 does not clear even the continuation-grade walk-forward gate, so further investment should stop unless a new problem statement is opened."
        ),
    }
    write_json(ROUND_DIR / "walk_forward_summary.json", summary)

    lines = [
        f"# {ROUND_ID} walk-forward summary",
        "",
        f"- `candidate_scheme_id(候选方案ID) = {CANDIDATE_SCHEME_ID}`",
        f"- `snapshot_id(快照ID) = {summary['snapshot_id']}`",
        f"- `round_decision(轮次结论) = {summary['round_decision']}`",
        f"- `continuation_pass_boolean(继续投入门槛是否通过) = {str(continuation_pass).lower()}`",
        f"- `framework_reference_pass_boolean(框架正式门槛是否通过) = {str(framework_pass).lower()}`",
        "",
        "## Aggregate",
        "",
        f"- `walk_forward_positive_window_ratio(滚动前推正窗口比例) = {walk_forward_positive_window_ratio:.6f}`" if walk_forward_positive_window_ratio is not None else "- `walk_forward_positive_window_ratio(滚动前推正窗口比例) = null`",
        f"- `walk_forward_ir(滚动前推IR) = {walk_forward_ir:.6f}`" if walk_forward_ir is not None else "- `walk_forward_ir(滚动前推IR) = null`",
        f"- `stitched_annual_relative_return(拼接年化超额收益) = {stitched_annual_relative_return:.6f}`" if stitched_annual_relative_return is not None else "- `stitched_annual_relative_return(拼接年化超额收益) = null`",
        f"- `stitched_max_drawdown(拼接最大回撤) = {stitched['stitched_max_drawdown']:.6f}`",
        f"- `monthly_positive_ratio(月度正收益占比) = {stitched['monthly_positive_ratio']:.6f}`" if stitched["monthly_positive_ratio"] is not None else "- `monthly_positive_ratio(月度正收益占比) = null`",
        f"- `return_concentration_ratio(收益集中度指标) = {stitched['return_concentration_ratio']:.6f}`" if stitched["return_concentration_ratio"] is not None else "- `return_concentration_ratio(收益集中度指标) = null`",
        "",
        "## Windows",
        "",
    ]
    for row in window_results:
        arr = row.get("annual_relative_return")
        rir = row.get("relative_ir")
        mdd = row.get("max_drawdown")
        lines.append(f"- `{row['window_id']}`: `annual_relative_return(年化超额收益) = {arr:.6f}`; `relative_ir(相对信息比率) = {rir:.6f}`; `max_drawdown(最大回撤) = {mdd:.6f}`")
    lines.extend(["", "## Conclusion", "", f"- {summary['conclusion']}"])
    (ROUND_DIR / "walk_forward_summary.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
