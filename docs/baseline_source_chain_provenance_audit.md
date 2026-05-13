# baseline source-chain provenance audit

## Scope

本审计只复核 `multi_equal_weight_v1` 依赖的上游 `exploratory_cross_horizon_c1_reversal_only` source-chain provenance。边界保持为：

- 不训练
- 不回测
- 不读取 `frozen test`
- 不生成 formal metrics/readout
- 不修改 baseline / challenger

## Files Reviewed

- [build_multi_equal_weight_v1_scores.py](/Users/wy/MiscProject/multi_factor/scripts/build_multi_equal_weight_v1_scores.py)
- [build_reversal_tail_composite_model_scores.py](/Users/wy/MiscProject/multi_factor/scripts/build_reversal_tail_composite_model_scores.py)
- [build_baseline_model_scores.py](/Users/wy/MiscProject/multi_factor/scripts/build_baseline_model_scores.py)
- [rr_exploratory_cross_horizon_reversal_momentum_20260501/preregistration.json](/Users/wy/MiscProject/multi_factor/artifacts/research_registry/research_rounds/rr_exploratory_cross_horizon_reversal_momentum_20260501/preregistration.json)
- [rr_exploratory_reversal_tail_handling_20260502/preregistration.json](/Users/wy/MiscProject/multi_factor/artifacts/research_registry/research_rounds/rr_exploratory_reversal_tail_handling_20260502/preregistration.json)
- [rr_confirmatory_reversal_cord30_promotion_20260506/preregistration.json](/Users/wy/MiscProject/multi_factor/artifacts/research_registry/research_rounds/rr_confirmatory_reversal_cord30_promotion_20260506/preregistration.json)
- [candidate_scheme_registry.jsonl](/Users/wy/MiscProject/multi_factor/artifacts/research_registry/candidate_scheme_registry.jsonl)
- [scheme_attempt_log.jsonl](/Users/wy/MiscProject/multi_factor/artifacts/research_registry/scheme_attempt_log.jsonl)
- [confirmatory_reversal_p98_trainval_20260506/model_scores_D0_audit.json](/Users/wy/MiscProject/multi_factor/artifacts/run_state/confirmatory_reversal_p98_trainval_20260506/model_scores_D0_audit.json)

## Source-Chain Summary

`multi_equal_weight_v1` 的固定依赖链可以静态复原为：

1. `build_baseline_model_scores.py`
   `single_signal_reversal_5d_v1`
   `exploratory_cross_horizon_c1_reversal_only`
2. `build_reversal_tail_composite_model_scores.py`
   `reversal_tail_exclude_p98_v1`
   source run = `exploratory_cross_horizon_c1_reversal_only`
3. `build_multi_equal_weight_v1_scores.py`
   `multi_equal_weight_v1`
   fixed component = `reversal_tail_exclude_p98_v1`

`c1` 的可见上游输入字段只恢复到：

- `project_sample_panel.instrument`
- `project_sample_panel.signal_date`
- `project_sample_panel.ranking_eligible_D0`
- `vw_bars_daily.ts_code`
- `vw_bars_daily.trade_date`
- `vw_bars_daily.adj_close`
- `run_input_contract.snapshot_id`

## D0 Visibility

- `c1` 的核心原始量是 `reversal_5d_raw = adj_close / LAG(adj_close, 5) - 1`。
- 排名使用 `ranking_eligible_D0` 过滤。
- 本地源码中未见 `LEAD` 或 `FOLLOWING`。
- `p98` 只是在同日横截面上对 negated reversal 做 `PERCENTILE_CONT(0.98)` tail exclusion，再重排。

当前判断：

- `c1` 直接构造满足 `D0 / 历史可见数据` 要求。
- `p98` tail rule 也只使用同日横截面和上游 `c1` 分数。

## Leakage Judgment

- 在可访问源码里，没有看到 `label_*`、`realized_return`、`execution_delayed_realized_return`、`actual_exit_date`、`actual_sell_price`、`next_open`、`next_close` 进入 `c1` 或 `p98` score builder。
- 因此没有发现 `c1` builder 或 `p98` builder 的直接 future/label/realized-return leakage。

## Feedback Risk

这里要分开两层：

- `c1` cross-horizon round 自身：
  - prereg candidate list 已冻结
  - serial rule 明确非级联淘汰
  - 明确禁止查看 2022-2025 测试集
  - 因此没有看到 `c1` builder 直接依赖 validation/frozen 结果反向改定义
- `p98` downstream tail-handling round：
  - prereg 明确使用 `median_daily_ic`、`top10_avg_label`、`top10_bot10_spread`
  - 还写出了 `label_5d_next_open_close` learnability 诊断口径
  - 因此存在 `trainval label-based source-selection feedback risk`
  - 这不是 score builder 直接泄漏，但也不是完全 feedback-free 的来源链

## Provenance / Reproducibility Gaps

当前本地最大的 blocker 有两个：

1. `scheme_attempt_log.jsonl` 记录了 `exploratory_cross_horizon_c1_reversal_only` 的 `scores_path`、`attempt_manifest_path`、`data_quality_audit_path`，但这些本地 run-state artifact 当前不存在，无法把 `c1` 执行链完整重验到 manifest/audit 级别。
2. registry 中 `exploratory_cross_horizon_c1_reversal_only` 的 `score_rule` 写成 `percentile_rank(reversal_5d_raw DESC)`，但本地 `single_signal_reversal_5d_v1` 实现实际映射到 `reversal_rank`，而 `reversal_rank` 是按 `reversal_5d_raw ASC` 计算。由于缺少本地 `c1` run-state artifact，无法再用已执行产物确认当时实际跑的是哪一个方向。

## Final Status

- source-chain provenance audit: `blocked`
- baseline status upgrade: `not eligible`
- baseline recommendation: 保持 `conditional pass`，继续保留 blocker

## Missing Evidence

- `artifacts/run_state/exploratory_cross_horizon_c1_reversal_only/model_scores_D0.parquet`
- `artifacts/run_state/exploratory_cross_horizon_c1_reversal_only/attempts/attempt_20260501_151329/run_state_attempt_manifest.json`
- `artifacts/run_state/exploratory_cross_horizon_c1_reversal_only/attempts/attempt_20260501_151329/data_quality_audit.json`
- 能够把 registry `DESC` 与本地 builder `ASC` 差异消解掉的 executed artifact / acceptance evidence
