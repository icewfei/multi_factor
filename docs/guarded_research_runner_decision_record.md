# Guarded Research Runner Decision Record

The guarded research runner is implemented as a unified research task entrypoint for `data_field_enrichment_v1` next-use governance. The next-use guardrail now sits before research task dispatch, not only before diagnostic scripts.

This record does not approve alpha, does not approve a strategy, is not OOS, and does not authorize frozen test access.

## Implemented Boundary

`scripts/run_guarded_research_task.py` reads a guarded research request JSON, validates it against `schemas/guarded_research_request.schema.json`, then calls the data enrichment next-use guardrail before task dispatch.

`scripts/run_guarded_clean_baseline_score_task.py` is a thin clean-baseline wrapper over the same runner. It requires `task_type=clean_baseline_score` and then delegates to the guarded runner, so blocked enrichment fields stop execution before any clean baseline score payload can run.

Every request must declare:

- `task_id`
- `consumer_name`
- `task_type`
- `run_scope`
- `requested_enrichment_fields`
- `declared_no_frozen_test_access`
- `declared_conditional_pass`
- `requested_layer_status`
- `allow_silent_fallback`
- `output_audit_path`
- `task_payload`

`requested_enrichment_fields=[]` is valid only when explicitly declared. This is the clean baseline score dry-dispatch path for tasks that do not consume enrichment fields.

## Current Dispatch Scope

The current runner only dispatches fixture-safe tasks:

- `diagnostic`: example diagnostic no-op dispatch
- `clean_baseline_score`: clean baseline score dry no-op dispatch

The clean baseline score task can pass with `requested_enrichment_fields=[]`. The current dry dispatch and wrapper do not invoke the clean baseline score builder, do not train, do not backtest, do not run portfolio, and do not generate holdings, `backtest_daily`, formal metrics, or readout artifacts.

Future enrichment-consuming clean baseline or challenger work must declare `requested_enrichment_fields` and pass the same guardrail before any task payload executes.

## Fail-Fast Policy

Blocked fields stop task execution:

- `listing_age_trading_days`
- `newly_listed_flag`

Unknown fields stop task execution. `portfolio` and `screening` task types are currently blocked. `conditional_pass` must be disclosed, `requested_layer_status` must not claim `full_pass`, and `allow_silent_fallback=true` is blocked.

The guarded runner writes an audit JSON containing request validation, next-use guardrail audit, `task_executed`, `blocked_reason`, and execution boundary flags. When the guardrail blocks, `task_executed=false` and `task_payload` is not dispatched.

## Non-Goals

This integration is not alpha, not strategy approval, not OOS, and not frozen test evidence. It does not modify the data enrichment policy conclusion and does not unblock `listing_age_trading_days` or `newly_listed_flag`.

No frozen test access is allowed. No training, backtest, portfolio run, holdings, `backtest_daily`, formal metrics, or readout generation is part of this stage.
