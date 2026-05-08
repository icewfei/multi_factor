from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SOURCE_AUDIT_PATH = (
    "configs/nonlinear_challenger_v1/feature_sets/"
    "feature_set_nlc_v1_fset01_source_audit.json"
)
BUILDER_PATH = "scripts/build_nonlinear_challenger_model_scores.py"
FEATURE_SET_PATH = "configs/nonlinear_challenger_v1/feature_sets/feature_set_nlc_v1_fset01.json"
MODEL_CONFIG_PATH = "configs/nonlinear_challenger_v1/model_configs/model_config_nlc_v1_lgbm_depth3_seed42.json"
CANDIDATE_PATH = "configs/nonlinear_challenger_v1/candidates/candidate_nlc_v1_fset01_lgbm_depth3_seed42.json"

ALLOWED_STATUSES = {"found", "not_found", "ambiguous", "derived_possible"}


def load_source_audit(repo_root: Path) -> dict:
    return json.loads((repo_root / SOURCE_AUDIT_PATH).read_text(encoding="utf-8"))


def test_source_audit_json_can_be_loaded(repo_root: Path) -> None:
    payload = load_source_audit(repo_root)

    assert isinstance(payload, dict)


def test_source_audit_covers_all_12_features(repo_root: Path) -> None:
    payload = load_source_audit(repo_root)

    assert len(payload["features"]) == 12


def test_each_feature_has_allowed_status_and_ready_flag(repo_root: Path) -> None:
    payload = load_source_audit(repo_root)

    for feature in payload["features"]:
        assert "status" in feature
        assert feature["status"] in ALLOWED_STATUSES
        assert "ready_for_training" in feature


def test_builder_still_fails_fast_when_source_audit_is_incomplete(repo_root: Path, tmp_path: Path) -> None:
    payload = load_source_audit(repo_root)
    assert payload["summary"]["ready_for_training_count"] < 12

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / BUILDER_PATH),
            "--feature-set",
            str(repo_root / FEATURE_SET_PATH),
            "--model-config",
            str(repo_root / MODEL_CONFIG_PATH),
            "--candidate",
            str(repo_root / CANDIDATE_PATH),
            "--run-id",
            "nonlinear_challenger_v1_fset01_lgbm_depth3_seed42_trainval",
            "--attempt-id",
            "attempt_manual_draft",
            "--output-dir",
            str(tmp_path / "out"),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "feature source mapping is not yet implemented / feature columns cannot be resolved." in result.stderr
    assert "feature_set_nlc_v1_fset01_source_audit.json" in result.stderr
