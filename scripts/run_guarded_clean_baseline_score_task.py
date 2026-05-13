#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


try:
    from scripts.run_guarded_research_task import GuardedResearchTaskError, run_guarded_research_task, write_json
except ModuleNotFoundError:
    runner_path = Path(__file__).with_name("run_guarded_research_task.py")
    spec = importlib.util.spec_from_file_location("run_guarded_research_task", runner_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load guarded research runner from {runner_path}")
    runner_module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("run_guarded_research_task", runner_module)
    spec.loader.exec_module(runner_module)
    GuardedResearchTaskError = runner_module.GuardedResearchTaskError
    run_guarded_research_task = runner_module.run_guarded_research_task
    write_json = runner_module.write_json


class GuardedCleanBaselineScoreTaskError(RuntimeError):
    """Raised when a clean baseline score request is invalid for this wrapper."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a clean baseline score dry task through the guarded research runner."
    )
    parser.add_argument("--request-json", type=Path, required=True)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"request JSON must be an object: {path}")
    return payload


def require_clean_baseline_score_request(request_path: Path) -> None:
    request = load_json(request_path)
    if request.get("task_type") != "clean_baseline_score":
        audit_path = request.get("output_audit_path")
        if isinstance(audit_path, str) and audit_path:
            write_json(
                Path(audit_path),
                {
                    "runner": "run_guarded_clean_baseline_score_task",
                    "task_type": request.get("task_type"),
                    "task_executed": False,
                    "blocked_reason": "wrapper_requires_task_type_clean_baseline_score",
                    "no_frozen_test_access": False,
                    "training_performed": False,
                    "backtest_run": False,
                    "portfolio_run_executed": False,
                    "formal_metrics_generated": False,
                },
            )
        raise GuardedCleanBaselineScoreTaskError("wrapper requires task_type=clean_baseline_score")


def main() -> int:
    args = parse_args()
    require_clean_baseline_score_request(args.request_json)
    run_guarded_research_task(args.request_json)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (GuardedCleanBaselineScoreTaskError, GuardedResearchTaskError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
