# Data Enrichment Next-Use Downstream Integration

This record upgrades `data_field_enrichment_v1` next-use governance from a standalone validation tool into a downstream integration pattern. It does not approve alpha, does not approve a strategy, is not OOS, and does not authorize frozen test access.

## Guardrail Pattern

Any downstream script that uses `data_field_enrichment_v1` fields must declare:

- `requested_fields`
- `intended_use`
- `consumer_name`
- `run_scope`
- `declared_no_frozen_test_access`
- `declared_conditional_pass`
- `requested_layer_status`
- `allow_silent_fallback`

The script must call `scripts/data_enrichment_next_use_guardrail_adapter.py` before consuming those fields and must write a next-use audit JSON. A non-`pass` audit must fail fast before downstream diagnostic, clean baseline, or challenger preparation logic continues.

Scripts that do not use enrichment fields may declare `requested_fields=[]`, but they still write an audit so the absence of enrichment consumption is explicit.

## Current Policy Boundaries

`data_field_enrichment_v1` remains a conditional enrichment layer. `conditional_pass` must be disclosed and must not be promoted to full pass. In plain terms, conditional_pass must be disclosed by every downstream consumer.

Blocked fields remain blocked:

- `listing_age_trading_days`
- `newly_listed_flag`

The following conditions must fail fast:

- Blocked fields entering any downstream path.
- Unknown fields in `requested_fields`.
- `portfolio` or `screening` as `intended_use`.
- `declared_no_frozen_test_access=false`.
- Missing or false `declared_conditional_pass`.
- `allow_silent_fallback=true`.
- Any attempt to claim `requested_layer_status=full_pass`.

Silent fallback is not allowed. In particular, calendar-day fields or proxies must not be silently substituted for blocked trading-day fields.

## Integrated Entrypoints

The following diagnostic entrypoints now call the adapter before their original logic:

- `scripts/diagnose_baseline_divergence_exposure.py`
- `scripts/diagnose_clean_baseline_family_model_edge.py`

Both default to `requested_fields=[]` because their current diagnostic inputs do not consume `data_field_enrichment_v1` fields directly. They expose `--enrichment-requested-fields` for explicit declarations and `--next-use-audit-path` for audit output.

The reference integration consumer is:

- `scripts/example_data_enrichment_guarded_diagnostic.py`

It reads a request JSON, calls the adapter, and only then runs a dummy diagnostic. It exists only to prove the integration pattern and is not a real strategy, alpha, backtest, portfolio process, or formal metrics/readout.

## Downstream Requirement

Future clean baseline or challenger scripts that consume enrichment fields must pass through `require_data_enrichment_next_use(...)` or `validate_next_use_request(...)` before use. They may only use policy-allowed D0 state fields, must keep `no_frozen_test_access=true`, must disclose the conditional layer status, and must write the next-use audit path in their outputs.
