# 当前阶段

## 状态结论

当前项目状态为：

```text
status: data_enrichment_and_guarded_research_workflow_phase
p98 / multi_equal_weight_v1: conditional reference only
clean_baseline_family: clean but insufficient TopK head quality; not portfolio-ready
data_field_enrichment_v1: conditional enrichment layer
guarded_clean_baseline_workflow_v1: implemented
next: clean baseline redesign research round
```

## 解释

### `data_enrichment_and_guarded_research_workflow_phase`

这表示项目已经从旧的 signal engineering closure 进入 baseline 治理、data enrichment next-use 和 guarded research workflow 对齐阶段。当前任务不是继续追加 nonlinear v4，也不是跑 portfolio，而是固定以下结论：

- nonlinear confirmed5 / v2 / v3 均不晋级。
- `p98` / `multi_equal_weight_v1` 只能作为 `conditional reference only`，不是 unconditional gold standard。
- no-p98 clean baseline clean but weak。
- clean baseline family score-layer 4/4 通过，但 model-layer / TopK head quality 不足，不进入 portfolio。
- `data_field_enrichment_v1` 是 `conditional enrichment layer`。
- data enrichment next-use guardrail 已实现。
- `guarded_clean_baseline_workflow_v1` 已实现。

### Current Portfolio Decision

当前不进入 portfolio。原因是：

- `p98` / `multi_equal_weight_v1` 不是 unconditional gold standard，只能作为 conditional reference。
- clean baseline family 虽然 score-layer clean，但 TopK head quality 不足。
- `data_field_enrichment_v1` 不是 alpha，也不是策略批准。
- trainval diagnosis 不是 OOS。

### Blocked Fields

`data_field_enrichment_v1` 的 blocked fields 为：

- `listing_age_trading_days`
- `newly_listed_flag`

blocked 字段修复前不得使用。任何 downstream 入口必须通过 next-use guardrail 或等价受控检查显式拒绝这些字段。

## 当前不应做的事情

在本阶段，仓库不应继续：

- 跑 portfolio
- 读取 frozen test
- 开 nonlinear v4
- 把 trainval diagnosis 当 OOS
- 追加新的日频量价信号探索
- 基于 trainval-only readout 做继续调参
- 用探索性优胜者替代严格确认性结论
- 把命名为 `fixed_test` 的 trainval 产物误包装为样本外结论

## Historical Stage

2026-05-07 的 `signal_engineering_phase_closed` 现在是 historical stage。该阶段仍解释了第一阶段信号工程为什么收口，但已经不再是仓库入口层的当前状态。

## 下一阶段含义

下一阶段建议是研究导向的：

- `clean baseline redesign research round`

当前含义是：

- 研究目标是重新设计更干净且更有 TopK head quality 的 clean baseline。
- 当前不建议继续平台化扩张。
- 当前不建议跑 portfolio。
- 当前不建议把 trainval diagnosis 当 OOS。
- 当前不建议继续开 nonlinear v4。
