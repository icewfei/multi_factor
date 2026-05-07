# v7 Calibration Before/After Summary (2026-04-18)

Candidate: `baseline_momentum_v7_liquidity_guard70`
Research round: `rr_baseline_liquidity_guard70_20260418`

## Context
This comparison isolates the effect of two contract repairs:
- shared-source `low_liquidity_flag_t` threshold fixed for `amount` in thousand CNY
- project-side `liquidity_rank` direction corrected so higher liquidity maps to higher rank

## Focus Metrics
| Metric | Before | After | Delta |
|---|---:|---:|---:|
| low_liquidity_weight_share | 1.000000 | 0.020451 | -0.979549 |
| low_liquidity_alpha_contribution_share | 0.599087 | -0.103141 | -0.702228 |
| topk_perturbation_pass | False | False | n/a |
| cost_stress_pass | False | False | n/a |
| annual_relative_return | -0.052948 | -0.069766 | -0.016818 |
| avg_invested_weight | 0.137367 | 0.208003 | +0.070637 |

## Readout
- `low_liquidity_weight_share` fell from nearly full exposure to a low single-digit share, confirming the old audit signal was heavily distorted by a unit mismatch in `low_liquidity_flag_t`.
- `low_liquidity_alpha_contribution_share` also flipped from strongly positive to negative, so the earlier reading should not be used as valid evidence of structural low-liquidity dependence.
- Even after recalibration, `topk_perturbation_pass` and `cost_stress_pass` still remain `false`, so `v7` is still not promotable.
- The calibrated `v7` is the valid reference going forward because it reflects the corrected shared snapshot and corrected liquidity rank semantics.

## Provenance
- Before run: `fullchain_baseline_liquidity_guard70_20260418_1620` on snapshot `warehouse_20260413_165753`
- After run: `fullchain_baseline_liquidity_guard70_recalibrated_20260418_1915` on snapshot `warehouse_20260418_181408`
- Run-state acceptance after recalibration: `overall_passed = True`
