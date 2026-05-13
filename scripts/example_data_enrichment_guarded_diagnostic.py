#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.data_enrichment_next_use_guardrail_adapter import validate_next_use_request
except ModuleNotFoundError:
    adapter_path = Path(__file__).with_name("data_enrichment_next_use_guardrail_adapter.py")
    spec = importlib.util.spec_from_file_location("data_enrichment_next_use_guardrail_adapter", adapter_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load guardrail adapter from {adapter_path}")
    adapter_module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("data_enrichment_next_use_guardrail_adapter", adapter_module)
    spec.loader.exec_module(adapter_module)
    validate_next_use_request = adapter_module.validate_next_use_request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reference diagnostic showing data_field_enrichment_v1 next-use guardrail integration."
    )
    parser.add_argument("--request-json", type=Path, required=True)
    parser.add_argument("--next-use-audit-path", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"request JSON must be an object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_guarded_diagnostic(args: argparse.Namespace) -> dict[str, Any]:
    request = load_json(args.request_json)
    audit = validate_next_use_request(
        request,
        audit_json=args.next_use_audit_path,
    )
    return {
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "diagnostic_only": True,
        "reference_consumer_only": True,
        "dummy_diagnostic_executed": True,
        "training_performed": False,
        "backtest_run": False,
        "portfolio_run_executed": False,
        "frozen_test_accessed": False,
        "formal_metrics_generated": False,
        "next_use_audit_path": args.next_use_audit_path.as_posix(),
        "data_enrichment_next_use": audit,
    }


def main() -> None:
    args = parse_args()
    payload = run_guarded_diagnostic(args)
    write_json(args.output_json, payload)


if __name__ == "__main__":
    main()
