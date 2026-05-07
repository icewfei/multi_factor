# Phase Summary: Exploratory Intraday Cohort5 Contract Design

- `research_round_id`: `rr_exploratory_intraday_cohort5_contract_design_20260501`
- `status`: `completed_intraday_cohort5_not_viable`
- `completed_at`: `2026-05-01T12:30:00+08:00`

---

## Formal Verdict

**All 3 intraday candidates (c1/c2/c3) failed prereg success rules under the 5-cohort contract (6/9 gates passed).**

The contract-matched v18 baseline (`exploratory_cohort5_v18_ref`) also ran successfully as reference (avg_invested_weight = 0.803).

### Gate Summary

| # | Gate | v18_ref | c1 | c2 | c3 |
|---|------|:-------:|:--:|:--:|:--:|
| 1 | annual_relative_return >= 0.01 | -0.571 ❌ | -0.194 ❌ | -0.246 ❌ | -0.157 ❌ |
| 2 | relative_ir >= 0.30 | -2.867 ❌ | -0.857 ❌ | -1.385 ❌ | -0.800 ❌ |
| 3 | return_delta vs v18 >= -0.005 | — | +0.377 ✅ | +0.325 ✅ | +0.414 ✅ |
| 4 | avg_invested_weight >= 0.15 | 0.803 ✅ | 0.808 ✅ | 0.808 ✅ | 0.829 ✅ |
| 5 | drawdown_delta vs v18 >= -0.05 | — | +0.373 ✅ | +0.379 ✅ | +0.414 ✅ |
| 6 | topk_8 >= 0.00 | +0.013 ✅ | +0.106 ✅ | +0.070 ✅ | +0.099 ✅ |
| 7 | topk_12 >= 0.00 | +0.072 ✅ | +0.121 ✅ | +0.078 ✅ | +0.119 ✅ |
| 8 | cost_stress >= 0.00 | -0.139 ❌ | -0.076 ❌ | -0.120 ❌ | -0.089 ❌ |
| 9 | turnover_delta <= 0.04 | — | +0.004 ✅ | +0.003 ✅ | +0.003 ✅ |
| **core_pass** | **all 9** | — | **6/9 FAIL** | **6/9 FAIL** | **6/9 FAIL** |

**Note on gate 9:** c3 turnover_delta = 0.0030, PASS (<= 0.04). An earlier inline report script had an inequality-direction bug that temporarily marked it as FAIL. The actual data is correct.

---

## Contract Change Impact

| Before (26-cohort) | After (5-cohort) |
|---|---|
| avg_invested_weight ~0.16 | **avg_invested_weight ~0.81** |
| topk_perturbation: FAIL (all candidates) | **topk_perturbation: PASS (all candidates)** |
| best result: 5/9 | best result: **6/9** |
| v18: annual_relative_return -0.275 | v18: annual_relative_return -0.571 |

The 5-cohort contract fixed the invested-weight problem and the topk perturbation problem. These were contract-level bottlenecks, not signal-level problems.

---

## Remaining Bottlenecks (still failing after contract change)

1. **Absolute return/IR**: negative because intraday alpha isn't enough to cover 82% benchmark return + ~82% invested weight
2. **Cost stress**: even with 20bp open/close slippage stress, the alpha gets consumed by trading costs

These are signal-level problems. The `intraday_trend_bias` single signal has genuine positive edge (consistently beats v18 by +0.37 return delta) but not enough to cross the absolute gates.

---

## Run Final Positioning

| Run | Role | Verdict |
|---|---|---|
| `v18_ref_5cohort` | Contract-matched baseline | Reference only |
| `c1_5cohort` | Intraday single signal | Fail (6/9). Best cost-stress profile. |
| `c2_5cohort` | Intraday 2-signal | Fail (6/9). Diluted c1, no incremental value. |
| `c3_5cohort` | Intraday 3-signal | Fail (6/9). Best return/drawdown profile. |

---

## Diagnostic Takeaway

> Under the 5-cohort contract, the intraday family became materially closer to viable than under the 26-cohort contract (5/9 → 6/9, topk perturbation fixed), but still failed prereg success rules due to insufficient absolute return/IR and negative cost-stress performance.

The contract change solved a contract problem (topk perturbation). The remaining bottlenecks are signal problems (absolute return, cost stress).

---

## Recommended Next Direction (single, not yet opened)

**Signal-layer improvement on `intraday_trend_bias` alone.** c1 is the strongest intraday candidate across both contracts. Its standalone positive edge against v18 is consistent (~+0.37 return delta), but its absolute return and cost-stress are negative. The most constrained path forward is to investigate whether a different signal construction or signal transformation (e.g., signed or regime-conditioned versions of trend_bias) can improve the signal-to-cost ratio enough to pass the remaining gates.
