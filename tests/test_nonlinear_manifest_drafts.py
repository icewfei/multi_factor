from __future__ import annotations

import json
from pathlib import Path


DRAFT_PATHS = {
    "feature_set": "configs/nonlinear_challenger_v1/feature_sets/feature_set_nlc_v1_fset01.json",
    "model_config": "configs/nonlinear_challenger_v1/model_configs/model_config_nlc_v1_lgbm_depth3_seed42.json",
    "candidate_scheme": "configs/nonlinear_challenger_v1/candidates/candidate_nlc_v1_fset01_lgbm_depth3_seed42.json",
}

REQUIRED_PROHIBITED_FIELDS = {
    "label_5d_next_open_close",
    "label_5d_next_open_close_raw",
    "execution_delayed_realized_return",
    "actual_exit_date",
    "actual_sell_price",
}


def load_draft(repo_root: Path, relative_path: str) -> dict:
    return json.loads((repo_root / relative_path).read_text(encoding="utf-8"))


def test_draft_manifests_can_be_loaded_as_json(repo_root: Path) -> None:
    for relative_path in DRAFT_PATHS.values():
        payload = load_draft(repo_root, relative_path)
        assert isinstance(payload, dict)


def test_feature_set_draft_respects_feature_budget_and_prohibited_fields(repo_root: Path) -> None:
    payload = load_draft(repo_root, DRAFT_PATHS["feature_set"])

    assert payload["feature_count"] <= 20
    assert payload["feature_count"] == len(payload["feature_list"])
    assert REQUIRED_PROHIBITED_FIELDS.issubset(set(payload["prohibited_fields"]))


def test_model_config_draft_disables_frozen_test_and_caps_depth(repo_root: Path) -> None:
    payload = load_draft(repo_root, DRAFT_PATHS["model_config"])

    assert payload["frozen_test_access"] is False
    assert payload["max_depth"] <= 3


def test_candidate_draft_is_preregistered_and_excludes_frozen_test_readouts(repo_root: Path) -> None:
    payload = load_draft(repo_root, DRAFT_PATHS["candidate_scheme"])

    assert payload["candidate_status"] == "preregistered"
    assert payload["frozen_test_access"] is False
    assert all("frozen_test" not in readout for readout in payload["allowed_readouts"])
