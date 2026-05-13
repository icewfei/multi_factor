#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA_PATH = ROOT / "schemas" / "guarded_research_request.schema.json"

try:
    from scripts.data_enrichment_next_use_guardrail_adapter import (
        DataEnrichmentNextUseGuardrailError,
        validate_next_use_request,
    )
except ModuleNotFoundError:
    adapter_path = Path(__file__).with_name("data_enrichment_next_use_guardrail_adapter.py")
    spec = importlib.util.spec_from_file_location("data_enrichment_next_use_guardrail_adapter", adapter_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load guardrail adapter from {adapter_path}")
    adapter_module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("data_enrichment_next_use_guardrail_adapter", adapter_module)
    spec.loader.exec_module(adapter_module)
    DataEnrichmentNextUseGuardrailError = adapter_module.DataEnrichmentNextUseGuardrailError
    validate_next_use_request = adapter_module.validate_next_use_request


TASK_TYPE_TO_INTENDED_USE = {
    "diagnostic": "diagnostic",
    "clean_baseline_score": "clean_baseline",
    "challenger_prep": "challenger",
    "portfolio": "portfolio",
    "screening": "screening",
}
DISPATCHABLE_TASK_TYPES = {"diagnostic", "clean_baseline_score"}


class GuardedResearchTaskError(RuntimeError):
    """Raised when the guarded runner blocks or cannot execute a request."""

    def __init__(self, audit: dict[str, Any]) -> None:
        reason = audit.get("blocked_reason") or "guarded research task blocked"
        super().__init__(reason)
        self.audit = audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a research task behind data enrichment next-use guardrails.")
    parser.add_argument("--request-json", type=Path, required=True)
    parser.add_argument("--schema-json", type=Path, default=DEFAULT_SCHEMA_PATH)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON payload must be an object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def validate_request_schema(request: dict[str, Any], schema_path: Path) -> dict[str, Any]:
    schema = load_json(schema_path)
    jsonschema.validate(request, schema)
    return {
        "status": "pass",
        "schema_path": schema_path.resolve().as_posix(),
    }


def build_next_use_request(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "requested_fields": request["requested_enrichment_fields"],
        "intended_use": TASK_TYPE_TO_INTENDED_USE[request["task_type"]],
        "consumer_name": request["consumer_name"],
        "run_scope": request["run_scope"],
        "declared_no_frozen_test_access": request["declared_no_frozen_test_access"],
        "declared_conditional_pass": request["declared_conditional_pass"],
        "requested_layer_status": request["requested_layer_status"],
        "allow_silent_fallback": request["allow_silent_fallback"],
    }


def build_base_audit(
    *,
    request: dict[str, Any] | None,
    request_path: Path,
    schema_path: Path,
    request_validation: dict[str, Any],
) -> dict[str, Any]:
    return {
        "generated_at_utc": utc_now(),
        "runner": "run_guarded_research_task",
        "request_path": request_path.resolve().as_posix(),
        "schema_path": schema_path.resolve().as_posix(),
        "request_validation": request_validation,
        "task_id": request.get("task_id") if request else None,
        "consumer_name": request.get("consumer_name") if request else None,
        "task_type": request.get("task_type") if request else None,
        "run_scope": request.get("run_scope") if request else None,
        "requested_enrichment_fields": request.get("requested_enrichment_fields") if request else None,
        "next_use_guardrail_audit": None,
        "task_executed": False,
        "task_result": None,
        "blocked_reason": None,
        "no_frozen_test_access": False,
        "training_performed": False,
        "backtest_run": False,
        "portfolio_run_executed": False,
        "formal_metrics_generated": False,
        "holdings_generated": False,
        "backtest_daily_generated": False,
    }


def dispatch_example_diagnostic(request: dict[str, Any]) -> dict[str, Any]:
    payload = request["task_payload"]
    marker_path = payload.get("marker_path")
    if marker_path:
        write_json(
            Path(marker_path),
            {
                "task_id": request["task_id"],
                "task_type": request["task_type"],
                "dummy_diagnostic_executed": True,
                "frozen_test_accessed": False,
            },
        )
    return {
        "dispatch": "example_diagnostic",
        "dummy_diagnostic_executed": True,
        "frozen_test_accessed": False,
    }


def dispatch_clean_baseline_score_noop(request: dict[str, Any]) -> dict[str, Any]:
    payload = request["task_payload"]
    marker_path = payload.get("marker_path")
    if marker_path:
        write_json(
            Path(marker_path),
            {
                "task_id": request["task_id"],
                "task_type": request["task_type"],
                "clean_baseline_score_dry_dispatch": True,
                "builder_invoked": False,
                "frozen_test_accessed": False,
            },
        )
    return {
        "dispatch": "clean_baseline_score_dry_noop",
        "clean_baseline_score_dry_dispatch": True,
        "builder_invoked": False,
        "frozen_test_accessed": False,
    }


def dispatch_task(request: dict[str, Any]) -> dict[str, Any]:
    task_type = request["task_type"]
    if task_type not in DISPATCHABLE_TASK_TYPES:
        raise ValueError(f"task_type not dispatchable by current guarded runner: {task_type}")
    if task_type == "diagnostic":
        return dispatch_example_diagnostic(request)
    if task_type == "clean_baseline_score":
        return dispatch_clean_baseline_score_noop(request)
    raise ValueError(f"unsupported task_type: {task_type}")


def run_guarded_research_task(request_path: Path, *, schema_path: Path = DEFAULT_SCHEMA_PATH) -> dict[str, Any]:
    request: dict[str, Any] | None = None
    output_audit_path: Path | None = None
    try:
        request = load_json(request_path)
        output_audit_path = Path(request.get("output_audit_path", ""))
        request_validation = validate_request_schema(request, schema_path)
        audit = build_base_audit(
            request=request,
            request_path=request_path,
            schema_path=schema_path,
            request_validation=request_validation,
        )
    except Exception as exc:
        request_validation = {"status": "blocked", "error": str(exc)}
        audit = build_base_audit(
            request=request,
            request_path=request_path,
            schema_path=schema_path,
            request_validation=request_validation,
        )
        audit["blocked_reason"] = f"request_validation_failed: {exc}"
        if output_audit_path is not None and str(output_audit_path):
            write_json(output_audit_path, audit)
        raise GuardedResearchTaskError(audit) from exc

    try:
        next_use_audit = validate_next_use_request(build_next_use_request(request))
        audit["next_use_guardrail_audit"] = next_use_audit
        audit["no_frozen_test_access"] = bool(next_use_audit["no_frozen_test_access"])
    except DataEnrichmentNextUseGuardrailError as exc:
        audit["next_use_guardrail_audit"] = exc.audit
        audit["no_frozen_test_access"] = bool(exc.audit.get("no_frozen_test_access") is True)
        audit["blocked_reason"] = "; ".join(exc.audit.get("fail_fast_reasons") or [str(exc)])
        write_json(Path(request["output_audit_path"]), audit)
        raise GuardedResearchTaskError(audit) from exc

    try:
        audit["task_result"] = dispatch_task(request)
        audit["task_executed"] = True
    except Exception as exc:
        audit["blocked_reason"] = f"task_dispatch_failed: {exc}"
        write_json(Path(request["output_audit_path"]), audit)
        raise GuardedResearchTaskError(audit) from exc

    write_json(Path(request["output_audit_path"]), audit)
    return audit


def main() -> int:
    args = parse_args()
    run_guarded_research_task(args.request_json, schema_path=args.schema_json)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GuardedResearchTaskError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
