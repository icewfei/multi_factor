# v17 vs v16 Summary

- Generated at: `2026-04-22T14:25:09+08:00`
- Reference: `price_volume_v16_remove_trend_consistency`
- Challenger: `price_volume_v17_head_extraction_smoothing`
- Reference run: `fullchain_price_volume_remove_trend_consistency_20260422_135614`
- Challenger run: `fullchain_price_volume_head_extraction_smoothing_20260422_141534`
- Final judgement: `weak_candidate`

## Key Comparison

- `annual_relative_return(年化超额收益)`: `-0.05889 -> -0.04706`
- `relative_ir(相对信息比率)`: `-0.42675 -> -0.40957`
- `max_drawdown(最大回撤)`: `-0.40370 -> -0.28266`
- `avg_cash_weight(平均现金权重)`: `0.84192 -> 0.77013`
- `avg_invested_weight(平均投资仓位)`: `0.15808 -> 0.22987`
- `avg_turnover_daily(平均日换手)`: `0.07405 -> 0.10936`
- `low_liquidity_weight_share(低流动性权重占比)`: `0.15016 -> 0.03019`
- `topk_perturbation_pass(TopK扰动通过)`: `false -> false`
- `cost_stress_pass(成本压力通过)`: `false -> false`

## Conclusion

`v17` materially improved `annual_relative_return(年化超额收益)`, `relative_ir(相对信息比率)`, `max_drawdown(最大回撤)`, and `low_liquidity_weight_share(低流动性权重占比)` versus `v16`. However, `avg_turnover_daily(平均日换手)` moved back up, and both `topk_perturbation_pass(TopK扰动通过)` plus `cost_stress_pass(成本压力通过)` still failed, so the candidate remains non-promotable.
