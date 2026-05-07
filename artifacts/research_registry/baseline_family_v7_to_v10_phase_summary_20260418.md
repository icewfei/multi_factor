# baseline family v7-v10 阶段性研究收口总结

## 1. 目的

本文件用于收口 `v7-v10` 这四轮基于校准后 `v7` reference 的探索结果，明确：

- 当前哪些结论已经稳定
- 哪些方向已经证伪，不应继续微调
- 下一条新方向应从哪里切入

本文件只总结当前阶段研究，不替代总纲、实施计划或候选方案 preregistration。

## 2. 当前有效 reference

当前唯一有效 reference 为：

- `candidate_scheme_id = baseline_momentum_v7_liquidity_guard70`
- `research_round_id = rr_baseline_liquidity_guard70_20260418`
- 口径：已纳入 `amount` 单位修正与 `liquidity_rank` 方向修正后的 **calibrated v7**

关键指标：

- `annual_relative_return = -0.06976572569304007`
- `relative_ir = -0.5287021621315882`
- `max_drawdown = -0.3968114993586318`
- `avg_cash_weight = 0.7919965084907071`
- `avg_invested_weight = 0.2080034915092814`
- `avg_turnover_daily = 0.09811299793683326`
- `low_liquidity_weight_share = 0.020450724262800736`
- `low_liquidity_alpha_contribution_share = -0.10314096828107921`
- `topk_perturbation_pass = false`
- `cost_stress_pass = false`

## 3. v7-v10 结果汇总

### 3.1 v7 recalibrated

研究定位：

- 修正 `amount` 单位与 `liquidity_rank` 方向后的校准 reference

主要结论：

- 之前近似 `1.0` 的低流动性暴露判断大部分来自口径错配
- 低流动性问题不再是主导问题
- 剩余问题是：
  - gross edge 偏弱
  - `TopK` cutoff 附近分离太薄
  - turnover / cost 拖累明显

### 3.2 v8 universe liquidity guard

- `candidate_scheme_id = baseline_momentum_v8_universe_liquidity_guard`

单维改动：

- 将与 `v7` 同阈值的流动性 guard 从 ranking 边界前移到 universe 边界

结论：

- 与 `v7` 基本等价，没有产生新的策略信息
- 说明在当前实现中，这条 `guard` 的位置调整不是主要矛盾

阶段判断：

- `guard position` 方向已基本试透，不应继续沿此方向微调

### 3.3 v9 liquidity weight penalty

- `candidate_scheme_id = baseline_momentum_v9_liquidity_weight_penalty`

单维改动：

- 冻结 `v7` 选股边界，只在组合层对低流动性样本做固定权重惩罚

结论：

- 相对 `v7` 没有改善，略差
- `low_liquidity_weight_share` 仍然接近原有水平
- `topk_perturbation_pass = false`
- `cost_stress_pass = false`

阶段判断：

- 在当前冻结选股边界下，只靠组合内权重惩罚不能修复主问题

### 3.4 v10 broadened head extraction

- `candidate_scheme_id = baseline_momentum_v10_broadened_head_extraction`

单维改动：

- 冻结 `v7` 的 score 与 guard
- 不再用 `Top10` 等权
- 改成 `Top10` 内固定 rank-decay 提取

结果相对 `v7`：

- `annual_relative_return`: `-0.06977 -> -0.07471`
- `relative_ir`: `-0.52870 -> -0.54597`
- `max_drawdown`: `-0.39681 -> -0.46672`
- `avg_turnover_daily`: `0.09811 -> 0.09800`
- `low_liquidity_weight_share`: `0.02045 -> 0.01847`
- `topk_perturbation_pass`: 仍为 `false`
- `cost_stress_pass`: 仍为 `false`

结论：

- 只靠在冻结 `Top10` 内做平滑提取，不能改善主问题，反而略差

阶段判断：

- “在同一极窄 head slice 内微调权重映射”不是下一条值得继续走的主线

## 4. 已稳定的阶段性结论

### 4.1 低流动性假象已基本澄清

- 旧结论里“极端低流动性暴露”主要受两件事污染：
  - `amount` 单位误读
  - `liquidity_rank` 方向误用
- 校准后，`low_liquidity_weight_share` 已降到很低水平
- 因此后续研究不应继续把“低流动性暴露”当作唯一核心问题

### 4.2 guard 家族已基本试透

- `v7` 更强 ranking guard 有一定改善
- `v8` universe guard 与 `v7` 等价
- 说明继续扫 guard 的位置或强度，预期信息增量很低

### 4.3 当前主问题不是执行 bug，而是弱 edge

从已完成诊断看：

- score 有弱正 IC 和整体 decile 单调性
- 但 edge 很薄
- `TopK=10` 的提取方式切在了最不稳的一段
- 成本进一步压缩了这条薄 edge

### 4.4 当前 extraction 微调没有解决主问题

- `v9` 权重惩罚无效
- `v10` rank-decay 提取无效
- 说明继续在同一套 score / same selected head 上做组合内微调，成功概率不高

## 5. 工程阶段结论

本阶段 run-state 工程测试结果：

- `chunk=10`：约 `283s`
- `chunk=5`：约 `277s`

结论：

- `chunk=5` 略快于 `10`
- 已足够作为当前机器默认工程配置
- 不建议继续把 `chunk` 当研究变量

## 6. 当前阶段研究收口判断

### 应停止继续微调的方向

- 更高或更多变体的 `ranking_eligibility_guard`
- `universe_guard` 位置微调
- 固定选股边界下的 `liquidity_weight_penalty`
- 冻结 `Top10` 内部的平滑 extraction 微调

### 当前最合理的阶段判断

`v7-v10` 的信息已经足够说明：

- 这条 baseline family 不是完全无信号
- 但当前 signal 的 gross edge 太薄
- 继续在 guard 与 narrow-head mapping 上抹参数，收益很可能递减，并提高研究自由度

## 7. 下一条新方向建议

不建议立刻开 `v11` 做另一次 guard 或 extraction 微调。

下一条最合理的新方向应满足：

- 继续单维改动
- 不回到低流动性 guard 家族
- 不继续在同一窄 head slice 内调权重
- 直接针对“弱 edge + 高 turnover + 极窄切片噪声”中的一个主因

### 推荐方向：turnover suppression / slower refresh

优先建议：

- 开一条新的单维研究线，测试 **降低组合刷新频率** 或 **降低日度换手** 是否能保住更多 gross edge

理由：

- 当前 daily turnover 约 `10%`
- 成本 stress 失败是稳定事实
- 既然 `v10` 证明“同一日的 extraction 微调”不够，下一步更值得试“时间维度的提取方式”

推荐的下一条候选方向可以是：

- `v11 = turnover_suppression`

例如只改一个核心维度：

- 保持 score 不变
- 保持 guard 不变
- 保持 `TopK=10` 不变
- 保持执行语义不变
- 只修改“何时允许替换现有持仓 / 何时保留旧持仓”的组合刷新规则

## 8. 总结

本阶段最重要的结论不是“找到了可晋级方案”，而是明确排除了几条看似合理但实际无效的微调路线。

`v7-v10` 收口后，应当：

- 以 calibrated `v7` 作为当前 reference
- 停止继续试 guard 家族与 narrow-head mapping 家族
- 若继续研究，转向新的单维方向，优先考虑 `turnover suppression / slower refresh`
