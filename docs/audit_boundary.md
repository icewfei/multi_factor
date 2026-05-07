# 审计边界说明

## 目的

本文档说明当前仓库中哪些结果可以作为探索性证据，哪些结果不能被表述为样本外证据，并解释当前 `fixed_test` 命名与 trainval-only 使用之间的历史边界问题。

## 可作为探索性证据的内容

以下内容可以作为探索性或研究治理证据使用：

- `scripts/` 中的研究脚本与诊断逻辑
- `contracts/` 与 `schemas/` 中的正式契约与结构定义
- `项目总纲及计划/` 中的研究设计、状态总结、自审与阶段说明
- `artifacts/research_registry/` 中的研究轮次留痕
- 绑定 trainval-only 快照的诊断 readout、validation readout、IC 对比、组合统计与失败证据

这类材料可以支持的结论包括：

- 某个候选是否是探索性赢家
- 某类局部特征工程是否改善了 IC、Sharpe、回撤或成本 stress
- 某阶段研究为什么收口
- 哪些叙事已经被 Oracle 或后续审计修正

## 不可作为 OOS 证据的内容

以下内容不应被包装为正式 OOS 证据：

- 绑定 `trainval-only` 研究快照的 readout
- 基于 `contracts/run_input_contract.research_trainval_20211231.json` 的结果
- 名称中包含 `confirmatory_*_trainval_*` 或 `fixed_test_*_trainval_*` 的历史产物，只要它们实际仍绑定 trainval-only 快照
- 任何已经被研究者查看过并用于继续决策的结果

根据现有契约与文档，当前仓库中相当一部分历史结果虽然目录名带有 `fixed_test`，但实际绑定的是：

- `snapshot_id = warehouse_20260429_trainval_20211231`
- `trainval_only research snapshot`

因此，这些材料更适合被解释为：

- trainval 治理期研究证据
- 过程审计证据
- 阶段性决策证据

而不是严格意义上的独立 OOS 证据。

## `fixed_test` / `trainval` 命名的历史问题

当前仓库存在一个需要明确披露的历史命名问题：

- 部分目录或字段使用了 `fixed_test` 命名
- 但其底层绑定的却是 `trainval-only` 研究快照

这会造成两个风险：

- 审阅者可能把这些结果误读为严格样本外评估
- 研究者自己也可能在叙述中不小心放大这些结果的证据等级

因此，当前阶段的审计原则应当是：

- 保留历史命名，不改写既有产物路径
- 但在解释层显式说明其 trainval-only 属性
- 在新文档中避免把这类结果称为 OOS 胜利证据

## Oracle 证据的边界

Oracle 结果可以支持的结论是：

- 在同一执行语义和成本模型下，框架不是机械地 execution-blocked

Oracle 结果不能直接支持的结论是：

- 某个真实候选已经具备可交易优势
- 某个现实特征族已经足够接近可正式部署
- 任何 trainval-only 赢家已经自动获得样本外资格

## 后续 `frozen_test` 的隔离要求

后续若建立真正的 `frozen_test` 或其他正式样本外评估层，至少应满足：

- 与当前 trainval-only 研究快照物理或逻辑隔离
- 研究阶段不得读取其 readout 后再继续调参
- 每个正式评估必须具备唯一的运行标识与契约绑定
- 一旦结果被查看，应立即记录其样本外资格已被消耗
- 不得把 trainval-only 结果与未来 frozen/OOS 结果混写在同一证据层级里

## 当前审计口径总结

当前仓库最适合对外表述为：

- 一个研究阶段已收口、证据仍可审计的项目
- 其大量结果可作为探索性与治理性证据
- 但严格 OOS 证据边界仍需要未来更干净的 frozen 隔离层来承接
