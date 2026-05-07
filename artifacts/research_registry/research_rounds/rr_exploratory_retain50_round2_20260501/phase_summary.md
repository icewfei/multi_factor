# Phase Summary: Retain50 — Daily-Recheck Retention

- `research_round_id`: `rr_exploratory_retain50_round2_20260501`
- `status`: `completed_retain50_daily_recheck_not_sufficient`
- `completed_at`: `2026-05-01T18:00:00+08:00`

---

## Verdict

**5/9 FAIL — wider band improved return/drawdown but did not reduce turnover.**

| Metric | Full Refresh | Retain15 | Retain50 |
|---|---|---|---|
| annual_relative_return | -0.194 | -0.136 | **-0.064** |
| max_drawdown | -0.564 | -0.510 | **-0.455** |
| **avg_turnover_daily** | **0.397** | **0.399** | **0.399** |
| cost_stress | -0.076 | -0.078 | -0.116 |
| topk_8 | 0.106 | 0.106 | 0.106 |

## Key Finding

**Turnover converged to ~0.399 across all three regimes.** Wider retention bands improved return and drawdown linearly (-0.194 → -0.136 → -0.064) but had zero effect on turnover. This means the daily-recheck retention semantics do not alter the structural turnover regime.

## Root Cause

The current `portfolio_refresh_contract` checks `retain_if_rank_leq` **daily** (every signal_date), not at cohort entry time. This means:
- A stock ranked ≤ 50 that is retained today may be ranked 200+ tomorrow → immediately replaced
- The retention window is effectively 1 day, not 5 days
- Structural turnover (1/5 of portfolio maturing daily = 0.20) plus daily rank-change replacement (0.20) = 0.40 aggregate — invariant to retention band width

## Next Direction

Cohort-entry locked retention — see design_note_cohort_entry_locked_retention.md.
