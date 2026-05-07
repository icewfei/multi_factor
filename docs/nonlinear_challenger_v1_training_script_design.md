# Nonlinear Challenger v1 Training Script Design

本文档定义 `Nonlinear Challenger v1` 未来训练脚本的设计边界与治理要求。它是训练脚本设计，不是训练实现，不是模型结果，也不是已验证成功的 ML 结论。

相关背景请同时参照：

- [docs/nonlinear_challenger_v1_design.md](/Users/wy/MiscProject/multi_factor/docs/nonlinear_challenger_v1_design.md)
- [docs/nonlinear_challenger_v1_manifest_spec.md](/Users/wy/MiscProject/multi_factor/docs/nonlinear_challenger_v1_manifest_spec.md)
- [docs/current_stage.md](/Users/wy/MiscProject/multi_factor/docs/current_stage.md)
- [docs/research_freeze_policy.md](/Users/wy/MiscProject/multi_factor/docs/research_freeze_policy.md)

## 1. 目的

本文档只定义未来训练脚本应该如何工作，不代表当前仓库已经允许进入训练实现。

未来训练脚本的目标只应是生成 `model_scores_D0`，也就是在既定执行语义下，为后续独立组合阶段提供 `D0` 打分结果。

本文档明确未来训练脚本不负责：

- `portfolio` 构建
- `backtest` 计算
- `fixed_test` 生成或读取
- 执行语义修改
- 对策略是否成功做直接判断

因此，即使本设计文档完成，也不能把它理解为“ML 方案已经验证可行”或“现在可以直接开始训练”。

## 2. 脚本边界

未来脚本建议名称为：

- `scripts/build_nonlinear_challenger_model_scores.py`

但本次不创建该脚本。

未来脚本只能：

- 读取 `feature_set_manifest`
- 读取 `model_config_manifest`
- 读取 `candidate_scheme_manifest`
- 读取允许的 `train / validation` 数据
- 训练受控模型
- 输出 `model_scores_D0`
- 输出 `model_scores_D0_audit.json`
- 输出 `training_manifest.json`

未来脚本不能：

- 读取 `frozen test`
- 生成 `holdings`
- 生成 `portfolio_daily_summary`
- 生成 `metrics`
- 生成 `fixed_test` 或 `readout`
- 修改 `project panels`
- 修改 `run_state`
- 修改 `artifacts` 历史结果

换言之，未来脚本只负责“受控训练并产出 D0 打分结果”，不负责后续组合、回测、readout、晋升判断或历史产物覆写。

## 3. 必须读取的 manifest

未来脚本启动前必须读取：

- `feature_set_manifest`
- `model_config_manifest`
- `candidate_scheme_manifest`

读取后必须完成一致性校验，至少包括：

- `feature_set_id` 一致
- `model_config_id` 一致
- `snapshot_id` 一致
- `candidate_status = preregistered`
- `frozen_test_access = false`
- `feature_count <= 20`
- `max_depth <= 3`
- `hyperparameter_tuning_allowed = false`
- `n_estimators_tuning_allowed = false`
- `baseline_binding_required_before_training = true`
- `baseline_candidate_scheme_id` 不得仍是 `placeholder`

这里的目的不是增加实现复杂度，而是防止未来脚本在运行时重新打开特征漂移、配置漂移、样本漂移或基线解绑。

## 4. 运行前 fail-fast 检查

未来脚本遇到以下任一情况时，必须直接失败，不得降级继续运行：

- manifest 缺失
- manifest JSON 非法
- `candidate_scheme_id` 已被旧结果复用
- `frozen_test_access` 不是 `false`
- `allowed_readouts` 包含 `frozen_test`
- `feature_count > 20`
- `source_column_mapping_required` 为 `true` 但未提供正式 `source mapping`
- 任一 `feature` 不存在
- 任一 `feature` 无法证明 `D0` 可见
- `prohibited_fields` 出现在 `feature_list`
- `model_config` 超出 `max_depth <= 3`
- `hyperparameter_tuning_allowed` 不为 `false`
- `baseline_candidate_scheme_id` 未绑定
- `snapshot_id` 与 `run_input_contract` 不匹配

