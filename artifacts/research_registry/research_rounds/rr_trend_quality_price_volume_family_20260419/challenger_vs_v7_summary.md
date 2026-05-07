# v14 vs Recalibrated v7 Summary

- `annual_relative_return`: -0.069766 -> -0.074637
- `relative_ir`: -0.528702 -> -0.554869
- `max_drawdown`: -0.396811 -> -0.346044
- `avg_invested_weight`: 0.208003 -> 0.189453
- `avg_turnover_daily`: 0.098113 -> 0.089080
- `low_liquidity_weight_share`: 0.020451 -> 0.021163
- `topk_perturbation_pass`: False -> False
- `cost_stress_pass`: False -> False

Conclusion: `v14` improves drawdown and turnover somewhat, but it still fails to surpass recalibrated `v7` on annual_relative_return and relative_ir, so it remains a `weak_candidate`.
