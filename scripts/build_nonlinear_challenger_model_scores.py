from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
VALIDATOR_PATH = SCRIPTS_DIR / "validate_nonlinear_challenger_manifests.py"
SOURCE_AUDIT_PATH = (
    ROOT
    / "configs"
    / "nonlinear_challenger_v1"
    / "feature_sets"
    / "feature_set_nlc_v1_fset01_source_audit.json"
)

MODEL_SCORES_FILENAME = "model_scores_D0.parquet"
MODEL_SCORES_AUDIT_FILENAME = "model_scores_D0_audit.json"
TRAINING_MANIFEST_FILENAME = "training_manifest.json"

MODEL_SCORES_COLUMNS = [
    "run_id",
    "candidate_scheme_id",
    "snapshot_id",
    "instrument",
    "signal_date",
    "model_score_D0",
    "feature_set_id",
    "model_config_id",
    "config_hash",
]

MODEL_SCORES_AUDIT_FIELDS = [
    "run_id",
    "attempt_id",
    "candidate_scheme_id",
    "snapshot_id",
    "row_count",
    "null_score_rows",
    "nonfinite_score_rows",
    "train_rows",
    "validation_rows",
    "feature_count",
    "feature_missing_summary",
    "feature_column_mapping_status",
    "baseline_candidate_scheme_id",
    "feature_set_hash",
    "model_config_hash",
    "config_hash",
    "status",
]

TRAINING_MANIFEST_FIELDS = [
    "run_id",
    "attempt_id",
    "candidate_scheme_id",
    "feature_set_id",
    "model_config_id",
    "snapshot_id",
    "config_hash",
    "random_seed",
    "training_started_at",
    "training_finished_at",
    "git_commit_hash",
    "environment_summary",
    "status",
]

FEATURE_SOURCE_MAPPING_NOT_IMPLEMENTED_MESSAGE = (
    "feature source mapping is not yet implemented / feature columns cannot be resolved."
)
DATA_LOADING_NOT_IMPLEMENTED_MESSAGE = "training data loading is not yet implemented."


class BuildError(Exception):
    """Raised when the model score builder cannot continue safely."""


def load_validator_symbols() -> tuple[type[Exception], Any, Any]:
    spec = importlib.util.spec_from_file_location("nlc_manifest_validator", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load manifest validator from {VALIDATOR_PATH}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ValidationError, module.load_json_manifest, module.validate_manifests


ValidationError, load_json_manifest, validate_manifests = load_validator_symbols()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build minimal Nonlinear Challenger v1 model_scores_D0 artifacts."
    )
    parser.add_argument("--feature-set", required=True, type=Path, help="Path to feature_set manifest JSON.")
    parser.add_argument("--model-config", required=True, type=Path, help="Path to model_config manifest JSON.")
    parser.add_argument("--candidate", required=True, type=Path, help="Path to candidate manifest JSON.")
    parser.add_argument("--run-id", required=True, help="Run identifier for the model_scores build attempt.")
    parser.add_argument("--attempt-id", required=True, help="Attempt identifier for the model_scores build attempt.")
    parser.add_argument("--output-dir", required=True, type=Path, help="Target output directory for future artifacts.")
    return parser


def load_and_validate_manifests(
    feature_set_path: Path,
    model_config_path: Path,
    candidate_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    feature_set = load_json_manifest(feature_set_path, "feature_set")
    model_config = load_json_manifest(model_config_path, "model_config")
    candidate = load_json_manifest(candidate_path, "candidate")
    validate_manifests(feature_set, model_config, candidate)
    return feature_set, model_config, candidate


def resolve_source_audit_path(feature_set: dict[str, Any]) -> Path:
    source_audit_value = feature_set.get("source_audit_file")
    if not source_audit_value:
        return SOURCE_AUDIT_PATH

    source_audit_path = Path(str(source_audit_value))
    if source_audit_path.is_absolute():
        return source_audit_path
    return ROOT / source_audit_path


def resolve_feature_sources_or_fail(
    feature_set: dict[str, Any],
    model_config: dict[str, Any],
    candidate: dict[str, Any],
) -> None:
    _ = model_config
    _ = candidate

    requested_features = feature_set.get("feature_list")
    if not isinstance(requested_features, list):
        raise BuildError("feature_set.feature_list must be a list before source gating can proceed.")

    audit_path = resolve_source_audit_path(feature_set)
    audit_suffix = f" See source audit: {audit_path}"

    try:
        source_audit = json.loads(audit_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BuildError(FEATURE_SOURCE_MAPPING_NOT_IMPLEMENTED_MESSAGE + audit_suffix) from exc
    except json.JSONDecodeError as exc:
        raise BuildError(FEATURE_SOURCE_MAPPING_NOT_IMPLEMENTED_MESSAGE + audit_suffix) from exc

    audit_features = source_audit.get("features")
    if not isinstance(audit_features, list):
        raise BuildError(
            FEATURE_SOURCE_MAPPING_NOT_IMPLEMENTED_MESSAGE
            + audit_suffix
        )

    feature_ready_flags: dict[str, bool] = {}
    for feature in audit_features:
        feature_name = feature.get("feature_name")
        if not isinstance(feature_name, str):
            continue
        feature_ready_flags[feature_name] = feature.get("ready_for_training") is True

    missing_from_audit = sorted(
        feature_name for feature_name in requested_features if feature_name not in feature_ready_flags
    )
    if missing_from_audit:
        raise BuildError(
            FEATURE_SOURCE_MAPPING_NOT_IMPLEMENTED_MESSAGE
            + " Requested features are missing from the source audit: "
            + ", ".join(missing_from_audit)
            + "."
            + audit_suffix
        )

    not_ready_features = sorted(
        feature_name for feature_name in requested_features if feature_ready_flags[feature_name] is not True
    )
    if not_ready_features:
        raise BuildError(
            FEATURE_SOURCE_MAPPING_NOT_IMPLEMENTED_MESSAGE
            + " Requested features are not ready_for_training=true: "
            + ", ".join(not_ready_features)
            + "."
            + audit_suffix
        )


def load_training_data_or_fail(
    feature_set: dict[str, Any],
    model_config: dict[str, Any],
    candidate: dict[str, Any],
    output_dir: Path,
) -> None:
    _ = feature_set
    _ = model_config
    _ = candidate
    _ = output_dir
    raise BuildError(DATA_LOADING_NOT_IMPLEMENTED_MESSAGE)


def run_builder(
    feature_set_path: Path,
    model_config_path: Path,
    candidate_path: Path,
    run_id: str,
    attempt_id: str,
    output_dir: Path,
) -> int:
    _ = run_id
    _ = attempt_id

    feature_set, model_config, candidate = load_and_validate_manifests(
        feature_set_path,
        model_config_path,
        candidate_path,
    )
    resolve_feature_sources_or_fail(feature_set, model_config, candidate)
    load_training_data_or_fail(feature_set, model_config, candidate, output_dir)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return run_builder(
            feature_set_path=args.feature_set,
            model_config_path=args.model_config,
            candidate_path=args.candidate,
            run_id=args.run_id,
            attempt_id=args.attempt_id,
            output_dir=args.output_dir,
        )
    except ValidationError as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        return 1
    except BuildError as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
