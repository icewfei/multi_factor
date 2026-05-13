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
    from scripts.run_guarded_clean_baseline_model_diagnosis_task import run_guarded_model_diagnosis
    from scripts.run_guarded_research_task import run_guarded_research_task, write_json
except ModuleNotFoundError:
    adapter_path = Path(__file__).with_name("data_enrichment_next_use_guardrail_adapter.py")
    adapter_spec = importlib.util.spec_from_file_location("data_enrichment_next_use_guardrail_adapter", adapter_path)
    if adapter_spec is None or adapter_spec.loader is None:
        raise ImportError(f"Unable to load guardrail adapter from {adapter_path}")
    adapter_module = importlib.util.module_from_spec(adapter_spec)
    sys.modules.setdefault("data_enrichment_next_use_guardrail_adapter", adapter_module)
    adapter_spec.loader.exec_module(adapter_module)
    DataEnrichmentNextUseGuardrailError = adapter_module.DataEnrichmentNextUseGuardrailError
    validate_next_use_request = adapter_module.validate_next_use_request

    runner_path = Path(__file__).with_name("run_guarded_research_task.py")
    runner_spec = importlib.util.spec_from_file_location("run_guarded_research_task", runner_path)
    if runner_spec is None or runner_spec.loader is None:
        raise ImportError(f"Unable to load guarded runner from {runner_path}")
    runner_module = importlib.util.module_from_spec(runner_spec)
    sys.modules.setdefault("run_guarded_research_task", runner_module)
    runner_spec.loader.exec_module(runner_module)
    run_guarded_research_task = runner_module.run_guarded_research_task
    write_json = runner_module.write_json

    diagnosis_path = Path(__file__).with_name("run_guarded_clean_baseline_model_diagnosis_task.py")
    diagnosis_spec = importlib.util.spec_from_file_location(
        "run_guarded_clean_baseline_model_diagnosis_task",
        diagnosis_path,
    )
    if diagnosis_spec is None or diagnosis_spec.loader is None:
        raise ImportError(f"Unable to load guarded diagnosis runner from {diagnosis_path}")
    diagnosis_module = importlib.util.module_from_spec(diagnosis_spec)
    sys.modules.setdefault("run_guarded_clean_baseline_model_diagnosis_task", diagnosis_module)
    diagnosis_spec.loader.exec_module(diagnosis_module)
    run_guarded_model_diagnosis = diagnosis_module.run_guarded_model_diagnosis


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run guarded clean baseline research workflow v1.")
    parser.add_argument("--request-json", type=Path, required=True)
    parser.add_argument("--schema-json", type=Path, default=DEFAULT_SCHEMA_PATH)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON payload must be an object: {path}")
    return payload


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def require_payload_string(payload: dict[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"task_payload.{field_name} must be a non-empty string")
    return value.strip()


def build_next_use_request(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "requested_fields": request["requested_enrichment_fields"],
        "intended_use": "clean_baseline",
        "consumer_name": request["consumer_name"],
        "run_scope": request["run_scope"],
        "declared_no_frozen_test_access": request["declared_no_frozen_test_access"],
        "declared_conditional_pass": request["declared_conditional_pass"],
        "requested_layer_status": request["requested_layer_status"],
        "allow_silent_fallback": request["allow_silent_fallback"],
    }


def base_audit(request: dict[str, Any] | None, request_path: Path, schema_path: Path) -> dict[str, Any]:
    payload = request.get("task_payload", {}) if request else {}
    return {
        "generated_at_utc": utc_now(),
        "runner": "run_guarded_clean_baseline_research_workflow",
        "workflow_version": "guarded_clean_baseline_research_workflow_v1",
        "request_path": request_path.resolve().as_posix(),
        "schema_path": schema_path.resolve().as_posix(),
        "task_id": request.get("task_id") if request else None,
        "consumer_name": request.get("consumer_name") if request else None,
        "run_scope": request.get("run_scope") if request else None,
        "requested_enrichment_fields": request.get("requested_enrichment_fields") if request else None,
        "baseline_id": payload.get("baseline_id"),
        "request_validation": None,
        "next_use_guardrail_audit": None,
        "guardrail_status": None,
        "workflow_executed": False,
        "score_builder_invoked": False,
        "diagnosis_invoked": False,
        "blocked_reason": None,
        "score_task_audit": None,
        "diagnosis_task_audit": None,
        "score_artifact_paths": {},
        "diagnosis_artifact_paths": {},
        "no_frozen_test_access": False,
        "training_performed": False,
        "backtest_run": False,
        "portfolio_ran": False,
        "portfolio_run_executed": False,
        "formal_metrics_generated": False,
        "holdings_generated": False,
        "backtest_daily_generated": False,
        "not_oos": True,
    }


def child_request_common(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "consumer_name": request["consumer_name"],
        "run_scope": request["run_scope"],
        "requested_enrichment_fields": request["requested_enrichment_fields"],
        "declared_no_frozen_test_access": request["declared_no_frozen_test_access"],
        "declared_conditional_pass": request["declared_conditional_pass"],
        "requested_layer_status": request["requested_layer_status"],
        "allow_silent_fallback": request["allow_silent_fallback"],
    }


def run_guarded_clean_baseline_workflow(
    request_path: Path,
    *,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
) -> dict[str, Any]:
    request: dict[str, Any] | None = None
    output_audit_path: Path | None = None
    try:
        request = load_json(request_path)
        output_audit_path = Path(request.get("output_audit_path", ""))
        schema = load_json(schema_path)
        jsonschema.validate(request, schema)
        audit = base_audit(request, request_path, schema_path)
        audit["request_validation"] = {"status": "pass", "schema_path": schema_path.resolve().as_posix()}
        if request.get("task_type") != "clean_baseline_score":
            audit["blocked_reason"] = "workflow_requires_task_type_clean_baseline_score"
            write_json(Path(request["output_audit_path"]), audit)
            raise RuntimeError(audit["blocked_reason"])
    except Exception as exc:
        if "audit" in locals() and audit.get("blocked_reason"):
            raise
        audit = base_audit(request, request_path, schema_path)
        audit["request_validation"] = {"status": "blocked", "error": str(exc)}
        audit["blocked_reason"] = f"request_validation_failed: {exc}"
        if output_audit_path is not None and str(output_audit_path):
            write_json(output_audit_path, audit)
        raise RuntimeError(audit["blocked_reason"]) from exc

    try:
        guardrail_audit = validate_next_use_request(build_next_use_request(request))
        audit["next_use_guardrail_audit"] = guardrail_audit
        audit["guardrail_status"] = guardrail_audit["status"]
        audit["no_frozen_test_access"] = bool(guardrail_audit["no_frozen_test_access"])
    except DataEnrichmentNextUseGuardrailError as exc:
        audit["next_use_guardrail_audit"] = exc.audit
        audit["guardrail_status"] = exc.audit.get("status")
        audit["no_frozen_test_access"] = bool(exc.audit.get("no_frozen_test_access") is True)
        audit["blocked_reason"] = "; ".join(exc.audit.get("fail_fast_reasons") or [str(exc)])
        write_json(Path(request["output_audit_path"]), audit)
        raise RuntimeError(audit["blocked_reason"]) from exc

    payload = request["task_payload"]
    baseline_id = require_payload_string(payload, "baseline_id")
    workflow_dir = Path(str(payload.get("workflow_dir") or Path(require_payload_string(payload, "output_dir")).parent))
    workflow_dir.mkdir(parents=True, exist_ok=True)
    score_output_dir = Path(require_payload_string(payload, "output_dir"))
    score_audit_path = workflow_dir / "score_task_audit.json"
    diagnosis_audit_path = workflow_dir / "model_layer_diagnosis_audit.json"
    score_request_path = workflow_dir / "score_task_request.json"
    diagnosis_request_path = workflow_dir / "model_layer_diagnosis_request.json"

    score_payload = {
        "baseline_id": baseline_id,
        "clean_sample_panel_path": require_payload_string(payload, "clean_sample_panel_path"),
        "output_dir": score_output_dir.as_posix(),
        "attempt_id": str(payload.get("attempt_id") or "attempt_guarded_workflow_score"),
    }
    for optional_field in ("run_input_contract_path", "snapshot_root_path", "warehouse_db_path", "snapshot_id"):
        if optional_field in payload:
            score_payload[optional_field] = payload[optional_field]
    score_request = {
        "task_id": f"{request['task_id']}_score",
        "task_type": "clean_baseline_score",
        "output_audit_path": score_audit_path.as_posix(),
        "task_payload": score_payload,
    } | child_request_common(request)
    write_json(score_request_path, score_request)
    score_audit = run_guarded_research_task(score_request_path, schema_path=schema_path)
    audit["score_task_audit"] = score_audit
    audit["score_builder_invoked"] = bool(score_audit["builder_invoked"])
    audit["score_artifact_paths"] = score_audit["output_paths"]

    diagnosis_payload = {
        "baseline_id": baseline_id,
        "score_path": score_audit["output_paths"]["score_output_path"],
        "label_panel_path": require_payload_string(payload, "label_panel_path"),
        "split_panel_path": require_payload_string(payload, "split_panel_path"),
        "topk": int(payload.get("topk") or 10),
        "score_order": str(payload.get("score_order") or "ascending"),
    }
    if "label_column" in payload:
        diagnosis_payload["label_column"] = payload["label_column"]
    diagnosis_request = {
        "task_id": f"{request['task_id']}_diagnosis",
        "task_type": "diagnostic",
        "output_audit_path": diagnosis_audit_path.as_posix(),
        "task_payload": diagnosis_payload,
    } | child_request_common(request)
    write_json(diagnosis_request_path, diagnosis_request)
    diagnosis_audit = run_guarded_model_diagnosis(diagnosis_request_path, schema_path=schema_path)
    audit["diagnosis_task_audit"] = diagnosis_audit
    audit["diagnosis_invoked"] = bool(diagnosis_audit["diagnosis_invoked"])
    audit["diagnosis_artifact_paths"] = diagnosis_audit["output_paths"]
    audit["workflow_executed"] = True
    write_json(Path(request["output_audit_path"]), audit)
    return audit


def main() -> int:
    args = parse_args()
    run_guarded_clean_baseline_workflow(args.request_json, schema_path=args.schema_json)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
