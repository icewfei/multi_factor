# run_state Artifacts

本目录承载项目运行态数据表。

建议路径：

- `artifacts/run_state/<run_id>/attempts/<attempt_id>/ranking_state_daily.parquet`
- `artifacts/run_state/<run_id>/attempts/<attempt_id>/execution_state_daily.parquet`
- `artifacts/run_state/<run_id>/attempts/<attempt_id>/holdings.csv`
- `artifacts/run_state/<run_id>/attempts/<attempt_id>/portfolio_weights_daily.csv`
- `artifacts/run_state/<run_id>/attempts/<attempt_id>/portfolio_daily_summary.csv`
- `artifacts/run_state/<run_id>/attempts/<attempt_id>/turnover_daily.csv`
- `artifacts/run_state/<run_id>/attempts/<attempt_id>/data_quality_audit.json`
- `artifacts/run_state/<run_id>/attempts/<attempt_id>/run_state_attempt_manifest.json`
- `artifacts/run_state/<run_id>/attempts/<attempt_id>/portfolio_artifacts_manifest.json`
- `artifacts/run_state/<run_id>/run_state_latest_attempt.json`
- `artifacts/run_state/<run_id>/project_label_panel.parquet`
- `artifacts/run_state/<run_id>/project_sample_panel.parquet`
- `artifacts/run_state/<run_id>/project_execution_panel.parquet`
- `artifacts/run_state/<run_id>/dataset_split_daily.parquet`
- `artifacts/run_state/sample_attempt_archive/<sample_run_id>__<attempt_id>/`

说明：

- `project_*`、`model_scores_*` 等输入产物保留在 `run_id` 根目录，便于复用。
- `ranking_state_daily`、`execution_state_daily` 和运行态审计产物按 `attempt_id` 隔离，避免 rerun 覆盖旧结果。
- 组合层最小骨架产物也按 `attempt_id` 隔离，默认复用同一 `attempt` 下的 run-state 与项目侧 panel。
- 运行态 parquet 先写 `.inprogress.parquet`，成功后再原子重命名为正式文件。
- 当前工程默认值：
  - `signal_date_chunk_size = 5`
  - `max_threads = 8`
  - `memory_limit_gb = 20`
- 上述工程默认值属于当前机器与当前链路的运行基线，不属于策略研究自由度。
- `sample_attempt_archive/` 只用于保存少量“已验收、可自包含复现”的 sample attempt，便于回归验证、目录清理后保留最小对照样本。
- `sample_attempt_archive/` 里的目录应直接包含该 attempt 的 `inputs/`、运行态 parquet、audit、manifest 和 acceptance report，不要求再保留原 `run_id` 根目录。
- `sample_attempt_archive/` 不是新的正式运行目录；正式全量或阶段性 run 仍应放在 `artifacts/run_state/<run_id>/` 下。
