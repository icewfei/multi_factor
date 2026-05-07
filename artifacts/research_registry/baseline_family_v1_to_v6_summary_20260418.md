# Baseline Family v1-v6 阶段性总结

更新时间：
- `2026-04-18`

范围：
- `baseline_reversal_momentum_lowvol_liquidity_v1`
- `baseline_reversal_momentum_lowvol_v2`
- `baseline_reversal_momentum_v3`
- `baseline_momentum_v4`
- `baseline_momentum_lowvol_v5`
- `baseline_momentum_v6_liquidity_guard`

共同边界：
- 共享数据源：`warehouse_20260413_165753`
- 执行逻辑：`warehouse_execution_v3`
- 运行环境：`/opt/anaconda3/envs/quant_trade`
- `TopK = 10`
- 全部方案均按单维改动登记并完成 full-chain、组合层与 fixed test

## 1. 结论先行

- `v1-v6` 这一整条 baseline 家族，截至目前**全部仍为 `weak_candidate`**。
- 当前最好的方案是 `baseline_momentum_v6_liquidity_guard`。
- `v6` 相比 `v4` 已经明显改善：
  - `annual_relative_return`
  - `relative_ir`
  - `max_drawdown`
  - `low_liquidity_alpha_contribution_share`
- 但 `v6` 仍未跨过 fixed test 的正式晋级门槛：
  - `low_liquidity_flag_high = true`
  - `topk_perturbation_pass = false`
  - `cost_stress_pass = false`
- 因此，本家族当前最合理的状态是：
  - 工程链路已稳定
  - 研究方向已收敛出“低流动性暴露”这个主问题
  - 不应把 `v6` 直接晋级主线

## 2. 工程结论

run-state 主链路实测用时：

| 版本 | candidate_scheme_id | chunk | run-state 用时 |
| --- | --- | ---: | ---: |
| v1 | `baseline_reversal_momentum_lowvol_liquidity_v1` | 500 | 1h 10m 24s |
| v2 | `baseline_reversal_momentum_lowvol_v2` | 500 | 1h 12m 14s |
| v3 | `baseline_reversal_momentum_v3` | 300 | 45m 11s |
| v4 | `baseline_momentum_v4` | 100 | 16m 16s |
| v5 | `baseline_momentum_lowvol_v5` | 50 | 8m 30s |
| v6 | `baseline_momentum_v6_liquidity_guard` | 10 | 4m 43s |

阶段性工程判断：
- 在当前脚本、当前数据规模和当前硬件上，`signal_date_chunk_size = 10` 的工程表现最好。
- 因此项目默认 `run_state` chunk 已正式收敛到 `10`。
- 这属于工程基线，不属于策略自由度。

## 3. 方案对比

| 版本 | 方案主键 | 单维改动 | annual_relative_return | relative_ir | max_drawdown | avg_cash_weight | avg_invested_weight | low_liquidity_weight_share | low_liquidity_alpha_contribution_share | TopK 扰动 | 成本 stress | 当前状态 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| v1 | `baseline_reversal_momentum_lowvol_liquidity_v1` | 基线四因子分数 | -0.1225 | -0.7294 | -0.5613 | 0.8685 | 0.1315 | 1.0000 | 1.3685 | fail | fail | weak |
| v2 | `baseline_reversal_momentum_lowvol_v2` | 去掉 `liquidity_20d_raw` | -0.1233 | -0.7609 | -0.6037 | 0.8493 | 0.1507 | 0.9973 | 1.4341 | fail | fail | weak |
| v3 | `baseline_reversal_momentum_v3` | 去掉 `volatility_20d_raw` | -0.1464 | -0.9011 | -0.7870 | 0.8263 | 0.1737 | 0.9970 | 1.9002 | fail | fail | weak |
| v4 | `baseline_momentum_v4` | 去掉 `reversal_5d_raw` | -0.0775 | -0.5073 | -0.4468 | 0.8614 | 0.1386 | 0.9991 | 1.0039 | fail | fail | weak |
| v5 | `baseline_momentum_lowvol_v5` | 在 `v4` 上加回 `volatility_20d_raw` | -0.1016 | -0.6804 | -0.6066 | 0.8154 | 0.1846 | 0.9988 | 0.8232 | fail | fail | weak |
| v6 | `baseline_momentum_v6_liquidity_guard` | 在 `v4` 上加流动性 guard | -0.0595 | -0.4176 | -0.4256 | 0.8619 | 0.1381 | 1.0000 | 0.6719 | fail | fail | weak |

## 4. 路径复盘

### 4.1 从 v1 到 v3

- `v1 -> v2`：
  - 单纯移除 `liquidity_20d_raw`，没有真正改善低流动性依赖。
  - 说明问题不只是“一个流动性特征进了分数”，而更像是整体选股结果本身就偏向低流动性样本。
- `v2 -> v3`：
  - 再去掉低波后，表现显著恶化。
  - 说明当时的低波并不是主要问题，反而可能在一定程度上起到缓冲作用。

### 4.2 v4 是第一个明显改善点

- `v4` 的 momentum-only 明显优于 `v3`：
  - 相对收益改善
  - 相对 IR 改善
  - 回撤改善
- 因此 `v4` 是当前家族里第一个真正可作为“结构参考”的版本。

### 4.3 v5 回撤了 v4 的进展

- 在 `v4` 基础上加回低波，表现整体退步。
- 这说明对当前家族而言，“momentum-only” 比 “momentum + lowvol” 更贴近可用方向。

### 4.4 v6 是目前最强 challenger

- `v6` 沿用 `v4` 的分数，不改 score，只在 ranking universe 上加流动性 guard。
- 这让它比 `v4` 得到了更好的：
  - `annual_relative_return`
  - `relative_ir`
  - `max_drawdown`
  - `low_liquidity_alpha_contribution_share`
- 这说明“问题更可能出在入选样本边界，而不是 score 本身的主方向”。

## 5. 为什么 v6 仍不能晋级

因为它虽然改善了，但还没有过最关键的审计门槛：

- `low_liquidity_flag_high = true`
- `topk_perturbation_pass = false`
- `cost_stress_pass = false`

制度含义：
- `v6` 可被视为“当前 baseline 家族中的最好版本”
- 但只能作为后续研究的参考起点
- 不能被视为确认性通过方案
- 更不能直接进入 `walk-forward` 或主线晋升

## 6. 后续建议

- 工程层：
  - 默认保持 `signal_date_chunk_size = 10`
  - 不再把 chunk 作为研究变量反复试探
- 研究层：
  - 后续新方案应继续坚持单维改动
  - 新方案优先围绕“如何继续降低低流动性依赖、同时不恶化扰动稳定性与成本 stress”展开
- 治理层：
  - 本家族后续若继续扩展，应以 `v6` 作为最新参考弱方案
  - 不得回头重写 `v1-v6` 的失败证据

## 7. 当前正式结论

- `v1-v6` 全部保留为失败或弱方案证据
- `v6` 是当前最优弱方案
- baseline 家族尚未出现可晋级候选
- 研究下一步应转向“结构性降低低流动性暴露”的下一代单维改动
