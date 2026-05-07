#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Build a standalone Alpha158 exact single-signal model_scores_D0.parquet under an
explicit run-input contract.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

from alpha158_canonical_common import FEATURE_META, build_feature_views, load_manifest
from single_signal_batch_common import CandidateSpec, materialize_ranked_single_signal


ROOT = Path("/Users/wy/MiscProject/multi_factor")
CONTRACTS_DIR = ROOT / "contracts"
RUN_STATE_DIR = ROOT / "artifacts" / "run_state"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build standalone Alpha158 exact single-signal scores.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--feature-name", required=True, help="Exact Alpha158 feature name, e.g. CORD30")
    parser.add_argument("--candidate-scheme-id", required=True)
    parser.add_argument("--input-dir", default=None)
    parser.add_argument(
        "--run-input-contract",
        default=None,
        help="Optional explicit run input contract JSON path. Defaults to contracts/run_input_contract.current.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dir = Path(args.input_dir) if args.input_dir else (RUN_STATE_DIR / args.run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    sample_panel = run_dir / "project_sample_panel.parquet"
    if not sample_panel.exists():
        raise FileNotFoundError(f"Required input file not found: {sample_panel}")

    run_input_contract_path = Path(args.run_input_contract) if args.run_input_contract else (
        CONTRACTS_DIR / "run_input_contract.current.json"
    )
    run_input = load_json(run_input_contract_path)
    snapshot_id = run_input["snapshot_id"]
    source_db_path = Path(run_input["source_root"]["snapshot_path"]) / "duckdb" / "warehouse.duckdb"
    if not source_db_path.exists():
        raise FileNotFoundError(f"Shared warehouse DB not found: {source_db_path}")

    manifest = load_manifest()
    feature_lookup = {
        row["qlib_feature_name"]: row
        for row in manifest["feature_catalog"]
    }
    feature_name = args.feature_name.upper()
    if feature_name not in feature_lookup:
        raise ValueError(f"Unknown Alpha158 feature name: {feature_name}")
    if feature_name not in FEATURE_META:
        raise ValueError(f"Missing feature metadata for Alpha158 feature: {feature_name}")
    feature_row = feature_lookup[feature_name]
    feature_meta = FEATURE_META[feature_name]
    spec = CandidateSpec(
        candidate_scheme_id=args.candidate_scheme_id,
        field_name=feature_row["canonical_project_field"],
        ranking_direction=feature_meta["ranking_direction"],
        interpretation=feature_meta.get("interpretation", feature_name),
    )

    con = duckdb.connect()
    try:
        build_feature_views(
            con,
            sample_panel,
            source_db_path,
            snapshot_id,
            [{**feature_row, **feature_meta}],
        )
        materialize_ranked_single_signal(
            con=con,
            spec=spec,
            run_dir=run_dir,
            score_builder_name="build_alpha158_standalone_model_scores.py",
        )
    finally:
        con.close()


if __name__ == "__main__":
    main()
