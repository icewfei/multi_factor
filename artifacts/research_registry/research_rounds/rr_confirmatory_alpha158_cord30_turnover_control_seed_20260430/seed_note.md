# CORD30 Turnover Control-Only Seed

日期：`2026-04-30`

## 一句话定义

- `candidate_scheme_id(候选方案ID) = confirmatory_alpha158_cord30_seed_refresh_hysteresis15_v1`
- `changed_dimension(唯一变化维度) = portfolio_refresh_rule(组合刷新规则)`

这条线只问一个问题：

**在不改变 `price_volume_single_signal_alpha158_cord30_v1` 原子信号本体的前提下，能否只靠一条更克制的 `refresh_hysteresis(刷新迟滞)` 规则，把 `avg_turnover_daily(平均日换手)` 压回 strict gate(严格门槛) 所需区间，而不显著伤害已经确认过的 `annual_relative_return(年化超额收益)` / `relative_ir(相对信息比率)` / `max_drawdown(最大回撤)` 边际优势。**

## 固定设计

- 保持 `alpha158_cord30_raw` 排序不变
- 保持 `TopK = 10` 不变
- 保持等权提取、权重映射、执行语义不变
- 只把跨日刷新规则改成：
  `retain incumbent if rank_position <= 15; refill remaining slots from highest-ranked eligible non-held names`

## 通过目标

这条 seed 不是为了“略微更好”，而是为了同时满足两层要求：

- 相对 standalone `cord30`：换手要明显下降，且不能显著伤害核心边际优势
- 相对 `v18`：要把 `validation_avg_turnover_daily_delta(验证期平均日换手变化)` 压回 `<= 0.02` 的 strict gate 区间，同时继续守住收益、IR、回撤和仓位底线
