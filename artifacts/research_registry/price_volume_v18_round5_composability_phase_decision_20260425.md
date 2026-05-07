# price-volume v18 / round 5 / composability phase decision

## Decision

- `pause_current_price_volume_family_tuning_line(暂停当前这条 price-volume family 微调线) = true`
- `advance_single_keeper_to_constrained_next_stage(推进单一 keeper 进入更克制的下一阶段设计) = false`
- `retain_watchlist_candidate_scheme_id(保留观察名单候选) = price_volume_single_signal_volume_price_synchronicity_20d_v1`

## Why

当前 `working_reference(工作基准)` 仍然是 `v18 = price_volume_v18_refresh_hysteresis`：

- `annual_relative_return(年化超额收益) = -0.044142`
- `relative_ir(相对信息比率) = -0.402481`
- `max_drawdown(最大回撤) = -0.277201`
- `avg_turnover_daily(平均日换手) = 0.111041`
- `low_liquidity_weight_share(低流动性权重占比) = 0.029557`
- `topk_perturbation_pass(TopK扰动通过) = false`
- `cost_stress_pass(成本压力通过) = false`

round 5 的确新增了 3 只 `clean positive keepers(干净正向保留信号)`：

- `price_volume_single_signal_turnover_acceleration_5_20_v1`
  - `full_sample_corr_ic(全样本IC) = 0.006315`
  - `avg_daily_ic(平均日IC) = 0.011075`
  - `positive_daily_ic_share(正IC日占比) = 0.561133`
- `price_volume_single_signal_volume_price_synchronicity_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.016661`
  - `avg_daily_ic(平均日IC) = 0.029966`
  - `positive_daily_ic_share(正IC日占比) = 0.636764`
- `price_volume_single_signal_up_amount_persistence_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.009374`
  - `avg_daily_ic(平均日IC) = 0.013587`
  - `positive_daily_ic_share(正IC日占比) = 0.549174`

但接下来的两轮 `composability screening(组合相容性筛查)` 都没有给出“可以安全升格”的证据。

### 1. `volume_price_synchronicity_20d_raw`

它是当前最强的新 keeper，也是这两轮里更有希望的一只。

静态三因子筛查分数层明显更好：

- `reference_full_sample_corr_ic(参考全样本IC) = 0.013345`
- `screen_full_sample_corr_ic(筛查全样本IC) = 0.017844`
- `reference_top10_minus_rank11_20(参考前10减11-20) = 0.000519`
- `screen_top10_minus_rank11_20(筛查前10减11-20) = 0.003473`

而且高核心区加法单调性是通过的：

- `core_high_sync_high_avg_label(核心高+量价同步高平均标签) = 0.004937`
- `core_high_sync_mid_avg_label(核心高+量价同步中平均标签) = 0.004792`

但它还是没能成为 `cleanly promotable(可干净升格)`：

- `reference_avg_top10_overlap_next_day(参考次日前10平均重叠) = 7.223071`
- `screen_avg_top10_overlap_next_day(筛查次日前10平均重叠) = 6.875955`
- `reference_avg_top10_liquidity_rank_mean(参考前10平均流动性分位) = 0.442297`
- `screen_avg_top10_liquidity_rank_mean(筛查前10平均流动性分位) = 0.394157`

也就是：
- `head_stability(头部稳定性)` 变差了
- `liquidity proxy(流动性代理)` 也变差了

### 2. `up_amount_persistence_20d_raw`

它也能改善一些静态分数层指标：

- `reference_full_sample_corr_ic(参考全样本IC) = 0.013345`
- `screen_full_sample_corr_ic(筛查全样本IC) = 0.013727`
- `reference_top10_minus_rank11_20(参考前10减11-20) = 0.000519`
- `screen_top10_minus_rank11_20(筛查前10减11-20) = 0.001130`

但它的问题更明显：

- `core_high_persist_high_avg_label(核心高+上涨量能持续性高平均标签) = 0.004275`
- `core_high_persist_mid_avg_label(核心高+上涨量能持续性中平均标签) = 0.004662`

这意味着高核心区加法单调性本身就没通过。

同时：

- `reference_avg_top10_overlap_next_day(参考次日前10平均重叠) = 7.223071`
- `screen_avg_top10_overlap_next_day(筛查次日前10平均重叠) = 6.940314`
- `reference_avg_top10_liquidity_rank_mean(参考前10平均流动性分位) = 0.442297`
- `screen_avg_top10_liquidity_rank_mean(筛查前10平均流动性分位) = 0.427264`

所以它比 `volume_price_synchronicity_20d_raw` 更不适合继续推进。

## Judgement

综合 `v22 direct substitution failure(v22 直接替换失败)`、`v23 gated overlay failure(v23 门控覆盖层失败)`、以及这两轮 `composability screening(组合相容性筛查)`：

- 现在**不适合**再开新的 `price-volume family(价量家族)` 微调 round
- 也**不适合**把任何一个新 keeper 直接推进到下一条 constrained family/overlay design(更克制的 family/覆盖层设计)

最合理的阶段判断是：

- **暂停当前这条 `price-volume family(价量家族)` 微调线**
- 只保留 `price_volume_single_signal_volume_price_synchronicity_20d_v1` 作为 `watchlist keeper(观察名单保留信号)`
- 但**暂时不升格、不直跑新 family、不直跑新 overlay**

## Next step

更合理的下一步是：

- 回到新的 `atomic single-signal discovery(原子单信号发现)` batch，或
- 转到一条不同的研究方向

而不是继续在当前 `v18 + new keepers(新 keeper)` 这条线上做 family 微调。
