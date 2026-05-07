# v22 component interaction diagnosis

## Core answer

`breakout_volume_confirmation_20d_raw` is a real `signal_edge_positive(正向边际优势)` single signal, but it fails as a direct family substitute because its interaction with `momentum_60_5_raw` is **not additively monotone** under the frozen `v18` contract.

## Evidence

### 1. The single signal is genuinely positive

- `full_sample_corr_ic(全样本IC) = 0.007258`
- `avg_daily_ic(平均日IC) = 0.011053`
- `positive_daily_ic_share(正IC日占比) = 0.554611`
- `avg_label_top10(前10平均标签) = 0.004263`
- `avg_label_rank11_20(11-20名平均标签) = 0.001971`
- `top10_minus_rank11_20(前10减11-20) = 0.002292`

So the raw signal is not fake; it really works in standalone ordering.

### 2. The family score is still positive at the static score layer

- `full_sample_corr_ic(全样本IC) = 0.012080`
- `avg_daily_ic(平均日IC) = 0.017646`
- `positive_daily_ic_share(正IC日占比) = 0.561716`
- `avg_label_top10(前10平均标签) = 0.004993`
- `avg_label_rank11_20(11-20名平均标签) = 0.004327`
- `top10_minus_rank11_20(前10减11-20) = 0.000667`

So `v22` did **not** fail because the score direction flipped negative.

### 3. The problem is the interaction with momentum

Component-rank correlation is slightly negative:
- `component_rank_correlation_full(组件分位相关系数-全样本) = -0.002535`
- `component_rank_correlation_avg_daily(组件分位相关系数-平均日) = -0.012908`
- `component_rank_correlation_positive_daily_share(组件分位相关系数为正的交易日占比) = 0.482545`

And the best interaction bucket is **not** `momentum_high + breakout_high`:
- `momentum_high_breakout_high_avg_label(高动量+高突破确认平均标签) = 0.004108`
- `momentum_high_breakout_mid_avg_label(高动量+中等突破确认平均标签) = 0.005328`

That means the breakout component is not a simple monotone enhancer on top of momentum. A plain equal-weight average over-rewards extreme breakout confirmation where momentum support is not actually the strongest realized region.

### 4. Head stability gets worse

- `v18_avg_top10_overlap_next_day(下日Top10平均重叠数) = 7.708`
- `v22_avg_top10_overlap_next_day(下日Top10平均重叠数) = 6.556`
- `v18_avg_turnover_daily(平均日换手) = 0.111041`
- `v22_avg_turnover_daily(平均日换手) = 0.124918`

So once the signal enters the live family, the head becomes materially less stable and the strategy turns over more.

### 5. The realized portfolio path deteriorates badly

- `annual_relative_return(年化超额收益)`: `-0.044142 -> -0.080301`
- `max_drawdown(最大回撤)`: `-0.277201 -> -0.517079`
- `selection_alpha_total(选股超额贡献总量)`: `0.717565 -> -0.080398`
- `cash_drag_total(现金拖累总量)`: `-2.229722 -> -2.200576`
- `low_liquidity_weight_share(低流动性权重占比)`: `0.029557 -> 0.059145`
- `low_liquidity_contribution_total(低流动性贡献总量)`: `-0.015160 -> -0.159319`

This is the strongest evidence: cash drag improves only slightly, but `selection_alpha_total(选股超额贡献总量)` flips from strongly positive to negative. So the main damage comes from **worse live stock selection and path behavior**, not from benchmark mechanics or cash usage alone.

## Final judgement

`breakout_volume_confirmation_20d_raw` is a valid standalone keeper, but it is **not a valid direct equal-weight replacement** for `liquidity_trend_20_60_raw` inside the frozen `v18` family.

The next time this signal is used, it should be tested as one of these instead:
- a constrained third signal instead of a two-signal direct replacement
- a gated overlay on top of momentum
- a conditional modifier that only acts inside already-strong momentum regions
