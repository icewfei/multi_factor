# v16 Signal-Edge + Head-Slice Diagnosis (20260422)

Candidate: `price_volume_v16_remove_trend_consistency`
Research round: `rr_price_volume_remove_trend_consistency_family_20260422`
Generated at: `2026-04-22T14:10:55+08:00`

## Signal Edge

- `full_sample_corr_ic(全样本IC)`: `0.013345`
- `avg_daily_ic(平均日IC)`: `0.020658`
- `median_daily_ic(中位日IC)`: `0.017744`
- `positive_daily_ic_share(正IC日占比)`: `0.55822`

## Head Slice

- `avg_label_top10(前10平均标签)`: `0.006814`
- `avg_label_rank11_20(11-20名平均标签)`: `0.006295`
- `avg_label_bottom10(后10平均标签)`: `0.000516`
- `top10_minus_rank11_20(前10减11-20)`: `0.000519`
- `avg_rank10_11_score_gap(第10/11名平均分数间距)`: `0.002006`
- `median_rank10_11_score_gap(第10/11名中位分数间距)`: `0.001284`
- `days_gap_lt_0_005(间距<0.005的天数)`: `5731` / `6302`
- `days_gap_lt_0_001(间距<0.001的天数)`: `2613` / `6302`

## Fixed Test

- `annual_relative_return(年化超额收益)`: `-0.058891`
- `relative_ir(相对信息比率)`: `-0.426748`
- `max_drawdown(最大回撤)`: `-0.403702`
- `avg_turnover_daily(平均日换手)`: `0.074052`
- `avg_cash_weight(平均现金权重)`: `0.841918`
- `avg_invested_weight(平均投资仓位)`: `0.158082`
- `low_liquidity_weight_share(低流动性权重占比)`: `0.150159`
- `topk_perturbation_pass(TopK扰动通过)`: `false`
- `cost_stress_pass(成本压力通过)`: `false`
- `cost_stress_annual_relative_return(成本压力年化超额收益)`: `-0.093452`

## Diagnosis

`v16` now shows a cleaner positive `signal_edge(信号边际优势)` than `v15`, and `avg_label_top10(前10平均标签)` is finally above `avg_label_rank11_20(11-20名平均标签)`. That means the family direction itself is no longer the main problem.

The remaining issue is that `head_slice(头部切片)` is still thin: `avg_rank10_11_score_gap(第10/11名平均分数间距)` remains small, and most days still sit in a narrow cutoff band. That matches the continued failure of `topk_perturbation_pass(TopK扰动通过)` and `cost_stress_pass(成本压力通过)`.

## Suggested Next Step

Prefer a `portfolio_extraction_only(仅组合提取)` challenger for `v17`: keep the `v16` two-signal family fixed, and change only how score ranks inside the selected head are converted into capital allocation.
