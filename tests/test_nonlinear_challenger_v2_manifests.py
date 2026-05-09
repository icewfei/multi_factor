from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from conftest import REPO_ROOT, load_json


FEATURE_SET_PATH = (
    "configs/nonlinear_challenger_v2/feature_sets/"
    "feature_set_nlc_v2_fset01_confirmed5_locked_inputs.json"
)
MODEL_CONFIG_PATH = (
    "configs/nonlinear_challenger_v2/model_configs/"
    "model_config_nlc_v2_lgbm_depth3_seed42_cs_volatility_discount_v1.json"
)
CANDIDATE_PATH = (
    "configs/nonlinear_challenger_v2/candidates/"
    "candidate_nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42.json"
)
CONFIRMED5_FEATURE_SET_PATH = (
    "configs/nonlinear_challenger_v1/feature_sets/"
    "feature_set_nlc_v1_fset01_confirmed5.json"
)
CONFIRMED5_MODEL_CONFIG_PATH = (
    "configs/nonlinear_challenger_v1/model_configs/"
    "model_config_nlc_v1_lgbm_depth3_seed42.json"
)
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


def write_temp_manifests(tmp_path: Path) -> tuple[Path, Path, Path]:
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


def test_v2_manifests_can_be_loaded() -> None:
    assert isinstance(load_json(FEATURE_SET_PATH), dict)
    assert isinstance(load_json(MODEL_CONFIG_PATH), dict)
    assert isinstance(load_json(CANDIDATE_PATH), dict)


def test_v2_feature_set_locks_confirmed5_inputs_without_new_feature_freedom() -> None:
    confirmed5 = load_json(CONFIRMED5_FEATURE_SET_PATH)
    v2 = load_json(FEATURE_SET_PATH)

    assert v2["feature_count"] == 5
    assert v2["feature_list"] == confirmed5["feature_list"]
    assert v2["source_column_mapping_required"] is True
    assert "volatility_20d" in v2["feature_list"]


def test_v2_model_config_keeps_confirmed5_hyperparameters_and_changes_only_score_transform() -> None:
    confirmed5 = load_json(CONFIRMED5_MODEL_CONFIG_PATH)
    v2 = load_json(MODEL_CONFIG_PATH)

    assert v2["max_depth"] == confirmed5["max_depth"]
    assert v2["num_leaves"] == confirmed5["num_leaves"]
    assert v2["learning_rate"] == confirmed5["learning_rate"]
    assert v2["n_estimators"] == confirmed5["n_estimators"]
    assert v2["post_score_transformation"]["single_primary_change_dimension"] == (
        "portfolio_aware_cross_sectional_score_transformation"
    )
    assert v2["post_score_transformation"]["fixed_formula"] == (
        "adjusted_score_D0 = raw_model_score_percentile_rank_D0 * "
        "(1.0 - volatility_20d_percentile_rank_D0)"
    )
    assert v2["post_score_transformation"]["tunable_parameters_allowed"] is False
    assert v2["post_score_transformation"]["validation_recalibration_allowed"] is False


def test_v2_candidate_declares_new_challenger_relationship_and_guardrails() -> None:
    candidate = load_json(CANDIDATE_PATH)

    assert candidate["research_round_id"] == "rr_nonlinear_challenger_v2_cs_volatility_discount_20260509"
    assert candidate["relation_to_confirmed5"]["parent_candidate_scheme_id"] == (
        "nlc_v1_confirmed5_lgbm_depth3_seed42"
    )
    assert candidate["single_primary_change_dimension"] == (
        "portfolio_aware_cross_sectional_score_transformation"
    )
    assert candidate["baseline_binding_required_before_training"] is True
    assert candidate["baseline_candidate_scheme_id"] == "multi_equal_weight_v1"
    assert candidate["frozen_test_access"] is False
    assert all("frozen_test" not in readout for readout in candidate["allowed_readouts"])


def test_v2_candidate_contains_required_promotion_gate_and_fail_fast_conditions() -> None:
    candidate = load_json(CANDIDATE_PATH)

    assert any("not show material deterioration versus confirmed5" in item for item in candidate["promotion_criteria"])
    assert any("must exceed baseline" in item for item in candidate["promotion_criteria"])
    assert any("total equity" in item for item in candidate["promotion_criteria"])
    assert any("invested capital" in item for item in candidate["promotion_criteria"])
    assert any("average invested_weight" in item for item in candidate["promotion_criteria"])
    assert any("average cash_weight" in item for item in candidate["promotion_criteria"])
    assert any("terminal exit flags" in item for item in candidate["promotion_criteria"])

    assert "source mapping not confirmed -> cannot train" in candidate["training_fail_fast_conditions"]
    assert "baseline comparison not bound -> cannot train" in candidate["training_fail_fast_conditions"]
    assert "manifest validator not passed -> cannot train" in candidate["training_fail_fast_conditions"]


def test_v2_manifests_pass_existing_validator(repo_root: Path) -> None:
    result = run_validator(
        repo_root,
        REPO_ROOT / FEATURE_SET_PATH,
        REPO_ROOT / MODEL_CONFIG_PATH,
        REPO_ROOT / CANDIDATE_PATH,
    )

    assert result.returncode == 0, result.stderr
    assert "validation passed" in result.stdout


def test_v2_validator_fails_if_baseline_binding_is_removed(repo_root: Path, tmp_path: Path) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidate["baseline_candidate_scheme_id"] = "<to_be_bound_before_training>"
    write_json(candidate_path, candidate)

    result = run_validator(repo_root, feature_set_path, model_config_path, candidate_path)

    assert result.returncode != 0
    assert "baseline_candidate_scheme_id" in result.stderr


def test_v2_validator_fails_if_frozen_test_readout_is_added(repo_root: Path, tmp_path: Path) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidate["allowed_readouts"].append("frozen_test_summary")
    write_json(candidate_path, candidate)

    result = run_validator(repo_root, feature_set_path, model_config_path, candidate_path)

    assert result.returncode != 0
    assert "allowed_readouts" in result.stderr
    assert "frozen_test" in result.stderr
