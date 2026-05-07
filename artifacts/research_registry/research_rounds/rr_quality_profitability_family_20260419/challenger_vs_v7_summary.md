# v12 vs Recalibrated v7 Summary

- `annual_relative_return`: -0.069766 -> -0.075695
- `relative_ir`: -0.528702 -> -0.491747
- `max_drawdown`: -0.396811 -> -0.194233
- `avg_invested_weight`: 0.208003 -> 0.104997
- `avg_turnover_daily`: 0.098113 -> 0.047313
- `low_liquidity_weight_share`: 0.020451 -> 0.107308
- `topk_perturbation_pass`: False -> False
- `cost_stress_pass`: False -> False

Conclusion: `v12` lowers turnover and drawdown but does not improve annual_relative_return enough to replace recalibrated `v7`, and it still fails perturbation plus cost-stress gates, so it remains a `weak_candidate`.
