# v15 vs Calibrated v7 Summary

- Generated at: `2026-04-22T10:13:30+08:00`
- Reference: `baseline_momentum_v7_liquidity_guard70`
- Challenger: `price_volume_v15_trend_liquidity_improvement_core`
- Reference run: `fullchain_baseline_liquidity_guard70_recalibrated_20260418_1915`
- Challenger run: `fullchain_price_volume_trend_liquidity_improvement_core_20260422_100611`
- Final judgement: `weak_candidate`

## Key Comparison

- `annual_relative_return`: `-0.06977 -> -0.05491`
- `relative_ir`: `-0.52870 -> -0.41194`
- `max_drawdown`: `-0.39681 -> -0.48752`
- `avg_cash_weight`: `0.79200 -> 0.81197`
- `avg_invested_weight`: `0.20800 -> 0.18803`
- `avg_turnover_daily`: `0.09811 -> 0.08847`
- `low_liquidity_weight_share`: `0.02045 -> 0.15932`
- `topk_perturbation_pass`: `false -> false`
- `cost_stress_pass`: `false -> false`

## Conclusion

`v15` is directionally more promising than several earlier family challengers because it improved annual relative return, relative IR, and turnover versus calibrated `v7`. However, it still cannot be promoted: drawdown worsened materially, low-liquidity weight share increased, and both `TopK` perturbation and cost-stress audit gates remained failing.
