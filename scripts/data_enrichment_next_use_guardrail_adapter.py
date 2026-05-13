#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY_PATH = ROOT / "configs" / "data_field_enrichment" / "enrichment_next_use_policy_v1.json"
DEFAULT_POLICY_SCHEMA_PATH = ROOT / "schemas" / "data_field_enrichment_next_use_policy.schema.json"


def _load_validator_module() -> Any:
    try:
        import validate_data_enrichment_next_use as validator  # type: ignore[import-not-found]

        return validator
    except ModuleNotFoundError:
        module_path = Path(__file__).with_name("validate_data_enrichment_next_use.py")
        spec = importlib.util.spec_from_file_location("validate_data_enrichment_next_use", module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load validator module from {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules.setdefault("validate_data_enrichment_next_use", module)
        spec.loader.exec_module(module)
        return module


_VALIDATOR = _load_validator_module()
NextUseValidationError = _VALIDATOR.NextUseValidationError


class DataEnrichmentNextUseGuardrailError(RuntimeError):
    """Raised when a downstream enrichment request is blocked by policy."""

    def __init__(self, audit: dict[str, Any]) -> None:
        reasons = audit.get("fail_fast_reasons") or ["data enrichment next-use guardrail blocked request"]
        super().__init__("; ".join(str(reason) for reason in reasons))
        self.audit = audit


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_next_use_request(
    *,
    requested_fields: list[str],
    intended_use: str,
    consumer_name: str,
    run_scope: str,
    declared_no_frozen_test_access: bool,
    declared_conditional_pass: bool,
    requested_layer_status: str | None,
    allow_silent_fallback: bool,
) -> dict[str, Any]:
    request: dict[str, Any] = {
        "requested_fields": requested_fields,
        "intended_use": intended_use,
        "consumer_name": consumer_name,
        "run_scope": run_scope,
        "declared_no_frozen_test_access": declared_no_frozen_test_access,
        "declared_conditional_pass": declared_conditional_pass,
        "allow_silent_fallback": allow_silent_fallback,
    }
    if requested_layer_status is not None:
        request["requested_layer_status"] = requested_layer_status
    return request


def validate_next_use_request(
    request: dict[str, Any],
    *,
    policy_json: Path = DEFAULT_POLICY_PATH,
    policy_schema: Path = DEFAULT_POLICY_SCHEMA_PATH,
    audit_json: Path | None = None,
) -> dict[str, Any]:
    policy = _VALIDATOR.load_next_use_policy(policy_json.resolve(), policy_schema.resolve())
    audit = _VALIDATOR.validate_next_use_request(policy, request)
    if audit_json is not None:
        write_json(audit_json.resolve(), audit)
    if audit["status"] != "pass":
        raise DataEnrichmentNextUseGuardrailError(audit)
    return audit


def require_data_enrichment_next_use(
    *,
    requested_fields: list[str],
    intended_use: str,
    consumer_name: str,
    run_scope: str,
    declared_no_frozen_test_access: bool = True,
    declared_conditional_pass: bool = True,
    requested_layer_status: str | None = "conditional_pass",
    allow_silent_fallback: bool = False,
    audit_json: Path | None = None,
    policy_json: Path = DEFAULT_POLICY_PATH,
    policy_schema: Path = DEFAULT_POLICY_SCHEMA_PATH,
) -> dict[str, Any]:
    request = build_next_use_request(
        requested_fields=requested_fields,
        intended_use=intended_use,
        consumer_name=consumer_name,
        run_scope=run_scope,
        declared_no_frozen_test_access=declared_no_frozen_test_access,
        declared_conditional_pass=declared_conditional_pass,
        requested_layer_status=requested_layer_status,
        allow_silent_fallback=allow_silent_fallback,
    )
    return validate_next_use_request(
        request,
        policy_json=policy_json,
        policy_schema=policy_schema,
        audit_json=audit_json,
    )
