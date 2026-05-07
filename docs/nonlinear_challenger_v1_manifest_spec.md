# Nonlinear Challenger v1 Manifest Spec

本文档定义 `Nonlinear Challenger v1` 在进入任何 ML 实现前必须满足的 manifest 规格。它是治理层与预注册层的约束文档，不是训练脚本，不是实验结果，也不是已验证成功的 challenger 结论。

相关背景请同时参照：

- [docs/nonlinear_challenger_v1_design.md](/Users/wy/MiscProject/multi_factor/docs/nonlinear_challenger_v1_design.md)
- [docs/nonlinear_challenger_v1_training_script_design.md](/Users/wy/MiscProject/multi_factor/docs/nonlinear_challenger_v1_training_script_design.md)
- [docs/current_stage.md](/Users/wy/MiscProject/multi_factor/docs/current_stage.md)
- [docs/research_freeze_policy.md](/Users/wy/MiscProject/multi_factor/docs/research_freeze_policy.md)
- [docs/audit_boundary.md](/Users/wy/MiscProject/multi_factor/docs/audit_boundary.md)

## 1. 目的

manifest 是 `Nonlinear Challenger v1` 在进入 ML 实现前的治理门槛。它的目标不是训练模型，而是先冻结 `feature_set`、`model_config`、`candidate_scheme`、候选预算和只读边界，避免实现阶段重新打开无边界调参或无边界换特征。

在本方案下，没有 manifest 预注册的 ML 运行，不得作为有效研究证据，不得作为正式 validation 比较对象，也不得被包装成 challenger 成败判断的依据。换言之，训练之前先冻结清单，是第一版受控非线性验证成立的前提。

## 2. 候选预算

第一版 `Nonlinear Challenger v1` 的预算必须显式受限：

- 最多 `2` 个 `feature_set`
- 最多 `3` 个 `model_config`
- 总候选数最多 `6` 个
- `validation readout` 正式查看最多 `1` 轮

若超出上述预算，必须：

- 另起新的 `research_round_id`
- 重新登记新增候选
- 不得继承原候选的 OOS 资格叙事
- 不得把上一轮已查看结果包装成“只是同一轮继续补跑”

这里的重点不是机械限制数字本身，而是防止根据 `validation` 结果无限新增候选。第一版只允许有限候选比较，不允许通过“再加几个候选看看”逐步把受控 challenger 重新变成自由探索。

## 3. feature_set_manifest

`feature_set_manifest` 至少应包含以下字段：

- `feature_set_id`
- `feature_set_version`
- `created_at`
- `created_by`
- `snapshot_id`
- `source_data_scope`
- `feature_count`
- `feature_list`
- `feature_family`
- `feature_description`
- `d0_visibility_statement`
- `pit_check_required`
- `leakage_risk_notes`
- `missing_value_policy`
- `winsorize_or_clip_policy`
- `standardization_policy`
- `allowed_training_split`
- `prohibited_fields`
- `feature_set_hash`

字段含义上应满足以下治理要求：

- `feature_set_id` 用于唯一标识一组预注册特征
- `feature_set_version` 用于表达该清单的版本，而不是训练结果的优劣
- `snapshot_id` 必须绑定当前允许的数据快照，不得漂移
- `source_data_scope` 必须明确“不新增新数据源”
- `feature_list` 应按稳定顺序完整列出特征名，避免 hash 因无意义重排而变化
- `feature_family` 与 `feature_description` 用于解释为何这些特征被纳入 challenger，而不是事后追认
- `d0_visibility_statement` 必须明确所有特征仅使用 `D0` 可见信息
- `pit_check_required` 必须为显式治理字段，不能默认省略
- `prohibited_fields` 应列出未来信息、标签派生字段、任何不允许进入训练的字段

第一版还必须满足以下约束：

- 最多 `20` 个特征
- 只能使用 `D0` 可见特征
- 不新增新数据源
- 禁止事后根据 `validation` 表现不断替换特征

如果 `feature_set_hash` 变化，即表示特征清单发生了实质变化，应生成新的 `feature_set_id` 或至少新的版本，并进入新的候选登记流程，而不是沿用旧候选身份。

## 4. model_config_manifest

`model_config_manifest` 至少应包含以下字段：

- `model_config_id`
- `model_family`
- `model_version`
- `random_seed`
- `target_label`
- `objective`
- `train_split`
- `validation_split`
- `frozen_test_access`
- `hyperparameters`
- `max_depth`
- `num_leaves`
- `learning_rate`
- `n_estimators`
- `regularization`
- `early_stopping_policy`
- `class_or_sample_weight_policy`
- `missing_value_handling`
- `model_config_hash`

第一版模型边界必须写死在 manifest 规格中：

- 只允许 `Ridge`
- 只允许 `ElasticNet`
- 只允许 `LightGBM` 小深度模型
- 只允许 `XGBoost` 小深度模型
- `max_depth <= 3`
- 禁止 `AutoML`
- 禁止神经网络
- 禁止大规模参数搜索

这些字段的作用不是让配置更方便，而是让模型自由度被提前暴露。建议按以下原则理解：

- `model_family` 决定模型类别边界
- `target_label` 与 `objective` 决定训练任务语义，不得在同一候选下事后切换
- `train_split` 与 `validation_split` 必须和现有样本制度严格对齐
- `frozen_test_access` 必须显式写为 `false`
- `hyperparameters` 应作为完整参数映射存在，避免只登记部分“关键参数”
- `early_stopping_policy` 若允许存在，也必须是有限且事先声明的策略，而不是无限回看验证集

只要 `model_config_hash` 变化，即表示模型配置发生了实质变化，不能沿用旧候选的身份或结果叙事。

## 5. candidate_scheme_manifest

