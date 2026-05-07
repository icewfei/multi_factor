from __future__ import annotations

import json
from pathlib import Path


TEMPLATE_PATHS = {
    "feature_set": "configs/nonlinear_challenger_v1/feature_sets/feature_set_manifest.template.json",
    "model_config": "configs/nonlinear_challenger_v1/model_configs/model_config_manifest.template.json",
    "candidate_scheme": "configs/nonlinear_challenger_v1/candidates/candidate_scheme_manifest.template.json",
}


def load_template(repo_root: Path, relative_path: str) -> dict:
    return json.loads((repo_root / relative_path).read_text(encoding="utf-8"))


def test_manifest_templates_can_be_loaded_as_json(repo_root: Path) -> None:
    for relative_path in TEMPLATE_PATHS.values():
        payload = load_template(repo_root, relative_path)
        assert isinstance(payload, dict)


def test_model_config_template_disables_frozen_test_access(repo_root: Path) -> None:
    payload = load_template(repo_root, TEMPLATE_PATHS["model_config"])

    assert payload["frozen_test_access"] is False


def test_feature_set_template_declares_feature_count(repo_root: Path) -> None:
    payload = load_template(repo_root, TEMPLATE_PATHS["feature_set"])

    assert "feature_count" in payload


def test_candidate_template_starts_as_preregistered(repo_root: Path) -> None:
    payload = load_template(repo_root, TEMPLATE_PATHS["candidate_scheme"])

    assert payload["candidate_status"] == "preregistered"
