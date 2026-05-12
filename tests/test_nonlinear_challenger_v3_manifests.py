from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from conftest import REPO_ROOT, load_json


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
CONFIRMED5_FEATURE_SET_PATH = (
    "configs/nonlinear_challenger_v1/feature_sets/"
    "feature_set_nlc_v1_fset01_confirmed5.json"
)
CONFIRMED5_MODEL_CONFIG_PATH = (
    "configs/nonlinear_challenger_v1/model_configs/"
    "model_config_nlc_v1_lgbm_depth3_seed42.json"
)
V2_FEATURE_SET_PATH = (
    "configs/nonlinear_challenger_v2/feature_sets/"
    "feature_set_nlc_v2_fset01_confirmed5_locked_inputs.json"
)
V2_MODEL_CONFIG_PATH = (
    "configs/nonlinear_challenger_v2/model_configs/"
    "model_config_nlc_v2_lgbm_depth3_seed42_cs_volatility_discount_v1.json"
)
V2_CANDIDATE_PATH = (
    "configs/nonlinear_challenger_v2/candidates/"
    "candidate_nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42.json"
)
SCRIPT_PATH = "scripts/validate_nonlinear_challenger_manifests.py"
PRIMARY_CHANGE_DIMENSION = "topk_head_quality_conditioned_capital_deployment"
REQUIRED_FORBIDDEN_MARKERS = {
    "fixed_test_manifest",
    "fixed_test_summary",
    "frozen_test_manifest",
    "frozen_test_summary",
}


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def run_validator(
    repo_root: Path,
    feature_set_path: Path,
    model_config_path: Path,
    candidate_path: Path,
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
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )


