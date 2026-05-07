# v7 Recalibrated Execution/Cost Drag Diagnosis (2026-04-18)

Candidate: `baseline_momentum_v7_liquidity_guard70`  
Research round: `rr_baseline_liquidity_guard70_20260418`  
Reference run: `fullchain_baseline_liquidity_guard70_recalibrated_20260418_1915`

## Executive Readout
Execution and cost drag **do hurt** this strategy, but they do **not fully explain** the failure.

The calibrated `v7` is already benchmark-relative negative **before** any extra cost stress:
- base `annual_relative_return = -0.069766`
- cost-stress `annual_relative_return = -0.114947`
- stress delta = `-0.045181`

So the right diagnosis is:
- the underlying gross edge is too weak,
- and a high-turnover execution profile makes that weak edge worse,
- rather than execution frictions alone overwhelming an otherwise strong signal.

## 1. What The Cost-Stress Failure Actually Means
Current gate:
- `cost_stress_pass = true` only if stressed `annual_relative_return >= 0.0`

Observed:
- base `annual_relative_return = -0.069766`
- stressed `annual_relative_return = -0.114947`
- incremental damage under stress = `-0.045181`

Interpretation:
- cost stress is clearly material
- but the strategy is already below zero before extra stress is applied
- therefore the failure is **not** “pure execution drag”
- it is “weak pre-cost edge plus meaningful trading drag”

## 2. Turnover Is Structurally High
From fixed test:
- `avg_turnover_daily = 0.098113`
- `median_turnover_daily = 0.100000`
- `max_turnover_daily = 0.160000`
- `rebalance_days = 6299`

From `turnover_daily.csv`, the path is very regular:
- many days at `0.05`
- many days at `0.10`
- occasional higher values such as `0.11` or `0.16`

Interpretation:
- this is effectively a near-daily rebalancing strategy
- daily turnover around `10%` is not a tail event here; it is the normal operating regime
- under this structure, even moderate entry/exit costs will have a large cumulative impact

## 3. Execution Frictions Exist, But They Are Not The Dominant Root Cause
From run-state / trade statistics:
- `topk_frozen_rows = 63020`
- `entry_filled_rows = 61856`
- `unfilled_topk_count = 1164`
- `avg_exit_delay_days = 0.3662`
- `delayed_exit_positions = 1942`
- `terminal_event_positions = 20`

Useful ratios:
- unfilled TopK share: about `1.85%` of frozen positions
- delayed-exit share: about `3.14%` of filled positions

Interpretation:
- there is real implementation friction
- but this does **not** look like a strategy whose results are mainly destroyed by widespread failure to enter or exit
- terminal events are negligible here
- delayed exits and unfilled entries are worth tracking, but they are secondary relative to turnover and weak gross edge

## 4. TopK Perturbation Failure Reinforces The Same Story
Current gate:
- `topk_perturbation_pass = true` only if both perturbed variants have `annual_relative_return >= 0.0`

Observed:
- base `TopK=10`: `-0.069766`
- `TopK=8`: `-0.073434`
- `TopK=12`: `-0.066117`

Interpretation:
- the perturbed variants are close to the base result
- so the strategy is not failing because one specific `TopK=10` implementation detail ruins an otherwise strong edge
- instead, the edge is weak across nearby extraction choices

This matters for execution diagnosis because it tells us:
- even if execution were smoother, the strategy would still not have a convincing benchmark-relative cushion

## 5. What Is And Is Not Causing The Problem
What **is** likely causing the problem:
- weak benchmark-relative gross edge
- high structural turnover
- mild-to-moderate execution friction layered on top

What is **not** the main explanation anymore:
- the old low-liquidity flag artifact
- severe inability to enter or exit positions
- one isolated `TopK=10` implementation bug

## Conclusion
Execution/cost drag is **real and important**, but it is not the sole or primary explanation.

The calibrated `v7` fails because:
1. the signal is only marginally positive at the score level,
2. the portfolio extraction turns that into a weak benchmark-relative edge,
3. and the strategy then runs with a turnover profile that is expensive enough to push an already weak edge further negative.

## Recommended Next Step
If the goal is to understand the next research move, the most useful framing is:
- do **not** treat this as “just reduce execution drag”
- instead ask whether the next single-dimension test should:
  - reduce turnover structurally, or
  - change score-to-portfolio extraction so the same signal is harvested less aggressively

That is a better next branch than continuing to tweak liquidity guards.
