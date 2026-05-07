# v7 Recalibrated Root-Cause Diagnosis: TopK Perturbation and Cost Stress (2026-04-18)

Candidate: `baseline_momentum_v7_liquidity_guard70`
Research round: `rr_baseline_liquidity_guard70_20260418`
Reference run: `fullchain_baseline_liquidity_guard70_recalibrated_20260418_1915`

## Executive Readout
- `run_state` itself is healthy: formal acceptance passed with no fatal blockers.
- The two remaining red flags are **not** primarily explained by the earlier low-liquidity unit mismatch.
- Both failures are now better read as a **weak gross edge problem** with meaningful trading drag, rather than a simple low-liquidity artifact.

## Base Strategy Context
- `annual_relative_return = -0.069766`
- `relative_ir = -0.528702`
- `avg_invested_weight = 0.208003`
- `avg_turnover_daily = 0.098113`
- `max_drawdown = -0.396811`

## 1. TopK Perturbation Failure
Current rule:
- `topk_perturbation_pass = true` only if **all** perturbed `annual_relative_return >= 0.0`

Observed:
- Base `TopK=10`: `-0.069766`
- `TopK=8`: `-0.073434`
- `TopK=12`: `-0.066117`
- Result: `topk_perturbation_pass = False`

Interpretation:
- The perturbation results are all **close to each other**, but all remain negative.
- That means the failure is driven more by the **base signal not clearing the zero relative-return floor** than by an unusually large collapse when `TopK` moves from 10 to 8 or 12.

Cutoff fragility evidence from `ranking_state_daily`:
- Average gap `rank 10 -> 11`: `0.001884`
- Median gap `rank 10 -> 11`: `0.000921`
- Days with `|gap(10,11)| < 0.005`: `5814 / 6302`
- Days with `|gap(10,11)| < 0.001`: `3394 / 6302`

Readout:
- There is real cutoff fragility near the 10/11 boundary.
- But the bigger issue is that even the perturbed variants remain negative, so the strategy is not failing **only** because of boundary instability.

## 2. Cost Stress Failure
Current rule:
- `cost_stress_pass = true` only if stressed `annual_relative_return >= 0.0`

Observed:
- Base `annual_relative_return`: `-0.069766`
- Cost-stress `annual_relative_return`: `-0.114947`
- Stress delta: `-0.045181`
- Result: `cost_stress_pass = False`

Turnover context:
- `avg_turnover_daily = 0.098113`
- `median_turnover_daily = 0.100000`
- `max_turnover_daily = 0.160000`
- `rebalance_days = 6299`

Readout:
- This is a near-daily rebalancing strategy with roughly 10% daily turnover.
- Under that turnover profile, a weak gross edge gets pushed further negative by even moderate cost stress.
- The failure is therefore consistent with **insufficient pre-cost edge plus meaningful trading drag**.

## 3. Low-Liquidity Context After Calibration
Observed after the unit/rank-direction fix:
- `low_liquidity_weight_share = 0.020451`
- `low_liquidity_alpha_contribution_share = -0.103141`
- `flag_high_low_liquidity_exposure = False`

Interpretation:
- The earlier “near-total low-liquidity exposure” reading no longer holds.
- That means the two remaining failures should no longer be interpreted as downstream consequences of a low-liquidity audit flag artifact.

## Conclusion
The calibrated `v7` now points to this hierarchy of problems:
1. The momentum-only guarded signal still has **negative benchmark-relative edge**.
2. The score around the `TopK` boundary is **thinly separated**, so small changes in K do not rescue the strategy.
3. With roughly `10%` daily turnover, **cost stress compounds the already weak edge**.

## Recommended Next Step
Do **not** immediately open a new candidate by continuing to tweak guard strength.
Instead, diagnose the next layer:
- whether the weak edge comes from the momentum-only score itself,
- or whether execution/cost drag is dominating what would otherwise be a marginal signal.
