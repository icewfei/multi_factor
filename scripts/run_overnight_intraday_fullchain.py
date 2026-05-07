#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Run full-chain fixed test for overnight/intraday v2 candidates against p98 baseline.

Steps:
  1. Build model scores (already done — v2 scores)
  2. Build run state skeleton (ranking_state, execution_state)
  3. Build portfolio artifacts (holdings, weights, turnover)
  4. Build fixed test artifacts (metrics, backtest, etc.)
  5. Build validation readout
  6. Compare against p98 baseline

Candidates selected from v2 diagnostic:
  - overnight_intraday_mom_ew_v2  (IC 0.0418, corr 0.85 with p98)
  - intraday_mom_5d_v1            (IC 0.0366, pure intraday, no tail handling)
"""

from __future__ import annotations

import hashlib
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

RESEARCH_ROUND_ID = "rr_exploratory_overnight_intraday_decomposition_20260506"

CANDIDATES = [
    {
        "run_id": "exploratory_overnight_intraday_mom_ew_v2",
        "scheme_id": "overnight_intraday_mom_ew_v2",
        "score_file": "model_scores_D0_v2.parquet",
        "description": "Overnight+Intraday momentum equal-weight, no tail handling",
    },
    {
        "run_id": "exploratory_intraday_mom_5d_v1",
        "scheme_id": "intraday_mom_5d_v1",
        "score_file": "model_scores_D0_v2.parquet",
        "description": "Pure intraday momentum 5d, no tail handling",
    },
    {
        "run_id": "exploratory_p98_overnight_supplement_v2",
        "scheme_id": "p98_overnight_supplement_v2",
        "score_file": "model_scores_D0_v2.parquet",
        "description": "p98 + 10% overnight momentum (closest to p98 IC)",
    },
]

P98_FIXED_TEST = FIXED_TEST / "confirmatory_reversal_p98_trainval_20260506"
VALIDATION_START = "20190101"
VALIDATION_END = "20211231"

CODE_HASH_FILES = [
    SCRIPTS / "build_run_state_skeleton.py",
    SCRIPTS / "build_portfolio_artifacts.py",
    SCRIPTS / "build_fixed_test_minimal.py",
    SCRIPTS / "build_confirmatory_validation_readout.py",
    SCRIPTS / "build_overnight_intraday_v2_scores.py",
]


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def write_json(p, payload):
    Path(p).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def compute_code_hash():
    h = hashlib.sha256()
    for f in CODE_HASH_FILES:
        h.update(f.name.encode())
        h.update(f.read_bytes())
    return h.hexdigest()


def run_cmd(args, desc=""):
    print(f"  [{desc}] Running: {' '.join(args)}")
    subprocess.run(args, check=True)


def stage_panels(run_dir):
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    for fname in [
        "project_label_panel.parquet",
        "project_sample_panel.parquet",
        "project_execution_panel.parquet",
        "data_quality_audit.json",
    ]:
        src = BASE_PANELS / fname
        dst = run_dir / fname
        if not dst.exists():
            dst.symlink_to(src)


def run_full_chain(run_id, scheme_id, score_file, desc):
    print(f"\n{'='*60}")
    print(f"Full-chain: {desc}")
    print(f"  run_id={run_id}, scheme_id={scheme_id}")
    print(f"{'='*60}")

    run_dir = RUN_STATE / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    stage_panels(run_dir)

    # Step 1: Pre-filter score file to single candidate_scheme_id
    source_score_path = RUN_STATE / "exploratory_overnight_intraday_decomposition_v1" / score_file
    if not source_score_path.exists():
        raise FileNotFoundError(f"Score file missing: {source_score_path}")

    filtered_score_path = run_dir / "model_scores_D0.parquet"
    if not filtered_score_path.exists():
        import duckdb
        con = duckdb.connect()
        try:
            con.execute(f"""
                COPY (
                    SELECT * FROM read_parquet('{source_score_path}')
                    WHERE candidate_scheme_id = '{scheme_id}'
                ) TO '{filtered_score_path}' (FORMAT PARQUET)
            """)
        finally:
            con.close()
    print(f"  Filtered scores: {filtered_score_path}")

    # Step 2: Build run state skeleton
    run_cmd(
        [
            PYTHON,
            str(SCRIPTS / "build_run_state_skeleton.py"),
            "--run-id", run_id,
            "--run-type", "exploratory",
            "--candidate-scheme-id", scheme_id,
            "--research-round-id", RESEARCH_ROUND_ID,
            "--scores-path", str(filtered_score_path),
            "--topk", "10",
        ],
        desc="build_run_state_skeleton",
    )

    attempt_id = load_json(run_dir / "run_state_latest_attempt.json")["attempt_id"]
    print(f"  attempt_id={attempt_id}")

    # Step 3: Build portfolio artifacts
    run_cmd(
        [
            PYTHON,
            str(SCRIPTS / "build_portfolio_artifacts.py"),
            "--run-id", run_id,
            "--attempt-id", attempt_id,
            "--run-input-contract", str(CONTRACT),
        ],
        desc="build_portfolio_artifacts",
    )

    # Step 4: Build fixed test
    fixed_test_dir = FIXED_TEST / run_id
    fixed_test_dir.mkdir(parents=True, exist_ok=True)
    run_cmd(
        [
            PYTHON,
            str(SCRIPTS / "build_fixed_test_minimal.py"),
            "--run-id", run_id,
            "--attempt-id", attempt_id,
            "--run-input-contract", str(CONTRACT),
        ],
        desc="build_fixed_test_minimal",
    )

    # Step 5: Validation readout
    run_cmd(
        [
            PYTHON,
            str(SCRIPTS / "build_confirmatory_validation_readout.py"),
            "--fixed-test-dir", str(fixed_test_dir),
            "--validation-start", VALIDATION_START,
            "--validation-end", VALIDATION_END,
            "--output-path", str(fixed_test_dir / "validation_readout.json"),
        ],
        desc="build_confirmatory_validation_readout",
    )

    validation = load_json(fixed_test_dir / "validation_readout.json")
    print(f"  Validation (2019-2021):")
    print(f"    annual_relative_return = {validation.get('annual_relative_return', 'N/A'):.6f}" if isinstance(validation.get('annual_relative_return'), float) else f"    annual_relative_return = {validation.get('annual_relative_return', 'N/A')}")
    print(f"    max_drawdown = {validation.get('max_drawdown', 'N/A')}")
    print(f"    sharpe_ratio = {validation.get('sharpe_ratio', 'N/A')}")
    print(f"    avg_turnover_daily = {validation.get('avg_turnover_daily', 'N/A')}")
    print(f"    avg_invested_weight = {validation.get('avg_invested_weight', 'N/A')}")

    return validation


def main():
    code_hash = compute_code_hash()
    print(f"Code hash: {code_hash[:16]}...")
    print(f"Contract: {CONTRACT}")

    # Load p98 baseline
    p98_val = load_json(P98_FIXED_TEST / "validation_readout.json")
    p98_cost = load_json(P98_FIXED_TEST / "cost_stress_summary.json")
    print(f"\n{'='*60}")
    print("p98 BASELINE (2019-2021 validation):")
    print(f"  annual_relative_return = {p98_val['annual_relative_return']:.6f}")
    print(f"  max_drawdown          = {p98_val['max_drawdown']:.6f}")
    print(f"  sharpe_ratio          = {p98_val['sharpe_ratio']:.6f}")
    print(f"  relative_ir           = {p98_val['relative_ir']:.6f}")
    print(f"  avg_turnover_daily    = {p98_val['avg_turnover_daily']:.6f}")
    print(f"  avg_invested_weight   = {p98_val['avg_invested_weight']:.6f}")
    print(f"  cost_stress_ann_rel   = {p98_cost['annual_relative_return']:.6f}")

    results = {}
    for c in CANDIDATES:
        try:
            val = run_full_chain(c["run_id"], c["scheme_id"], c["score_file"], c["description"])
            cost = load_json(FIXED_TEST / c["run_id"] / "cost_stress_summary.json")
            results[c["run_id"]] = {
                "scheme_id": c["scheme_id"],
                "description": c["description"],
                "validation": val,
                "cost_stress": cost,
            }
        except Exception as e:
            print(f"  FAILED: {e}")
            results[c["run_id"]] = {"error": str(e)}

    # Comparison summary
    print(f"\n{'='*80}")
    print("COMPARISON SUMMARY (2019-2021 validation window)")
    print(f"{'='*80}")
    print(f"{'Scheme':<42} {'AnnRelRet':>10} {'MaxDD':>10} {'Sharpe':>8} {'Turnover':>10} {'InvWt':>8} {'CostStress':>10}")
    print("-" * 108)

    def fmt(v):
        return f"{v:.6f}" if isinstance(v, float) else str(v)

    print(f"{'p98 (baseline)':<42} {fmt(p98_val['annual_relative_return']):>10} "
          f"{fmt(p98_val['max_drawdown']):>10} {fmt(p98_val['sharpe_ratio']):>8} "
          f"{fmt(p98_val['avg_turnover_daily']):>10} {fmt(p98_val['avg_invested_weight']):>8} "
          f"{fmt(p98_cost['annual_relative_return']):>10}")

    for run_id, r in results.items():
        if "error" in r:
            print(f"{run_id:<42} {'ERROR: ' + r['error']}")
            continue
        sid = r.get("scheme_id", run_id)
        v = r.get("validation")
        c = r.get("cost_stress")
        if v is None or c is None:
            print(f"{sid:<42} {'MISSING DATA'}")
            continue
        print(f"{sid:<42} {fmt(v.get('annual_relative_return', 0)):>10} "
              f"{fmt(v.get('max_drawdown', 0)):>10} {fmt(v.get('sharpe_ratio', 0)):>8} "
              f"{fmt(v.get('avg_turnover_daily', 0)):>10} {fmt(v.get('avg_invested_weight', 0)):>8} "
              f"{fmt(c.get('annual_relative_return', 0)):>10}")

    # Save report
    report = {
        "generated_at": now_iso(),
        "code_hash": code_hash,
        "p98_baseline": {
            "validation": p98_val,
            "cost_stress": p98_cost,
        },
        "candidates": {},
    }
    for run_id, r in results.items():
        sid = r.get("scheme_id", run_id)
        report["candidates"][run_id] = {
            "scheme_id": sid,
            "description": r.get("description", ""),
        }
        if "validation" in r:
            report["candidates"][run_id].update({
                k: r["validation"][k]
                for k in [
                    "annual_relative_return", "max_drawdown", "sharpe_ratio",
                    "relative_ir", "avg_turnover_daily", "avg_invested_weight",
                    "total_return",
                ]
                if k in r["validation"]
            })
            report["candidates"][run_id]["cost_stress_annual_relative_return"] = (
                r["cost_stress"]["annual_relative_return"]
            )

    out_dir = FIXED_TEST / "overnight_intraday_fullchain"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / f"fullchain_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", report)
    print(f"\nReport saved to {out_dir}")


if __name__ == "__main__":
    main()
