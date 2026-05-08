# nonlinear_challenger_v1 配置目录说明

本目录只存放 `Nonlinear Challenger v1` 的预注册配置。

本目录中可以包含：

- `feature_set manifest` 模板或预注册文件
- `model_config manifest` 模板或预注册文件
- `candidate_scheme manifest` 模板或预注册文件

本目录中不应存放：

- 训练结果
- `validation readout`
- 失败证据

失败证据应进入：

- `artifacts/research_registry/`

`configs/` 与 `artifacts/research_registry/` 不能混用。

- `configs/` 用于事前冻结和预注册
- `artifacts/research_registry/` 用于运行后登记和失败留痕

若把两者混写，会破坏“先冻结、后运行、再登记”的治理顺序。

当前目录也可以存放少量 `draft manifest` 草案，用于在训练实现前先审计自由度与边界。

- `draft manifest` 仍属于预注册配置
- `draft manifest` 不代表模型已经训练
- `draft manifest` 不代表 challenger 已验证成功

当前还可以包含基于 source audit 收敛后的受限候选，例如 `confirmed5` 子集。

- `confirmed5` 只允许引用已在 source audit 中确认 `ready_for_training=true` 的既有项目特征
- `confirmed5` 仍然只是预注册配置，不代表训练、验证或回测已经执行
