# rr_confirmatory_alpha158_vsumd60_round2_strict_recheck_20260429 results

- `candidate_scheme_id(候选方案ID) = price_volume_single_signal_alpha158_vsumd60_v1`
- `round_decision(轮次结论) = KEEP`
- `pass_boolean(布尔通过) = true`

## Validation Deltas

- `annual_relative_return_delta(年化超额收益变化) = 0.151895`
- `relative_ir_delta(相对信息比率变化) = 0.993775`
- `max_drawdown_delta(最大回撤变化) = 0.348097`
- `avg_turnover_daily_delta(平均日换手变化) = 0.019115`
- `candidate_avg_invested_weight(候选平均持仓权重) = 0.189870`

## Subperiod Rechecks

- `validation_h1_2019_2020h1`
  - `annual_relative_return_delta(年化超额收益变化) = 0.161858`
  - `relative_ir_delta(相对信息比率变化) = 0.801780`
- `validation_h2_2020h2_2021`
  - `annual_relative_return_delta(年化超额收益变化) = 0.211317`
  - `relative_ir_delta(相对信息比率变化) = 1.199143`

## Stress And Robustness

- `cost_stress_annual_relative_return_delta(成本压力年化超额收益变化) = 0.013052`
- `low_liquidity_weight_share_delta(低流动性权重占比变化) = -0.040169`
- `topk8_annual_relative_return_delta(TopK=8年化超额收益变化) = 0.026527`
- `topk12_annual_relative_return_delta(TopK=12年化超额收益变化) = 0.015647`

## Rule

- `(validation_annual_relative_return_delta > 0.10) AND (validation_relative_ir_delta > 0.50) AND (validation_max_drawdown_delta >= 0.10) AND (validation_avg_turnover_daily_delta <= 0.02) AND (candidate_avg_invested_weight >= 0.18) AND (validation_h1_annual_relative_return_delta > 0) AND (validation_h1_relative_ir_delta > 0) AND (validation_h2_annual_relative_return_delta > 0) AND (validation_h2_relative_ir_delta > 0) AND (cost_stress_annual_relative_return_delta > 0) AND (low_liquidity_weight_share_delta <= 0) AND (topk8_annual_relative_return_delta > 0) AND (topk12_annual_relative_return_delta > 0)`
