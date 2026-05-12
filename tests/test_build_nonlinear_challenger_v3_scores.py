from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb
import pandas as pd

from conftest import load_json, load_module, read_text


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
SCRIPT_PATH = "scripts/build_nonlinear_challenger_v3_scores.py"
EXPECTED_CANDIDATE_SCHEME_ID = (
    "nlc_v3_confirmed5_locked_topk_head_quality_conditioned_capital_deployment_lgbm_depth3_seed42"
)
EXPECTED_BASE_INPUT_CANDIDATE_SCHEME_ID = "nlc_v1_confirmed5_lgbm_depth3_seed42"
EXPECTED_CONDITIONING_POLICY_VERSION = "nlc_v3_hqcd_v1"


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


def build_base_scores_fixture(tmp_path: Path) -> Path:
    scores_path = tmp_path / "confirmed5_model_scores.parquet"
    con = duckdb.connect()
    try:
        con.execute(
            f"""
            COPY (
                SELECT * FROM (
                    VALUES
                        ('warehouse_20260429_trainval_20211231', 'AAA.SZ', '20200124', '{EXPECTED_BASE_INPUT_CANDIDATE_SCHEME_ID}', 0.20),
                        ('warehouse_20260429_trainval_20211231', 'BBB.SZ', '20200124', '{EXPECTED_BASE_INPUT_CANDIDATE_SCHEME_ID}', 0.50),
                        ('warehouse_20260429_trainval_20211231', 'CCC.SZ', '20200124', '{EXPECTED_BASE_INPUT_CANDIDATE_SCHEME_ID}', 0.90),
                        ('warehouse_20260429_trainval_20211231', 'AAA.SZ', '20200125', '{EXPECTED_BASE_INPUT_CANDIDATE_SCHEME_ID}', 0.10),
                        ('warehouse_20260429_trainval_20211231', 'BBB.SZ', '20200125', '{EXPECTED_BASE_INPUT_CANDIDATE_SCHEME_ID}', 0.60),
                        ('warehouse_20260429_trainval_20211231', 'CCC.SZ', '20200125', '{EXPECTED_BASE_INPUT_CANDIDATE_SCHEME_ID}', 0.80)
                ) AS t(snapshot_id, instrument, signal_date, candidate_scheme_id, model_score_D0)
            ) TO '{scores_path.as_posix()}' (FORMAT PARQUET)
            """
        )
    finally:
        con.close()
    return scores_path


