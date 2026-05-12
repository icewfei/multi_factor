from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb
import pandas as pd

from conftest import load_module, read_text


SCRIPT_PATH = "scripts/diagnose_nonlinear_challenger_v3_model_edge.py"


def write_parquet(path: Path, frame: pd.DataFrame) -> None:
    con = duckdb.connect()
    try:
        con.register("frame_view", frame)
        con.execute(f"COPY frame_view TO '{path.as_posix()}' (FORMAT PARQUET)")
    finally:
        con.close()


def build_fixture_files(tmp_path: Path) -> dict[str, Path]:
    instruments = [f"I{i:02d}" for i in range(20)]
    score_levels = [1.0 - i * 0.05 for i in range(20)]
    date_specs = [
        ("20200102", "train", list(range(20)), [0, 1, 4, 5, 2, 3] + list(range(6, 20)), [0, 1, 3, 2] + list(range(4, 20))),
        ("20200103", "train", [0, 1, 3, 2] + list(range(4, 20)), [0, 2, 4, 5, 1, 3] + list(range(6, 20)), list(range(20))),
        ("20210104", "validation", [1, 0, 2, 3] + list(range(4, 20)), [4, 5, 0, 1, 2, 3] + list(range(6, 20)), list(range(20))),
        ("20210105", "validation", [0, 2, 1, 3] + list(range(4, 20)), [2, 4, 0, 1, 3, 5] + list(range(6, 20)), [1, 0, 2, 3] + list(range(4, 20))),
    ]

    label_rows: list[dict[str, object]] = []
    split_rows: list[dict[str, object]] = []
    confirmed5_rows: list[dict[str, object]] = []
    v3_rows: list[dict[str, object]] = []
    v2_rows: list[dict[str, object]] = []
    baseline_rows: list[dict[str, object]] = []

    snapshot_id = "snap"
    confirmed5_path = tmp_path / "confirmed5_scores.parquet"
    v3_scores_path = tmp_path / "v3_scores.parquet"
    v2_scores_path = tmp_path / "v2_scores.parquet"
    baseline_scores_path = tmp_path / "baseline_scores.parquet"
    label_panel_path = tmp_path / "label_panel.parquet"
    split_panel_path = tmp_path / "split_panel.parquet"
    v3_audit_path = tmp_path / "v3_audit.json"
    v2_audit_path = tmp_path / "v2_audit.json"
    source_binding_path = tmp_path / "source_binding.json"
    output_json = tmp_path / "diagnosis.json"
    output_md = tmp_path / "diagnosis.md"

    for signal_date, split_bucket, confirmed5_order, v2_order, baseline_order in date_specs:
        label_map = {instruments[idx]: 0.20 - rank * 0.01 for rank, idx in enumerate(range(20))}
        confirmed5_score_map = {instruments[idx]: score_levels[rank] for rank, idx in enumerate(confirmed5_order)}
        v2_score_map = {instruments[idx]: score_levels[rank] for rank, idx in enumerate(v2_order)}
        baseline_score_map = {instruments[idx]: score_levels[rank] for rank, idx in enumerate(baseline_order)}
        confirmed5_rank_map = {instruments[idx]: rank for rank, idx in enumerate(confirmed5_order)}

        for instrument in instruments:
            label_rows.append(
                {
                    "snapshot_id": snapshot_id,
                    "instrument": instrument,
                    "signal_date": signal_date,
                    "label_5d_next_open_close": label_map[instrument],
                    "label_defined": True,
                }
            )
            split_rows.append(
                {
                    "snapshot_id": snapshot_id,
                    "instrument": instrument,
                    "signal_date": signal_date,
                    "split_bucket": split_bucket,
                    "train_flag": split_bucket == "train",
                    "validation_flag": split_bucket == "validation",
                }
            )
            confirmed5_rows.append(
                {
                    "snapshot_id": snapshot_id,
                    "instrument": instrument,
                    "signal_date": signal_date,
                    "candidate_scheme_id": "nlc_v1_confirmed5_lgbm_depth3_seed42",
                    "model_score_D0": confirmed5_score_map[instrument],
                }
            )
            v3_rows.append(
                {
                    "snapshot_id": snapshot_id,
                    "instrument": instrument,
                    "signal_date": signal_date,
                    "candidate_scheme_id": "nlc_v3_confirmed5_locked_topk_head_quality_conditioned_capital_deployment_lgbm_depth3_seed42",
                    "raw_score_D0": confirmed5_score_map[instrument],
                    "adjusted_score_D0": confirmed5_score_map[instrument],
                    "model_score_D0": confirmed5_score_map[instrument],
                    "provisional_topk_member": confirmed5_rank_map[instrument] < 10,
                }
            )
            v2_rows.append(
                {
                    "snapshot_id": snapshot_id,
                    "instrument": instrument,
                    "signal_date": signal_date,
                    "candidate_scheme_id": "nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42",
                    "adjusted_score_D0": v2_score_map[instrument],
                }
            )
            baseline_rows.append(
                {
                    "instrument": instrument,
                    "signal_date": signal_date,
                    "candidate_scheme_id": "multi_equal_weight_v1",
                    "model_score_D0": baseline_score_map[instrument],
                }
            )

    write_parquet(confirmed5_path, pd.DataFrame(confirmed5_rows))
    write_parquet(v3_scores_path, pd.DataFrame(v3_rows))
    write_parquet(v2_scores_path, pd.DataFrame(v2_rows))
    write_parquet(baseline_scores_path, pd.DataFrame(baseline_rows))
    write_parquet(label_panel_path, pd.DataFrame(label_rows))
    write_parquet(split_panel_path, pd.DataFrame(split_rows))

    v3_audit_path.write_text(
        json.dumps(
            {
                "candidate_scheme_id": "nlc_v3_confirmed5_locked_topk_head_quality_conditioned_capital_deployment_lgbm_depth3_seed42",
                "base_score_source": "confirmed5_raw_score_D0",
                "base_score_input_path": str(confirmed5_path),
                "conditioning_source_path": "/private/tmp/fixture_conditioning_source.json",
                "conditioning_policy_version": "nlc_v3_hqcd_v1",
                "head_quality_conditioning_source": "train_window_frozen_calibration",
                "row_count": 80,
                "provisional_topk_rows": 40,
                "topk": 10,
                "training_performed": False,
                "frozen_test_accessed": False,
                "portfolio_outputs_generated": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    v2_audit_path.write_text(
        json.dumps(
            {
                "candidate_scheme_id": "nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42",
                "row_count": 80,
                "raw_input_null_score_rows": 0,
                "score_transform_policy_version": "cs_volatility_discount_v1",
                "training_performed": False,
                "frozen_test_accessed": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    source_binding_path.write_text(
        json.dumps(
            {
                "source_binding_id": "nlc_v3_score_source_binding_v1",
                "conditioning_source_binding": {
                    "canonical_source_requirement": "conditioning source must be formalized before long-term use",
                    "long_term_formal_source_must_not_use_path_prefixes": ["/private/tmp/"],
                },
                "notes": [
                    "This binding contract only governs score-layer inputs for nonlinear challenger v3.",
                    "It does not authorize portfolio, holdings, metrics, readout, or frozen-test usage.",
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "v3_scores": v3_scores_path,
        "v3_audit": v3_audit_path,
        "v2_scores": v2_scores_path,
        "v2_audit": v2_audit_path,
        "baseline_scores": baseline_scores_path,
        "label_panel": label_panel_path,
        "split_panel": split_panel_path,
        "source_binding": source_binding_path,
        "output_json": output_json,
        "output_md": output_md,
    }


def run_script(repo_root: Path, files: dict[str, Path]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(repo_root / SCRIPT_PATH),
            "--v3-scores",
            str(files["v3_scores"]),
            "--v3-audit",
            str(files["v3_audit"]),
            "--v2-scores",
            str(files["v2_scores"]),
            "--v2-audit",
            str(files["v2_audit"]),
            "--baseline-scores",
            str(files["baseline_scores"]),
            "--label-panel",
            str(files["label_panel"]),
            "--split-panel",
            str(files["split_panel"]),
            "--source-binding",
            str(files["source_binding"]),
            "--output-json",
            str(files["output_json"]),
            "--output-md",
            str(files["output_md"]),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_v3_model_edge_diagnosis_outputs_expected_shape(repo_root: Path, tmp_path: Path) -> None:
    files = build_fixture_files(tmp_path)
    result = run_script(repo_root, files)
    assert result.returncode == 0, result.stderr

    payload = json.loads(files["output_json"].read_text(encoding="utf-8"))
    assert payload["frozen_test_accessed"] is False
    assert payload["formal_metrics_generated"] is False
    assert payload["portfolio_run_executed"] is False
    assert "v3_train" in payload["diagnostics"]
    assert "confirmed5_validation" in payload["diagnostics"]
    assert "v2_validation" in payload["diagnostics"]
    assert "baseline_train" in payload["diagnostics"]
    assert payload["diagnostics"]["v3_train"]["provisional_topk_rows"] == 20
    assert payload["diagnostics"]["v3_validation"]["provisional_topk_rows"] == 20
    assert payload["coverage_summary"]["train"]["score_coverage_difference"]["v3_minus_confirmed5"] == 0.0


def test_v3_model_edge_diagnosis_discloses_temporary_source_and_conditional_recommendation(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    files = build_fixture_files(tmp_path)
    result = run_script(repo_root, files)
    assert result.returncode == 0, result.stderr

    payload = json.loads(files["output_json"].read_text(encoding="utf-8"))
    assert payload["source_binding_disclosure"]["temporary_conditioning_source"] is True
    assert payload["conclusion"]["temporary_conditioning_source"] is True
    assert payload["conclusion"]["materially_worse_overall"] is False
    assert payload["conclusion"]["topk_head_quality_improved_vs_confirmed5"] is False
    assert payload["conclusion"]["topk_head_quality_improved_vs_v2"] is True
    assert payload["conclusion"]["recommendation"] == "conditional_portfolio_dry_run_only_after_formal_source_resolution"


def test_v3_model_edge_diagnosis_markdown_contains_scope_and_disclosures(repo_root: Path, tmp_path: Path) -> None:
    files = build_fixture_files(tmp_path)
    result = run_script(repo_root, files)
    assert result.returncode == 0, result.stderr

    md_text = files["output_md"].read_text(encoding="utf-8")
    assert "NOT A BACKTEST" in md_text
    assert "temporary gate artifact" in md_text
    assert "## 3. Train Diagnostics" in md_text
    assert "## 4. Validation Diagnostics" in md_text
    assert "## 5. Cross-Model Comparison" in md_text


def test_script_text_excludes_portfolio_artifact_generation_commands() -> None:
    script_text = read_text(SCRIPT_PATH).lower()
    assert "holdings.csv" not in script_text
    assert "portfolio_weights" not in script_text
    assert "build_portfolio_artifacts" not in script_text
    assert "artifacts/fixed_test/" not in script_text


def test_module_threshold_constants_are_exposed() -> None:
    module = load_module(SCRIPT_PATH, "diagnose_nonlinear_challenger_v3_model_edge_module")
    assert module.VALIDATION_RANKIC_DAMAGE_THRESHOLD == -0.005
    assert module.VALIDATION_ICIR_DAMAGE_THRESHOLD == -0.05