def is_allowed_v3_readout(readout: str) -> bool:
    return (
        (readout.startswith("train_") or readout.startswith("validation_"))
        and "test" not in readout
        and "frozen_test" not in readout
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


def test_v3_manifests_can_be_loaded() -> None:
    assert isinstance(load_json(FEATURE_SET_PATH), dict)
    assert isinstance(load_json(MODEL_CONFIG_PATH), dict)
    assert isinstance(load_json(CANDIDATE_PATH), dict)


def test_v3_ids_are_consistent_across_manifests() -> None:
    feature_set = load_json(FEATURE_SET_PATH)
    model_config = load_json(MODEL_CONFIG_PATH)
    candidate = load_json(CANDIDATE_PATH)

    assert candidate["feature_set_id"] == feature_set["feature_set_id"]
    assert candidate["model_config_id"] == model_config["model_config_id"]
    assert candidate["research_round_id"] == (
        "rr_nonlinear_challenger_v3_topk_head_quality_conditioned_capital_deployment_20260512"
    )
    assert candidate["candidate_scheme_id"] == (
        "nlc_v3_confirmed5_locked_topk_head_quality_conditioned_capital_deployment_lgbm_depth3_seed42"
    )


def test_v3_single_primary_change_dimension_exists_and_is_unique() -> None:
    model_config = load_json(MODEL_CONFIG_PATH)
    candidate = load_json(CANDIDATE_PATH)

    assert candidate["single_primary_change_dimension"] == PRIMARY_CHANGE_DIMENSION
    assert model_config["deployment_policy_interface"]["single_primary_change_dimension"] == PRIMARY_CHANGE_DIMENSION
    assert candidate["single_primary_change_description"].count(PRIMARY_CHANGE_DIMENSION) <= 1
    assert candidate["single_primary_change_description"]


def test_v3_locks_confirmed5_and_v2_without_follow_on_retuning() -> None:
    candidate = load_json(CANDIDATE_PATH)

    assert candidate["relation_to_confirmed5"]["confirmed5_locked"] is True
    assert candidate["relation_to_confirmed5"]["confirmed5_follow_on_allowed"] is False
    assert candidate["relation_to_confirmed5"]["relationship_type"] == (
        "new_research_round_not_confirmed5_retuning"
    )
    assert candidate["relation_to_v2"]["v2_locked"] is True
    assert candidate["relation_to_v2"]["v2_follow_on_allowed"] is False
    assert candidate["relation_to_v2"]["relationship_type"] == "new_research_round_not_v2_retuning"


def test_v3_feature_set_keeps_confirmed5_and_v2_inputs_locked() -> None:
    confirmed5 = load_json(CONFIRMED5_FEATURE_SET_PATH)
    v2 = load_json(V2_FEATURE_SET_PATH)
    v3 = load_json(FEATURE_SET_PATH)

    assert v3["feature_count"] == 5
    assert v3["feature_list"] == confirmed5["feature_list"] == v2["feature_list"]
    assert v3["source_parent_feature_set_id"] == "nlc_v2_fset01_confirmed5_locked_inputs"


def test_v3_model_config_keeps_lightgbm_hyperparameters_unchanged() -> None:
    confirmed5 = load_json(CONFIRMED5_MODEL_CONFIG_PATH)
    v2 = load_json(V2_MODEL_CONFIG_PATH)
    v3 = load_json(MODEL_CONFIG_PATH)

    assert v3["max_depth"] == confirmed5["max_depth"] == v2["max_depth"]
    assert v3["num_leaves"] == confirmed5["num_leaves"] == v2["num_leaves"]
    assert v3["learning_rate"] == confirmed5["learning_rate"] == v2["learning_rate"]
    assert v3["n_estimators"] == confirmed5["n_estimators"] == v2["n_estimators"]
    assert v3["deployment_policy_interface"]["new_model_inputs_allowed"] is False
    assert v3["deployment_policy_interface"]["lightgbm_hyperparameter_changes_allowed"] is False
    assert v3["deployment_policy_interface"]["execution_semantics_changes_allowed"] is False
    assert v3["deployment_policy_interface"]["terminal_exit_policy_changes_allowed"] is False
    assert v3["deployment_policy_interface"]["portfolio_guard_changes_allowed"] is False


def test_v3_forbidden_fields_include_fixed_test_and_frozen_test_markers() -> None:
    feature_set = load_json(FEATURE_SET_PATH)

    assert REQUIRED_FORBIDDEN_MARKERS.issubset(set(feature_set["prohibited_fields"]))
    assert "test_rankic_summary" in feature_set["prohibited_fields"]


def test_v3_allowed_readouts_only_use_train_or_validation_and_exclude_test() -> None:
    candidate = load_json(CANDIDATE_PATH)

    assert candidate["allowed_readouts"]
    assert all(is_allowed_v3_readout(readout) for readout in candidate["allowed_readouts"])


def test_v3_promotion_gates_include_baseline_same_contract_and_topk_head_quality() -> None:
    candidate = load_json(CANDIDATE_PATH)
    promotion_criteria = candidate["promotion_criteria"]

    assert any("model-layer diagnostics must not show material deterioration" in item for item in promotion_criteria)
    assert any("TopK head quality must improve" in item for item in promotion_criteria)
    assert any("same-contract portfolio comparison must exceed baseline" in item for item in promotion_criteria)
    assert any("total equity" in item for item in promotion_criteria)
    assert any("invested capital" in item for item in promotion_criteria)
    assert any("cash must be reported" in item for item in promotion_criteria)
    assert any("turnover must be reported" in item for item in promotion_criteria)


def test_v3_fail_fast_guardrails_cover_manifest_test_and_frozen_test_voiding() -> None:
    candidate = load_json(CANDIDATE_PATH)

    assert "manifest validator not passed -> cannot implement" in candidate["training_fail_fast_conditions"]
    assert (
        "pytest tests/test_nonlinear_challenger_v3_manifests.py not passed -> cannot implement"
        in candidate["training_fail_fast_conditions"]
    )
    assert "any frozen_test or fixed_test access plan detected -> void" in candidate["training_fail_fast_conditions"]
    assert "do_not_access_frozen_test" in candidate["prohibited_actions"]
    assert "do_not_access_fixed_test" in candidate["prohibited_actions"]


def test_v3_manifests_pass_existing_validator(repo_root: Path) -> None:
    result = run_validator(
        repo_root,
        REPO_ROOT / FEATURE_SET_PATH,
        REPO_ROOT / MODEL_CONFIG_PATH,
        REPO_ROOT / CANDIDATE_PATH,
    )

    assert result.returncode == 0, result.stderr
    assert "validation passed" in result.stdout


def test_v3_pytest_guard_fails_if_test_readout_is_added(tmp_path: Path) -> None:
    _, _, candidate_path = write_temp_manifests(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidate["allowed_readouts"].append("test_rankic_summary")
    write_json(candidate_path, candidate)

    assert any("test" in readout for readout in candidate["allowed_readouts"])
    assert not all(is_allowed_v3_readout(readout) for readout in candidate["allowed_readouts"])


def test_v3_validator_fails_if_frozen_test_readout_is_added(repo_root: Path, tmp_path: Path) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidate["allowed_readouts"].append("frozen_test_summary")
    write_json(candidate_path, candidate)

    result = run_validator(repo_root, feature_set_path, model_config_path, candidate_path)

    assert result.returncode != 0
    assert "allowed_readouts" in result.stderr
    assert "frozen_test" in result.stderr