`candidate_scheme_manifest` 至少应包含以下字段：

- `candidate_scheme_id`
- `research_round_id`
- `feature_set_id`
- `model_config_id`
- `snapshot_id`
- `run_id`
- `attempt_id`
- `candidate_tier`
- `preregistered_at`
- `preregistered_by`
- `expected_outputs`
- `allowed_readouts`
- `promotion_criteria`
- `failure_criteria`
- `candidate_status`

该 manifest 是单个候选的治理主键，至少需要满足以下要求：

- `candidate_scheme_id` 必须唯一
- 同一 `candidate` 不允许跑出结果后再改 `feature_set` 或 `model_config`
- 失败候选必须保留
- 不允许只保留最好候选

其中：

- `research_round_id` 用于标记该候选属于哪一轮受控比较
- `run_id` 与 `attempt_id` 用于区分一次正式运行与技术性重试，但不能借机改配置
- `candidate_tier` 可用于区分 baseline control、linear regularized control、nonlinear challenger 等角色
- `expected_outputs` 用于约束未来脚本可产出的正式结果类型
- `allowed_readouts` 用于限制哪些 readout 可以被正式查看
- `promotion_criteria` 与 `failure_criteria` 应引用或对齐 design 文档中的晋升/失败规则
- `candidate_status` 应至少能表达 `preregistered`、`ran`、`failed`、`promoted`、`retired` 等治理状态

该层的关键作用，是防止实现阶段用“还是同一个 candidate”来掩盖实质上的配置漂移。

## 6. hash 与不可变性

第一版建议使用 hash 机制表达 manifest 的不可变性：

- `feature_set_hash` 用于冻结特征清单及其关键处理策略
- `model_config_hash` 用于冻结模型参数与训练设置
- `config_hash` 用于组合 `feature_set_hash + model_config_hash + split_policy`

建议原则如下：

- `feature_set_hash` 由 `feature_list`、特征顺序规范化结果、预处理策略、禁止字段约束等共同生成
- `model_config_hash` 由 `model_family`、目标定义、样本切分、关键超参数、缺失值处理、early stopping 规则等共同生成
- `config_hash` 应反映“这个候选到底在跑什么”，因此不能只依赖模型参数而忽略 split policy
- 任何 hash 改变都必须生成新的 `candidate_scheme_id`
- 不能用同一个 `candidate_scheme_id` 覆盖旧配置

如果后续需要修正文案、补充说明或更正非实质元数据，可以更新 manifest 注释字段；但只要涉及特征、模型、样本制度或训练边界的实质变化，就必须视为新候选，而不是旧候选覆写。

## 7. 文件建议路径

后续若进入 manifest 实现，建议采用以下路径分层：

- `configs/nonlinear_challenger_v1/feature_sets/`
- `configs/nonlinear_challenger_v1/model_configs/`
- `configs/nonlinear_challenger_v1/candidates/`

或在运行后登记阶段使用：

- `artifacts/research_registry/nonlinear_challenger_v1/`

两类路径的职责必须区分清楚：

- `configs/` 用于预注册配置
- `artifacts/research_registry/` 用于运行后登记与失败证据
- 两者不能混用

当前仓库中的样例模板路径可参照：

- [`configs/nonlinear_challenger_v1/feature_sets/feature_set_manifest.template.json`](/Users/wy/MiscProject/multi_factor/configs/nonlinear_challenger_v1/feature_sets/feature_set_manifest.template.json)
- [`configs/nonlinear_challenger_v1/model_configs/model_config_manifest.template.json`](/Users/wy/MiscProject/multi_factor/configs/nonlinear_challenger_v1/model_configs/model_config_manifest.template.json)
- [`configs/nonlinear_challenger_v1/candidates/candidate_scheme_manifest.template.json`](/Users/wy/MiscProject/multi_factor/configs/nonlinear_challenger_v1/candidates/candidate_scheme_manifest.template.json)

原因在于，预注册配置与运行后证据是两个不同层级。若把它们混在一起，很容易让“事前冻结”和“事后登记”之间失去边界。

## 8. 运行前检查

未来任何 ML 训练脚本若要进入主线，启动前至少必须检查：

- `feature_set_manifest` 存在
- `model_config_manifest` 存在
- `candidate_scheme_manifest` 存在
- `candidate` 数量没有超预算
- `frozen_test_access = false`
- `feature_count <= 20`
- `max_depth <= 3`
- `candidate_scheme_id` 未被旧结果复用
- `snapshot_id` 与 `run_input_contract` 匹配

若任一检查不通过，脚本应 fail fast，而不是默认降级继续运行。第一版的目标是宁可拒绝不合规训练，也不接受“先跑了再补登记”。

## 9. 失败留痕

`Nonlinear Challenger v1` 的失败留痕必须被视为正式研究资产，而不是可忽略噪音。规则应明确如下：

- 每个候选无论成功失败都必须登记
- 失败原因要写入 `failure_evidence_log`
- 不允许删除失败候选
- 不允许只汇报最佳结果
- `validation` 失败也是有效研究结论

这部分与第一阶段治理原则保持一致。若 challenger 在受控预算下失败，其失败本身就回答了“当前信息源下非线性是否值得继续加预算”这一问题，因此必须完整保留，而不能只留下少数好看的结果。

## 10. 当前结论

本文档只是 `Nonlinear Challenger v1` 的 manifest 规格，不是实现计划落地完成，也不意味着现在可以立即训练。

完成本文件之后，下一步应先新增 manifest 样例模板，再进入实现前审阅；不应跳过模板层直接写训练脚本。只有在 manifest 模板、预算边界、hash 规则和失败留痕机制都冻结后，后续实现才有资格被视为受控 challenger 的正式工程阶段。
