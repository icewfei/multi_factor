# Alpha158 CORR30 + CORD30 Dual-Signal Family

日期：`2026-04-30`

## 一句话定义

- `research_round_id(研究轮次ID) = rr_alpha158_corr30_cord30_dual_signal_family_20260430`
- `candidate_scheme_id(候选方案ID) = alpha158_corr30_cord30_dual_signal_family_v1`

这条线不是继续磨 `cord30` 单信号，也不是恢复 Alpha158 confirmatory 微调线。

这条线要验证的是：

**如果单信号 `TopK + 等权 + 全刷新` 的高换手问题有明显结构性，那么把 `corr30` 和 `cord30` 这两张机制相近但不完全同质的 reserve atomic keepers(储备原子信号) 做最小双信号融合，是否能仅凭“评分面更平滑”本身，把换手压下来。**

## 固定设计

- 只改 `score_family(评分家族)`
- 采用：
  `mean(percentile_rank(alpha158_corr30_raw DESC), percentile_rank(alpha158_cord30_raw DESC))`
- 保持：
  - `TopK = 10`
  - `equal_weight(等权)`
  - `full_daily_refresh(全日刷新)`
  - 其他执行和成本契约不变

## 为什么先不放 `vsumd60`

`vsumd60` 仍保留为 `reserve atomic keeper(储备原子信号)`，但它更偏 `bottom-avoidance(避雷型)` / `cash-drag(现金拖累)` 问题。

这第一条 family seed 要先回答的是：

**head-extraction(头部提取) 信号之间的最小融合，能不能先把结构性换手问题降下来。**
