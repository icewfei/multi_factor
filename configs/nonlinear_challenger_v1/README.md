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
