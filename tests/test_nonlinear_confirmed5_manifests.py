from __future__ import annotations

from conftest import load_json


SOURCE_AUDIT_PATH = (
    "configs/nonlinear_challenger_v1/feature_sets/"
    "feature_set_nlc_v1_fset01_source_audit.json"
)
CONFIRMED5_FEATURE_SET_PATH = (
    "configs/nonlinear_challenger_v1/feature_sets/"
    "feature_set_nlc_v1_fset01_confirmed5.json"
)
CONFIRMED5_CANDIDATE_PATH = (
    "configs/nonlinear_challenger_v1/candidates/"
    "candidate_nlc_v1_confirmed5_lgbm_depth3_seed42.json"
)
ORIGINAL_FEATURE_SET_PATH = (
    "configs/nonlinear_challenger_v1/feature_sets/feature_set_nlc_v1_fset01.json"
)

EXPECTED_CONFIRMED5_FEATURES = [
    "reversal_5d",
    "cord30",
    "corr30",
    "vsumd60",
    "volatility_20d",
]

EXPECTED_ORIGINAL_FEATURES = [
    "p98",
    "reversal_5d",
    "reversal_20d",
    "cord30",
    "corr30",
    "vsumd60",
    "overnight_return_1d",
    "intraday_return_1d",
    "volatility_20d",
    "turnover_20d",
    "amount_20d",
    "market_index_return_20d",
]


def test_confirmed5_feature_set_json_can_be_loaded() -> None:
    payload = load_json(CONFIRMED5_FEATURE_SET_PATH)

    assert isinstance(payload, dict)


def test_confirmed5_feature_set_contains_exactly_the_five_ready_features() -> None:
    payload = load_json(CONFIRMED5_FEATURE_SET_PATH)

    assert payload["feature_count"] == 5
    assert payload["feature_list"] == EXPECTED_CONFIRMED5_FEATURES


def test_confirmed5_features_are_all_marked_ready_in_source_audit() -> None:
    source_audit = load_json(SOURCE_AUDIT_PATH)
    confirmed5 = load_json(CONFIRMED5_FEATURE_SET_PATH)
    ready_flags = {
        feature["feature_name"]: feature["ready_for_training"]
        for feature in source_audit["features"]
    }

    assert set(confirmed5["feature_list"]) == set(EXPECTED_CONFIRMED5_FEATURES)
    assert all(ready_flags[name] is True for name in confirmed5["feature_list"])


def test_confirmed5_candidate_binds_confirmed5_feature_set_and_excludes_frozen_test() -> None:
    candidate = load_json(CONFIRMED5_CANDIDATE_PATH)

    assert candidate["feature_set_id"] == "nlc_v1_fset01_confirmed5"
    assert candidate["frozen_test_access"] is False
    assert all("frozen_test" not in readout for readout in candidate["allowed_readouts"])
    assert all(
        readout.startswith("train_") or readout.startswith("validation_")
        for readout in candidate["allowed_readouts"]
    )


def test_original_fset01_manifest_remains_the_12_feature_draft() -> None:
    payload = load_json(ORIGINAL_FEATURE_SET_PATH)

    assert payload["feature_set_id"] == "nlc_v1_fset01_price_volume_interaction"
    assert payload["feature_count"] == 12
    assert payload["feature_list"] == EXPECTED_ORIGINAL_FEATURES
