# price-volume `v22 + amount_shock composability screen + v23` 阶段性收口与方向决策

日期：2026-04-25

## 1. 范围

本次小收口覆盖三部分：

- `v22 = price_volume_v22_breakout_volume_confirmation_substitution`
- `amount_shock_5_20_raw composability screening(组合相容性筛查)`
- `v23 = price_volume_v23_amount_shock_gated_overlay`

统一参考基准：

- `working_reference(工作基准) = price_volume_v18_refresh_hysteresis`

## 2. 结论先行

- **不建议继续测新的 `overlay(覆盖层)` 候选。**
- **建议暂停当前这条 price-volume family 微调线。**
- **下一步应回到新的 `atomic single-signal discovery(原子单信号发现)`。**

原因不是“这条线完全没 edge(边际优势)”，而是：

- `v22` 说明：正向单信号直接替换进 family 可能显著破坏 live portfolio path(真实组合路径)。
- `amount_shock_5_20_raw composability screen(组合相容性筛查)` 说明：它是正向 keeper(保留信号)，但与 `v18` 核心双因子的组合相容性只是 `mixed(混合)`，不是干净可晋升。
- `v23` 说明：即便把它收缩成一个保守的 `gated overlay(门控覆盖层)`，也没有把策略推进到比 `v18` 更好的综合状态。

## 3. 三部分证据

### 3.1 `v22`：直接 family 替换失败

相对 `v18`：

- `annual_relative_return(年化超额收益)`: `-0.044142 -> -0.080301`
- `relative_ir(相对信息比率)`: `-0.402481 -> -0.640110`
- `max_drawdown(最大回撤)`: `-0.277201 -> -0.517079`
- `avg_turnover_daily(平均日换手)`: `0.111041 -> 0.124918`
- `low_liquidity_weight_share(低流动性权重占比)`: `0.029557 -> 0.059145`

判断：

- `breakout_volume_confirmation_20d_raw` 虽然是 `signal_edge_positive(正向信号边际优势)` 单信号，但**不能直接作为 family 替换项**。
- 它的问题不在静态分数翻负，而在 interaction(交互) 和 head stability(头部稳定性) 变差。

### 3.2 `amount_shock_5_20_raw composability screen`：相容性是 `mixed(混合)`

单信号本身：

- `full_sample_corr_ic(全样本IC) = 0.007194`
- `avg_daily_ic(平均日IC) = 0.011316`
- `positive_daily_ic_share(正IC日占比) = 0.557828`

静态三因子筛查相对 `v18` 核心双因子：

- `reference_full_sample_corr_ic(参考全样本IC) = 0.013345`
- `screen_full_sample_corr_ic(筛查全样本IC) = 0.014923`
- `reference_top10_minus_rank11_20(参考前10减11-20) = 0.000519`
- `screen_top10_minus_rank11_20(筛查前10减11-20) = 0.000868`

但问题仍在：

- `core_high_amount_high_avg_label(核心高+量能冲击高平均标签) = 0.004380`
- `core_high_amount_mid_avg_label(核心高+量能冲击中平均标签) = 0.005159`

这说明：

- 它不是“在核心强区越高越好”的干净加法组件。

头部稳定性代理也恶化：

- `reference_avg_top10_overlap_next_day(参考次日前10平均重叠) = 7.223071`
- `screen_avg_top10_overlap_next_day(筛查次日前10平均重叠) = 6.289791`

判断：

- `amount_shock_5_20_raw` 是 keeper(保留信号)。
- 但它**不是干净可直接推广进 family 的组件**。

### 3.3 `v23`：保守 gated overlay 也没能赢过 `v18`

这是在恢复冻结 `liquidity_guard(流动性保护)` 语义后的有效结果。

相对 `v18`：

- `annual_relative_return(年化超额收益)`: `-0.044142 -> -0.048058`
- `relative_ir(相对信息比率)`: `-0.402481 -> -0.424456`
- `max_drawdown(最大回撤)`: `-0.277201 -> -0.283994`
- `avg_turnover_daily(平均日换手)`: `0.111041 -> 0.109417`
- `avg_cash_weight(平均现金权重)`: `0.767875 -> 0.771585`
- `low_liquidity_weight_share(低流动性权重占比)`: `0.029557 -> 0.032957`
- `topk_perturbation_pass(TopK扰动通过)`: `false -> false`
- `cost_stress_pass(成本压力通过)`: `false -> false`

判断：

- `gated overlay(门控覆盖层)` 比直接替换克制很多，但**仍不足以优于 `v18`**。
- 这说明当前继续沿 `overlay(覆盖层)` 线微调，边际收益已经很低。

## 4. 方法论判断

到这一步，研究方法需要明确分层：

### 已经证明合理的部分

- `single-signal discovery(单信号发现)` 是必要且有效的。
- `composability screening(组合相容性筛查)` 是必要新增层。
- 不能再把 `signal_edge_positive(正向信号边际优势)` 直接等同于“适合进 family”。

### 已经进入边际递减的部分

- 直接 family 替换
- 保守 third-signal overlay
- 在当前 `v18` 核心双因子上继续做小幅结构微调

## 5. 正式决策

### 5.1 现在不建议做什么

- 不建议继续开新的 `overlay(覆盖层)` 候选
- 不建议继续在 `v18` 这条 price-volume family 上做 `score_family(评分家族)` 微调
- 不建议开 `v24` 去继续修 `amount_shock_5_20_raw`

### 5.2 现在建议做什么

**暂停当前这条 price-volume family 微调线，回到新的 `atomic single-signal discovery(原子单信号发现)`。**

下一阶段应优先寻找：

- 与 `momentum_60_5_raw` 更正交
- 与 `liquidity_trend_20_60_raw` 更相容
- 且 head-slice(头部切片) 更稳

的新原子信号，而不是继续在现有保留信号上做局部修饰。

## 6. 一句话结论

**`v22` 证明“正向 keeper 不等于可直接替换进 family”，`amount_shock composability screen` 证明“相容性只是 mixed”，`v23` 证明“保守 overlay 也还不够”。因此当前最合理的研究动作是暂停这条 price-volume family 微调线，回到新的原子信号发现。**
