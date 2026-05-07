# VSUMD60 Walk-Forward Regime Diagnosis (2022-2025)

Candidate: `price_volume_single_signal_alpha158_vsumd60_v1`  
Round: `rr_walk_forward_alpha158_vsumd60_v1_20260430`

## Core Conclusion

`vsumd60` 在 `2022-2023` 强、到 `2024-2025` 转弱，**主要不是因为横截面 signal-edge(信号边际优势) 消失了**，而是因为：

1. 它更像一个 **bottom-avoidance / loser-avoidance(避雷型 / 回避弱者型)** 排序信号，而不是一个能在强 beta(高贝塔) 年份里稳定抓到最强领涨头部的 `head-extraction(头部提取)` 信号。
2. 当前 standalone 合约长期维持 `avg_invested_weight(平均投资仓位) ≈ 19%`、`avg_cash_weight(平均现金仓位) ≈ 81%`，在 `2022-2023` 这种 benchmark(基准) 偏弱年份会天然受益，但在 `2024-2025` 这种 benchmark 强上涨年份会被明显 `cash_drag(现金拖累)`。
3. 到 `2025`，部署层稳定性也确实开始变差，不只是“涨得没 benchmark 快”，而是 `relative_ir(相对信息比率)`、月度胜率和收益集中度都一起恶化了。

一句话判断：

**如果问题定义仍然是“在当前 standalone TopK + 高现金占比合约下，把 `vsumd60` 做成一条可晋升主线策略”，那这条线应当止步。**  
**如果问题定义改成“把 `vsumd60` 保留为一个有用的 broad-rank / downside-filter(广谱排序 / 下行过滤) 原子信号”，则可以继续，但不该再沿当前 standalone 主线硬推。**

## What Changed

### 1. 2022-2023 的强，主要来自防守而不是进攻

`walk-forward` 窗口结果：

- `wf_2022`: `annual_relative_return(年化超额收益) = 0.241934`
- `wf_2023`: `annual_relative_return(年化超额收益) = 0.109923`
- `wf_2024`: `annual_relative_return(年化超额收益) = -0.041708`
- `wf_2025`: `annual_relative_return(年化超额收益) = -0.134445`

对应年度绝对收益与 benchmark：

- `2022`: `strategy_return_year(策略年度收益) = -0.001725`, `benchmark_return_year(基准年度收益) = -0.189253`
- `2023`: `strategy_return_year(策略年度收益) = 0.046279`, `benchmark_return_year(基准年度收益) = -0.053432`
- `2024`: `strategy_return_year(策略年度收益) = 0.055698`, `benchmark_return_year(基准年度收益) = 0.099785`
- `2025`: `strategy_return_year(策略年度收益) = 0.105224`, `benchmark_return_year(基准年度收益) = 0.270329`

解释：

- `2022-2023` 胜出，不是因为策略绝对收益特别高，而是因为它**跌得少 / 防守更强**。
- `2024-2025` 转弱，也不是因为策略绝对亏钱；它仍然是正收益，但**涨不过 benchmark**。

### 2. 横截面 IC 没坏，甚至 2024 更强

按年份看 `signal-edge(信号边际优势)`：

- `2022`: `full_sample_corr_ic(全样本IC) = 0.005553`, `avg_daily_ic(平均日IC) = 0.008866`
- `2023`: `full_sample_corr_ic(全样本IC) = 0.008934`, `avg_daily_ic(平均日IC) = 0.010165`
- `2024`: `full_sample_corr_ic(全样本IC) = 0.018070`, `avg_daily_ic(平均日IC) = 0.024686`
- `2025`: `full_sample_corr_ic(全样本IC) = 0.013687`, `avg_daily_ic(平均日IC) = 0.015665`

所以不能把 `2024-2025` 的转弱简单解释成：

> “信号失效了。”

更准确地说：

> **signal 作为 broad ordering(广谱排序) 还在，但当前 portfolio contract(组合合约) 没有把这种排序优势转成对 benchmark 的稳定超额。**

### 3. 真正的问题在 head extraction，而不是全排序

按年份看头部分层：

