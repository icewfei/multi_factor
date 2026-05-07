# Alpha158 CORD30 Turnover-Control Seed Closeout And Pause Decision

日期：`2026-04-30`

---

## 一句话结论

- `confirmatory_alpha158_cord30_seed_refresh_hysteresis15_v1 = REJECT`
- `Alpha158 confirmatory fine-tuning line(确认性微调线) = pause`

也就是说：

**`cord30 turnover control-only(仅换手控制)` 这条唯一被允许追加的单维线已经失败，因此 Alpha158 confirmatory 微调线到这里正式暂停。**

---

## 1. 这次 seed 测了什么

本轮对象是：

- `candidate_scheme_id(候选方案ID) = confirmatory_alpha158_cord30_seed_refresh_hysteresis15_v1`
- `research_round_id(研究轮次ID) = rr_confirmatory_alpha158_cord30_turnover_control_seed_20260430`

它冻结了：

- `price_volume_single_signal_alpha158_cord30_v1` 的原子信号本体
- `TopK = 10`
- 等权提取
- 权重映射
- 执行与成本语义

唯一改变的是：

- `portfolio_refresh_rule(组合刷新规则)`

具体规则是：

- 对现有持仓设置 `rank_position <= 15` 的保留带
- 仅对腾出的空位，用新的高排名股票补满到 `10`

这是一条严格意义上的：

- `turnover control-only(仅换手控制)` 单维问题定义线

---

## 2. 结果为什么判失败

核心结果如下：

- `pass_boolean(布尔通过结果) = false`
- `validation_avg_turnover_daily(验证期平均日换手) = 0.099678`
- `avg_turnover_daily_delta_vs_cord30(相对cord30平均日换手变化) = -0.005080`
- `avg_turnover_daily_delta_vs_v18(相对v18平均日换手变化) = +0.023998`

同时：

- `annual_relative_return_delta_vs_cord30(相对cord30年化超额收益变化) = -0.006430`
- `relative_ir_delta_vs_cord30(相对cord30相对信息比率变化) = -0.035924`
- `max_drawdown_delta_vs_cord30(相对cord30最大回撤变化) = +0.002549`
- `avg_invested_weight(平均投资仓位) = 0.199466`

这说明它有两个特点：

1. **方向是对的**
- 换手确实下降了
- 回撤也略有改善

2. **力度不够**
- 相对 standalone `cord30`，换手只降了 `0.005080`
- prereg 目标要求至少 `<= -0.01`
- 相对 `v18`，换手仍然高出 `0.023998`
- strict gate(严格门槛) 要求 `<= 0.02`

所以这次失败不是因为：

- `cord30` 信号失效
- 收益或 IR 全面塌掉

而是因为：

**这条 `refresh_hysteresis15(刷新迟滞15)` 工具虽然有效，但不足以把换手真正压回治理要求之内。**

---

## 3. 这次失败意味着什么

它意味着两件事。

### 3.1 对 `cord30`

`cord30` 的定位不变：

- `price_volume_single_signal_alpha158_cord30_v1 = high-quality reserve atomic keeper(高质量储备原子信号)`

因为它的问题仍然高度聚焦：

- 不是信号质量差
- 不是仓位不够
- 而是部署后的 `turnover(换手)` 约束没有被解决

### 3.2 对 Alpha158 confirmatory 线

更重要的是：

此前已经正式写过一条治理承诺：

- 只允许再开 **1 条** `turnover control-only(仅换手控制)` 新线
- **如果这条线仍失败，就正式暂停 Alpha158 confirmatory 微调线**

现在这条唯一获准的新线已经失败，因此治理上不应再继续：

- 扩新的 Alpha158 confirmatory shortlist
- 围绕 `cord30` 再开第 2 条、第 3 条换手微调线
- 把同一问题换个小参数继续磨

---

## 4. 正式阶段决策

当前正式决策是：

1. `confirmatory_alpha158_cord30_seed_refresh_hysteresis15_v1 = REJECT`
2. `price_volume_single_signal_alpha158_cord30_v1` 继续保留为 `high-quality reserve atomic keeper(高质量储备原子信号)`
3. `strict_confirmatory_winner(严格确认性赢家) = none`
4. `Alpha158 confirmatory fine-tuning line(确认性微调线) = pause`

这意味着：

- **暂停的是 Alpha158 confirmatory 微调线**
- **不是否定 Alpha158 原子层曾经发现过的信息**
- 更不是把 `cord30 / corr30 / vsumd60` 从 reserve 池中删除

---

## 5. 下一步边界

暂停之后，下一步不应再做：

- `cord30` 的第 2 条 turnover seed
- `corr30` 的重新 strict recheck
- 新一轮 Alpha158 confirmatory 微调 shortlist

暂停之后，允许做的只有两类事：

1. 将已有 Alpha158 结果保留为 `reserve atomic keepers(储备原子信号池)`
2. 转去新的问题定义，而不是继续在当前 Alpha158 confirmatory 微调线上打磨

---

## 6. 决策句

**`cord30 turnover-control seed` 已失败，且这正是此前被允许的唯一额外单维 follow-up(后续跟进)；因此，Alpha158 confirmatory 微调线到此正式暂停。**
