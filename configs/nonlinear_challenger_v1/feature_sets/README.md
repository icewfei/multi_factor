# feature_sets 目录说明

本目录用于保存 `feature_set manifest` 的模板与后续预注册文件。

`feature_set manifest` 的作用是：

- 冻结候选使用的特征清单
- 冻结特征家族与处理口径
- 明确 `D0` 可见性与 `PIT` 边界

第一版约束如下：

- 最多 `2` 个 `feature_set`
- 每个 `feature_set` 最多 `20` 个特征
- 特征必须 `D0` 可见
- 不得新增新数据源
- 不得根据 `validation` 结果事后替换特征

本目录不应存放训练结果、特征表现总结或验证指标。
