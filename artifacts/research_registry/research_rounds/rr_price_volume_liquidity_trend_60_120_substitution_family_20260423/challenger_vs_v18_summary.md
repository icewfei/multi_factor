# v21 vs v18 summary

- `reference_candidate_scheme_id(参考候选方案ID) = price_volume_v18_refresh_hysteresis`
- `challenger_candidate_scheme_id(挑战候选方案ID) = price_volume_v21_liquidity_trend_60_120_substitution`

## Key Metrics

- `annual_relative_return(年化超额收益)`: `-0.044142 -> -0.050648`
- `relative_ir(相对信息比率)`: `-0.402481 -> -0.424477`
- `max_drawdown(最大回撤)`: `-0.277201 -> -0.247644`
- `avg_cash_weight(平均现金权重)`: `0.767875 -> 0.790748`
- `avg_invested_weight(平均投资权重)`: `0.232125 -> 0.209252`
- `avg_turnover_daily(平均日换手)`: `0.111041 -> 0.099939`
- `low_liquidity_weight_share(低流动性权重占比)`: `0.029557 -> 0.031002`
- `topk_perturbation_pass(TopK扰动通过)`: `false -> false`
- `cost_stress_pass(成本压力通过)`: `false -> false`
- `cost_stress_annual_relative_return(成本压力年化超额收益)`: `-0.096173 -> -0.097290`

## Conclusion

The direct substitution from `liquidity_trend_20_60_raw` to `liquidity_trend_60_120_raw` improved `max_drawdown(最大回撤)` and `avg_turnover_daily(平均日换手)` versus `v18`, but `annual_relative_return(年化超额收益)` and `relative_ir(相对信息比率)` worsened, `low_liquidity_weight_share(低流动性权重占比)` ticked up slightly, and both `topk_perturbation_pass(TopK扰动通过)` plus `cost_stress_pass(成本压力通过)` still failed.

Therefore `price_volume_v21_liquidity_trend_60_120_substitution` remains a `weak_candidate(弱候选)`.
