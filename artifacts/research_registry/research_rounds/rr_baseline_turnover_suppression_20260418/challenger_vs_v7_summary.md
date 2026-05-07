# v11 vs recalibrated v7 summary

- candidate: `baseline_momentum_v11_turnover_suppression`
- round: `rr_baseline_turnover_suppression_20260418`
- reference: `baseline_momentum_v7_liquidity_guard70`

## Engineering

- v11 run-state seconds: 314.08
- v11 chunk size: 10

## Strategy comparison

- annual_relative_return: -0.069766 -> -0.071962
- relative_ir: -0.528702 -> -0.543989
- max_drawdown: -0.396811 -> -0.423756
- avg_cash_weight: 0.791997 -> 0.789307
- avg_invested_weight: 0.208003 -> 0.210693
- avg_turnover_daily: 0.098113 -> 0.099925
- low_liquidity_weight_share: 0.020451 -> 0.022226
- low_liquidity_alpha_contribution_share: -0.103141 -> -0.087843
- topk_perturbation_pass: False -> False
- cost_stress_pass: False -> False

## Conclusion

Turnover suppression with a sticky top20 retention band did not improve annual relative return, relative IR, drawdown, turnover, perturbation stability, or cost stress robustness versus the recalibrated v7 reference.
