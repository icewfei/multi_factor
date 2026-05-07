# v22 vs v18 summary

- `annual_relative_return(年化超额收益)`: `-0.044142 -> -0.080301`
- `relative_ir(相对信息比率)`: `-0.402481 -> -0.640110`
- `max_drawdown(最大回撤)`: `-0.277201 -> -0.517079`
- `avg_turnover_daily(平均日换手)`: `0.111041 -> 0.124918`
- `avg_cash_weight(平均现金权重)`: `0.767875 -> 0.742565`
- `avg_invested_weight(平均持仓权重)`: `0.232125 -> 0.257435`
- `low_liquidity_weight_share(低流动性权重占比)`: `0.029557 -> 0.059145`
- `topk_perturbation_pass(TopK扰动通过)`: `False -> False`
- `cost_stress_pass(成本压力通过)`: `False -> False`
- `cost_stress_annual_relative_return(成本压力年化超额收益)`: `-0.096173 -> -0.136431`

`run_state_acceptance(运行态验收)` 5 项检查全部通过，但 `v22` 相对 `v18` 在核心策略指标和审计门槛上都明显更差，因此继续记为 `weak_candidate(弱候选)`。
