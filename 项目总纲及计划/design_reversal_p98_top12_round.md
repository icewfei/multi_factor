# Design: Reversal P98 TopK-12 Follow-up

**Status:** Minimal follow-up after the p98 liquidity-guard screen failed to surface a clean candidate.

## Why this round exists

- `p98 reversal` remains the live baseline after all partner-composite lines failed
- baseline diagnosis recommended `liquidity_guard` first, but the cheap guard screen found no attractive threshold
- baseline oracle TopK curve showed `Top12` retains nearly the same average oracle label as `Top10`
- `Top12` is therefore the smallest remaining extraction-geometry change worth testing before reopening larger framework discussions

## Research Question

Can `reversal_tail_exclude_p98_top12_v1` beat the live `p98 Top10` baseline at the fixed-test / validation layer by widening extraction from `TopK=10` to `TopK=12` while keeping the signal definition unchanged?

## Positioning

- Phase: `signal/learnability`
- Tier: `exploratory`
- Type: `portfolio_extraction_followup`
- Changed dimension: `topk_parameter`

## Baseline

- frozen baseline fixed-test:
  - `confirmatory_reversal_p98_trainval_20260506`

## Candidate

- `reversal_tail_exclude_p98_top12_v1`

Signal definition is unchanged:

```text
negated reversal score
exclude raw scores strictly above daily p98
percent_rank within surviving rows
```

Only extraction changes:

```text
TopK: 10 -> 12
```

## Success Criteria

All conditions must pass:

- validation annual relative return delta vs p98_top10 > 0
- validation relative IR delta vs p98_top10 > 0
- validation max drawdown delta vs p98_top10 >= 0
- cost_stress annual relative return delta vs p98_top10 >= 0
- low_liquidity_weight_share delta vs p98_top10 <= 0
- validation avg turnover delta vs p98_top10 <= 0.02
- validation avg invested weight delta vs p98_top10 >= 0

## Why no TopK perturbation rule here

- this is a direct `TopK` parameter round
- using `TopK` robustness as a hard pass/fail rule would conflate the changed dimension with the diagnostic around it
- this round only asks whether `Top12` itself is a better deployment mapping than `Top10`

## Stop Condition

If `Top12` also fails, then the next step should not be another tiny extraction tweak inside the current `p98` line.
