# 当前阶段

## 状态结论

根据 [项目状态总结 2026-05-07](/Users/wy/MiscProject/multi_factor/项目总纲及计划/project_status_20260507.md)，当前项目状态为：

```text
status: signal_engineering_phase_closed
exploratory_winner: multi_equal_weight_v1
strict_confirmatory_winner: none (annual_relative_return < 0)
next: awaiting new data modality or project scope change
```

## 解释

### `signal_engineering_phase_closed`

这表示第一阶段围绕现有日频量价特征空间的信号工程探索已经收口。当前任务不再是继续追加新的局部信号变体，而是把现有结论固化为可审计资产，并为下一阶段做边界准备。

### `exploratory_winner = multi_equal_weight_v1`

当前探索性赢家是 `multi_equal_weight_v1`。根据项目状态文档，它由 `p98 + cord30 + vsumd60 + corr30` 等权复合而成，在若干统计指标上优于旧基线，但年化相对收益仍为负。

因此，它可以被视为当前阶段的最佳探索性组合，不可以被解释为严格确认性赢家。

### `strict_confirmatory_winner = none`

当前没有严格确认性赢家。项目状态文档已明确给出原因：

- `strict_confirmatory_winner: none (annual_relative_return < 0)`

这意味着现有候选即使在部分统计指标上改善，也没有达到“可作为严格确认性赢家”的收益门槛。

## 当前不应做的事情

在本阶段，仓库不应继续：

- 追加新的日频量价信号探索
- 基于 trainval-only readout 做继续调参
- 用探索性优胜者替代严格确认性结论
- 把命名为 `fixed_test` 的 trainval 产物误包装为样本外结论

## 下一阶段含义

项目状态已给出下一步方向：

- `awaiting new data modality or project scope change`

当前含义是：

- 若继续推进，需要引入新的数据模态
- 或者改变项目范围与问题设定
- 不应在原有日频量价局部特征空间里继续高频迭代相近候选
