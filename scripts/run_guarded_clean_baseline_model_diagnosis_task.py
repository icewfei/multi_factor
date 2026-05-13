#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import jsonschema
import pandas as pd


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run guarded clean baseline model-layer diagnosis for a single score artifact."
    )
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


def require_payload_string(payload: dict[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"task_payload.{field_name} must be a non-empty string")
    return value.strip()


def build_next_use_request(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "requested_fields": request["requested_enrichment_fields"],
        "intended_use": "diagnostic",
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
        "runner": "run_guarded_clean_baseline_model_diagnosis_task",
        "request_path": request_path.resolve().as_posix(),
        "schema_path": schema_path.resolve().as_posix(),
        "task_id": request.get("task_id") if request else None,
        "consumer_name": request.get("consumer_name") if request else None,
        "task_type": request.get("task_type") if request else None,
        "run_scope": request.get("run_scope") if request else None,
        "requested_enrichment_fields": request.get("requested_enrichment_fields") if request else None,
        "baseline_id": payload.get("baseline_id"),
        "request_validation": None,
        "next_use_guardrail_audit": None,
        "guardrail_status": None,
        "diagnosis_invoked": False,
        "task_executed": False,
        "blocked_reason": None,
        "diagnosis_metrics": None,
        "output_paths": {},
        "no_frozen_test_access": False,
        "portfolio_ran": False,
        "portfolio_run_executed": False,
        "formal_metrics_generated": False,
        "training_performed": False,
        "backtest_run": False,
        "not_oos": True,
    }


def read_joined_frame(
    *,
    score_path: Path,
    label_panel_path: Path,
    split_panel_path: Path,
    baseline_id: str,
    label_column: str,
) -> pd.DataFrame:
    con = duckdb.connect()
    try:
        query = f"""
        WITH score_t AS (
            SELECT snapshot_id, instrument, signal_date, candidate_scheme_id, model_score_D0
            FROM read_parquet(?)
            WHERE candidate_scheme_id = ?
        ),
        label_t AS (
            SELECT snapshot_id, instrument, signal_date, {label_column} AS forward_return
            FROM read_parquet(?)
            WHERE COALESCE(label_defined, TRUE)
        ),
        split_t AS (
            SELECT DISTINCT
                snapshot_id,
                instrument,
                signal_date,
                split_bucket
            FROM read_parquet(?)
        )
        SELECT
            s.snapshot_id,
            s.instrument,
            s.signal_date,
            s.model_score_D0,
            l.forward_return,
            sp.split_bucket
        FROM score_t s
        INNER JOIN label_t l
          USING (snapshot_id, instrument, signal_date)
        INNER JOIN split_t sp
          USING (snapshot_id, instrument, signal_date)
        WHERE sp.split_bucket IN ('train', 'validation')
          AND s.model_score_D0 IS NOT NULL
          AND l.forward_return IS NOT NULL
        """
        return con.execute(
            query,
            [
                score_path.as_posix(),
                baseline_id,
                label_panel_path.as_posix(),
                split_panel_path.as_posix(),
            ],
        ).df()
    finally:
        con.close()


def split_metrics(frame: pd.DataFrame, *, topk: int, score_order: str) -> dict[str, Any]:
    if frame.empty:
        return {
            "coverage": {"rows": 0, "dates": 0, "instruments": 0},
            "rank_ic": None,
            "icir": None,
            "top_bottom": None,
            "topk_proxy": None,
        }

    rank_ics: list[float] = []
    top_returns: list[float] = []
    bottom_returns: list[float] = []
    for _, day in frame.groupby("signal_date"):
        if day["model_score_D0"].nunique() < 2 or day["forward_return"].nunique() < 2:
            continue
        rank_ics.append(float(day["model_score_D0"].corr(day["forward_return"], method="spearman")))
        ordered = day.sort_values("model_score_D0", ascending=(score_order == "ascending"))
        top_returns.append(float(ordered.head(topk)["forward_return"].mean()))
        bottom_returns.append(float(ordered.tail(topk)["forward_return"].mean()))

    rank_ic_mean = float(pd.Series(rank_ics).mean()) if rank_ics else None
    rank_ic_std = float(pd.Series(rank_ics).std()) if len(rank_ics) > 1 else None
    icir = rank_ic_mean / rank_ic_std if rank_ic_mean is not None and rank_ic_std not in (None, 0.0) else None
    top_mean = float(pd.Series(top_returns).mean()) if top_returns else None
    bottom_mean = float(pd.Series(bottom_returns).mean()) if bottom_returns else None
    return {
        "coverage": {
            "rows": int(len(frame)),
            "dates": int(frame["signal_date"].nunique()),
            "instruments": int(frame["instrument"].nunique()),
        },
        "rank_ic": {
            "mean": rank_ic_mean,
            "daily_count": len(rank_ics),
        },
        "icir": icir,
        "top_bottom": {
            "top_mean_forward_return": top_mean,
            "bottom_mean_forward_return": bottom_mean,
            "spread": top_mean - bottom_mean if top_mean is not None and bottom_mean is not None else None,
        },
        "topk_proxy": {
            "topk": int(topk),
            "avg_topk_forward_return": top_mean,
        },
    }


def compute_diagnosis_metrics(request: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    payload = request["task_payload"]
    baseline_id = require_payload_string(payload, "baseline_id")
    score_path = Path(require_payload_string(payload, "score_path"))
    label_panel_path = Path(require_payload_string(payload, "label_panel_path"))
    split_panel_path = Path(require_payload_string(payload, "split_panel_path"))
    label_column = str(payload.get("label_column") or "label_5d_next_open_close")
    score_order = str(payload.get("score_order") or "ascending")
    topk = int(payload.get("topk") or 10)

    frame = read_joined_frame(
        score_path=score_path,
        label_panel_path=label_panel_path,
        split_panel_path=split_panel_path,
        baseline_id=baseline_id,
        label_column=label_column,
    )
    metrics = {
        "baseline_id": baseline_id,
        "metric_scope": "model_layer_trainval_diagnosis_only",
        "score_order": score_order,
        "splits": {
            split: split_metrics(frame[frame["split_bucket"] == split], topk=topk, score_order=score_order)
            for split in ("train", "validation")
        },
        "no_frozen_test_access": True,
        "portfolio_ran": False,
        "formal_metrics_generated": False,
        "not_oos": True,
    }
    output_paths = {
        "score_path": score_path.as_posix(),
        "label_panel_path": label_panel_path.as_posix(),
        "split_panel_path": split_panel_path.as_posix(),
    }
    return metrics, output_paths


def run_guarded_model_diagnosis(request_path: Path, *, schema_path: Path = DEFAULT_SCHEMA_PATH) -> dict[str, Any]:
    request: dict[str, Any] | None = None
    output_audit_path: Path | None = None
    try:
        request = load_json(request_path)
        output_audit_path = Path(request.get("output_audit_path", ""))
        schema = load_json(schema_path)
        jsonschema.validate(request, schema)
        audit = base_audit(request, request_path, schema_path)
        audit["request_validation"] = {"status": "pass", "schema_path": schema_path.resolve().as_posix()}
    except Exception as exc:
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

    metrics, input_paths = compute_diagnosis_metrics(request)
    audit["diagnosis_metrics"] = metrics
    audit["output_paths"] = input_paths | {"diagnosis_audit_path": request["output_audit_path"]}
    audit["diagnosis_invoked"] = True
    audit["task_executed"] = True
    audit["baseline_id"] = metrics["baseline_id"]
    audit["no_frozen_test_access"] = True
    write_json(Path(request["output_audit_path"]), audit)
    return audit


def main() -> int:
    args = parse_args()
    run_guarded_model_diagnosis(args.request_json, schema_path=args.schema_json)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
