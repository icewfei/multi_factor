# Phase Summary: Portfolio Refresh Rule — retain15

- `research_round_id`: `rr_exploratory_refresh_rule_turnover_reduction_20260501`
- `status`: `completed_retain15_partial_finding`

---

## Verdict

**5/9 FAIL — method round with partial positive finding.**

| Gate | retain15 | Baseline | Result |
|---|---|---|---|
| annual_relative_return | -0.136 | -0.194 | ❌ |
| relative_ir | -0.537 | -0.857 | ❌ |
| return_delta vs baseline | **+0.059** | — | ✅ |
| avg_invested_weight | 0.810 | 0.808 | ✅ |
| drawdown_delta | **+0.054** | — | ✅ |
| topk_8 | 0.106 | 0.106 | ✅ |
| topk_12 | 0.121 | 0.121 | ✅ |
| cost_stress | -0.078 | -0.076 | ❌ |
| **avg_turnover_daily** | **0.399** | **0.397** | ❌ |

## Key Findings

1. **Retention mechanism showed partial positive evidence** — return improved (+0.058), drawdown improved (+0.054), IR improved (+0.320). The rule correctly identified and retained high-quality incumbents.
2. **Turnover target failed** — turnover remained at 0.399 (essentially unchanged from 0.397 baseline). Target was ≤0.20.
3. **Root cause: retain threshold too narrow.** Under a 4,311-name universe, rank ≤ 15 represents the top 0.35%. Most incumbents fall outside this band on any given day, so daily replacement continues.
4. **Daily equal-weight rebalancing itself remains a turnover source.** Even retained names generate trade flow when the total holding count shifts and weights are re-equalized.

## Next Direction

Wider retention band (retain_if_rank_leq = 50 or 100) — see design_note_wider_retention_band.md.
