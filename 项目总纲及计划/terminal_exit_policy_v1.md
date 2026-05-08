# Terminal Exit Policy v1

**Contract:** `contracts/terminal_exit_policy.v1.json`
**Date:** 2026-05-08
**Status:** Policy contract only — no implementation of pricing or filtering.

## Purpose

This document defines the terminal pricing policy and unresolved exit handling rules for the multi-factor project. It establishes:

1. The terminal pricing hierarchy
2. State definitions for every terminal / unresolved exit case
3. Hard blocker rules dictating what must not enter portfolio
4. Portfolio consumption rules (fail-fast, no pricing)
5. The implementation boundary between upstream pricing and downstream enforcement

## Background

The current shared source `serving.vw_execution_path_daily` produces rows with `actual_exit_date=NULL` in two categories:
- **delist + no_terminal_pricing_source**: terminal event exists but no pricing was applied → `terminal_event_unpriced`
- **exit_unresolved**: no exit signal, no terminal event → `exit_unresolved`

The project design layer already specifies a `terminal_exit_pricing_hierarchy = cash_settlement -> last_tradable_close -> zero_recovery`, but this hierarchy has not been fully implemented in the shared source or project execution path.

This contract codifies the policy so that:
- All consumers agree on what each state means
- The portfolio layer can fail-fast with clear justification
- Future implementation has an unambiguous specification to target

## Terminal Pricing Hierarchy

The hierarchy is ordered — each layer is tried in sequence. A higher-ranked layer must be exhausted before falling to the next.

### Layer 1: cash_settlement

**When applicable:** An explicit `cash_settlement_amount` exists with auditable field provenance (e.g. exchange-delisted cash buyout, merger consideration).

**Requirements:**
- `cash_settlement_amount` is non-null and traceable to a verifiable source field
- The source field origin is documented and auditable

**Flag:** `terminal_exit_conservative_flag = false`

### Layer 2: last_tradable_close

**When applicable:** An auditable close price or adjusted-return basis can be sourced from the last tradable day immediately preceding the terminal event effective date.

**Requirements:**
- Close price or adjusted return is from a verifiable source (not an approximation)
- The last tradable date is confirmed by calendar and tradability data

**Flag:** `terminal_exit_conservative_flag = false`

### Layer 3: zero_recovery

**When applicable:** Only as a conservative fallback when neither cash_settlement nor last_tradable_close is available.

**Requirements:**
- Must carry `terminal_exit_conservative_flag = true`
- `actual_sell_price` is set to zero
- Must never be used as a convenience workaround or default

**Flag:** `terminal_exit_conservative_flag = true` (mandatory)

## State Definitions

| State | Meaning | Portfolio Allowed |
|---|---|---|
| `terminal_priced_cash_settlement` | Priced via cash settlement | Yes (fields complete) |
| `terminal_priced_last_tradable_close` | Priced via last tradable close | Yes (fields complete) |
| `terminal_priced_zero_recovery` | Priced via zero recovery with conservative flag | Yes (fields complete, flagged) |
| `terminal_event_unpriced` | Terminal event exists, no pricing applied | **No — hard blocker** |
| `exit_unresolved` | No exit signal, no terminal event | **No — hard blocker** |
| `calendar_insufficient` | Calendar data insufficient | **No — hard blocker** |

## Hard Blocker Rules

Three states are hard blockers. Rows in these states must not enter portfolio:

1. **terminal_event_unpriced** — A terminal event exists but no pricing was applied. Including in portfolio would create an unpriced exit and corrupt realized-return calculations.

2. **exit_unresolved** — The exit path is entirely unresolved. `actual_exit_date` is NULL and no terminal event is recorded.

3. **calendar_insufficient** — Calendar data insufficient to resolve exit timing or tradability.

## Portfolio Consumption Rules

The portfolio layer operates under strict constraints:

- **Fail-fast**: On any row where `actual_exit_date IS NULL` or `actual_sell_price IS NULL` or `execution_delayed_realized_return IS NULL`, the portfolio must fail-fast.
- **No pricing**: The portfolio layer must not determine terminal pricing.
- **No filtering**: The portfolio layer must not filter unresolved rows and continue downstream.
- **No date substitution**: `planned_exit_date` must not be used as `actual_exit_date`.

Required fields for portfolio consumption:
- `actual_exit_date`
- `actual_sell_price`
- `execution_delayed_realized_return`

## Implementation Boundary

| Concern | Owner |
|---|---|
| Terminal pricing logic | execution path / project_execution_panel upstream |
| build_project_panels.py | Passthrough or standardize only; must not invent prices |
| Zero recovery introduction | Must be a formal policy output, not a portfolio workaround |
| Portfolio enforcement | Fail-fast only; no pricing, no filtering |

Future implementation should resolve each terminal event against the pricing hierarchy in the execution path or `project_execution_panel` layer, producing complete `actual_exit_date`, `actual_sell_price`, and `execution_delayed_realized_return` before the row reaches portfolio.

## Prohibited Actions

The following are explicitly prohibited by this contract and the project design:

1. Backfilling `actual_exit_date`
2. Treating `planned_exit_date` as `actual_exit_date`
3. Filtering unresolved rows to let the rest continue
4. Modifying `backtest_executable` to work around unresolved exits
5. Modifying the portfolio guard to silently skip unresolved rows
6. Running backtests with unresolved exit rows present
