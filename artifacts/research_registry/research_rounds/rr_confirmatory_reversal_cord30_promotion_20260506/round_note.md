# Round Note: Reversal + Cord30 Promotion

**Status:** Preregistered.

## Positioning

- Phase: `signal/learnability`
- Tier: `confirmatory`
- Type: `baseline_promotion_check`
- Changed dimension: `score_family_composition`

## Question

Can the diagnostic winner `reversal_p98_cord30_ew_v1` survive the real fixed-test pipeline and beat `reversal_tail_exclude_p98_v1` as the new active baseline candidate?

## Baseline

- `reversal_tail_exclude_p98_v1`

## Challenger

- `reversal_p98_cord30_ew_v1`

## Frozen construction

```text
composite = 0.5 × PERCENT_RANK(p98_reversal_score) + 0.5 × PERCENT_RANK(cord30_score)
```

No tuning. No additional candidate. No contract change.

## Pass rule

The challenger must beat the primary baseline on:

- validation annual relative return
- validation relative IR
- validation max drawdown
- cost stress annual relative return
- TopK perturbation at 8 and 12

while also keeping:

- turnover delta <= 0.02
- low-liquidity share delta <= 0
- invested weight >= 0.18

## Reference

- Design: `项目总纲及计划/design_reversal_cord30_promotion_round.md`
