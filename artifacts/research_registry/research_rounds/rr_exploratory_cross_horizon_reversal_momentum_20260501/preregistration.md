# Preregistration: Cross-Horizon Reversal + Momentum

- `research_round_id`: `rr_exploratory_cross_horizon_reversal_momentum_20260501`
- `research_tier`: `exploratory`
- `round_type`: `family_construction`
- `status`: `preregistered`

## Research Question

在 5-cohort 合同下，以短持有期反转（reversal_5d）与中持有期动量（momentum_60_5）构建的跨频信号基线，能否通过 prereg success rules？

## Baseline

`exploratory_cohort5_v18_ref` (momentum + liquidity_trend, 5-cohort contract, contract-matched)

## Candidates

| Order | ID | Signal | min_feature | Role |
|---|---|---|---|---|
| 1 | `c1_reversal_only` | reversal_5d | >= 1 | Single signal control |
| 2 | `c2_momentum_only` | momentum_60_5 | >= 1 | Single signal control |
| 3 | `c3_reversal_momentum` | reversal + momentum | >= 2 | Main test candidate |

## Serial Rule

Serial but NOT cascading. All 3 candidates frozen at prereg. c1/c2 results do not affect c3 execution. No mid-round definition changes.

## c3 Outperformance Rule

c3 must pass core_pass_condition AND outperform at least one of c1/c2 on annual_relative_return or cost_stress.

## Changed Dimension

`score_family_composition`
