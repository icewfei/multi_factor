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


def resolve_feature_sources_or_fail(
    feature_set: dict[str, Any],
    model_config: dict[str, Any],
    candidate: dict[str, Any],
) -> None:
    _ = model_config
    _ = candidate

    mapping_required = feature_set.get("source_column_mapping_required")
    existence_status = str(feature_set.get("feature_column_existence_status", ""))
    audit_path = SOURCE_AUDIT_PATH
    audit_suffix = f" See source audit: {audit_path}"

    try:
        source_audit = json.loads(audit_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BuildError(FEATURE_SOURCE_MAPPING_NOT_IMPLEMENTED_MESSAGE + audit_suffix) from exc
    except json.JSONDecodeError as exc:
        raise BuildError(FEATURE_SOURCE_MAPPING_NOT_IMPLEMENTED_MESSAGE + audit_suffix) from exc

    summary = source_audit.get("summary", {})
    ready_for_training_count = summary.get("ready_for_training_count")
    total_features = summary.get("total_features")
    if ready_for_training_count != total_features:
        raise BuildError(
            FEATURE_SOURCE_MAPPING_NOT_IMPLEMENTED_MESSAGE
            + f" Source audit reports ready_for_training_count={ready_for_training_count}, "
            f"total_features={total_features}."
            + audit_suffix
        )

    if mapping_required is True:
        raise BuildError(FEATURE_SOURCE_MAPPING_NOT_IMPLEMENTED_MESSAGE + audit_suffix)

    if "require_source_column_mapping_before_training" in existence_status:
        raise BuildError(FEATURE_SOURCE_MAPPING_NOT_IMPLEMENTED_MESSAGE + audit_suffix)

    raise BuildError(FEATURE_SOURCE_MAPPING_NOT_IMPLEMENTED_MESSAGE + audit_suffix)


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
    _ = output_dir

    feature_set, model_config, candidate = load_and_validate_manifests(
        feature_set_path,
        model_config_path,
        candidate_path,
    )
    resolve_feature_sources_or_fail(feature_set, model_config, candidate)
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
