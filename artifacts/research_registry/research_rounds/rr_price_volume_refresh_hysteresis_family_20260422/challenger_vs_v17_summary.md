# v18 vs v17 Summary

- Generated at: `2026-04-22T14:42:38+08:00`
- Reference: `price_volume_v17_head_extraction_smoothing`
- Challenger: `price_volume_v18_refresh_hysteresis`
- Reference run: `fullchain_price_volume_head_extraction_smoothing_20260422_141534`
- Challenger run: `fullchain_price_volume_refresh_hysteresis_20260422_143317`
- Final judgement: `weak_candidate`

## Key Comparison

- `annual_relative_return(年化超额收益)`: `-0.04706 -> -0.04414`
- `relative_ir(相对信息比率)`: `-0.40957 -> -0.40248`
- `max_drawdown(最大回撤)`: `-0.28266 -> -0.27720`
- `avg_cash_weight(平均现金权重)`: `0.77013 -> 0.76787`
- `avg_invested_weight(平均投资仓位)`: `0.22987 -> 0.23213`
- `avg_turnover_daily(平均日换手)`: `0.10936 -> 0.11104`
- `low_liquidity_weight_share(低流动性权重占比)`: `0.03019 -> 0.02956`
- `topk_perturbation_pass(TopK扰动通过)`: `false -> false`
- `cost_stress_pass(成本压力通过)`: `false -> false`

## Conclusion

`v18` slightly improved `annual_relative_return(年化超额收益)`, `relative_ir(相对信息比率)`, `max_drawdown(最大回撤)`, and `low_liquidity_weight_share(低流动性权重占比)` versus `v17`. However, it did not reduce `avg_turnover_daily(平均日换手)`, and both `topk_perturbation_pass(TopK扰动通过)` plus `cost_stress_pass(成本压力通过)` still failed, so the candidate remains non-promotable.
