# model_configs 目录说明

本目录用于保存 `model_config manifest` 的模板与后续预注册文件。

`model_config manifest` 的作用是：

- 冻结模型家族
- 冻结关键超参数边界
- 冻结样本切分与 `frozen_test_access` 约束

第一版约束如下：

- 最多 `3` 个 `model_config`
- 只允许 `Ridge`
- 只允许 `ElasticNet`
- 只允许 `LightGBM` 小深度模型
- 只允许 `XGBoost` 小深度模型
- `max_depth <= 3`
- 禁止 `AutoML`
- 禁止神经网络
- 禁止大规模参数搜索

本目录不应存放训练日志、验证结果或调参历史。
