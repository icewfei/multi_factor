# Note: Local Feature-Space Exhaustion (2026-05-06)

## Scope of today's follow-up line

All work below kept the same trainval-only contract, same execution semantics, and same core label target.

Tested today:

- `reversal_p98_corr30_ew_v1` -> failed
- `reversal_p98_cord30_w10_v1` -> failed
- `reversal_tail_exclude_p98_top12_v1` -> failed
- `reversal_p98_intraday_reversal_asymmetry_w20_v1` -> failed
- `p98` liquidity-guard cheap screen -> no clean candidate
- reversal-family composability screen -> one promising same-family modifier found in diagnostics, but it failed in full chain

## What these failures mean

This is not a repetition of the old "framework is broken" story.

The pattern is narrower:

- many local tweaks improve one or more of:
  - drawdown
  - turnover
  - cost stress
  - TopK robustness
  - diagnostic IC / spread
- but they do **not** convert into a clean validation-layer win over the live `p98` baseline

In other words:

> The current bars-derived feature space still contains information, but the project's recent failures suggest that **small score-composition and extraction tweaks inside this feature space are now near exhausted**.

## Strongest evidence from today

### 1. External partner line did not promote

- `cord30` failed at 50/50
- `corr30` failed at 50/50
- `cord30` still failed even when reduced to 10% weight

So the issue is not simply "we chose the wrong external partner weight."

### 2. Local deployment tweaks did not rescue p98

- tighter liquidity thresholds improved head liquidity in diagnostics but did not produce a clear candidate
- `TopK=12` improved some robustness metrics but still failed return / cost-stress / invested-weight tests

So the issue is not simply "Top10 is too narrow" or "liquidity guard is too loose."

### 3. Same-family modifier also failed

- `intraday_reversal_asymmetry_rank` looked genuinely promising in the cheap screen:
  - low correlation with `p98`
  - higher diagnostic spread
  - better top-slice liquidity
- but the fixed-test round still failed against `p98`

So the issue is not simply "we need one better local modifier inside the reversal family."

## Operational conclusion

For the current trainval-only research snapshot and current bars-derived feature space:

1. Keep `reversal_tail_exclude_p98_v1` as the live baseline.
2. Stop opening more tiny rounds of:
   - small partner reweighting
   - minor TopK shifts
   - same-family additive modifiers
   - simple liquidity-threshold tightening
3. If the project continues, the next step should be a **new source/modality step**, not another local composition tweak.

## What is still open

This note does **not** prove:

- that all possible feature engineering is exhausted forever
- that new data acquisition is guaranteed to work
- that there is no better portfolio mapping at all

It only says:

> within the currently explored local neighborhood around `p98`, the marginal research return on more tiny tweaks now looks low.