第一版应坚持 fail-fast，而不是在边界不明确时“先跑出来再补说明”。如果不能证明合规，就必须拒绝训练。

## 5. 数据读取边界

未来训练脚本的数据读取边界必须写死：

- 只允许读取 `train / validation`
- 不得读取 `frozen test`
- 不得读取未来观察期
- 所有特征必须来自 `D0` 可见信息
- `target_label` 只能用于训练目标，不能作为特征
- execution realized fields 不能作为特征

这意味着训练脚本既不能消费正式隔离评估层，也不能把执行结果字段、未来收益字段或标签派生字段伪装成输入特征。

## 6. 输出设计

未来脚本至少应输出：

- `model_scores_D0.parquet`
- `model_scores_D0_audit.json`
- `training_manifest.json`

`model_scores_D0.parquet` 至少应包含：

- `run_id`
- `candidate_scheme_id`
- `snapshot_id`
- `instrument`
- `signal_date`
- `model_score_D0`
- `feature_set_id`
- `model_config_id`
- `config_hash`

`model_scores_D0_audit.json` 至少应包含：

- `row_count`
- `null_score_rows`
- `nonfinite_score_rows`
- `train_rows`
- `validation_rows`
- `feature_count`
- `feature_missing_summary`
- `feature_column_mapping_status`
- `frozen_test_access`
- `candidate_scheme_id`
- `feature_set_hash`
- `model_config_hash`
- `config_hash`

`training_manifest.json` 至少应包含：

- `code_version` 或 `git_commit_hash`
- `run_id`
- `attempt_id`
- `candidate_scheme_id`
- `feature_set_id`
- `model_config_id`
- `snapshot_id`
- `config_hash`
- `random_seed`
- `training_started_at`
- `training_finished_at`
- `environment summary`

输出设计的目标是保证后续独立阶段可以读取 `D0` 打分，同时保留最小但充分的审计信息，证明该次训练到底跑了什么、用了什么配置、产生了多少可用分数。

## 7. 不允许输出的内容

未来训练脚本不得输出：

- `backtest_daily.csv`
- `holdings.csv`
- `portfolio_daily_summary.csv`
- `metrics.json`
- `audit_summary.json`
- `fixed_test` 结果
- `validation readout` 报告
- 任何 `promotion` 结论

训练脚本只负责“打分”。组合构建、回测、readout、晋升或失败判断，必须由后续独立阶段处理。

## 8. 失败留痕

未来脚本必须保留失败留痕，而不是把失败当作可以静默抹去的技术噪音。

要求如下：

- 如果训练前 fail-fast，必须写明失败原因
- 如果训练过程中失败，必须写 `failure_evidence_log`
- 失败不能删除 manifest
- 失败不能复用 `candidate_scheme_id` 改配置重跑
- 如果要改配置，必须新建 candidate

这里的关键原则是：失败也是正式研究证据。未来若因配置、字段映射、特征可见性或训练流程失败而中止，该失败也应可被审计追踪。

## 9. 与后续链路关系

未来正式顺序必须是：

1. manifest freeze
2. build `model_scores_D0`
3. validate `model_scores_D0` schema
4. build `run_state`
5. build portfolio artifacts
6. validation readout
7. GPT 审计
8. 仍不得自动进入 `frozen test`

这条链路强调“训练脚本只是中间阶段”。即使 `model_scores_D0` 成功产出，也仍然只是下一步输入，不代表候选已经通过验证，更不代表可以自动消耗 `frozen test`。

## 10. 当前结论

本文档完成后，仍不代表现在可以直接训练。

下一步应先补齐 `source column mapping / feature existence spec`，确保未来脚本启动前可以正式证明每个候选特征都存在、可映射、且满足 `D0` 可见边界。

只有当 `feature mapping`、`baseline binding`、`training script design` 都审计通过后，才允许进入训练脚本实现阶段。
