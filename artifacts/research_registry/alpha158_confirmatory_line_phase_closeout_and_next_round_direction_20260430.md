# Alpha158 Confirmatory Line Phase Closeout And Next Round Direction

日期：`2026-04-30`

---

## 一句话结论

当前这条 `Alpha158 standalone confirmatory(单信号确认性)` 线，已经完成两个阶段的收缩：

- `price_volume_single_signal_alpha158_vsumd60_v1`
- `price_volume_single_signal_alpha158_corr30_v1`

两者都证明了自己是**高质量的正向原子信号**，但都没有最终晋级成新的确认性主线。

因此，当前阶段的正式结论是：

- `vsumd60 = reserve atomic keeper(储备原子信号)`
- `corr30 = reserve atomic keeper(储备原子信号)`
- `active_confirmatory_winner(活跃确认性赢家) = none`

下一步不再继续细磨这两只，而是切换到一个新的问题定义：

**寻找更高 `avg_invested_weight(平均投资仓位)` 的 head-extraction 候选。**

---

## 1. 本阶段收口

### 1.1 `vsumd60`

阶段判断：

- confirmatory round 1：`KEEP`
- strict confirmatory recheck：`KEEP`
- `walk-forward(滚动前推)`：未达到正式晋级阈值
- standalone 主线：正式结束

为什么收口：

- 它更像 `bottom-avoidance(避雷型)` / `downside-filter(下行过滤型)` 信号
- 不适合继续被当作当前主线策略硬推
- 但保留为 `reserve atomic keeper(储备原子信号)` 是合理的

### 1.2 `corr30`

阶段判断：

- head-extraction shortlist：`KEEP`
- strict confirmatory recheck：`REJECT`

为什么没晋级：

- 它对 `v18` 的 `annual_relative_return(年化超额收益)`、`relative_ir(相对信息比率)`、`max_drawdown(最大回撤)`、`avg_turnover_daily(平均日换手)` 都给出了很干净的改善
- 但 strict gate(严格门槛) 下：
  - `candidate_avg_invested_weight(候选平均投资仓位) = 0.173812`
  - 未达到 `>= 0.18`

因此它的定位应当是：

- **高质量 reserve atomic keeper(高质量储备原子信号)**
- 但不是当前可晋升主线

---

## 2. 阶段性判断

到这里，问题已经很清楚：

- 不是 Alpha158 原子信号里完全没有东西
- 也不是这些信号没有相对 `v18` 的改进
- 真正卡住晋级的，是：
  - `capital deployment intensity(资本部署强度)` 不够高
  - 或者 `turnover(换手)` 代价太高

因此，下一阶段最该改的不是“继续围绕 `vsumd60 / corr30` 做更细的微调”，而是：

**换一个新问题定义，优先找天然更高仓位、同时仍保有 head-extraction(头部提取) 特征的候选。**

---

## 3. 下一轮问题定义

新的 round 不再问：

- 谁在当前低仓位结构里相对 `v18` 更好

而改问：

- **谁有更高 `avg_invested_weight(平均投资仓位)` 潜力，同时仍能保持 head-extraction 的相对优势。**

这意味着下一轮的筛选标准要显式偏向：

- 更高部署强度
- 更少 `cash_drag(现金拖累)`
- 更像“主动押注强者”的排序，而不是“轻仓避弱”

---

## 4. 下一轮 shortlist 方向

建议下一轮只放 `3` 只，保持 confirmatory 预算纪律：

- `price_volume_single_signal_alpha158_imxd5_v1`
- `price_volume_single_signal_alpha158_cord30_v1`
- `price_volume_single_signal_alpha158_imax20_v1`

选择理由：

- `imxd5`：已有较高 `avg_invested_weight(平均投资仓位)` 记录，机制偏 `path-ordering / breakout timing(路径排序 / 突破时序)`
- `cord30`：已有较高 `avg_invested_weight(平均投资仓位)` 记录，且相对 `v18` 的改进幅度大，但此前死在 `turnover(换手)` 约束，值得在新问题定义下重新审视
- `imax20`：机制更偏 `breakout freshness(突破新鲜度)`，与 `corr/cord` 并不完全同质，适合纳入这轮更高仓位导向的 shortlist

---

## 5. 正式动作

当前正式动作是：

1. 冻结 `vsumd60` 为 `reserve atomic keeper(储备原子信号)`
2. 冻结 `corr30` 为 `reserve atomic keeper(储备原子信号)`
3. 结束当前这条 confirmatory 主线
4. 进入新的 round：
   `higher-invested-weight head-extraction shortlist(更高仓位头部提取短名单)`

一句话收口：

**上一阶段证明了“哪些信号是好的”；下一阶段要证明“哪些好的信号，值得真正多上仓位”。**
