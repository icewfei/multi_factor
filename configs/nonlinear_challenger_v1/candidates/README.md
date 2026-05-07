# candidates 目录说明

本目录用于保存 `candidate_scheme manifest` 的模板与后续预注册文件。

`candidate_scheme manifest` 的作用是：

- 把单个候选与 `feature_set`、`model_config`、`snapshot_id` 绑定
- 冻结候选预算内的正式比较对象
- 明确允许查看的 readout 与晋升/失败规则

第一版约束如下：

- 总候选数最多 `6` 个
- `candidate_scheme_id` 必须唯一
- 同一 `candidate` 不能在跑完后再改 `feature_set` 或 `model_config`
- 失败候选必须保留

本目录只负责事前预注册，不负责运行后证据登记。
