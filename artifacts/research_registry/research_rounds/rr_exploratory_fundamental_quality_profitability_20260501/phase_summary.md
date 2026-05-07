# Phase Summary: Fundamental Quality/Profitability

- `research_round_id`: `rr_exploratory_fundamental_quality_profitability_20260501`
- `status`: `completed_fundamental_quality_profitability_not_viable`
- `completed_at`: `2026-05-01T16:30:00+08:00`

---

## Verdict

**All 3 candidates failed prereg success rules. Quality/profitability fundamental direction closed.**

| Candidate | Verdict | ann_rel_ret | topk_8 | cost_stress |
|---|---|---|---|---|
| c1_roe_dt | **6/9 FAIL** | -0.325 | +0.009 | -0.159 |
| c2_roa_yearly | **5/9 FAIL** | -0.293 | +0.012 | -0.179 |
| c3_roe_roa | **4/9 FAIL** | -0.313 | -0.044 | -0.199 |

### Key Findings

1. **Best candidate c1_roe_dt (6/9)**: same tier as intraday c1 but weaker absolute return
2. **c3 combination did not improve robustness**: topk_8 worsened from +0.012 (best single) to -0.044, cost_stress from -0.159 to -0.199
3. **Low-turnover intuition did not materialize**: fundamental turnover (0.3935) was identical to v18 (0.3935). Under percentile-rank + TopK system, turnover is driven by daily universe changes, not signal rebalancing frequency.

---

## Cumulative Status: 5-Cohort Signal Families

| Round | Direction | Best Result |
|---|---|---|
| Intraday 26-cohort | Technical price signals | 5/9 |
| Intraday 5-cohort | Technical price signals | 6/9 |
| Volume-gated | Signal conditioning | 6/9 |
| Cross-horizon | Reversal + momentum | 3/9 |
| **Fundamental quality/profitability** | **ROE/ROA** | **6/9** |

All 5 rounds failed. No signal family tested under the 5-cohort contract has passed prereg success rules.
