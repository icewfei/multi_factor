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

项目当前状态为：

```text
status: current_data_regime_research_stopped
p98 / multi_equal_weight_v1: conditional reference only
clean_baseline_family: clean but insufficient TopK head quality; not portfolio-ready
current D0 OHLCV + state regime: stopped for clean baseline / TopK / mid-rank research
strategy_research: paused
sandbox_understanding: completed
repository_role: audit asset and engineering asset
```

这意味着当前工作重点已经从继续策略研究，转为保留、整理和审计既有研究资产。当前不应把 `p98` 包装为 gold standard，也不应继续追求更高历史收益、开启 v4、训练、回测或跑 portfolio。

同时，`current_data_regime_research_stopped` 只停止策略推进，不停止所有研究理解。此前允许的 `paper-only` pre-registration 与 `exploratory descriptive` mechanism research 已经完成当前这一轮 sandbox understanding，用于解释失败机制、整理问题定义和准备未来独立立项；这些工作不得宣称 alpha、生成 candidate、跑 portfolio、读取 frozen test，或把 trainval diagnosis 包装为 OOS。当前默认不再继续同一研究问题下的新 sandbox 扩张。

当前主结论：

- `p98` / `multi_equal_weight_v1` 只能作为 `conditional reference only`，不是 unconditional gold standard。
- clean baseline family 的 score-layer 4/4 通过，整体 clean，但 model-layer / TopK head quality 不足，not portfolio-ready。
- `data_field_enrichment_v1` 是 `conditional enrichment layer`，只允许通过 next-use policy 的字段进入后续受控诊断或 baseline 研究。
- `guarded_clean_baseline_workflow_v1` 已实现，作为使用 enrichment 字段的 clean baseline score 与 model-layer diagnosis 受控入口。
- 当前 D0 OHLCV + state 字段体系下，clean baseline / TopK / mid-rank 研究已经停止。
- sandbox understanding 已完成；仓库当前进入 preservation / audit-first 状态。
- 后续只有在出现新信息源、新数据模态，或独立 pre-register 的新研究问题后，才允许考虑重启。

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
  contract-level audit tests 与部分 fixture-level 实现测试，用于固定核心研究语义、字段边界、执行语义和治理红线。
- [`configs/`](/Users/wy/MiscProject/multi_factor/configs)：
  预留给后续运行配置索引。当前正式契约仍位于 `contracts/` 与 `schemas/`。

## 当前不应继续做什么

在当前阶段，仓库不应继续做以下事情：

- 不跑 portfolio，当前没有 portfolio-ready clean baseline 或 challenger
- 不读取 frozen test
- 不开启 v4，当前不建议继续开新 nonlinear challenger
- 不把 trainval diagnosis 当 OOS
- 不继续新增日频量价自由探索信号
- 不基于 trainval readout 继续调模型参数或包装赢家叙事
- 不把现有 `artifacts/fixed_test` 中绑定 trainval-only 快照的结果误当作新的 OOS 证据
- 不移动、删除或重写既有 `artifacts`
- 不上传 `data/`、`tushare_data/`、`parquet`、`csv`、`db`、`pkl`、`h5` 等本地数据或大型运行产物

## 如何阅读本仓库

建议按以下顺序阅读：

1. 先看 [docs/current_stage.md](/Users/wy/MiscProject/multi_factor/docs/current_stage.md)，快速了解当前阶段结论。
2. 再看 [docs/final_project_review_after_data_regime_stop.md](/Users/wy/MiscProject/multi_factor/docs/final_project_review_after_data_regime_stop.md)，理解项目研究路径、工程状态、无法继续的原因和下一步建议。
3. 再看 [docs/current_data_regime_research_stop_decision.md](/Users/wy/MiscProject/multi_factor/docs/current_data_regime_research_stop_decision.md)，理解为什么当前 D0 OHLCV + state 研究范式停止。
4. 再看 [docs/exploratory_sandbox_policy_after_data_regime_stop.md](/Users/wy/MiscProject/multi_factor/docs/exploratory_sandbox_policy_after_data_regime_stop.md)，理解 stop decision 后哪些 paper-only 与 descriptive mechanism research 曾被允许。
5. 再看 [docs/project_closure_after_sandbox_completion.md](/Users/wy/MiscProject/multi_factor/docs/project_closure_after_sandbox_completion.md)，理解为什么 sandbox understanding 已完成，以及为什么当前默认不再继续同一命题下的新 sandbox 诊断。
6. 再看 [docs/research_problem_reframing_options_after_data_regime_stop.md](/Users/wy/MiscProject/multi_factor/docs/research_problem_reframing_options_after_data_regime_stop.md)，理解哪些问题重定义只允许纸面预研，为什么最终建议暂停策略研究。
7. 再看 [docs/multi_equal_weight_baseline_status_decision_record.md](/Users/wy/MiscProject/multi_factor/docs/multi_equal_weight_baseline_status_decision_record.md)，理解 `p98` / `multi_equal_weight_v1` 为什么只能作为 conditional reference only。
8. 再看 [docs/clean_baseline_family_decision_record.md](/Users/wy/MiscProject/multi_factor/docs/clean_baseline_family_decision_record.md)，理解 clean baseline family 为什么 clean but not portfolio-ready。
9. 再看 [docs/data_enrichment_v1_next_use_decision_record.md](/Users/wy/MiscProject/multi_factor/docs/data_enrichment_v1_next_use_decision_record.md)，理解 `data_field_enrichment_v1` 的 conditional enrichment layer 边界。
10. 再看 [docs/guarded_clean_baseline_workflow_v1_decision_record.md](/Users/wy/MiscProject/multi_factor/docs/guarded_clean_baseline_workflow_v1_decision_record.md)，理解 guarded clean baseline workflow v1 的受控入口语义。
11. 再看 [docs/rank_band_full_profile_descriptive_research_design.md](/Users/wy/MiscProject/multi_factor/docs/rank_band_full_profile_descriptive_research_design.md)，理解已完成的 descriptive-only sandbox 研究问题如何限定边界。
12. 再看 [docs/repo_map.md](/Users/wy/MiscProject/multi_factor/docs/repo_map.md)，理解各目录职责与当前工程边界。
13. 然后看 [docs/phase1_signal_engineering_closure_report.md](/Users/wy/MiscProject/multi_factor/docs/phase1_signal_engineering_closure_report.md)，理解第一阶段信号工程为什么收口。
14. 审计口径相关内容看 [docs/audit_boundary.md](/Users/wy/MiscProject/multi_factor/docs/audit_boundary.md) 与 [docs/research_freeze_policy.md](/Users/wy/MiscProject/multi_factor/docs/research_freeze_policy.md)。
15. 如果要运行当前审计测试，先看 [docs/test_running.md](/Users/wy/MiscProject/multi_factor/docs/test_running.md)。
16. 需要原始治理与方法背景时，再回到 [项目总纲及计划](/Users/wy/MiscProject/multi_factor/项目总纲及计划) 与 [项目总纲](/Users/wy/MiscProject/multi_factor/项目总纲及计划/项目总纲/new_multifactor_project_framework_v1.md)。

## 运行审计测试

当前 `tests/` 主要是 contract-level audit tests，用于固定核心研究语义、字段边界与治理红线，不连接真实数据，也不是收益验证。

安装依赖：

```bash
python -m pip install -r requirements-dev.txt
```

运行测试：

```bash
python -m pytest tests/
```
