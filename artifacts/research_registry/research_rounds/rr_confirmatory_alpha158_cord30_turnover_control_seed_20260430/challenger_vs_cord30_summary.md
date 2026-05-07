# CORD30 Turnover-Control Seed Results

生成时间: 2026-04-30T16:30:51+08:00

## 候选方案

- `candidate_scheme_id(候选方案ID) = confirmatory_alpha158_cord30_seed_refresh_hysteresis15_v1`
- `changed_dimension(唯一变化维度) = portfolio_refresh_rule(组合刷新规则)`
- `refresh_rule(刷新规则) = refresh_hysteresis15(holder ≤ rank 15 保留, 空缺最高分补足到 10)`

## 布尔通过

- `pass_boolean(布尔通过结果) = false`

## Challenger 验证期绝对指标

- `validation_annual_relative_return(验证期年化超额收益) = -0.122068`
- `validation_relative_ir(验证期相对信息比率) = -0.905926`
- `validation_max_drawdown(验证期最大回撤) = -0.053158`
- `validation_avg_turnover_daily(验证期平均日换手) = 0.099678`
- `validation_avg_invested_weight(验证期平均投资仓位) = 0.199466`

## vs standalone CORD30

- `annual_relative_return_delta_vs_cord30 = -0.006430`
- `relative_ir_delta_vs_cord30 = -0.035924`
- `max_drawdown_delta_vs_cord30 = 0.002549`
- `avg_turnover_daily_delta_vs_cord30 = -0.005080`

Reference cord30 annual_relative_return: -0.115638
Reference cord30 avg_turnover_daily: 0.104758

## vs v18 (外部锚点)

- `annual_relative_return_delta_vs_v18 = 0.152775`
- `relative_ir_delta_vs_v18 = 0.997450`
- `max_drawdown_delta_vs_v18 = 0.345631`
- `avg_turnover_daily_delta_vs_v18 = 0.023998`

Reference v18 annual_relative_return: -0.274842
Reference v18 avg_turnover_daily: 0.075680

## 布尔条件逐项检查

- vs CORD30: avg_turnover_daily_delta <= -0.01 → False
- vs CORD30: annual_relative_return_delta >= -0.02 → True
- vs CORD30: relative_ir_delta >= -0.10 → True
- vs CORD30: max_drawdown_delta >= -0.02 → True
- vs v18: annual_relative_return_delta > 0.10 → True
- vs v18: relative_ir_delta > 0.50 → True
- vs v18: max_drawdown_delta >= 0.10 → True
- vs v18: avg_turnover_daily_delta <= 0.02 → False
- avg_invested_weight >= 0.18 → True
