# Design: Reversal P98 + Intraday Reversal Asymmetry (20%) Follow-up

**Status:** Minimal exploratory follow-up after the partner-composite line and p98 extraction tweaks both failed.

## Why this round exists

- `p98 reversal` remains the live baseline
- `cord30`, `corr30`, lightweight `cord30`, tighter liquidity guard, and `TopK=12` all failed to promote over `p98`
- reversal-family composability screen found one same-family modifier that looks genuinely different from the failed partner lines:
  - `intraday_reversal_asymmetry_rank`
  - very low average daily correlation with `p98` (`~0.055`)
  - slightly higher median IC than `p98`
  - much stronger diagnostic spread
  - better top-slice liquidity than `p98`

## Research Question

Can `reversal_p98_intraday_reversal_asymmetry_w20_v1` beat the live `p98 reversal` baseline at the fixed-test / validation layer while keeping the modification local to the reversal family?

## Positioning

- Phase: `signal/learnability`
- Tier: `exploratory`
- Type: `family_modifier_followup`
- Changed dimension: `score_family_composition`

## Baseline

- frozen baseline fixed-test:
  - `confirmatory_reversal_p98_trainval_20260506`

## Candidate

- `reversal_p98_intraday_reversal_asymmetry_w20_v1`

```text
0.8 × percent_rank(p98_reversal_score) + 0.2 × intraday_reversal_asymmetry_rank
```

## Why this candidate

- unlike `cord30`, it improves diagnostic spread without worsening top-slice liquidity
- unlike `corr30`, it does not look like a weaker diluted copy of the base line
- unlike `reversal_followthrough_rank`, it is not almost perfectly collinear with `p98`

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

If this same-family modifier also fails, the project should stop trying to rescue the current line through small score-composition tweaks inside the existing feature space.
