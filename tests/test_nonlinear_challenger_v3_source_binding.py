from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb

from conftest import load_json, schema_required


FEATURE_SET_PATH = (
    "configs/nonlinear_challenger_v3/feature_sets/"
    "feature_set_nlc_v3_fset01_confirmed5_locked_inputs.json"
)
MODEL_CONFIG_PATH = (
    "configs/nonlinear_challenger_v3/model_configs/"
    "model_config_nlc_v3_lgbm_depth3_seed42_locked_hparams_topk_head_quality_conditioned_capital_deployment.json"
)
CANDIDATE_PATH = (
    "configs/nonlinear_challenger_v3/candidates/"
    "candidate_nlc_v3_confirmed5_locked_topk_head_quality_conditioned_capital_deployment_lgbm_depth3_seed42.json"
)
SOURCE_BINDING_PATH = "configs/nonlinear_challenger_v3/source_bindings/v3_score_source_binding.json"
SCHEMA_PATH = "schemas/nonlinear_challenger_v3_conditioning_source.schema.json"
SCRIPT_PATH = "scripts/build_nonlinear_challenger_v3_scores.py"
EXPECTED_CANDIDATE_SCHEME_ID = (
    "nlc_v3_confirmed5_locked_topk_head_quality_conditioned_capital_deployment_lgbm_depth3_seed42"
)
EXPECTED_BASE_INPUT_CANDIDATE_SCHEME_ID = "nlc_v1_confirmed5_lgbm_depth3_seed42"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def write_temp_manifests(tmp_path: Path) -> tuple[Path, Path, Path]:
    feature_set_path = tmp_path / "feature_set.json"
    model_config_path = tmp_path / "model_config.json"
    candidate_path = tmp_path / "candidate.json"
    write_json(feature_set_path, load_json(FEATURE_SET_PATH))
    write_json(model_config_path, load_json(MODEL_CONFIG_PATH))
    write_json(candidate_path, load_json(CANDIDATE_PATH))
    return feature_set_path, model_config_path, candidate_path


def build_base_scores_fixture(tmp_path: Path, *, input_candidate_scheme_id: str) -> Path:
    scores_path = tmp_path / "base_scores.parquet"
    con = duckdb.connect()
    try:
        con.execute(
            f"""
            COPY (
                SELECT * FROM (
                    VALUES
                        ('warehouse_20260429_trainval_20211231', 'AAA.SZ', '20200124', '{input_candidate_scheme_id}', 0.20),
                        ('warehouse_20260429_trainval_20211231', 'BBB.SZ', '20200124', '{input_candidate_scheme_id}', 0.50),
                        ('warehouse_20260429_trainval_20211231', 'CCC.SZ', '20200124', '{input_candidate_scheme_id}', 0.90)
                ) AS t(snapshot_id, instrument, signal_date, candidate_scheme_id, model_score_D0)
            ) TO '{scores_path.as_posix()}' (FORMAT PARQUET)
            """
        )
    finally:
        con.close()
    return scores_path


def build_conditioning_source_fixture(tmp_path: Path) -> Path:
    payload = {
        "schema_version": "nlc_v3_conditioning_source_schema_v1",
        "snapshot_id": "warehouse_20260429_trainval_20211231",
        "candidate_scheme_id": EXPECTED_CANDIDATE_SCHEME_ID,
        "base_score_source": "confirmed5_raw_score_D0",
        "conditioning_policy_version": "nlc_v3_hqcd_v1",
        "head_quality_conditioning_source": "train_window_frozen_calibration",
        "calibration_scope": "train_only",
        "topk": 2,
        "leakage_audit_flags": {
            "train_only_or_expanding_past_only": True,
            "no_validation_lookup": True,
            "no_frozen_test_lookup": True,
            "no_future_signal_date_lookup": True,
            "no_portfolio_feedback_lookup": True,
            "state_inputs_d0_visible": True
        },
        "forbidden_input_tags": [],
        "calibration_rows": [
            {
                "topk_rank_bucket": "top_1",
                "head_quality_cell_id": "top_1",
                "head_quality_cell_percentile_rank": 1.0
            },
            {
                "topk_rank_bucket": "top_2",
                "head_quality_cell_id": "top_2",
                "head_quality_cell_percentile_rank": 0.2
            },
            {
                "topk_rank_bucket": "global_topk_train_reference",
                "head_quality_cell_id": "global_topk_train_reference",
                "head_quality_cell_percentile_rank": 0.4
            }
        ],
        "provenance": {
            "source_binding_id": "nlc_v3_score_source_binding_v1",
            "source_score_candidate_scheme_id": EXPECTED_BASE_INPUT_CANDIDATE_SCHEME_ID,
            "source_score_artifact_path": str(tmp_path / "base_scores.parquet"),
            "source_label_panel_path": "fixture://project_label_panel.parquet",
            "source_split_panel_path": "fixture://dataset_split_daily.parquet",
            "generated_by": "tests.test_nonlinear_challenger_v3_source_binding",
            "generated_at": "2026-05-12T00:00:00+00:00",
            "temporal_scope": "train_only",
            "validation_used": False,
            "frozen_test_used": False,
            "portfolio_feedback_used": False,
            "storage_policy": "repo_governed_artifact"
        }
    }
    conditioning_path = tmp_path / "conditioning_source.json"
    write_json(conditioning_path, payload)
    return conditioning_path


