# Phase Summary: Volume-Confirmed Intraday Trend Bias

- `research_round_id`: `rr_exploratory_trend_bias_volume_confirmed_20260501`
- `status`: `completed_volume_gate_not_viable`
- `completed_at`: `2026-05-01T14:00:00+08:00`

---

## Verdict

**FAIL (6/9) — same viability tier as ungated c1 under the same 5-cohort contract.**

| Gate | Value | Result |
|---|---|---|
| annual_relative_return >= 0.01 | -0.171 | ❌ |
| relative_ir >= 0.30 | -0.901 | ❌ |
| return_delta vs baseline >= -0.005 | +0.023 | ✅ |
| avg_invested_weight >= 0.15 | 0.814 | ✅ |
| drawdown_delta vs baseline >= -0.05 | +0.112 | ✅ |
| topk_8 >= 0.00 | +0.062 | ✅ |
| topk_12 >= 0.00 | +0.074 | ✅ |
| cost_stress >= 0.00 | -0.113 | ❌ |
| turnover_delta <= 0.04 | -0.0004 | ✅ |

Baseline: `exploratory_cohort5_c1_trendbias_only` (ungated, same 5-cohort contract).

---

## Failure Analysis

**1. Volume gate did not improve cost_stress.**
The cost-stress model uses fixed slippage (20bp open + 20bp close), not liquidity-sensitive slippage. Excluding low-volume stocks does not reduce assumed trading costs under this model. Cost stress actually worsened (-0.076 → -0.113).

**2. Gate excluded 52.72% of stock-days and reduced diversification.**
The reduced candidate pool made the portfolio more sensitive to perturbation (topk_8 dropped from 0.106 to 0.062). More cash was not the issue (invested_weight stayed at 0.81), but fewer names in the TopK meant higher concentration risk.

**3. Alpha improved slightly but not enough.**
Return improved by +0.023 (from -0.194 to -0.171), drawdown improved by +0.112 (from -0.564 to -0.452). But IR worsened (-0.857 to -0.901) and cost_stress worsened, leaving the overall viability tier unchanged at 6/9.

---

## Strategic Closure

**Intraday microstructure standalone line is now closed across three attempts:**

| Round | Contract | Best Result | Failing Gates |
|---|---|---|---|
| 26-cohort baseline | holding_cohort_count=26 | 5/9 | return, IR, topk_8, topk_12, cost_stress |
| 5-cohort contract redesign | holding_cohort_count=5 | 6/9 | return, IR, cost_stress |
| Volume-gated conditioning | 5-cohort + volume gate | 6/9 | return, IR, cost_stress |

The intraday signals have genuine but limited alpha. Under the current D1-D5 + TopK + cash-retention framework, they cannot pass the prereg success rules regardless of contract tuning or regime conditioning. The remaining bottleneck is signal-layer alpha thickness, not contract design or gate optimization.

---

## Recommended Next Direction (not yet registered)

Investigate whether a fundamentally different signal family — such as overnight-gap-based signals, cross-sectional mean-reversion beyond 5-day horizon, or inter-market momentum — can provide positive absolute return under the existing 5-cohort contract. The 5-cohort contract has been validated as functional; the issue is signal quality, not contract design.
