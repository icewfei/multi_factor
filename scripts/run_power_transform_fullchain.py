#!/opt/anaconda3/envs/quant_trade/bin/python
"""Full-chain test for power transform candidates vs p98 baseline."""

import json
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path("/Users/wy/MiscProject/multi_factor")
PYTHON = "/opt/anaconda3/envs/quant_trade/bin/python"
SCRIPTS = ROOT / "scripts"
RUN_STATE = ROOT / "artifacts" / "run_state"
FIXED_TEST = ROOT / "artifacts" / "fixed_test"
CONTRACT = ROOT / "contracts" / "run_input_contract.research_trainval_20211231.json"
BASE_PANELS = RUN_STATE / "project_panels_research_trainval_20211231_20260429"
ROUND_ID = "rr_exploratory_power_transform_reversal_20260506"
V4_SCORES = RUN_STATE / "exploratory_power_transform_v4" / "model_scores_D0_power_v4.parquet"
P98_FIXED_TEST = FIXED_TEST / "confirmatory_reversal_p98_trainval_20260506"

CANDIDATES = [
    ("exploratory_power_inv_rev_a4_v1", "power_inv_rev_a4_v1", "Power transform alpha=4"),
    ("exploratory_power_inv_rev_a6_v1", "power_inv_rev_a6_v1", "Power transform alpha=6"),
]


def run_cmd(args, desc=""):
    print(f"  [{desc}] {' '.join(args[:5])}...")
    subprocess.run(args, check=True)


def stage_panels(run_dir):
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    for fname in ["project_label_panel.parquet", "project_sample_panel.parquet",
                   "project_execution_panel.parquet", "data_quality_audit.json"]:
        src = BASE_PANELS / fname
        dst = run_dir / fname
        if not dst.exists():
            dst.symlink_to(src)


def run_one(run_id, scheme_id, desc):
    print(f"\n{'='*60}")
    print(f"Full-chain: {desc} ({scheme_id})")
    print(f"{'='*60}")

    run_dir = RUN_STATE / run_id
    stage_panels(run_dir)

    # Filter scores to single scheme
    import duckdb
    filtered = run_dir / "model_scores_D0.parquet"
    if not filtered.exists():
        con = duckdb.connect()
        con.execute(f"COPY (SELECT * FROM read_parquet('{V4_SCORES}') WHERE candidate_scheme_id='{scheme_id}') TO '{filtered}' (FORMAT PARQUET)")
        con.close()

    # Run state skeleton
    run_cmd([PYTHON, str(SCRIPTS / "build_run_state_skeleton.py"),
             "--run-id", run_id, "--run-type", "exploratory",
             "--candidate-scheme-id", scheme_id,
             "--research-round-id", ROUND_ID,
             "--scores-path", str(filtered), "--topk", "10"],
            desc="run_state")

    attempt_id = json.loads((run_dir / "run_state_latest_attempt.json").read_text())["attempt_id"]

    # Portfolio artifacts
    run_cmd([PYTHON, str(SCRIPTS / "build_portfolio_artifacts.py"),
             "--run-id", run_id, "--attempt-id", attempt_id,
             "--run-input-contract", str(CONTRACT)], desc="portfolio")

    # Fixed test
    ft_dir = FIXED_TEST / run_id
    ft_dir.mkdir(parents=True, exist_ok=True)
    run_cmd([PYTHON, str(SCRIPTS / "build_fixed_test_minimal.py"),
             "--run-id", run_id, "--attempt-id", attempt_id,
             "--run-input-contract", str(CONTRACT)], desc="fixed_test")

    # Validation readout
    run_cmd([PYTHON, str(SCRIPTS / "build_confirmatory_validation_readout.py"),
             "--fixed-test-dir", str(ft_dir),
             "--validation-start", "20190101", "--validation-end", "20211231",
             "--output-path", str(ft_dir / "validation_readout.json")], desc="validation")

    return json.loads((ft_dir / "validation_readout.json").read_text())


def main():
    # Load p98
    p98_val = json.loads((P98_FIXED_TEST / "validation_readout.json").read_text())
    p98_cost = json.loads((P98_FIXED_TEST / "cost_stress_summary.json").read_text())

    print("p98 BASELINE (2019-2021):")
    print(f"  ann_rel_ret={p98_val['annual_relative_return']:.6f}  max_dd={p98_val['max_drawdown']:.6f}  sharpe={p98_val['sharpe_ratio']:.2f}  turnover={p98_val['avg_turnover_daily']:.4f}  inv_wt={p98_val['avg_invested_weight']:.4f}")
    print(f"  cost_stress={p98_cost['annual_relative_return']:.6f}")

    results = {}
    for run_id, scheme_id, desc in CANDIDATES:
        try:
            val = run_one(run_id, scheme_id, desc)
            cost = json.loads((FIXED_TEST / run_id / "cost_stress_summary.json").read_text())
            results[run_id] = {"scheme_id": scheme_id, "desc": desc, "val": val, "cost": cost}
            print(f"  RESULT: ann_rel_ret={val['annual_relative_return']:.6f}  max_dd={val['max_drawdown']:.6f}  sharpe={val['sharpe_ratio']:.2f}")
        except Exception as e:
            print(f"  FAILED: {e}")

    print(f"\n{'='*80}")
    print("COMPARISON (2019-2021 validation)")
    print(f"{'='*80}")
    print(f"{'Scheme':<35} {'AnnRelRet':>10} {'MaxDD':>10} {'Sharpe':>8} {'Turnover':>10} {'InvWt':>8} {'CostStress':>10}")
    print("-" * 91)

    def f(v):
        return f"{v:.6f}" if isinstance(v, float) else str(v)

    print(f"{'p98 (baseline)':<35} {f(p98_val['annual_relative_return']):>10} {f(p98_val['max_drawdown']):>10} {f(p98_val['sharpe_ratio']):>8} {f(p98_val['avg_turnover_daily']):>10} {f(p98_val['avg_invested_weight']):>8} {f(p98_cost['annual_relative_return']):>10}")

    for run_id, r in results.items():
        v = r["val"]
        c = r["cost"]
        print(f"{r['scheme_id']:<35} {f(v['annual_relative_return']):>10} {f(v['max_drawdown']):>10} {f(v['sharpe_ratio']):>8} {f(v['avg_turnover_daily']):>10} {f(v['avg_invested_weight']):>8} {f(c['annual_relative_return']):>10}")

    # Save comparison
    out = FIXED_TEST / "power_transform_fullchain"
    out.mkdir(parents=True, exist_ok=True)
    json.dump({
        "as_of": datetime.now().isoformat(),
        "p98": {"val": p98_val, "cost": p98_cost},
        "candidates": {rid: {"scheme_id": r["scheme_id"],
                              "val": {k: r["val"].get(k) for k in ["annual_relative_return", "max_drawdown", "sharpe_ratio", "avg_turnover_daily", "avg_invested_weight"]},
                              "cost": r["cost"]}
                       for rid, r in results.items()}
    }, open(out / "comparison.json", "w"), indent=2)
    print(f"\nSaved: {out / 'comparison.json'}")


if __name__ == "__main__":
    main()
