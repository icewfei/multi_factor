# v23 vs v18 Summary

- `reference_candidate_scheme_id(参考候选方案ID) = price_volume_v18_refresh_hysteresis`
- `challenger_candidate_scheme_id(挑战候选方案ID) = price_volume_v23_amount_shock_gated_overlay`

## Key Metrics

- `annual_relative_return(年化超额收益)`: `-0.044142 -> -0.048058`
- `relative_ir(相对信息比率)`: `-0.402481 -> -0.424456`
- `max_drawdown(最大回撤)`: `-0.277201 -> -0.283994`
- `avg_cash_weight(平均现金权重)`: `0.767875 -> 0.771585`
- `avg_invested_weight(平均投资权重)`: `0.232125 -> 0.228415`
- `avg_turnover_daily(平均日换手)`: `0.111041 -> 0.109417`
- `low_liquidity_weight_share(低流动性权重占比)`: `0.029557 -> 0.032957`
- `topk_perturbation_pass(TopK扰动通过)`: `false -> false`
- `cost_stress_pass(成本压力通过)`: `false -> false`
- `cost_stress_annual_relative_return(成本压力年化超额收益)`: `-0.096173 -> -0.099359`

## Conclusion

`v23` remained close to `v18` on turnover and liquidity exposure, but `annual_relative_return(年化超额收益)`, `relative_ir(相对信息比率)`, and `max_drawdown(最大回撤)` all worsened, while `topk_perturbation_pass(TopK扰动通过)` and `cost_stress_pass(成本压力通过)` still failed. Therefore the gated-overlay design remains a `weak_candidate(弱候选)` and cannot replace `v18`.
