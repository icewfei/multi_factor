from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import load_json, load_module, read_text


FEATURE_SET_PATH = "configs/nonlinear_challenger_v1/feature_sets/feature_set_nlc_v1_fset01.json"
MODEL_CONFIG_PATH = "configs/nonlinear_challenger_v1/model_configs/model_config_nlc_v1_lgbm_depth3_seed42.json"
CANDIDATE_PATH = "configs/nonlinear_challenger_v1/candidates/candidate_nlc_v1_fset01_lgbm_depth3_seed42.json"
SCRIPT_PATH = "scripts/build_nonlinear_challenger_model_scores.py"


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


def run_builder(
    repo_root: Path,
    feature_set_path: Path,
    model_config_path: Path,
    candidate_path: Path,
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
            "--run-id",
            "nonlinear_challenger_v1_fset01_lgbm_depth3_seed42_trainval",
            "--attempt-id",
            "attempt_manual_draft",
            "--output-dir",
            str(output_dir),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_builder_script_exists(repo_root: Path) -> None:
    assert (repo_root / SCRIPT_PATH).exists()


def test_builder_cli_help_runs(repo_root: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(repo_root / SCRIPT_PATH), "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--feature-set" in result.stdout
    assert "--output-dir" in result.stdout


def test_builder_calls_manifest_validator_before_feature_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module(SCRIPT_PATH, "build_nonlinear_challenger_model_scores_module")
    call_order: list[str] = []

    def fake_load_json_manifest(path: Path, label: str) -> dict:
        _ = path
        call_order.append(f"load:{label}")
        return {"label": label}

    def fake_validate_manifests(feature_set: dict, model_config: dict, candidate: dict) -> None:
        _ = feature_set
        _ = model_config
        _ = candidate
        call_order.append("validate")

    def fake_resolve_feature_sources_or_fail(feature_set: dict, model_config: dict, candidate: dict) -> None:
        _ = feature_set
        _ = model_config
        _ = candidate
        call_order.append("resolve")
        raise module.BuildError("stub unresolved mapping")

    monkeypatch.setattr(module, "load_json_manifest", fake_load_json_manifest)
    monkeypatch.setattr(module, "validate_manifests", fake_validate_manifests)
    monkeypatch.setattr(module, "resolve_feature_sources_or_fail", fake_resolve_feature_sources_or_fail)

    with pytest.raises(module.BuildError, match="stub unresolved mapping"):
        module.run_builder(
            feature_set_path=Path("feature.json"),
            model_config_path=Path("model.json"),
            candidate_path=Path("candidate.json"),
            run_id="run_id",
            attempt_id="attempt_id",
            output_dir=Path("output"),
        )

    assert call_order == [
        "load:feature_set",
        "load:model_config",
        "load:candidate",
        "validate",
        "resolve",
    ]


def test_builder_fails_when_frozen_access_is_enabled(repo_root: Path, tmp_path: Path) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(tmp_path)
    model_config = json.loads(model_config_path.read_text(encoding="utf-8"))
    model_config["frozen_test_access"] = True
    write_json(model_config_path, model_config)

    result = run_builder(repo_root, feature_set_path, model_config_path, candidate_path, tmp_path / "out")

    assert result.returncode != 0
    assert "frozen_test_access" in result.stderr


def test_builder_fails_when_baseline_is_placeholder(repo_root: Path, tmp_path: Path) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidate["baseline_candidate_scheme_id"] = "<to_be_bound_before_training>"
    write_json(candidate_path, candidate)

    result = run_builder(repo_root, feature_set_path, model_config_path, candidate_path, tmp_path / "out")

    assert result.returncode != 0
    assert "baseline_candidate_scheme_id" in result.stderr


def test_builder_fails_fast_when_feature_source_mapping_is_not_ready(repo_root: Path, tmp_path: Path) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(tmp_path)

    result = run_builder(repo_root, feature_set_path, model_config_path, candidate_path, tmp_path / "out")

    assert result.returncode != 0
    assert "feature source mapping is not yet implemented / feature columns cannot be resolved." in result.stderr


def test_builder_source_excludes_portfolio_metrics_and_readout_paths() -> None:
    script_text = read_text(SCRIPT_PATH)

    assert "holdings.csv" not in script_text
    assert "metrics.json" not in script_text
    assert "portfolio_daily_summary.csv" not in script_text
    assert "backtest_daily.csv" not in script_text
    assert "validation_readout" not in script_text
    assert "build_portfolio_artifacts.py" not in script_text
    assert "build_fixed_test_minimal.py" not in script_text
