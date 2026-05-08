from __future__ import annotations

import pytest

from conftest import load_json, load_module, read_text


ROUND_ID = "rr_nonlinear_challenger_v1_confirmed5"
CANDIDATE_ID = "nlc_v1_confirmed5_lgbm_depth3_seed42"


def test_nonlinear_confirmed5_registry_guardrails_pass() -> None:
    module = load_module("scripts/build_run_state_skeleton.py", "build_run_state_skeleton_registry_test")

    payload = module.validate_registry_guardrails(CANDIDATE_ID, ROUND_ID)

    assert payload["changed_dimension"] == "nonlinear_challenger_confirmed5_model_scores"
    assert payload["candidate_entry"]["candidate_scheme_id"] == CANDIDATE_ID
    assert payload["research_round_entry"]["research_round_id"] == ROUND_ID
    assert payload["preregistration"]["change_control_rule"] == "single_dimension_only"


def test_wrong_candidate_scheme_id_still_fails_registry_guardrails() -> None:
    module = load_module("scripts/build_run_state_skeleton.py", "build_run_state_skeleton_registry_test")

    with pytest.raises(ValueError, match="candidate_scheme_id is not registered before full-chain execution"):
        module.validate_registry_guardrails("nlc_v1_confirmed5_lgbm_depth3_seed999", ROUND_ID)


def test_wrong_research_round_id_still_fails_registry_guardrails() -> None:
    module = load_module("scripts/build_run_state_skeleton.py", "build_run_state_skeleton_registry_test")

    with pytest.raises(ValueError, match="research_round_id is not registered before full-chain execution"):
        module.validate_registry_guardrails(CANDIDATE_ID, "rr_nonlinear_challenger_v1_missing")


def test_nonlinear_confirmed5_preregistration_contract_is_explicit() -> None:
    prereg = load_json(
        "artifacts/research_registry/research_rounds/rr_nonlinear_challenger_v1_confirmed5/preregistration.json"
    )

    assert prereg["changed_dimension"] == "nonlinear_challenger_confirmed5_model_scores"
    assert prereg["change_control_rule"] == "single_dimension_only"
    assert prereg["candidate_scheme_ids"] == [CANDIDATE_ID]
    assert prereg["constants_frozen"]["feature_set_id"] == "nlc_v1_fset01_confirmed5"
    assert prereg["constants_frozen"]["model_config_id"] == "nlc_v1_lgbm_regressor_depth3_seed42"
    assert prereg["constants_frozen"]["frozen_test_access"] is False
    assert prereg["allowed_candidate_contract"]["feature_names"] == [
        "reversal_5d",
        "cord30",
        "corr30",
        "vsumd60",
        "volatility_20d",
    ]


def test_run_state_skeleton_does_not_expose_registry_bypass_flag() -> None:
    script_text = read_text("scripts/build_run_state_skeleton.py")

    assert "--skip-registry-guardrails-dry-run" not in script_text
