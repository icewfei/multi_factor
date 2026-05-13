# Guarded Clean Baseline Workflow V1 Decision Record

`guarded_clean_baseline_research_workflow_v1` is implemented as the controlled path for clean baseline score generation and model-layer diagnosis.

This workflow is not alpha, not strategy approval, not OOS, and not frozen test evidence. It does not modify clean baseline definitions and does not design a new strategy.

## Implemented Chain

The workflow executes in this order:

- Request schema validation.
- `data_field_enrichment_v1` next-use guardrail.
- Guarded clean baseline score builder dispatch.
- Score artifact audit.
- Guarded model-layer diagnosis.
- Workflow-level audit.

Guardrail pass is required before the score builder is allowed to run. Guardrail pass is also required before model-layer diagnosis is allowed to run.

## Blocking Rules

Blocked fields stop the entire workflow before score or diagnosis artifacts are generated:

- `listing_age_trading_days`
- `newly_listed_flag`

Unknown enrichment fields also stop execution. `portfolio` and `screening` remain blocked. Silent fallback is not allowed, and `conditional_pass` must not be promoted to full pass.

## Outputs

Allowed workflow requests produce:

- `workflow_audit.json`
- `model_scores_D0.parquet`
- `model_scores_D0_audit.json`
- `source_chain_audit.json`
- guarded model-layer diagnosis audit

The model-layer diagnosis is trainval-only and reports RankIC, ICIR, top-bottom, coverage, and TopK proxy diagnostics. These are model-layer diagnostic values only, not formal strategy metrics or readouts.

## Hard Boundaries

The workflow does not train ML models, does not run backtests, does not run portfolio construction, does not generate holdings, does not generate `backtest_daily`, and does not generate formal metrics/readout.

No frozen test access is allowed. The workflow audit records `no_frozen_test_access=true`, `portfolio_ran=false`, `formal_metrics_generated=false`, and `not_oos=true`.

Future baseline and challenger research that consumes `data_field_enrichment_v1` fields should migrate to this guarded workflow or an equivalent guarded workflow entrypoint.
