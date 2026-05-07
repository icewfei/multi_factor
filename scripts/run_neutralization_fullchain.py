#!/opt/anaconda3/envs/quant_trade/bin/python
"""Full-chain test for neutralized reversal candidates."""

import json, subprocess, duckdb
from datetime import datetime
from pathlib import Path

ROOT = Path("/Users/wy/MiscProject/multi_factor")
PYTHON = "/opt/anaconda3/envs/quant_trade/bin/python"
SCRIPTS = ROOT / "scripts"
RUN_STATE = ROOT / "artifacts" / "run_state"
FIXED_TEST = ROOT / "artifacts" / "fixed_test"
CONTRACT = ROOT / "contracts" / "run_input_contract.research_trainval_20211231.json"
BASE_PANELS = RUN_STATE / "project_panels_research_trainval_20211231_20260429"
ROUND_ID = "rr_exploratory_neutralization_20260506"
V1_SCORES = RUN_STATE / "exploratory_neutralization_v1" / "model_scores_D0_neut.parquet"
P98_FT = FIXED_TEST / "confirmatory_reversal_p98_trainval_20260506"

CANDIDATES = [
    ("exploratory_pr_mom_ind_neut_v1", "pr_mom_ind_neut_v1", "Industry-neutralized momentum"),
    ("exploratory_pr_mom_size_ind_neut_v1", "pr_mom_size_ind_neut_v1", "Size+Industry-neutralized momentum"),
    ("exploratory_pr_mom_raw_v1", "pr_mom_raw_v1", "Raw momentum (no neutralization, baseline)"),
]


def run_cmd(args, desc=""):
    print(f"  [{desc}] {' '.join(args[:4])}...")
    subprocess.run(args, check=True)


def stage_panels(run_dir):
    run_dir = Path(run_dir); run_dir.mkdir(parents=True, exist_ok=True)
    for f in ["project_label_panel.parquet", "project_sample_panel.parquet",
              "project_execution_panel.parquet", "data_quality_audit.json"]:
        dst = run_dir / f
        if not dst.exists(): dst.symlink_to(BASE_PANELS / f)


def run_one(run_id, scheme_id, desc):
    print(f"\n{'='*60}\nFull-chain: {desc} ({scheme_id})\n{'='*60}")
    run_dir = RUN_STATE / run_id
    stage_panels(run_dir)

    # Filter scores
    filtered = run_dir / "model_scores_D0.parquet"
    if not filtered.exists():
        con = duckdb.connect()
        con.execute(f"COPY (SELECT * FROM read_parquet('{V1_SCORES}') WHERE candidate_scheme_id='{scheme_id}') TO '{filtered}' (FORMAT PARQUET)")
        con.close()

    # Build run state
    run_cmd([PYTHON, str(SCRIPTS / "build_run_state_skeleton.py"),
             "--run-id", run_id, "--run-type", "exploratory",
             "--candidate-scheme-id", scheme_id,
             "--research-round-id", ROUND_ID,
             "--scores-path", str(filtered), "--topk", "10"], desc="skeleton")

    aid = json.loads((run_dir / "run_state_latest_attempt.json").read_text())["attempt_id"]

    # Portfolio
    run_cmd([PYTHON, str(SCRIPTS / "build_portfolio_artifacts.py"),
             "--run-id", run_id, "--attempt-id", aid,
             "--run-input-contract", str(CONTRACT)], desc="portfolio")

    # Fixed test
    ft_dir = FIXED_TEST / run_id; ft_dir.mkdir(parents=True, exist_ok=True)
    run_cmd([PYTHON, str(SCRIPTS / "build_fixed_test_minimal.py"),
             "--run-id", run_id, "--attempt-id", aid,
             "--run-input-contract", str(CONTRACT)], desc="fixed_test")

    # Validation
    run_cmd([PYTHON, str(SCRIPTS / "build_confirmatory_validation_readout.py"),
             "--fixed-test-dir", str(ft_dir),
             "--validation-start", "20190101", "--validation-end", "20211231",
             "--output-path", str(ft_dir / "validation_readout.json")], desc="validation")

    return json.loads((ft_dir / "validation_readout.json").read_text()), ft_dir


def main():
    p98_val = json.loads((P98_FT / "validation_readout.json").read_text())
    p98_cost = json.loads((P98_FT / "cost_stress_summary.json").read_text())

    print("p98 BASELINE (2019-2021):")
    print(f"  ann_rel_ret={p98_val['annual_relative_return']:.6f}  max_dd={p98_val['max_drawdown']:.6f}  sharpe={p98_val['sharpe_ratio']:.2f}  turnover={p98_val['avg_turnover_daily']:.4f}  inv_wt={p98_val['avg_invested_weight']:.4f}")
    print(f"  cost_stress={p98_cost['annual_relative_return']:.6f}")

    results = {}
    for run_id, scheme_id, desc in CANDIDATES:
        try:
            val, ft_dir = run_one(run_id, scheme_id, desc)
            cost = json.loads((ft_dir / "cost_stress_summary.json").read_text())
            liq = json.loads((ft_dir / "low_liquidity_exposure_summary.json").read_text())
            results[run_id] = {"scheme_id": scheme_id, "desc": desc, "val": val, "cost": cost, "liq": liq}
            print(f"  RESULT: arr={val['annual_relative_return']:.6f} dd={val['max_drawdown']:.6f} sh={val['sharpe_ratio']:.2f} to={val['avg_turnover_daily']:.4f}")
        except Exception as e:
            print(f"  FAILED: {e}")

    print(f"\n{'='*90}")
    print("COMPARISON (2019-2021 validation)")
    print(f"{'='*90}")
    print(f"{'Scheme':<35} {'AnnRelRet':>10} {'MaxDD':>10} {'Sharpe':>8} {'Turnover':>10} {'InvWt':>8} {'CostStress':>10} {'LiqWt':>8}")
    print("-" * 99)

    def f(v, decimals=6):
        return f"{v:.{decimals}f}" if isinstance(v, float) else str(v)

    p98_l = json.loads((P98_FT / "low_liquidity_exposure_summary.json").read_text())
    print(f"{'p98 (baseline)':<35} {f(p98_val['annual_relative_return']):>10} {f(p98_val['max_drawdown']):>10} {f(p98_val['sharpe_ratio'],2):>8} {f(p98_val['avg_turnover_daily']):>10} {f(p98_val['avg_invested_weight']):>8} {f(p98_cost['annual_relative_return']):>10} {f(p98_l.get('low_liquidity_weight_share',0)):>8}")

    for rid, r in results.items():
        v, c, l = r["val"], r["cost"], r.get("liq", {})
        print(f"{r['scheme_id']:<35} {f(v['annual_relative_return']):>10} {f(v['max_drawdown']):>10} {f(v['sharpe_ratio'],2):>8} {f(v['avg_turnover_daily']):>10} {f(v['avg_invested_weight']):>8} {f(c['annual_relative_return']):>10} {f(l.get('low_liquidity_weight_share',0)):>8}")

    # Save
    out = FIXED_TEST / "neutralization_fullchain"
    out.mkdir(parents=True, exist_ok=True)
    json.dump({"as_of": datetime.now().isoformat(), "p98": {"val": p98_val, "cost": p98_cost}, "results": {rid: {"scheme_id": r["scheme_id"], "val": r["val"], "cost": r["cost"]} for rid, r in results.items()}}, open(out / "comparison.json", "w"), indent=2)
    print(f"\nSaved: {out / 'comparison.json'}")


if __name__ == "__main__":
    main()
