# Round Note: Reversal + Cord30 Liquidity Guard 0.60

**Status:** Preregistered.

## Positioning

- Phase: `signal/learnability`
- Tier: `exploratory`
- Type: `deployment_fix`
- Changed dimension: `ranking_eligibility_guard`

## Candidate

- `reversal_p98_cord30_liqguard60_v1`

## Frozen score

```text
0.5 × percent_rank(p98_reversal_score) + 0.5 × percent_rank(cord30_score)
```

## Only changed dimension

- add `liquidity_rank >= 0.60` before ranking

## Goal

Recover promotion failure by reducing low-liquidity deployment loss without reopening score search.
