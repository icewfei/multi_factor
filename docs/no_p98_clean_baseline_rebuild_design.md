# no-p98 clean baseline rebuild design

## Scope

本设计用于定义一个不依赖 `p98`、不依赖 trainval label-based source selection 的 clean baseline rebuild 方案。本文档只讨论 clean baseline 的设计与治理边界，不训练，不跑 portfolio，不生成 formal metrics/readout，不读取 `frozen test`，不修改当前 `multi_equal_weight_v1` 历史记录，不把 trainval 当 `OOS`。

## baseline_id

- `baseline_id`: `no_p98_reversal_baseline_v1`

## Design Summary

- 目标 baseline 是 `clean baseline candidate`
- score source 固定为 `c1 ASC / reversal_rank`
- `no p98`
- `no label-based source selection`
- 输入边界固定为 `D0 visible only`
- `no frozen test access`
- 该 baseline 不是策略成功声明
- 该 baseline 用于替代或并列当前 `conditional baseline`

## Score Source

### 1. Primary Score Line

- baseline score source: `exploratory_cross_horizon_c1_reversal_only`
- executed direction basis: `c1 ASC / reversal_rank`
- source score artifact target: `model_score_D0`

### 2. Explicit Exclusions

- `no p98`
- 不允许 `reversal_tail_exclude_p98_v1`
- 不允许任何 tail-handling promotion 组件进入 clean baseline source chain
- `no label-based source selection`
- 不允许使用 `median_daily_ic`
- 不允许使用 `top10_avg_label`
- 不允许使用 `top10_bot10_spread`
- 不允许使用 `label_5d_next_open_close`

### 3. Governance Interpretation

- `c1` 当前可作为 clean baseline rebuild 的候选 score source，是因为 source-chain artifact 可重建，且 `D0 visibility / leakage audit` 已通过
- 这只说明它可以作为 clean baseline candidate 的分数来源
- 这不是策略成功声明，不是 portfolio 胜利声明，也不是 `OOS` 证明

## Input Fields

clean baseline rebuild 的允许输入字段固定为：

- `D0 visible only`
- `adj_close`
- `ranking_eligible_D0`
- `snapshot_id`

如果需要连接键或同义字段，应仅服务于把上述可见字段映射进 `c1 ASC / reversal_rank` 的计算链，不得扩展到标签、执行结果或未来收益反馈。

## Prohibited Fields And Feedback

以下内容不得进入 clean baseline source selection、score build、audit judgment 或升级判断：

- `label_*`
- `realized_return`
- `actual_exit_date`
- `actual_sell_price`
- `future return`
- `validation/frozen/test feedback`

同时禁止：

- 任何围绕 validation 的调参
- 任何 trainval label diagnostics 驱动的 source selection
- 任何冻结测试集读取或引用
- 任何复杂模型设计

## Promotion Usage

- 晋级用途：`clean baseline candidate`
- 不是策略成功声明
- 用于替代或并列当前 `conditional baseline`

当前允许的治理表述是：

- `clean baseline candidate`
- `replacement-or-parallel reference for the current conditional baseline`

当前禁止的治理表述是：

- `validated winning strategy`
- `formal success claim`
- `OOS-proven baseline`
- `frozen-test-cleared baseline`

## Required Future Artifacts

未来如果执行这条 rebuild，必须输出以下 artifact：

- `model_scores_D0.parquet`
- `model_scores_D0_audit.json`
- `source_chain_audit.json`
- `run_state_attempt_manifest.json`

这些 artifact 的用途是治理可复验，不是 formal metrics/readout 的替代物。

## Fail-Fast Conditions

出现以下任一情况，clean baseline rebuild 必须 fail-fast：

- 出现 `p98`
- 出现 `label diagnostics`
- 出现 `frozen test`
- `score direction` 不明
- `D0 visibility` 不成立

更具体地说，以下情况必须直接阻断：

- source chain 中出现 `reversal_tail_exclude_p98_v1`
- 文档、配置或脚本出现 `median_daily_ic`
- 文档、配置或脚本出现 `top10_avg_label`
- 文档、配置或脚本出现 `top10_bot10_spread`
- 文档、配置或脚本出现 `label_5d_next_open_close`
- 任何 `frozen test` access 变为 true
- `c1 ASC / reversal_rank` 不能被清晰声明为 score direction
- builder 不能满足 `D0 visible only`

## Governance Boundary

- `no p98`
- `no label-based source selection`
- `D0 visible only`
- `no frozen test access`
- 不训练 ML 模型
- 不跑 portfolio
- 不生成 formal metrics/readout
- 不围绕 validation 调参
- 不修改当前 `multi_equal_weight_v1` 历史记录

## Final Record

- baseline_id: `no_p98_reversal_baseline_v1`
- score source: `c1 ASC / reversal_rank`
- p98 usage: `no p98`
- label-based selection usage: `no label-based source selection`
- input visibility: `D0 visible only`
- frozen-test policy: `no frozen test access`
- intended role: `clean baseline candidate`
