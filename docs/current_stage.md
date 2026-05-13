# 当前阶段

## 状态结论

当前项目状态为：

```text
status: current_data_regime_research_stopped
p98 / multi_equal_weight_v1: conditional reference only
clean_baseline_family: clean but insufficient TopK head quality; not portfolio-ready
current D0 OHLCV + state regime: stopped for clean baseline / TopK / mid-rank research
strategy_research: paused
repository_role: audit asset and engineering asset
```

这表示项目已经从 `data_enrichment_and_guarded_research_workflow_phase` 进入当前数据范式停止状态。当前任务不是继续追加 nonlinear v4，不是跑 portfolio，也不是继续 clean baseline redesign，而是固定以下结论：

- nonlinear confirmed5 / v2 / v3 均不晋级。
- `p98` / `multi_equal_weight_v1` 只能作为 `conditional reference only`，不是 unconditional gold standard。
- no-p98 clean baseline clean but weak。
- clean baseline family score-layer clean，但 model-layer / TopK head quality 不足，不进入 portfolio。
- composite 路线已否决。
- liquidity_quality 路线已否决。
- head-exclusion 证据不足。
- mid-rank edge yearly stability 不足。
- 当前 D0 OHLCV + state 字段体系下没有 portfolio-ready clean candidate。

## Current Portfolio Decision

当前不进入 portfolio。原因是：

- `p98` / `multi_equal_weight_v1` 不是 unconditional gold standard，只能作为 conditional reference。
- clean baseline family 虽然 score-layer clean，但 TopK head quality 不足。
- composite / liquidity_quality / head-exclusion / mid-rank 路线均未产生可部署候选。
- `data_field_enrichment_v1` 是 conditional enrichment layer，不是 alpha，也不是策略批准。
- trainval diagnosis 不是 OOS。

## Blocked Fields

`data_field_enrichment_v1` 的 blocked fields 为：

- `listing_age_trading_days`
- `newly_listed_flag`

blocked 字段修复前不得使用。任何 downstream 入口必须通过 next-use guardrail 或等价受控检查显式拒绝这些字段。

## 当前不应做的事情

在本阶段，仓库不应继续：

- 跑 portfolio 或 portfolio dry-run
- 读取 frozen test
- 开 nonlinear v4
- 训练新模型
- 回测
- 生成 formal metrics/readout
- 设计具体交易规则
- 把 trainval diagnosis 当 OOS
- 把 `p98` / `multi_equal_weight_v1` 当 clean gold standard
- 追加新的日频量价信号探索
- 基于 trainval-only readout 做继续调参
- 用探索性优胜者替代严格确认性结论
- 把命名为 `fixed_test` 的 trainval 产物误包装为样本外结论

## Historical Stages

2026-05-07 的 `signal_engineering_phase_closed` 是 historical stage。该阶段解释第一阶段信号工程为什么收口，但已经不再是仓库入口层的当前状态。

`data_enrichment_and_guarded_research_workflow_phase` 也是 historical stage。该阶段完成了 `data_field_enrichment_v1` next-use guardrail 与 `guarded_clean_baseline_workflow_v1`，并支持后续 clean baseline redesign 的受控研究路径。该路径现在已被 `current_data_regime_research_stop_decision` 覆盖。

## 下一阶段含义

下一阶段建议是治理与工程整理，而不是策略推进：

- 保留仓库作为可审计资产和工程资产。
- 更新入口文档，明确最新 stop decision。
- 补齐测试依赖和测试运行说明。
- 整理哪些文档是当前真相源，哪些文档是历史阶段记录。
- 只在出现新信息源、新数据模态，或独立 pre-register 的新研究问题后，才允许考虑重启研究。

当前不建议继续平台化扩张，不建议跑 portfolio，不建议把 trainval diagnosis 当 OOS，不建议继续开 nonlinear v4，不建议继续当前 D0 OHLCV + state 规则变体。
