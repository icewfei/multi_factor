# Phase Summary: Retain50 + 10-Cohort

- `research_round_id`: `rr_exploratory_retain50_10cohort_20260501`
- `status`: `completed_method_combo_not_sufficient`

---

## Verdict

**6/9 FAIL — same 3 gates as all other method rounds.**

| Config | ann_rel_ret | turnover | cost_stress | topk_8 | Verdict |
|---|---|---|---|---|---|
| 5-cohort full | -0.194 | 0.397 | -0.076 | 0.106 | 6/9 |
| 5-cohort R50 | -0.064 | 0.399 | -0.116 | 0.106 | 5/9 |
| 10-cohort full | -0.181 | 0.199 | -0.082 | 0.005 | 6/9 |
| **10-cohort R50** | **-0.117** | **0.199** | **-0.100** | **0.005** | **6/9** |

## Key Findings

1. **10-cohort solved turnover feasibility** (0.199, within ≤0.25 target)
2. **Retain50 improved return/drawdown** vs 10-cohort full refresh (+0.064, +0.074)
3. **But retained its cost_stress penalty** — cost_stress worsened in both 5-cohort (-0.076→-0.116) and 10-cohort (-0.082→-0.100)
4. **All 4 configurations converge on the same 3 failing gates:** annual_relative_return, relative_ir, cost_stress

## Conclusion

Portfolio_refresh_rule + holding_cohort_count parameter search is near exhausted under the current framework. The remaining gates appear to require framework-level changes.
