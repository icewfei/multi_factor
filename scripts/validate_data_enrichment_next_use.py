#!/opt/anaconda3/envs/quant_trade/bin/python
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path("/Users/wy/MiscProject/multi_factor")
DEFAULT_POLICY_PATH = ROOT / "configs" / "data_field_enrichment" / "enrichment_next_use_policy_v1.json"
DEFAULT_POLICY_SCHEMA_PATH = ROOT / "schemas" / "data_field_enrichment_next_use_policy.schema.json"
DEFAULT_REQUEST_JSON_PATH = Path("/private/tmp/data_enrichment_next_use_request.json")
DEFAULT_OUTPUT_JSON_PATH = Path("/private/tmp/data_enrichment_next_use_guardrail_audit.json")
ALLOWED_INTENDED_USES = {"diagnostic", "clean_baseline", "challenger"}
KNOWN_INTENDED_USES = ALLOWED_INTENDED_USES | {"portfolio", "screening"}


class NextUseValidationError(Exception):
    """Raised when the validator inputs are incomplete or invalid."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate downstream usage requests against data enrichment next-use policy."
    )
    parser.add_argument(
        "--request-json",
        type=Path,
        default=DEFAULT_REQUEST_JSON_PATH,
        help="Path to a downstream next-use request JSON file.",
    )
    parser.add_argument(
        "--policy-json",
        type=Path,
        default=DEFAULT_POLICY_PATH,
        help="Path to enrichment_next_use_policy_v1.json.",
    )
    parser.add_argument(
        "--policy-schema",
        type=Path,
        default=DEFAULT_POLICY_SCHEMA_PATH,
        help="Path to data_field_enrichment_next_use_policy.schema.json.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=DEFAULT_OUTPUT_JSON_PATH,
        help="Path to write the guardrail audit JSON.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def normalize_string_list(value: Any, *, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise NextUseValidationError(f"{field_name} must be a list of strings")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise NextUseValidationError(f"{field_name} must contain only non-empty strings")
    return list(dict.fromkeys(item.strip() for item in value))


def require_nonempty_string(payload: dict[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise NextUseValidationError(f"{field_name} must be a non-empty string")
    return value.strip()


def load_next_use_policy(policy_path: Path, policy_schema_path: Path) -> dict[str, Any]:
    if not policy_path.exists():
        raise NextUseValidationError(f"policy JSON not found: {policy_path}")
    if not policy_schema_path.exists():
        raise NextUseValidationError(f"policy schema JSON not found: {policy_schema_path}")

    policy = load_json(policy_path)
    policy_schema = load_json(policy_schema_path)
    jsonschema.validate(policy, policy_schema)
    return policy


def validate_request_shape(request: dict[str, Any]) -> dict[str, Any]:
    requested_fields = normalize_string_list(request.get("requested_fields"), field_name="requested_fields")
    intended_use = require_nonempty_string(request, "intended_use")
    consumer_name = require_nonempty_string(request, "consumer_name")
    run_scope = require_nonempty_string(request, "run_scope")

    declared_no_frozen_test_access = request.get("declared_no_frozen_test_access")
    declared_conditional_pass = request.get("declared_conditional_pass")
    requested_layer_status = request.get("requested_layer_status")
    allow_silent_fallback = request.get("allow_silent_fallback", False)

    if not isinstance(declared_no_frozen_test_access, bool):
        raise NextUseValidationError("declared_no_frozen_test_access must be a boolean")
    if not isinstance(declared_conditional_pass, bool):
        raise NextUseValidationError("declared_conditional_pass must be a boolean")
    if requested_layer_status is not None and not isinstance(requested_layer_status, str):
        raise NextUseValidationError("requested_layer_status must be a string when provided")
    if not isinstance(allow_silent_fallback, bool):
        raise NextUseValidationError("allow_silent_fallback must be a boolean")

    return {
        "requested_fields": requested_fields,
        "intended_use": intended_use,
        "consumer_name": consumer_name,
        "run_scope": run_scope,
        "declared_no_frozen_test_access": declared_no_frozen_test_access,
        "declared_conditional_pass": declared_conditional_pass,
        "requested_layer_status": requested_layer_status,
        "allow_silent_fallback": allow_silent_fallback,
    }


def validate_next_use_request(policy: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    normalized_request = validate_request_shape(request)
    requested_fields = normalized_request["requested_fields"]
    intended_use = normalized_request["intended_use"]

    allowed_fields = set(policy["allowed_fields"])
    blocked_fields = set(policy["blocked_fields"])
    conditional_fields = set(policy["conditional_fields"])
    known_fields = allowed_fields | blocked_fields | conditional_fields

    allowed_fields_used = [field for field in requested_fields if field in allowed_fields]
    blocked_fields_requested = [field for field in requested_fields if field in blocked_fields]
    unknown_fields_requested = [field for field in requested_fields if field not in known_fields]

    fail_fast_reasons: list[str] = []
    if blocked_fields_requested:
        fail_fast_reasons.append(
            "blocked_fields_requested: " + ", ".join(blocked_fields_requested)
        )
    if unknown_fields_requested:
        fail_fast_reasons.append(
            "unknown_fields_requested: " + ", ".join(unknown_fields_requested)
        )
    if intended_use not in KNOWN_INTENDED_USES:
        fail_fast_reasons.append(f"unknown_intended_use: {intended_use}")
    elif intended_use not in ALLOWED_INTENDED_USES:
        fail_fast_reasons.append(f"intended_use_not_allowed_by_policy: {intended_use}")
    if normalized_request["declared_no_frozen_test_access"] is not True:
        fail_fast_reasons.append("declared_no_frozen_test_access must be true")
    if normalized_request["declared_conditional_pass"] is not True:
        fail_fast_reasons.append("declared_conditional_pass must be true")

    requested_layer_status = normalized_request["requested_layer_status"]
    if requested_layer_status == "full_pass":
        fail_fast_reasons.append("requested_layer_status must not promote conditional_pass to full_pass")
    elif requested_layer_status not in (None, "conditional_pass"):
        fail_fast_reasons.append(
            f"requested_layer_status must be conditional_pass when provided: {requested_layer_status}"
        )

    if normalized_request["allow_silent_fallback"]:
        fail_fast_reasons.append("allow_silent_fallback must be false")

    status = "pass" if not fail_fast_reasons else "blocked"
    audit_time = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return {
        "status": status,
        "consumer_name": normalized_request["consumer_name"],
        "run_scope": normalized_request["run_scope"],
        "intended_use": intended_use,
        "requested_fields": requested_fields,
        "allowed_fields_used": allowed_fields_used,
        "blocked_fields_requested": blocked_fields_requested,
        "unknown_fields_requested": unknown_fields_requested,
        "required_disclosure": list(policy["required_disclosure"]),
        "fail_fast_reasons": fail_fast_reasons,
        "policy_version": policy["policy_version"],
        "policy_layer_type": policy["layer_type"],
        "no_frozen_test_access": bool(policy["no_frozen_test_access"]),
        "conditional_pass": bool(policy["conditional_pass"]),
        "requested_layer_status": requested_layer_status,
        "declared_no_frozen_test_access": normalized_request["declared_no_frozen_test_access"],
        "declared_conditional_pass": normalized_request["declared_conditional_pass"],
        "allow_silent_fallback": normalized_request["allow_silent_fallback"],
        "audit_time": audit_time,
    }


def build_stdout_summary(audit: dict[str, Any], output_json_path: Path) -> str:
    lines = [
        f"status={audit['status']}",
        f"consumer_name={audit['consumer_name']}",
        f"intended_use={audit['intended_use']}",
        f"allowed_fields_used={len(audit['allowed_fields_used'])}",
        "blocked_fields_requested="
        + (", ".join(audit["blocked_fields_requested"]) if audit["blocked_fields_requested"] else "none"),
        "unknown_fields_requested="
        + (", ".join(audit["unknown_fields_requested"]) if audit["unknown_fields_requested"] else "none"),
        "fail_fast_reasons="
        + (" | ".join(audit["fail_fast_reasons"]) if audit["fail_fast_reasons"] else "none"),
        f"audit_json={output_json_path}",
    ]
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    if not args.request_json.exists():
        raise NextUseValidationError(f"request JSON not found: {args.request_json}")

    policy = load_next_use_policy(
        policy_path=args.policy_json.resolve(),
        policy_schema_path=args.policy_schema.resolve(),
    )
    request = load_json(args.request_json.resolve())
    audit = validate_next_use_request(policy, request)
    write_json(args.output_json.resolve(), audit)
    print(build_stdout_summary(audit, args.output_json.resolve()))
    return 0 if audit["status"] == "pass" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NextUseValidationError as exc:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "error": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        raise SystemExit(1)
