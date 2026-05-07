# multi_factor

## 项目目标

本项目的目标不是继续把历史回测做高，而是把一个低自由度、可审计、尽量抗过拟合的多因子排序研究系统沉淀为可复查的工程资产。

当前仓库保留了以下几类核心资产：

- 研究脚本集合
- 数据契约与字段映射
- 结果 Schema
- 研究过程文档与阶段性结论
- 已产出的研究摘要与审计产物

## 当前阶段

根据 [项目状态总结 2026-05-07](/Users/wy/MiscProject/multi_factor/项目总纲及计划/project_status_20260507.md)，项目当前状态为：

```text
status: signal_engineering_phase_closed
exploratory_winner: multi_equal_weight_v1
strict_confirmatory_winner: none (annual_relative_return < 0)
next: awaiting new data modality or project scope change
```

这意味着当前工作重点是收口、固化、审计与为下一阶段做边界准备，而不是继续在同一批日频量价特征上做自由探索。

## 目录结构说明

- [`scripts/`](/Users/wy/MiscProject/multi_factor/scripts)：
  研究期脚本集合，包含特征构造、打分、组合、诊断、验证 readout 与审计脚本。它们是当前项目的核心实现资产，但还不是最终的模块化 `src/` 包。
- [`contracts/`](/Users/wy/MiscProject/multi_factor/contracts)：
  正式数据契约、字段映射、来源表映射、主键定义。
- [`schemas/`](/Users/wy/MiscProject/multi_factor/schemas)：
  各类中间表与结果产物的 Schema 定义。
- [`artifacts/`](/Users/wy/MiscProject/multi_factor/artifacts)：
  已存在的研究摘要、固定测试摘要、运行态与 walk-forward 产物。该目录是研究留痕资产，不应在审计骨架补齐阶段被移动、删除或重写。
- [`项目总纲及计划/`](/Users/wy/MiscProject/multi_factor/项目总纲及计划)：
  项目总纲、方法说明、状态总结、阶段设计与收口说明。
- [`docs/`](/Users/wy/MiscProject/multi_factor/docs)：
  本次新增的标准审计文档骨架，用于帮助外部审阅者快速理解仓库边界、当前阶段和证据口径。
- [`src/`](/Users/wy/MiscProject/multi_factor/src)：
  预留给后续模块化抽取的标准源码入口。当前核心逻辑仍在 `scripts/`。
- [`tests/`](/Users/wy/MiscProject/multi_factor/tests)：
  预留给后续正式测试集合。当前尚缺 pytest 测试骨架。
- [`configs/`](/Users/wy/MiscProject/multi_factor/configs)：
  预留给后续运行配置索引。当前正式契约仍位于 `contracts/` 与 `schemas/`。

## 当前不应继续做什么

在当前阶段，仓库不应继续做以下事情：

- 不继续新增日频量价自由探索信号
- 不基于 trainval readout 继续调模型参数或包装赢家叙事
- 不把现有 `artifacts/fixed_test` 中绑定 trainval-only 快照的结果误当作新的 OOS 证据
- 不移动、删除或重写既有 `artifacts`
- 不上传 `data/`、`tushare_data/`、`parquet`、`csv`、`db`、`pkl`、`h5` 等本地数据或大型运行产物

## 如何阅读本仓库

建议按以下顺序阅读：

1. 先看 [docs/current_stage.md](/Users/wy/MiscProject/multi_factor/docs/current_stage.md)，快速了解当前阶段结论。
2. 再看 [docs/repo_map.md](/Users/wy/MiscProject/multi_factor/docs/repo_map.md)，理解各目录职责与当前工程边界。
3. 然后看 [docs/phase1_signal_engineering_closure_report.md](/Users/wy/MiscProject/multi_factor/docs/phase1_signal_engineering_closure_report.md)，理解第一阶段信号工程为什么收口。
4. 审计口径相关内容看 [docs/audit_boundary.md](/Users/wy/MiscProject/multi_factor/docs/audit_boundary.md) 与 [docs/research_freeze_policy.md](/Users/wy/MiscProject/multi_factor/docs/research_freeze_policy.md)。
5. 需要原始治理与方法背景时，再回到 [项目总纲及计划](/Users/wy/MiscProject/multi_factor/项目总纲及计划) 与 [项目总纲](/Users/wy/MiscProject/multi_factor/项目总纲及计划/项目总纲/new_multifactor_project_framework_v1.md)。
