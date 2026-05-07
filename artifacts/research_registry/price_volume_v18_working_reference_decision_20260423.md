`price_volume_v18_refresh_hysteresis` 自 `2026-04-23` 起冻结为当前 price-volume 主线的 `working_reference(工作基准)`。

冻结理由：

- 在 `v16-v20` 范围内，`v18` 保持了最好的综合平衡：
  - `annual_relative_return(年化超额收益) = -0.044142`
  - `relative_ir(相对信息比率) = -0.402481`
  - `max_drawdown(最大回撤) = -0.277201`
- `v19` 的 `extraction_stability_cap(提取稳定性上限)` 没有压低 `avg_turnover_daily(平均日换手)`。
- `v20` 的 `piecewise_bucket_extraction(分桶式提取)` 只有极小幅度的正向变化，但没有形成足够强的新台阶。

阶段性判断：

- 暂停继续微调 `v19/v20` 这条 `portfolio_extraction(组合提取)` / `portfolio_refresh_rule(组合刷新规则)` 线。
- 后续新的 price-volume 主线比较，默认以 `v18` 为 reference，而不是以 `v19` 或 `v20` 为 reference。
- 下一阶段优先回到 `single-signal discovery(单信号发现)`，补更强的原子信号，而不是继续在组合层抹参数。
