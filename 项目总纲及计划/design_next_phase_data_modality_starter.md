# Design: Next-Phase Data/Modality Starter

**Status:** Design only. Not registered. No experiment runnable yet with current local assets.

## Why this exists

The current `p98` line survived all recent challengers, but the local tweak space now looks thin:

- external partners failed
- same-family modifier failed
- TopK tweak failed
- cheap liquidity-guard screen produced no clean full-chain candidate

This suggests the next useful phase is no longer:

- another tiny extraction tweak
- another tiny score-weight tweak
- another minor same-family additive combination

## Next-phase question

If the project is reopened beyond the current local feature space, what is the smallest new information source that is most likely to matter?

## Recommended direction

Target **one new modality** that measures something the current daily OHLCV-derived ranks do not directly capture.

Best first hypothesis:

### Overnight / downside repair microstructure

Reason:

- the strongest surviving live line is still reversal-based
- several promising but failing modifiers also come from downside / intraday repair structure
- that pattern suggests the project is repeatedly touching a real mechanism, but only through weak daily proxies

## Minimal starter, if new data becomes available

### Research question

Does one new overnight/downside-repair modality provide standalone oracle-related signal that is materially different from the current `p98` reversal line?

### Anchor label

- oracle 5-day forward return
- tradeable-constrained trainval universe

### Baseline

- `reversal_tail_exclude_p98_v1`

### Minimal first test

Do **not** jump directly to full pipeline.

First do:

1. standalone learnability audit
2. top-slice direction check
3. pairwise correlation vs `p98`

### Success criterion

The new modality is worth a formal round only if it shows all of:

- median daily IC meaningfully above noise
- positive Top10-Bot10 spread
- pairwise rank correlation vs `p98` low enough to imply nontrivial new information

## What not to do next

- do not resume broad equal-weight partner search inside the current bars-only feature space
- do not keep opening more tiny TopK / guard variants of `p98`
- do not reopen `cord30` / `corr30` without genuinely new evidence

## Practical blocker

With current local assets, this next step is mostly blocked by **lack of a truly new modality** inside the accessible research snapshot.

So the project is now ready for:

> a deliberate new-modality step, not another local recombination step
