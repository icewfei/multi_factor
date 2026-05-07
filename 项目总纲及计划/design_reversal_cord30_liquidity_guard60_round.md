# Design: Reversal + Cord30 Liquidity Guard 0.60

**Status:** Minimal deployment-fix round.

## Context

- `reversal_p98_cord30_ew_v1` passed the diagnostic composite check but failed promotion.
- Postmortem showed:
  - higher `selection_alpha_total`
  - better drawdown / turnover / cost stress
  - but worse validation annual relative return
  - lower invested weight
  - higher low-liquidity exposure
- Cheap liquidity screen showed that `liquidity_rank >= 0.60` preserves most of the composite's diagnostic IC/spread while materially improving the Top10 liquidity profile.

## Research Question

If we keep the `reversal_p98_cord30` score unchanged and add only a stricter ranking liquidity guard at `liquidity_rank >= 0.60`, can the composite recover promotion against the `p98 reversal` baseline at the fixed-test / validation layer?

## Round Positioning

- Phase: `signal/learnability`
- Tier: `exploratory`
- Type: `deployment_fix`
- Changed dimension: `ranking_eligibility_guard`

## Baseline

Primary frozen baseline:

- `reversal_tail_exclude_p98_v1`
- frozen fixed-test run:
  - `confirmatory_reversal_p98_trainval_20260506`

Secondary frozen diagnostic reference:

- unguarded composite `reversal_p98_cord30_ew_v1`
- used only to interpret whether the guard fixed deployment loss at an acceptable diagnostic cost

## Candidate

**`reversal_p98_cord30_liqguard60_v1`**

- same score as `reversal_p98_cord30_ew_v1`
- only change:
  - require `liquidity_rank >= 0.60` before ranking

## Success Criteria

All conditions must pass.

### Validation edge vs p98 baseline

- `validation_annual_relative_return_delta_vs_p98 > 0`
- `validation_relative_ir_delta_vs_p98 > 0`
- `validation_max_drawdown_delta_vs_p98 >= 0`

### Deployment robustness

- `cost_stress_annual_relative_return_delta_vs_p98 >= 0`
- `low_liquidity_weight_share_delta_vs_p98 <= 0`
- `topk8_annual_relative_return_delta_vs_p98 > 0`
- `topk12_annual_relative_return_delta_vs_p98 > 0`
- `validation_avg_turnover_daily_delta_vs_p98 <= 0.02`
- `candidate_avg_invested_weight >= 0.18`

## Why 0.60

From the cheap liquidity screen:

- `liq >= 0.60` kept median IC at `0.0509`
- kept Top10 spread at `+0.0106`
- raised Top10 average liquidity rank from `0.5606` to `0.8091`

This is the cleanest compromise among the screened thresholds.
