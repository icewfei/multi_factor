# fixed_test Artifacts

建议路径：

- `artifacts/fixed_test/<run_id>/`

最低预留产物：

- `backtest_daily.csv`
- `metrics.json`
- `holdings.csv`
- `portfolio_weights_daily.csv`
- `portfolio_daily_summary.csv`
- `annual_return_table.csv`
- `holding_period_return_distribution.csv`
- `topk_perturbation_summary.json`
- `trade_statistics_summary.json`
- `data_quality_audit.json`
- `data_contract_summary.json`
- `audit_summary.json`
- `cash_source_explanation.csv`
- `low_liquidity_exposure_summary.json`
- `cost_stress_summary.json`
- `return_attribution_summary.json`

补充说明：

- `data_contract_summary.json`：固定测试使用的数据口径、环境、snapshot 与 benchmark 基线摘要。
- `audit_summary.json`：固定测试层对 warning / blocker / 低流动性暴露 / 成本 stress / TopK 轻扰动的聚合审计摘要。
- `cash_source_explanation.csv`：现金保留的主要来源解释，至少区分 `NO_SIGNAL`、`SUSPENSION`、`LIMIT_UP_UNBUYABLE`、`FILTERED_OUT`。
- `low_liquidity_exposure_summary.json`：低流动性暴露与贡献摘要，当前属于 near-formal 审计口径。
- `cost_stress_summary.json`：固定测试层的简版成本 stress 结果。
- `return_attribution_summary.json`：固定测试层的简版 benchmark / 现金拖累 / 选股 alpha 归因摘要。
