# Design: Reversal + CORR30 Minimal Composite

**Status:** Minimal follow-up after the `cord30` partner line failed.

## Why this round exists

- `p98 + cord30` failed full-chain promotion
- `p98 + cord30 + liquidity_guard60` also failed
- cheap partner screen selected `corr30` as the best remaining partner:
  - lower cross-rank correlation vs `p98`
  - higher diagnostic spread than `cord30`
  - better top-slice liquidity profile than `cord30`

## Research Question

Can `reversal_p98_corr30_ew_v1` beat the `p98 reversal` baseline at the fixed-test / validation layer?

## Positioning

- Phase: `signal/learnability`
- Tier: `exploratory`
- Type: `minimal_composite_check`
- Changed dimension: `score_family_composition`

## Baseline

- frozen baseline fixed-test:
  - `confirmatory_reversal_p98_trainval_20260506`

## Candidate

- `reversal_p98_corr30_ew_v1`

```text
0.5 × percent_rank(p98_reversal_score) + 0.5 × percent_rank(corr30_score)
```

## Success Criteria

All conditions must pass:

- validation annual relative return delta vs p98 > 0
- validation relative IR delta vs p98 > 0
- validation max drawdown delta vs p98 >= 0
- cost_stress annual relative return delta vs p98 >= 0
- low_liquidity_weight_share delta vs p98 <= 0
- topk8 annual relative return delta vs p98 > 0
- topk12 annual relative return delta vs p98 > 0
- validation avg turnover delta vs p98 <= 0.02
- avg invested weight >= 0.18
