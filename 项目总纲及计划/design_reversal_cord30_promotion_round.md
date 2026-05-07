# Design: Reversal + Cord30 Promotion Round

**Status:** Design + prereg + execution candidate. This round promotes the diagnostic winner into a real fixed-test comparison.

## Context

- `reversal_tail_exclude_p98_v1` passed the tail-handling round:
  - median IC = `0.0459`
  - Top10-Bot10 spread = `+0.0049`
- `reversal_p98_cord30_ew_v1` passed the minimal composite diagnostic:
  - median IC = `0.0545`
  - Top10-Bot10 spread = `+0.0139`
- The composite beat both `p98 reversal` and `cord30` in the diagnostic layer.

The remaining unresolved question is no longer "is there any information in this composite?"

The unresolved question is:

> Can the diagnostic winner survive the real project pipeline and beat `p98 reversal` under the same trainval-only fixed-test contract?

## Research Question

Under the frozen trainval-only contract and execution semantics, does `reversal_p98_cord30_ew_v1` outperform `reversal_tail_exclude_p98_v1` at the fixed-test / validation layer without introducing new robustness failures?

## Round Positioning

- Phase: `signal/learnability`
- Tier: `confirmatory`
- Type: `baseline_promotion_check`
- Changed dimension: `score_family_composition`

## Primary Baseline

**`reversal_tail_exclude_p98_v1`**

- Interpretation: the new standalone reversal baseline after tail handling
- Role: formal baseline reference for this promotion round
- Construction:
  - negate raw reversal score
  - compute daily `p98` on the raw negated score
  - exclude rows with score strictly above the daily `p98`
  - re-rank remaining rows cross-sectionally

## Candidate

**`reversal_p98_cord30_ew_v1`**

Formula:

```text
0.5 × PERCENT_RANK(p98_reversal_score) + 0.5 × PERCENT_RANK(cord30_score)
```

Construction is frozen:

1. build `p98` tail-handled reversal exactly as in the previous round
2. join with `cord30`
3. compute cross-sectional `PERCENT_RANK` per `signal_date` for each component
4. equal-weight average the two rank scores
5. re-rank for TopK selection

## Secondary Reference

**`price_volume_single_signal_alpha158_cord30_v1`**

- Used only as an aspirational external reference
- Not part of pass/fail
- Purpose: show whether the promoted composite also clears the previous `cord30` validation tier

## Frozen Dimensions

- snapshot: `warehouse_20260429_trainval_20211231`
- contract: `run_input_contract.research_trainval_20211231.json`
- TopK: `10`
- execution semantics: unchanged
- cost stress model: unchanged
- validation window: `20190101-20211231`
- no new data source
- no refresh-rule change
- no weight tilt
- no second composite candidate

## Success Criteria

All conditions must pass.

### A. Validation edge vs primary baseline

- `validation_annual_relative_return_delta_vs_p98 > 0`
- `validation_relative_ir_delta_vs_p98 > 0`
- `validation_max_drawdown_delta_vs_p98 >= 0`

### B. Robustness / pipeline compatibility

- `cost_stress_annual_relative_return_delta_vs_p98 >= 0`
- `topk8_annual_relative_return_delta_vs_p98 > 0`
- `topk12_annual_relative_return_delta_vs_p98 > 0`
- `validation_avg_turnover_daily_delta_vs_p98 <= 0.02`
- `low_liquidity_weight_share_delta_vs_p98 <= 0.00`
- `candidate_avg_invested_weight >= 0.18`

## Why This Round Is Minimal

- It opens no new signal search line.
- It tests one already-frozen composite only.
- It does not touch data acquisition.
- It does not change contract or execution semantics.
- It asks only one promotion question:
  - does the diagnostic winner remain superior after passing through the real project pipeline?

## Decision Logic

- If all rules pass:
  - `reversal_p98_cord30_ew_v1` becomes the new active baseline candidate
  - next phase moves to a small composite line rather than data acquisition
- If any rule fails:
  - `reversal_tail_exclude_p98_v1` remains the active standalone baseline
  - `cord30` does not yet earn promotion as a fixed composite partner
