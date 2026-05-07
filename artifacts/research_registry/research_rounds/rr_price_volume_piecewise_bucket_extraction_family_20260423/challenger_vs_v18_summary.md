`v20 = price_volume_v20_piecewise_bucket_extraction` 相对 `v18 = price_volume_v18_refresh_hysteresis` 的正式结论是：仍然属于 `weak_candidate(弱候选)`。

关键对比：

- `annual_relative_return(年化超额收益)`：`-0.044142 -> -0.043794`
- `relative_ir(相对信息比率)`：`-0.402481 -> -0.396497`
- `avg_turnover_daily(平均日换手)`：`0.111041 -> 0.111038`

但同时：

- `max_drawdown(最大回撤)`：`-0.277201 -> -0.280821`
- `low_liquidity_weight_share(低流动性权重占比)`：`0.029557 -> 0.029682`
- `topk_perturbation_pass(TopK扰动通过)`：仍为 `false`
- `cost_stress_pass(成本压力通过)`：仍为 `false`

结论：

`piecewise_bucket_extraction(分桶式提取)` 这条线并非完全没用，因为它让 `annual_relative_return(年化超额收益)`、`relative_ir(相对信息比率)` 和 `avg_turnover_daily(平均日换手)` 都出现了非常小的正向改善；但改善幅度太小，且没有跨过两道关键门槛，所以目前不能视为可晋级方案。