def run_builder(
    repo_root: Path,
    feature_set_path: Path,
    model_config_path: Path,
    candidate_path: Path,
    base_scores_path: Path,
    conditioning_source_path: Path,
    source_binding_path: Path,
    output_dir: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(repo_root / SCRIPT_PATH),
            "--feature-set",
            str(feature_set_path),
            "--model-config",
            str(model_config_path),
            "--candidate",
            str(candidate_path),
            "--base-scores",
            str(base_scores_path),
            "--conditioning-source",
            str(conditioning_source_path),
            "--source-binding",
            str(source_binding_path),
            "--run-id",
            "nlc_v3_source_binding_fixture",
            "--attempt-id",
            "attempt_fixture",
            "--output-dir",
            str(output_dir),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_source_binding_contract_explicitly_distinguishes_confirmed5_from_reversal_tail() -> None:
    binding = load_json(SOURCE_BINDING_PATH)

    assert binding["source_binding_id"] == "nlc_v3_score_source_binding_v1"
    assert binding["base_score_binding"]["base_score_source"] == "confirmed5_raw_score_D0"
    assert binding["base_score_binding"]["bound_input_candidate_scheme_ids"] == [
        "nlc_v1_confirmed5_lgbm_depth3_seed42"
    ]
    assert "reversal_tail_exclude_p98_v1" in binding["base_score_binding"]["prohibited_candidate_scheme_ids"]
    assert "/private/tmp/" in binding["base_score_binding"]["long_term_formal_source_must_not_use_path_prefixes"]
    assert "/private/tmp/" in binding["conditioning_source_binding"]["long_term_formal_source_must_not_use_path_prefixes"]


def test_conditioning_source_schema_requires_provenance_fields() -> None:
    required = set(schema_required(SCHEMA_PATH))
    provenance_required = set(load_json(SCHEMA_PATH)["properties"]["provenance"]["required"])

    assert "provenance" in required
    assert "schema_version" in required
    assert {
        "source_binding_id",
        "source_score_candidate_scheme_id",
        "source_score_artifact_path",
        "source_label_panel_path",
        "source_split_panel_path",
        "generated_by",
        "generated_at",
        "temporal_scope",
        "validation_used",
        "frozen_test_used",
        "portfolio_feedback_used",
        "storage_policy",
    } <= provenance_required


def test_builder_fails_fast_when_reversal_tail_is_passed_as_confirmed5_input(repo_root: Path, tmp_path: Path) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(tmp_path)
    result = run_builder(
        repo_root,
        feature_set_path,
        model_config_path,
        candidate_path,
        build_base_scores_fixture(tmp_path, input_candidate_scheme_id="reversal_tail_exclude_p98_v1"),
        build_conditioning_source_fixture(tmp_path),
        repo_root / SOURCE_BINDING_PATH,
        tmp_path / "out",
    )

    assert result.returncode != 0
    assert "prohibited for v3 confirmed5 binding" in result.stderr
    assert "reversal_tail_exclude_p98_v1" in result.stderr


def test_builder_fails_fast_when_conditioning_source_provenance_is_missing(repo_root: Path, tmp_path: Path) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(tmp_path)
    base_scores_path = build_base_scores_fixture(
        tmp_path,
        input_candidate_scheme_id=EXPECTED_BASE_INPUT_CANDIDATE_SCHEME_ID,
    )
    conditioning_source_path = build_conditioning_source_fixture(tmp_path)
    payload = json.loads(conditioning_source_path.read_text(encoding="utf-8"))
    del payload["provenance"]
    write_json(conditioning_source_path, payload)

    result = run_builder(
        repo_root,
        feature_set_path,
        model_config_path,
        candidate_path,
        base_scores_path,
        conditioning_source_path,
        repo_root / SOURCE_BINDING_PATH,
        tmp_path / "out",
    )

    assert result.returncode != 0
    assert "conditioning_source schema validation failed" in result.stderr
    assert "provenance" in result.stderr


def test_builder_fails_fast_when_source_binding_candidate_contract_is_mutated(repo_root: Path, tmp_path: Path) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(tmp_path)
    base_scores_path = build_base_scores_fixture(
        tmp_path,
        input_candidate_scheme_id=EXPECTED_BASE_INPUT_CANDIDATE_SCHEME_ID,
    )
    conditioning_source_path = build_conditioning_source_fixture(tmp_path)
    source_binding = load_json(SOURCE_BINDING_PATH)
    source_binding["base_score_binding"]["bound_input_candidate_scheme_ids"] = ["wrong_candidate_scheme_id"]
    source_binding_path = tmp_path / "source_binding.json"
    write_json(source_binding_path, source_binding)

    result = run_builder(
        repo_root,
        feature_set_path,
        model_config_path,
        candidate_path,
        base_scores_path,
        conditioning_source_path,
        source_binding_path,
        tmp_path / "out",
    )

    assert result.returncode != 0
    assert "bound_input_candidate_scheme_ids mismatch" in result.stderr
