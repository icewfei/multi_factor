# Phase Summary: Cross-Horizon Reversal + Momentum

- `research_round_id`: `rr_exploratory_cross_horizon_reversal_momentum_20260501`
- `status`: `completed_cross_horizon_not_viable`
- `completed_at`: `2026-05-01T15:00:00+08:00`

---

## Verdict

**All 3 candidates failed prereg success rules. Cross-horizon technical-price direction closed.**

| Candidate | Result | ann_rel_ret | topk_8 | cost_stress |
|---|---|---|---|---|
| c1_reversal_only | 3/9 FAIL | -0.532 | -0.273 | -0.391 |
| c2_momentum_only | 2/9 FAIL | -0.627 | -0.055 | -0.187 |
| c3_reversal_momentum | 3/9 FAIL | **-0.397** | -0.334 | -0.430 |

### Key Findings

1. **Combination buffering exists**: c3 (-0.397) is better than both c1 (-0.532) and c2 (-0.627). The reversal+momentum combination provides genuine diversification benefit.

2. **But absolute level too low**: c3's annual_relative_return of -0.397 is far from the +0.01 threshold. Both topk perturbation and cost_stress are severely negative.

3. **Reversal and momentum both fail under high-invested-weight**: The 5-cohort contract's 72-84% invested weight amplifies the TopK head resolution problem for both signals.

## Strategic Closure

> Under the 5-cohort contract, cross-horizon price-based technical signals also failed to meet prereg success rules. Together with the already closed intraday standalone line, the 5-cohort technical-price signal direction is now closed.

## Recommended Next Direction

Fundamental signals (quality/profitability/value). These use PIT financial data rather than price-volume technicals, providing truly orthogonal alpha sources with different frequency and cost profiles.