- `2022`: `avg_label_top10(前10平均标签) = 0.000742`, `avg_label_rank11_20(11-20名平均标签) = 0.002088`, `avg_label_bottom10(后10平均标签) = -0.017718`
- `2023`: `avg_label_top10 = 0.003158`, `avg_label_rank11_20 = 0.004003`, `avg_label_bottom10 = -0.009146`
- `2024`: `avg_label_top10 = 0.004234`, `avg_label_rank11_20 = 0.005059`, `avg_label_bottom10 = -0.023163`
- `2025`: `avg_label_top10 = 0.010296`, `avg_label_rank11_20 = 0.011578`, `avg_label_bottom10 = -0.011566`

这 4 年有一个非常一致的事实：

- `bottom10(后10名)` 明显差，说明它很会识别弱者
- 但 `top10(前10名)` **始终没有显著优于 `11-20名`**

这说明 `vsumd60` 的机制更像：

- 会把“差的东西”排到后面
- 但不太能把“最该重仓的最强赢家”稳定拎到最前面

这在 `2022-2023` 问题不大，因为市场本身更弱，**少踩雷 + 多持现金** 就能赢 benchmark。  
但在 `2024-2025`，如果你抓不到真正最强头部，且仓位又不高，就会明显输给上涨 benchmark。

### 4. 现金拖累是结构性主因，不是偶然噪音

`2022-2025` 各年组合层几乎没变：

- `avg_invested_weight(平均投资仓位)` 都在 `0.1904 ~ 0.1912`
- `avg_cash_weight(平均现金仓位)` 都在 `0.8088 ~ 0.8096`
- `avg_turnover_daily(平均日换手)` 都稳定在 `~0.095`

也就是说：

- `2024-2025` 的转弱，不是因为仓位突然漂了
- 不是因为换手突然失控了
- 而是因为**这套长期低仓位 / 高现金的防守型组合结构，在强 beta 年份天然吃亏**

### 5. 2025 不只是“跑输”，而是稳定性也开始变差

`2025`：

- `annual_relative_return(年化超额收益) = -0.134445`
- `relative_ir(相对信息比率) = -1.114229`
- `positive_relative_days_share(正相对收益日占比) = 0.469136`
- `monthly_positive_ratio(月度正收益占比) = 0.416667`
- `return_concentration_ratio(收益集中度指标) = 0.820864`

这意味着：

- 不只是全年相对收益为负
- 月度层面也偏弱
- 少数好月份贡献了大部分正收益，收益分布开始变脆

所以 `2025` 给出的信号是：

> **当前 standalone 合约下，这个策略的部署稳定性已经不够舒服了。**

## Decision

### 继续还是止步？

建议分两种问题定义来定：

1. 如果目标是：
   **“继续把 standalone `vsumd60` 做成一条可晋升主线策略”**

   结论：**正式止步。**

   原因：
   - 三条单维 family seed 全失败
   - `walk_forward_positive_window_ratio(滚动前推正窗口比例) = 0.5`，低于正式阈值 `0.75`
   - `walk_forward_ir(滚动前推IR) = 0.105110`，低于正式阈值 `0.30`
   - `2024-2025` 显示它不适合当前 standalone 低仓位主线合约

2. 如果目标是：
   **“保留一个有研究价值的原子信号，未来放到不同问题定义里再用”**

   结论：**可以继续保留，但降级处理。**

   更准确的定位应改成：

   - `vsumd60` 是一张 `standalone reserve card(单信号储备卡)`
   - 它更适合被理解为 `broad-rank / downside-filter signal(广谱排序 / 下行过滤信号)`
   - 不适合继续被当成“当前合约下的 standalone 主晋级对象”

## Recommended Next Step

最合理的下一步不是继续磨 `vsumd60` 这条 standalone 线，而是二选一：

1. **正式收口并止步**
   - 把 `vsumd60` 冻结为 `reserve atomic keeper(储备原子信号)`
   - 结束这条 standalone / family seed 研究线

2. **换问题定义后再开新线**
   - 明确承认：当前问题不是 signal 全失效，而是 `head extraction + capital usage(头部提取 + 资本使用)` 不匹配
   - 后续若再研究，必须是新的问题定义，不应再延长当前这条线

我的建议更偏向第 `1` 条：

**把当前 standalone `vsumd60` 主线正式收口，保留信号，不再继续投这条线。**
