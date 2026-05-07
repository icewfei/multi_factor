# Artifacts Directory Contract

本目录只承载项目运行产物，不承载共享真相源。

固定子目录：

- `fixed_test/`
- `walk_forward/`
- `shadow_tracking/`
- `run_state/`

规则：

- 共享数据源视图和 parquet 不得复制到本目录冒充真相源
- 本目录只保存 run-level 结果、项目运行态状态和项目审计摘要
- 所有子目录产物都应绑定 `run_id + snapshot_id`；其中 `run_state` 的运行态输出还必须绑定 `attempt_id`
- 研究登记、方案主键和失败证据骨架位于 `artifacts/research_registry/`
