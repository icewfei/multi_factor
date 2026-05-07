# v16 vs v15 Summary

- Generated at: `2026-04-22T14:05:20+08:00`
- Reference: `price_volume_v15_trend_liquidity_improvement_core`
- Challenger: `price_volume_v16_remove_trend_consistency`
- Reference run: `fullchain_price_volume_trend_liquidity_improvement_core_20260422_100611`
- Challenger run: `fullchain_price_volume_remove_trend_consistency_20260422_135614`
- Final judgement: `weak_candidate`

## Key Comparison

- `annual_relative_return(年化超额收益)`: `-0.05491 -> -0.05889`
- `relative_ir(相对信息比率)`: `-0.41194 -> -0.42675`
- `max_drawdown(最大回撤)`: `-0.48752 -> -0.40370`
- `avg_cash_weight(平均现金权重)`: `0.81197 -> 0.84192`
- `avg_invested_weight(平均投资仓位)`: `0.18803 -> 0.15808`
- `avg_turnover_daily(平均日换手)`: `0.08847 -> 0.07405`
- `low_liquidity_weight_share(低流动性权重占比)`: `0.15932 -> 0.15016`
- `topk_perturbation_pass(TopK扰动通过)`: `false -> false`
- `cost_stress_pass(成本压力通过)`: `false -> false`

## Conclusion

`v16` improved `annual_relative_return(年化超额收益)`, `relative_ir(相对信息比率)`, `max_drawdown(最大回撤)`, `avg_turnover_daily(平均日换手)`, and `low_liquidity_weight_share(低流动性权重占比)` versus `v15`. However, it still failed both `topk_perturbation_pass(TopK扰动通过)` and `cost_stress_pass(成本压力通过)`, so it remains non-promotable.
