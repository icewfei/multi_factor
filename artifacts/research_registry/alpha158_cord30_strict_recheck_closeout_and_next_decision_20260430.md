# Alpha158 CORD30 Strict Recheck Closeout And Next Decision

日期：`2026-04-30`

---

## 一句话结论

- `price_volume_single_signal_alpha158_cord30_v1 = high-quality reserve atomic keeper(高质量储备原子信号)`
- `strict_confirmatory_winner(严格确认性赢家) = none`

`cord30` 已经证明自己是**很强的正向原子信号**，但在当前严格治理口径下，它仍然没有晋级成新的严格确认性主线赢家。

---

## 1. 为什么 `cord30` 只能停在 reserve

`cord30` 的强项非常明确：

- `validation_annual_relative_return_delta(验证期年化超额收益变化) = +0.159204`
- `validation_relative_ir_delta(验证期相对信息比率变化) = +1.033374`
- `validation_max_drawdown_delta(验证期最大回撤变化) = +0.343081`
- `candidate_avg_invested_weight(候选平均投资仓位) = 0.209712`

而且它在严格复核下：

- 前后两个验证子阶段都保持正向
- `cost_stress_annual_relative_return_delta(成本压力年化超额收益变化) > 0`
- `low_liquidity_weight_share_delta(低流动性权重占比变化) < 0`
- `topk8 / topk12 perturbation(TopK扰动)` 也保持正向

这说明：

**`cord30` 不是“脆弱的偶然结果”，而是一只真正有质量的 atomic keeper(原子保留信号)。**

但它最终没过 strict gate(严格门槛) 的原因也同样清楚：

- `validation_avg_turnover_daily_delta(验证期平均日换手变化) = +0.029079`
- 严格门槛要求 `<= 0.02`

因此，它当前的准确定位是：

- **不是主线赢家**
- **不是失败品**
- **而是高质量 reserve atomic keeper(高质量储备原子信号)**

---

## 2. 当前阶段正式判断

到这里，Alpha158 confirmatory 线已经给出了一个稳定结论：

- `vsumd60`：能过确认，但止步于 `walk-forward(滚动前推)` / 主线部署问题
- `corr30`：能过 shortlist(短名单)，止步于 strict recheck 的 `avg_invested_weight(平均投资仓位)` 门槛
- `cord30`：能过更高仓位 shortlist，止步于 strict recheck 的 `turnover(换手)` 门槛

所以当前并不是：

- “完全没有好信号”

而是：

- **有高质量信号，但它们分别卡在不同的部署约束上，还没有合成一个 strict-confirmatory winner(严格确认性赢家)。**

---

## 3. 下一步二选一

现在只剩两个合理动作：

### 选项 A：暂停这条 Alpha158 confirmatory 线

适用条件：

- 如果我们认为当前这条线已经充分证明：
  - Alpha158 原子层有信息
  - 但在现合约和现治理门槛下，继续细磨边际回报很低

优点：

- 及时止损
- 避免继续在同一问题上反复打磨

缺点：

- 会放弃一个已经很接近 strict winner 的 `cord30`

### 选项 B：只开一条 `turnover control(换手控制)` 新问题定义线

适用条件：

- 如果我们承认 `cord30` 的唯一剩余主问题已经非常聚焦：
  - **不是收益不够**
  - **不是仓位不够**
  - **而是换手偏高**

允许的唯一研究问题应当写成：

> 在不改变 `cord30` 原子信号本体的前提下，能否只通过 `turnover control(换手控制)` 这一维，把 `validation_avg_turnover_daily_delta(验证期平均日换手变化)` 从 `+0.029079` 压到 strict gate 所需区间，而不显著伤害它已经确认过的 return / IR / drawdown edge(收益/IR/回撤边际优势)？

优点：

- 问题非常干净
- 只改一个维度，治理上最容易守住
- 是当前最接近 strict winner 的一条线

缺点：

- 如果这一条也失败，就应当正式停止 Alpha158 confirmatory 微调线

---

## 4. 推荐决策

推荐：

**不开泛化新线，不再扩 shortlist，只允许一条 `turnover control(换手控制)` 单维新问题定义线。**

原因：

- `cord30` 已经足够强，不值得直接丢掉
- 但也不值得重新开大池或继续多维细磨
- 当前剩余问题已经被收缩成了一个非常明确、非常可审计的单维问题

因此，推荐动作是：

1. 将 `cord30` 正式标注为 `high-quality reserve atomic keeper(高质量储备原子信号)`
2. 当前仍声明 `strict_confirmatory_winner = none`
3. 只允许再开 **1 条** `turnover control-only(仅换手控制)` 新线
4. 如果这条线失败，正式暂停 Alpha158 confirmatory 微调线

---

## 5. 决策句

**当前不应直接暂停 Alpha158 confirmatory 线，而应只再允许 1 条以 `turnover control(换手控制)` 为唯一维度的新问题定义线；若仍失败，则正式暂停。**
