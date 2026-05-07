from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PLACEHOLDER_BASELINE_ID = "<to_be_bound_before_training>"


class ValidationError(Exception):
    """Raised when manifest validation fails."""


def load_json_manifest(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError(f"{label} manifest could not be loaded: file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{label} manifest could not be loaded: invalid JSON in {path}: {exc}") from exc
    except OSError as exc:
        raise ValidationError(f"{label} manifest could not be loaded: {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValidationError(f"{label} manifest must be a JSON object: {path}")

    return payload


def require_field(payload: dict[str, Any], field: str, label: str) -> Any:
    if field not in payload:
        raise ValidationError(f"{label} manifest is missing required field: {field}")
    return payload[field]


def validate_manifests(
    feature_set: dict[str, Any],
    model_config: dict[str, Any],
    candidate: dict[str, Any],
) -> None:
    feature_set_id = require_field(feature_set, "feature_set_id", "feature_set")
    candidate_feature_set_id = require_field(candidate, "feature_set_id", "candidate")
    if feature_set_id != candidate_feature_set_id:
        raise ValidationError(
            "feature_set_id mismatch: "
            f"feature_set={feature_set_id!r}, candidate={candidate_feature_set_id!r}"
        )

    model_config_id = require_field(model_config, "model_config_id", "model_config")
    candidate_model_config_id = require_field(candidate, "model_config_id", "candidate")
    if model_config_id != candidate_model_config_id:
        raise ValidationError(
            "model_config_id mismatch: "
            f"model_config={model_config_id!r}, candidate={candidate_model_config_id!r}"
        )

    feature_snapshot_id = require_field(feature_set, "snapshot_id", "feature_set")
    candidate_snapshot_id = require_field(candidate, "snapshot_id", "candidate")
    if feature_snapshot_id != candidate_snapshot_id:
        raise ValidationError(
            "snapshot_id mismatch: "
            f"feature_set={feature_snapshot_id!r}, candidate={candidate_snapshot_id!r}"
        )

    # Current draft model_config does not carry a dedicated snapshot_id field.
    # If one is added later, it must agree with the other manifests.
    model_snapshot_id = model_config.get("snapshot_id")
    if model_snapshot_id is not None and model_snapshot_id != feature_snapshot_id:
        raise ValidationError(
            "snapshot_id mismatch: "
            f"model_config={model_snapshot_id!r}, feature_set={feature_snapshot_id!r}"
        )

    feature_count = require_field(feature_set, "feature_count", "feature_set")
    feature_list = require_field(feature_set, "feature_list", "feature_set")
    prohibited_fields = require_field(feature_set, "prohibited_fields", "feature_set")
    if not isinstance(feature_list, list):
        raise ValidationError("feature_set.feature_list must be a list")
    if not isinstance(prohibited_fields, list):
        raise ValidationError("feature_set.prohibited_fields must be a list")
    if feature_count > 20:
        raise ValidationError(f"feature_count must be <= 20, got {feature_count}")
    if feature_count != len(feature_list):
        raise ValidationError(
            "feature_count must equal len(feature_list): "
            f"feature_count={feature_count}, len(feature_list)={len(feature_list)}"
        )

    prohibited_feature_hits = sorted(set(feature_list) & set(prohibited_fields))
    if prohibited_feature_hits:
        raise ValidationError(
            "prohibited_fields must not appear in feature_list: "
            + ", ".join(prohibited_feature_hits)
        )

    if require_field(feature_set, "source_column_mapping_required", "feature_set") is not True:
        raise ValidationError("feature_set.source_column_mapping_required must be true")

    if require_field(model_config, "frozen_test_access", "model_config") is not False:
        raise ValidationError("model_config.frozen_test_access must be false")
    if require_field(candidate, "frozen_test_access", "candidate") is not False:
        raise ValidationError("candidate.frozen_test_access must be false")

    allowed_readouts = require_field(candidate, "allowed_readouts", "candidate")
    if not isinstance(allowed_readouts, list):
        raise ValidationError("candidate.allowed_readouts must be a list")
    if any("frozen_test" in str(readout) for readout in allowed_readouts):
        raise ValidationError("candidate.allowed_readouts must not include frozen_test")

    if require_field(model_config, "max_depth", "model_config") > 3:
        raise ValidationError("model_config.max_depth must be <= 3")
    if require_field(model_config, "hyperparameter_tuning_allowed", "model_config") is not False:
        raise ValidationError("model_config.hyperparameter_tuning_allowed must be false")
    if require_field(model_config, "n_estimators_tuning_allowed", "model_config") is not False:
        raise ValidationError("model_config.n_estimators_tuning_allowed must be false")
    if require_field(model_config, "automl_allowed", "model_config") is not False:
        raise ValidationError("model_config.automl_allowed must be false")
    if require_field(model_config, "neural_network_allowed", "model_config") is not False:
        raise ValidationError("model_config.neural_network_allowed must be false")
    if require_field(model_config, "large_scale_parameter_search_allowed", "model_config") is not False:
        raise ValidationError("model_config.large_scale_parameter_search_allowed must be false")

    if require_field(candidate, "candidate_status", "candidate") != "preregistered":
        raise ValidationError("candidate.candidate_status must be 'preregistered'")
    if require_field(candidate, "baseline_binding_required_before_training", "candidate") is not True:
        raise ValidationError("candidate.baseline_binding_required_before_training must be true")

    baseline_candidate_scheme_id = require_field(candidate, "baseline_candidate_scheme_id", "candidate")
    if baseline_candidate_scheme_id == PLACEHOLDER_BASELINE_ID or not str(baseline_candidate_scheme_id).strip():
        raise ValidationError(
            "candidate.baseline_candidate_scheme_id must be bound before training; "
            f"got {baseline_candidate_scheme_id!r}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate Nonlinear Challenger v1 manifest consistency and guardrails."
    )
    parser.add_argument("--feature-set", required=True, type=Path, help="Path to feature_set manifest JSON.")
    parser.add_argument("--model-config", required=True, type=Path, help="Path to model_config manifest JSON.")
    parser.add_argument("--candidate", required=True, type=Path, help="Path to candidate manifest JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        feature_set = load_json_manifest(args.feature_set, "feature_set")
        model_config = load_json_manifest(args.model_config, "model_config")
        candidate = load_json_manifest(args.candidate, "candidate")
        validate_manifests(feature_set, model_config, candidate)
    except ValidationError as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        return 1

    print("validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
