# Design: Reversal + Cord30 Weight-10 Follow-up

**Status:** Design for a single exploratory follow-up after the 50/50 `cord30` line failed promotion and the cheap weight screen selected a lighter partner mix.

## Why this round exists

- `reversal_p98_cord30_ew_v1` failed full-chain promotion
- `reversal_p98_cord30_liqguard60_v1` also failed
- postmortem showed `cord30` was not useless:
  - selection alpha improved
  - TopK8 / TopK12 perturbation improved
  - but deployment loss and liquidity drag prevented promotion
- cheap weight screen showed a lighter mix can keep strong diagnostic spread while improving top-slice liquidity materially

## Research Question

Can `reversal_p98_cord30_w10_v1` recover fixed-test promotion against the `p98 reversal` baseline by keeping `cord30` as only a light auxiliary component?

## Positioning

- Phase: `signal/learnability`
- Tier: `exploratory`
- Type: `weighted_partner_followup`
- Changed dimension: `score_family_composition`

## Baseline

- frozen baseline fixed-test:
  - `confirmatory_reversal_p98_trainval_20260506`

## Secondary references

- failed 50/50 promotion line:
  - `confirmatory_reversal_p98_cord30_trainval_20260506`
- cheap weight screen:
  - `artifacts/fixed_test/reversal_cord30_weight_screen/weight_screen_20260506.json`

## Candidate

- `reversal_p98_cord30_w10_v1`

```text
0.9 × percent_rank(p98_reversal_score) + 0.1 × percent_rank(cord30_score)
```

## Why 10%

- among weights below 50%, `0.10` gave the best Top10 liquidity profile
- median IC remained high (`~0.0499`)
- Top10-Bot10 spread remained strong (`~0.0132`)
- it is the smallest structural deviation from the standalone `p98` baseline

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

## Stop Condition

If the lightweight `cord30` mix still fails against `p98`, close the `cord30` partner-composite line and keep `p98 reversal` as the live baseline.
