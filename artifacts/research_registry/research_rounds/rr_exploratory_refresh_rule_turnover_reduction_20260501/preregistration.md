# Preregistration: Portfolio Refresh Rule — Turnover Reduction

- `research_round_id`: `rr_exploratory_refresh_rule_turnover_reduction_20260501`
- `research_tier`: `exploratory`
- `round_type`: `method_investigation`
- `status`: `preregistered`

## Research Question

仅将 portfolio_refresh_rule 从 daily_full_refresh 改为 top15_retention_band，能否将 turnover 从 0.39 压到 ≤0.20，使 cost_stress ≥ 0？

## Formal Baseline

`exploratory_cohort5_c1_trendbias_only` — same signal, same 5-cohort contract, daily full refresh.

## Candidate

Single candidate: `exploratory_refresh_c1_retain15`

## Refresh Rule

`retain_if_rank_leq = 15` — incumbents ranked ≤ 15 on current signal date are retained. New entries fill remaining slots up to TopK=10. Unfilled slots remain cash.

## Success Rules — 9 gates

| Gate | Condition |
|---|---|
| annual_relative_return | >= 0.01 |
| relative_ir | >= 0.30 |
| return_delta vs c1_full_refresh | >= -0.01 |
| avg_invested_weight | >= 0.15 |
| drawdown_delta vs c1_full_refresh | >= -0.05 |
| topk_perturbation | topk_8 >= 0 AND topk_12 >= 0 |
| cost_stress | >= 0.00 |
| **turnover_absolute** (替换旧 delta gate) | **avg_turnover_daily <= 0.20** |

Turnover gate replaced from relative-delta to absolute target. This is a method round; the primary goal is direct turnover reduction.
