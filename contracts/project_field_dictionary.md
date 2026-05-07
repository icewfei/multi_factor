# 本项目字段字典

## 用途

本字典只描述 `multi_factor` 项目侧的数据层字段，不重写共享数据源的真相定义。

字段分类固定为：

- `shared_source_field`：直接来自共享数据源
- `project_normalized_field`：项目侧规范化映射字段
- `project_run_state_field`：运行态字段，只在本项目内存在
- `project_artifact_field`：报告或 artifact 专用字段

## 核心字段

| field | category | source | 说明 |
|---|---|---|---|
| `snapshot_id` | `shared_source_field` | parquet_duckdb | 数据快照主键 |
| `instrument` | `project_normalized_field` | `ts_code` | 项目统一证券主键 |
| `signal_date` | `project_normalized_field` | `trade_date` | 项目统一信号日期 |
| `entry_date` | `project_normalized_field` | `next_trade_date_1` / `entry_date_D1` | 统一入场日期 |
| `planned_exit_date` | `project_normalized_field` | `next_trade_date_5` / `planned_exit_date_D5` | 统一计划退出日期 |
| `label_5d_next_open_close` | `shared_source_field` | `labels_daily` | 正式研究标签 |
| `label_5d_next_open_close_raw` | `shared_source_field` | `labels_daily` | 理论标签 |
| `label_defined` | `shared_source_field` | `labels_daily` | 理论标签是否可计算 |
| `entry_tradeable` | `shared_source_field` | `sample_eligibility_daily` | `D1` 可买 |
| `planned_exit_tradeable` | `shared_source_field` | `sample_eligibility_daily` | `D5` 收盘可卖 |
| `actual_exit_date` | `shared_source_field` | `execution_path_daily` | 实际退出日 |
| `execution_delayed_realized_return` | `shared_source_field` | `execution_path_daily` | 真实清算收益 |
| `run_id` | `project_run_state_field` | project-only | 项目运行主键 |
| `attempt_id` | `project_run_state_field` | project-only | 同一 `run_id` 下的 rerun / attempt 主键 |
| `research_round_id` | `project_artifact_field` | project-only | 研究轮次主键 |
| `candidate_scheme_id` | `project_artifact_field` | project-only | 正式注册后的候选方案主键 |
| `model_score_D0` | `project_run_state_field` | project-only | 排序模型分数 |
| `topk_frozen_D0` | `project_run_state_field` | project-only | 是否进入冻结 `TopK` |
| `execution_attempt_D1` | `project_run_state_field` | project-only | 是否尝试执行 |
| `entry_filled_D1` | `project_run_state_field` | project-only | 最终运行态建仓是否成交 |
| `backtest_executable` | `project_run_state_field` | project-only | 最终运行态是否形成持仓 |
| `position_id` | `project_artifact_field` | project-only | 单笔持仓主键 |
| `weight_mapping_multiplier` | `project_artifact_field` | project-only | 组合层权重映射乘子，仅在启用权重惩罚类方案时生效 |
| `entry_fill_weight` | `project_artifact_field` | project-only | 组合层实际建仓权重 |
| `opening_weight` | `project_artifact_field` | project-only | 组合层日初权重 |
| `closing_weight` | `project_artifact_field` | project-only | 组合层日末权重 |
| `cash_weight` | `project_artifact_field` | project-only | 组合层现金权重 |
| `invested_weight` | `project_artifact_field` | project-only | 组合层投资仓位 |
| `turnover_daily` | `project_artifact_field` | project-only | 组合层日度换手 |
| `mask_reason_json` | `shared_source_field` | `sample_eligibility_daily` | 共享侧 mask 原因 |
| `data_quality_audit` | `project_artifact_field` | project-only | 项目侧质量审计摘要 |

## 约束

- 本项目不得重新定义共享真相字段的经济含义
- 若共享字段命名不符合项目习惯，只能通过映射层重命名，不得篡改原义
- 所有 `project_run_state_field` 不得回写到共享数据源
