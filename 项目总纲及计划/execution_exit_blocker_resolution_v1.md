# Execution Exit Blocker Resolution v1

**Contract:** `contracts/execution_exit_blocker_resolution.v1.json`
**Date:** 2026-05-08
**Status:** Resolution requirements only — no implementation of resolution logic.

## Purpose

This document defines how each type of execution exit blocker can be resolved. It specifies what upstream work must happen before any blocker is lifted. It does not implement any resolution logic.

## Current State

20 rows in the backtest_executable subset have `actual_exit_date=NULL`:
- 10 `terminal_event_unpriced` (delist + no pricing)
- 10 `exit_unresolved` (no exit signal, no terminal event)
- 0 `calendar_insufficient`

All 20 are hard blockers. Portfolio dry-run is blocked.

## Resolution Matrix

| Blocker | Resolution Path | Auto-Unblock | Portfolio Can Resolve |
|---|---|---|---|
| terminal_event_unpriced | terminal_pricing_policy | No | No |
| exit_unresolved | execution_path_completion | No | No |
| calendar_insufficient | calendar/tradability source repair | No | No |

### terminal_event_unpriced

Apply the `cash_settlement -> last_tradable_close -> zero_recovery` hierarchy upstream. Required fields: `terminal_event_type`, `terminal_event_date`, `terminal_exit_pricing_method`, plus layer-specific pricing fields. Resolves when the row transitions to a `terminal_priced_*` state with complete `actual_exit_date`, `actual_sell_price`, `execution_delayed_realized_return`.

### exit_unresolved

Complete the execution path upstream by determining whether the exit is a normal close, delayed sell, or missing terminal event. Required fields: `actual_exit_date`, `actual_sell_price`, `execution_delayed_realized_return`, `execution_path_status`.

### calendar_insufficient

Repair or extend trading calendar and tradability source coverage. Required: `trading_calendar_coverage`, `tradability_source_coverage`.

## Global Prohibitions

- `portfolio_workaround`: false
- `planned_exit_date_substitution_allowed`: false
- `filter_unresolved_and_continue`: false
- `silent_zero_recovery_allowed`: false
- `trainer_or_model_scores_layer_execution_blocker_handling`: false

## Recommended Implementation Order

1. **last_tradable_close auditability check** — All 10 terminal_event_unpriced rows have `last_tradable_date` but the source is `contract_degraded`. Verify auditable close prices exist.
2. **zero_recovery decision** — If step 1 fails for any row, decide whether zero_recovery is formally enabled with `terminal_exit_conservative_flag=true`.
3. **exit_unresolved investigation** — Distinguish calendar/source coverage gaps from genuinely missing exit signals.
4. **Restore portfolio dry-run** — Only after zero rows with `actual_exit_date=NULL` remain in the backtest_executable subset.
