# rr_confirmatory_alpha158_cord30_round5_strict_recheck_20260430 results

- `candidate_scheme_id(候选方案ID) = price_volume_single_signal_alpha158_cord30_v1`
- `round_decision(轮次结论) = REJECT`
- `pass_boolean(布尔通过) = false`

## Validation Deltas

- `annual_relative_return_delta(年化超额收益变化) = 0.159204`
- `relative_ir_delta(相对信息比率变化) = 1.033374`
- `max_drawdown_delta(最大回撤变化) = 0.343081`
- `avg_turnover_daily_delta(平均日换手变化) = 0.029079`
- `candidate_avg_invested_weight(候选平均持仓权重) = 0.209712`

## Subperiod Rechecks

- `validation_h1_2019_2020h1`
  - `annual_relative_return_delta(年化超额收益变化) = 0.187487`
  - `relative_ir_delta(相对信息比率变化) = 0.947210`
- `validation_h2_2020h2_2021`
  - `annual_relative_return_delta(年化超额收益变化) = 0.203921`
  - `relative_ir_delta(相对信息比率变化) = 1.133878`

## Stress And Robustness

- `cost_stress_annual_relative_return_delta(成本压力年化超额收益变化) = 0.030245`
- `low_liquidity_weight_share_delta(低流动性权重占比变化) = -0.032832`
- `topk8_annual_relative_return_delta(TopK=8年化超额收益变化) = 0.052347`
- `topk12_annual_relative_return_delta(TopK=12年化超额收益变化) = 0.040713`

## Rule

- `(validation_annual_relative_return_delta > 0.10) AND (validation_relative_ir_delta > 0.50) AND (validation_max_drawdown_delta >= 0.10) AND (validation_avg_turnover_daily_delta <= 0.02) AND (candidate_avg_invested_weight >= 0.18) AND (validation_h1_annual_relative_return_delta > 0) AND (validation_h1_relative_ir_delta > 0) AND (validation_h2_annual_relative_return_delta > 0) AND (validation_h2_relative_ir_delta > 0) AND (cost_stress_annual_relative_return_delta > 0) AND (low_liquidity_weight_share_delta <= 0) AND (topk8_annual_relative_return_delta > 0) AND (topk12_annual_relative_return_delta > 0)`
