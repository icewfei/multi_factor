from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from conftest import load_json


SCRIPT_PATH = "scripts/diagnose_clean_baseline_redesign_v1_model_edge.py"
MANIFEST_PATH = "configs/clean_baselines/redesign_round_v1/clean_baseline_redesign_manifest.json"
OLD_CLEAN = [
    "no_p98_reversal_baseline_v1",
    "clean_momentum_20d_baseline_v1",
    "clean_liquidity_adjusted_reversal_baseline_v1",
    "clean_equal_weight_random_eligible_baseline_v1",
]


def write_parquet(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table(payload), path)


def write_audit(path: Path, baseline_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "candidate_scheme_id": baseline_id,
                "baseline_id": baseline_id,
                "p98_used": False,
                "label_diagnostics_used": False,
                "frozen_test_accessed": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def score_payload(candidate_scheme_id: str, *, good: bool = True) -> dict:
    rows = {
        "snapshot_id": ["snap"] * 8,
        "instrument": ["AAA.SZ", "BBB.SZ", "CCC.SZ", "DDD.SZ"] * 2,
        "signal_date": ["20210104"] * 4 + ["20210105"] * 4,
        "candidate_scheme_id": [candidate_scheme_id] * 8,
        "baseline_id": [candidate_scheme_id] * 8,
    }
    scores = [0.0, 0.3, 0.6, 0.9, 0.0, 0.4, 0.5, 0.9] if good else [0.9, 0.6, 0.3, 0.0, 0.9, 0.5, 0.4, 0.0]
    return rows | {"model_score_D0": scores}


def build_fixture(tmp_path: Path) -> dict[str, Path]:
    manifest = load_json(MANIFEST_PATH)
    redesign_root = tmp_path / "redesign"
    old_root = tmp_path / "old"
    label_panel = tmp_path / "label_panel.parquet"
    split_panel = tmp_path / "split_panel.parquet"
    p98_scores = tmp_path / "p98_scores.parquet"
    multi_scores = tmp_path / "multi_scores.parquet"
    rows = {
        "snapshot_id": ["snap"] * 8,
        "instrument": ["AAA.SZ", "BBB.SZ", "CCC.SZ", "DDD.SZ"] * 2,
        "signal_date": ["20210104"] * 4 + ["20210105"] * 4,
    }
    write_parquet(
        label_panel,
        rows
        | {
            "label_5d_next_open_close": [0.04, 0.02, -0.01, -0.03, 0.03, 0.01, -0.02, -0.04],
            "label_defined": [True] * 8,
        },
    )
    write_parquet(split_panel, rows | {"split_bucket": ["train"] * 4 + ["validation"] * 4, "train_flag": [True] * 4 + [False] * 4, "validation_flag": [False] * 4 + [True] * 4})
    for candidate in manifest["candidates"]:
        baseline_id = candidate["baseline_id"]
        run_dir = redesign_root / baseline_id
        write_parquet(run_dir / "model_scores_D0.parquet", score_payload(baseline_id, good=True))
        write_audit(run_dir / "model_scores_D0_audit.json", baseline_id)
    for baseline_id in OLD_CLEAN:
        run_dir = old_root / baseline_id
        write_parquet(run_dir / "model_scores_D0.parquet", score_payload(baseline_id, good=(baseline_id != "no_p98_reversal_baseline_v1")))
        write_audit(run_dir / "model_scores_D0_audit.json", baseline_id)
    write_parquet(p98_scores, score_payload("reversal_tail_exclude_p98_v1", good=False))
    multi_payload = score_payload("multi_equal_weight_v1", good=False)
    multi_payload.pop("snapshot_id")
    write_parquet(multi_scores, multi_payload)
    return {
        "redesign_root": redesign_root,
        "old_root": old_root,
        "label_panel": label_panel,
        "split_panel": split_panel,
        "p98_scores": p98_scores,
        "multi_scores": multi_scores,
        "output_json": tmp_path / "diagnosis.json",
        "output_md": tmp_path / "diagnosis.md",
    }


def test_redesign_model_edge_diagnosis_outputs_required_metrics(repo_root: Path, tmp_path: Path) -> None:
    fixture = build_fixture(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / SCRIPT_PATH),
            "--redesign-scores-root",
            str(fixture["redesign_root"]),
            "--old-family-root",
            str(fixture["old_root"]),
            "--label-panel",
            str(fixture["label_panel"]),
            "--split-panel",
            str(fixture["split_panel"]),
            "--p98-scores",
            str(fixture["p98_scores"]),
            "--multi-equal-scores",
            str(fixture["multi_scores"]),
            "--topk",
            "1",
            "--output-json",
            str(fixture["output_json"]),
            "--output-md",
            str(fixture["output_md"]),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(fixture["output_json"].read_text(encoding="utf-8"))
    assert payload["training_performed"] is False
    assert payload["portfolio_run_executed"] is False
    assert payload["formal_metrics_generated"] is False
    assert payload["frozen_test_accessed"] is False
    assert payload["p98_reference_status"] == "conditional_reference_only"
    first_candidate = "clean_reversal_5d_tradability_filtered_v1"
    validation = payload["diagnostics"][first_candidate]["validation"]
    assert {"rank_ic", "icir", "top_bottom_spread", "decile_forward_return", "coverage", "yearly_stability", "topk_head_proxy", "score_coverage_difference"} <= set(validation)
    assert first_candidate in payload["conclusion"]["candidate_results"]
