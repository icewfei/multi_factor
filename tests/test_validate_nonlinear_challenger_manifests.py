from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from conftest import load_json


FEATURE_SET_PATH = "configs/nonlinear_challenger_v1/feature_sets/feature_set_nlc_v1_fset01.json"
MODEL_CONFIG_PATH = "configs/nonlinear_challenger_v1/model_configs/model_config_nlc_v1_lgbm_depth3_seed42.json"
CANDIDATE_PATH = "configs/nonlinear_challenger_v1/candidates/candidate_nlc_v1_fset01_lgbm_depth3_seed42.json"
SCRIPT_PATH = "scripts/validate_nonlinear_challenger_manifests.py"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def run_validator(repo_root: Path, feature_set_path: Path, model_config_path: Path, candidate_path: Path) -> subprocess.CompletedProcess[str]:
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
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )


def write_temp_manifests(repo_root: Path, tmp_path: Path) -> tuple[Path, Path, Path]:
    feature_set = load_json(FEATURE_SET_PATH)
    model_config = load_json(MODEL_CONFIG_PATH)
    candidate = load_json(CANDIDATE_PATH)

    feature_set_path = tmp_path / "feature_set.json"
    model_config_path = tmp_path / "model_config.json"
    candidate_path = tmp_path / "candidate.json"

    write_json(feature_set_path, feature_set)
    write_json(model_config_path, model_config)
    write_json(candidate_path, candidate)

    return feature_set_path, model_config_path, candidate_path


def test_current_manifests_fail_because_baseline_candidate_is_still_placeholder(
    repo_root: Path, tmp_path: Path
) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(repo_root, tmp_path)

    result = run_validator(repo_root, feature_set_path, model_config_path, candidate_path)

    assert result.returncode == 0
    assert "validation passed" in result.stdout


def test_validation_fails_if_baseline_candidate_is_replaced_with_placeholder(
    repo_root: Path, tmp_path: Path
) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(repo_root, tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidate["baseline_candidate_scheme_id"] = "<to_be_bound_before_training>"
    write_json(candidate_path, candidate)

    result = run_validator(repo_root, feature_set_path, model_config_path, candidate_path)

    assert result.returncode != 0
    assert "baseline_candidate_scheme_id" in result.stderr
    assert "<to_be_bound_before_training>" in result.stderr


def test_validation_fails_when_allowed_readouts_include_frozen_test(repo_root: Path, tmp_path: Path) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(repo_root, tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidate["allowed_readouts"].append("frozen_test_summary")
    write_json(candidate_path, candidate)

    result = run_validator(repo_root, feature_set_path, model_config_path, candidate_path)

    assert result.returncode != 0
    assert "allowed_readouts" in result.stderr
    assert "frozen_test" in result.stderr


def test_validation_fails_when_feature_count_exceeds_budget(repo_root: Path, tmp_path: Path) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(repo_root, tmp_path)
    feature_set = json.loads(feature_set_path.read_text(encoding="utf-8"))
    feature_set["feature_count"] = 21
    write_json(feature_set_path, feature_set)

    result = run_validator(repo_root, feature_set_path, model_config_path, candidate_path)

    assert result.returncode != 0
    assert "feature_count must be <= 20" in result.stderr


def test_validation_fails_when_prohibited_field_appears_in_feature_list(
    repo_root: Path, tmp_path: Path
) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(repo_root, tmp_path)
    feature_set = json.loads(feature_set_path.read_text(encoding="utf-8"))
    feature_set["feature_list"].append("actual_exit_date")
    feature_set["feature_count"] = len(feature_set["feature_list"])
    write_json(feature_set_path, feature_set)

    result = run_validator(repo_root, feature_set_path, model_config_path, candidate_path)

    assert result.returncode != 0
    assert "prohibited_fields" in result.stderr
    assert "actual_exit_date" in result.stderr
