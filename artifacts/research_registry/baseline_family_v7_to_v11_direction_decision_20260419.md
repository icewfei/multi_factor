# baseline family v7-v11 阶段性方向判断

## 1. 结论

结论先行：

- **这条 baseline 家族已经不值得继续微调。**
- **后续不应继续在 `v7` 附近做 guard / weight penalty / extraction / refresh rule 的小修小补。**
- **下一条新方向应切换到一条真正不同的 score family。**

工程侧同时收口：

- `signal_date_chunk_size` 默认值继续固定为 `5`
- `chunk` 不再作为研究变量继续试验

## 2. 当前有效 reference

当前仍应以 **calibrated `v7`** 作为 baseline 家族的唯一有效 reference：

- `candidate_scheme_id = baseline_momentum_v7_liquidity_guard70`
- `research_round_id = rr_baseline_liquidity_guard70_20260418`
- `snapshot_id = warehouse_20260418_181408`

关键指标：

- `annual_relative_return = -0.06976572569304007`
- `relative_ir = -0.5287021621315882`
- `max_drawdown = -0.3968114993586318`
- `avg_cash_weight = 0.7919965084907071`
- `avg_invested_weight = 0.2080034915092814`
- `avg_turnover_daily = 0.09811299793683326`
- `topk_perturbation_pass = false`
- `cost_stress_pass = false`

## 3. v7-v11 结果摘要

### 3.1 v7 recalibrated

定位：

- 修正 `amount` 单位与 `liquidity_rank` 方向之后的校准 reference

阶段结论：

- 低流动性暴露假象已基本澄清
- 剩余问题是：
  - gross edge 偏弱
  - cutoff 附近分离太薄
  - turnover / cost 拖累明显

### 3.2 v8 universe liquidity guard

结论：

- 与 `v7` 本质等价
- 说明同阈值 guard 前移到 universe 边界没有产生新信息

### 3.3 v9 liquidity weight penalty

结论：

- 在冻结 `v7` 选股边界下，只做组合内流动性权重惩罚没有改善
- 策略指标和稳定性都未改善

### 3.4 v10 broadened head extraction

结论：

- 在冻结 `v7` score + guard 的前提下，仅在同一窄 head slice 内做 rank-decay extraction 没有改善
- 略微降低了部分低流动性指标，但没有转化成更好的 relative return / IR / drawdown

### 3.5 v11 turnover suppression

结论：

- `sticky_top20_hold_band_v1` 没有改善 calibrated `v7`
- 关键对比：
  - `annual_relative_return`: `-0.06977 -> -0.07196`
  - `relative_ir`: `-0.52870 -> -0.54399`
  - `max_drawdown`: `-0.39681 -> -0.42376`
  - `avg_turnover_daily`: `0.09811 -> 0.09992`
  - `topk_perturbation_pass`: 仍为 `false`
  - `cost_stress_pass`: 仍为 `false`

阶段判断：

- 只靠在当前 score family 上加一个固定保留带，不能解决弱 edge 和成本问题

## 4. 为什么应停止继续微调 baseline 家族

### 4.1 已经试过的单维方向足够多

`v7-v11` 已经覆盖了这条 baseline 家族最自然的几类单维改动：

- stronger ranking guard
- same-threshold universe guard
- liquidity weight penalty
- fixed extraction smoothing
- turnover suppression / slower refresh

这些方向都没有把 calibrated `v7` 推到可晋级状态。

### 4.2 剩余问题不再像是“局部参数没调对”

当前证据更支持：

- signal 本身有弱 edge，但太薄
- 不是某个 guard 阈值、某个 extraction 公式、某个 retain band 的局部错误
- 继续在这条 family 上微调，信息增量已经明显递减

### 4.3 继续微调会明显提高研究自由度

若再继续开 `v12+`，大概率就会滑向：

- 更多 hold-band 阈值
- 更多 extraction 公式
- 更多 turnover suppression 规则
- guard / refresh / penalty 交叉组合

这会快速抬升研究空间，过拟合风险显著上升。

## 5. 工程结论

当前工程基线应固定为：

- `signal_date_chunk_size = 5`
- `max_threads = 8`
- `memory_limit_gb = 20`

说明：

- `build_run_state_skeleton.py` 默认值已经是 `5`
- `artifacts/run_state/README.md` 也已写成 `5`
- 当前不需要再改回；它已经处于正确状态

## 6. 下一条新方向建议

### 建议：切换到真正不同的 score family

不建议继续在当前 momentum-only baseline family 上做局部微调。

下一条应尝试：

- **真正不同的 signal family**

例如优先考虑以下两类之一：

1. **quality / profitability family**
- ROE / ROA / gross margin / operating profitability / accrual quality
- 理由：
  - 与当前 momentum-only 家族机制差异大
  - 更可能带来新的 edge 结构，而不是在旧 edge 上抹参数

2. **value / investment family**
- earnings yield / book-to-price / cash-flow yield / asset growth / investment restraint
- 理由：
  - 与当前短中期价格动量逻辑足够正交
  - 更适合验证“是否需要全新横截面排序机制”

### 不建议的下一步

- 再开一个 `v12` 去扫 hold band 阈值
- 再开新的 guard 变体
- 再做同一家族内的 weight penalty / extraction 微调

## 7. 推荐的下一动作

最合理的下一步不是直接开跑，而是：

1. 先把 baseline family 正式收口为“已停止继续微调”
2. 选定 **一个** 全新 score family
3. 为该 family 写新的 `candidate_scheme_id` 与 preregistration
4. 继续保持单维研究纪律

## 8. 总结

`v7-v11` 的核心意义，不是找到了可晋级候选，而是证明了：

- calibrated `v7` 是当前 baseline family 中最好的弱方案
- 这条 family 已经被探索到收益递减区间
- 继续微调的研究价值低、过拟合风险高

因此，当前正确决策是：

- **停止继续微调 baseline family**
- **把研究资源转向真正不同的 score family**
