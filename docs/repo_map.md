# 仓库结构地图

## 目的

本文档解释当前仓库中主要目录的职责，并明确哪些内容属于研究期资产，哪些内容是未来标准工程骨架的占位。

## 核心目录职责

### `scripts/`

[`scripts/`](/Users/wy/MiscProject/multi_factor/scripts) 是当前项目最重要的实现目录，主要包含：

- 特征构造脚本
- `model_scores_D0` 构造脚本
- 单信号与多信号组合脚本
- 组合层与 portfolio 产物构造脚本
- 诊断、审计、validation readout 脚本
- 研究轮次驱动脚本

需要明确的是：

- `scripts/` 目前仍是研究脚本集合
- `scripts/` 不等于最终形态的 `src/` 模块
- 当前审计目标是先把这些资产纳入标准说明框架，而不是在本轮把它们重构成正式包

### `contracts/`

[`contracts/`](/Users/wy/MiscProject/multi_factor/contracts) 保存当前正式数据契约与字段约束，包括：

- 运行输入契约
- 来源表映射
- 字段映射
- 主键定义
- 项目字段字典

对外审计时，应把 `contracts/` 视为当前项目的正式配置与语义边界来源之一。

### `schemas/`

[`schemas/`](/Users/wy/MiscProject/multi_factor/schemas) 定义当前中间表与结果产物的结构约束，包括：

- `model_scores_D0`
- `project_label_panel`
- `project_sample_panel`
- `backtest_daily`
- `portfolio_daily_summary`
- `trade_statistics_summary`
- `audit_summary`

对外审计时，应把 `schemas/` 视为当前项目输出口径的结构化定义层。

### `artifacts/`

[`artifacts/`](/Users/wy/MiscProject/multi_factor/artifacts) 保存既有研究与审计留痕，包括：

- `fixed_test/`
- `research_registry/`
- `run_state/`
- `walk_forward/`
- `shadow_tracking/`

这一目录的职责是保留过程证据与结果摘要，而不是作为本轮新增工程骨架的写入目标。当前任务不移动、不删除、不改写这里的既有产物。

### `项目总纲及计划/`

[`项目总纲及计划/`](/Users/wy/MiscProject/multi_factor/项目总纲及计划) 保存治理、设计、总结与阶段状态文档，包括：

- 项目总纲
- 方法说明
- 状态总结
- 阶段设计说明
- 自审与收口说明

这是当前仓库中最接近“研究管理与制度层真相源”的文档集合。

## 新增标准骨架的角色

### `docs/`

[`docs/`](/Users/wy/MiscProject/multi_factor/docs) 用来承接标准审计入口文档，帮助审阅者快速回答四个问题：

- 当前项目做到哪一步了
- 哪些结论已经收口
- 哪些证据可以用于什么口径
- 下一阶段为什么不能沿着旧路径继续加码

### `src/`

[`src/`](/Users/wy/MiscProject/multi_factor/src) 目前只是标准骨架占位目录。它代表后续模块化方向，而不是当前真实实现所在地。

### `tests/`

[`tests/`](/Users/wy/MiscProject/multi_factor/tests) 目前也是标准骨架占位目录，用于后续补齐正式测试集合。

### `configs/`

[`configs/`](/Users/wy/MiscProject/multi_factor/configs) 目前仅保留配置索引入口。当前正式契约仍在 `contracts/` 与 `schemas/`。

## 当前工程边界

截至当前版本，仓库应被理解为：

- 一个已经形成较完整研究资产的项目
- 其核心实现仍以 `scripts/` 为主
- 其正式配置语义在 `contracts/` 与 `schemas/`
- 其研究治理与结论文档在 `项目总纲及计划/`
- 其标准审计骨架正在补齐，但尚未完成最终模块化重构
