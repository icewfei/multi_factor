# v17 Turnover / Cost Decomposition (20260422)

Candidate: `price_volume_v17_head_extraction_smoothing`
Research round: `rr_price_volume_head_extraction_smoothing_family_20260422`

## Headline

- `annual_relative_return(年化超额收益) = -0.047056`
- `relative_ir(相对信息比率) = -0.409567`
- `max_drawdown(最大回撤) = -0.282662`
- `avg_turnover_daily(平均日换手) = 0.109358`
- `cost_stress_annual_relative_return(成本压力年化超额收益) = -0.098385`
- `annual_relative_cost_drag(年化超额收益成本拖累) = -0.051329`

## Turnover Decomposition

- `replacement_turnover_component_total(替换型换手总量) = 71.239394`
- `incumbent_resize_component_total(存量调权换手总量) = 283.481818`
- `replacement_share_of_component_flow(替换型换手占组件流量比) = 0.200832`
- `incumbent_resize_share_of_component_flow(存量调权换手占组件流量比) = 0.799168`
- `post_warmup_replacement_share_of_component_flow(剔除建仓期后替换型换手占比) = 0.200858`
- `post_warmup_incumbent_resize_share_of_component_flow(剔除建仓期后存量调权换手占比) = 0.799142`

## Daily Pattern

- `entry_only_days(仅进场日数) = 1`
- `exit_only_days(仅退出日数) = 1`
- `mixed_replacement_days(同时换入换出日数) = 4562`
- `resize_active_days(存在存量调权日数) = 6297`
- `median_turnover_daily(中位日换手) = 0.111111`
- `p90_turnover_daily(日换手90分位) = 0.112121`
- `p99_turnover_daily(日换手99分位) = 0.133333`

## Cost Drag Interpretation

- `annualized_turnover_proxy(年化换手代理) = 27.558131`
- `drag_per_1x_annual_turnover(每1倍年化换手的成本拖累代理) = 0.001863`
- `topk_perturbation_pass(TopK扰动通过) = false`
- `cost_stress_pass(成本压力通过) = false`

## Diagnosis

- Main source: `incumbent_resize`
- Post-warmup main source: `incumbent_resize`
- Summary: Turnover is dominated by incumbent resize flow rather than pure entry/exit replacement flow.