def build_conditioning_source_fixture(
    tmp_path: Path,
    *,
    forbidden_input_tags: list[str] | None = None,
    head_quality_conditioning_source: str = "train_window_frozen_calibration",
    topk: int = 2,
    include_global_reference: bool = True,
) -> Path:
    calibration_rows: list[dict[str, object]] = [
        {
            "topk_rank_bucket": "top_1",
            "head_quality_cell_id": "top_1_cell",
            "head_quality_cell_percentile_rank": 1.0,
        },
        {
            "topk_rank_bucket": "top_2",
            "head_quality_cell_id": "top_2_cell",
            "head_quality_cell_percentile_rank": 0.2,
        },
    ]
    if include_global_reference:
        calibration_rows.append(
            {
                "topk_rank_bucket": "global_topk_train_reference",
                "head_quality_cell_id": "global_topk_reference",
                "head_quality_cell_percentile_rank": 0.4,
            }
        )

    payload = {
        "snapshot_id": "warehouse_20260429_trainval_20211231",
        "candidate_scheme_id": EXPECTED_CANDIDATE_SCHEME_ID,
        "base_score_source": "confirmed5_raw_score_D0",
        "conditioning_policy_version": EXPECTED_CONDITIONING_POLICY_VERSION,
        "head_quality_conditioning_source": head_quality_conditioning_source,
        "calibration_scope": "train_only",
        "topk": topk,
        "leakage_audit_flags": {
            "train_only_or_expanding_past_only": True,
            "no_validation_lookup": True,
            "no_frozen_test_lookup": True,
            "no_future_signal_date_lookup": True,
            "no_portfolio_feedback_lookup": True,
            "state_inputs_d0_visible": True,
        },
        "forbidden_input_tags": [] if forbidden_input_tags is None else forbidden_input_tags,
        "calibration_rows": calibration_rows,
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
            "--run-id",
            "nlc_v3_score_builder_fixture",
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


def test_v3_score_builder_topk_membership_formula_and_candidate_scheme_are_correct(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(tmp_path)
    base_scores_path = build_base_scores_fixture(tmp_path)
    conditioning_source_path = build_conditioning_source_fixture(tmp_path)
    output_dir = tmp_path / "out"

    result = run_builder(
        repo_root,
        feature_set_path,
        model_config_path,
        candidate_path,
        base_scores_path,
        conditioning_source_path,
        output_dir,
    )
    assert result.returncode == 0, result.stderr

    con = duckdb.connect()
    try:
        df = con.execute(
            f"""
            SELECT
                instrument,
                signal_date,
                candidate_scheme_id,
                raw_score_D0,
                provisional_topk_member,
                topk_rank_bucket,
                head_quality_cell_id,
                head_quality_cell_percentile_rank,
                capital_deployment_multiplier,
                adjusted_score_D0,
                conditioning_policy_version,
                leakage_audit_flags
            FROM read_parquet('{(output_dir / "model_scores_D0.parquet").as_posix()}')
            WHERE signal_date = '20200125'
            ORDER BY instrument
            """
        ).fetchdf()
    finally:
        con.close()

    assert list(df["instrument"]) == ["AAA.SZ", "BBB.SZ", "CCC.SZ"]
    assert list(df["candidate_scheme_id"]) == [EXPECTED_CANDIDATE_SCHEME_ID] * 3
    assert list(df["conditioning_policy_version"]) == [EXPECTED_CONDITIONING_POLICY_VERSION] * 3

    assert bool(df.loc[0, "provisional_topk_member"]) is False
    assert pd.isna(df.loc[0, "topk_rank_bucket"])
    assert df.loc[0, "capital_deployment_multiplier"] == 0.0
    assert df.loc[0, "adjusted_score_D0"] == 0.0

    assert bool(df.loc[1, "provisional_topk_member"]) is True
    assert df.loc[1, "topk_rank_bucket"] == "top_2"
    assert df.loc[1, "head_quality_cell_id"] == "top_2_cell"
    assert df.loc[1, "head_quality_cell_percentile_rank"] == 0.2
    assert df.loc[1, "capital_deployment_multiplier"] == 0.6
    assert df.loc[1, "adjusted_score_D0"] == 0.36

    assert bool(df.loc[2, "provisional_topk_member"]) is True
    assert df.loc[2, "topk_rank_bucket"] == "top_1"
    assert df.loc[2, "head_quality_cell_id"] == "top_1_cell"
    assert df.loc[2, "head_quality_cell_percentile_rank"] == 1.0
    assert df.loc[2, "capital_deployment_multiplier"] == 1.0
    assert df.loc[2, "adjusted_score_D0"] == 0.8

    for row_idx in [1, 2]:
        multiplier = float(df.loc[row_idx, "capital_deployment_multiplier"])
        assert 0.50 <= multiplier <= 1.00
        assert df.loc[row_idx, "adjusted_score_D0"] == df.loc[row_idx, "raw_score_D0"] * multiplier

    leakage_flags = json.loads(df.loc[2, "leakage_audit_flags"])
    assert leakage_flags["train_only_or_expanding_past_only"] is True
    assert leakage_flags["no_validation_lookup"] is True
    assert leakage_flags["no_frozen_test_lookup"] is True
    assert leakage_flags["no_future_signal_date_lookup"] is True
    assert leakage_flags["no_portfolio_feedback_lookup"] is True
    assert leakage_flags["state_inputs_d0_visible"] is True


def test_v3_score_builder_fails_fast_when_conditioning_source_is_missing_for_topk(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(tmp_path)
    base_scores_path = build_base_scores_fixture(tmp_path)
    conditioning_source_path = build_conditioning_source_fixture(
        tmp_path,
        include_global_reference=False,
    )

    payload = json.loads(conditioning_source_path.read_text(encoding="utf-8"))
    payload["calibration_rows"] = [row for row in payload["calibration_rows"] if row["topk_rank_bucket"] != "top_2"]
    write_json(conditioning_source_path, payload)

    result = run_builder(
        repo_root,
        feature_set_path,
        model_config_path,
        candidate_path,
        base_scores_path,
        conditioning_source_path,
        tmp_path / "out",
    )

    assert result.returncode != 0
    assert "conditioning source missing" in result.stderr


def test_v3_score_builder_fails_fast_on_validation_or_frozen_inputs(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(tmp_path)
    base_scores_path = build_base_scores_fixture(tmp_path)

    validation_conditioning_path = build_conditioning_source_fixture(
        tmp_path,
        forbidden_input_tags=["validation"],
    )
    validation_result = run_builder(
        repo_root,
        feature_set_path,
        model_config_path,
        candidate_path,
        base_scores_path,
        validation_conditioning_path,
        tmp_path / "out_validation",
    )
    assert validation_result.returncode != 0
    assert "validation" in validation_result.stderr

    frozen_conditioning_path = build_conditioning_source_fixture(
        tmp_path,
        forbidden_input_tags=["frozen_test"],
    )
    frozen_result = run_builder(
        repo_root,
        feature_set_path,
        model_config_path,
        candidate_path,
        base_scores_path,
        frozen_conditioning_path,
        tmp_path / "out_frozen",
    )
    assert frozen_result.returncode != 0
    assert "frozen_test" in frozen_result.stderr


def test_v3_score_builder_output_audit_marks_no_training(repo_root: Path, tmp_path: Path) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(tmp_path)
    base_scores_path = build_base_scores_fixture(tmp_path)
    conditioning_source_path = build_conditioning_source_fixture(tmp_path)
    output_dir = tmp_path / "out"

    result = run_builder(
        repo_root,
        feature_set_path,
        model_config_path,
        candidate_path,
        base_scores_path,
        conditioning_source_path,
        output_dir,
    )
    assert result.returncode == 0, result.stderr

    audit = json.loads((output_dir / "score_builder_audit.json").read_text(encoding="utf-8"))
    assert audit["training_performed"] is False
    assert audit["frozen_test_accessed"] is False
    assert audit["portfolio_outputs_generated"] is False
    assert audit["candidate_scheme_id"] == EXPECTED_CANDIDATE_SCHEME_ID
    assert audit["base_score_source"] == "confirmed5_raw_score_D0"
    assert audit["row_count"] == 6
    assert audit["null_score_rows"] == 0
    assert audit["nonfinite_score_rows"] == 0
    assert audit["provisional_topk_rows"] == 4
    assert audit["non_topk_rows"] == 2


def test_v3_score_builder_fails_fast_when_manifest_id_mismatches(repo_root: Path, tmp_path: Path) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidate["candidate_scheme_id"] = "wrong_candidate_id"
    write_json(candidate_path, candidate)

    result = run_builder(
        repo_root,
        feature_set_path,
        model_config_path,
        candidate_path,
        build_base_scores_fixture(tmp_path),
        build_conditioning_source_fixture(tmp_path),
        tmp_path / "out",
    )

    assert result.returncode != 0
    assert "candidate_scheme_id mismatch" in result.stderr


def test_v3_score_builder_script_does_not_train_model() -> None:
    script_text = read_text(SCRIPT_PATH).lower()
    assert "import lightgbm" not in script_text
    assert "lgbmregressor" not in script_text
    assert ".fit(" not in script_text
    assert ".predict(" not in script_text


def test_module_level_base_score_binding_matches_v3_candidate() -> None:
    module = load_module(SCRIPT_PATH, "build_nonlinear_challenger_v3_scores_module")
    assert module.MANIFEST_BASE_SCORE_BINDINGS[EXPECTED_CANDIDATE_SCHEME_ID] == "confirmed5_raw_score_D0"
    assert module.EXPECTED_CONDITIONING_POLICY_VERSION == EXPECTED_CONDITIONING_POLICY_VERSION
