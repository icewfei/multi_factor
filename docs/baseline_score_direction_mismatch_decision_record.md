# baseline score direction mismatch decision record

## Scope

本记录用于冻结 `exploratory_cross_horizon_c1_reversal_only` 的 `score_rule` 方向不一致问题应如何表述。本文档只基于已经完成的 source-chain rebuild / audit 结论，不训练模型，不跑回测，不读取 `frozen test`，不生成新的 metrics/readout，不修改 baseline / challenger，不修改历史 registry 记录来美化问题。

## Decision Summary

- registry 写法是 `registry DESC`
- implementation 实际是 `implementation ASC / reversal_rank`
- executed behavior evidence 支持 `ASC / reversal_rank`
- 当前定性为：`registry documentation mismatch`
- 但历史治理层面仍保留 `direction mismatch disclosure blocker`
- baseline remains conditional
- `p98 source-selection feedback risk remains`
- `no frozen test access`

## Evidence Boundary

本记录接受以下已经固定的重建结论：

- `c1` artifact 可以本地重建
- `c1` D0 visibility audit 通过
- `c1` leakage audit 通过
- 重建证据显示：
  - c1 score 与 `reversal_rank` 精确匹配 `10,776,418` 行
  - c1 score 只与 `reversal_followthrough_rank` 匹配 `2,652` 行

这些证据足以支持 executed behavior judgment，但不构成 `OOS` 或 `frozen test` 结论。

## Mismatch Classification

### 1. Registry Side

- registry 文字写的是 `percentile_rank(reversal_5d_raw DESC)`
- 这与本地 `single_signal_reversal_5d_v1` 的实现方向不一致

### 2. Implementation Side

- implementation 实际绑定的是 `single_signal_reversal_5d_v1 -> reversal_rank`
- `reversal_rank` 的排序定义是 `ORDER BY reversal_5d_raw ASC`

### 3. Executed Behavior Evidence

- executed behavior evidence 明确更支持 `ASC / reversal_rank`
- 证据强度已经足以反驳“实际执行方向是 DESC / reversal_followthrough_rank”的主要解释
- 因此，当前不应把这个问题定性为 implementation bug 已证实

## Formal Decision

当前正式定性为：

- `registry DESC` 与 executed implementation 不一致
- executed behavior evidence supports `implementation ASC / reversal_rank`
- 因此更合理的治理定性是：`registry documentation mismatch`

但这里不是“问题已经完全消失”。原因是：

- 历史 registry 仍然保留 `DESC` 文本
- 历史报告如果直接引用 registry，会与 executed behavior evidence 冲突
- 因此历史材料和后续报告都必须披露该 mismatch

## What This Decision Does Not Do

本记录明确不做以下动作：

- 不修改 baseline 行为
- 不修改历史 registry 来掩盖问题
- 不把 trainval rebuild 当成 `OOS`
- 不把这次方向判定当成 baseline upgrade approval
- 不解除 `p98` provenance 风险

## Required Disclosure

后续任何引用 `exploratory_cross_horizon_c1_reversal_only` 或其下游 baseline 的材料，都必须写明：

- registry 原文是 `DESC`
- implementation 实际是 `ASC / reversal_rank`
- executed behavior evidence supports `ASC / reversal_rank`
- historical reports must disclose mismatch
- baseline remains conditional
- `p98 source-selection feedback risk remains`
- `no frozen test access`

## Blocker Status

这次决策没有把 direction blocker 完全清零，只是把它从“方向未知”收敛成“方向已由 executed evidence 指向 ASC，但 registry documentation mismatch 仍需披露”。

因此当前 blocker 状态应表述为：

- `executed direction ambiguity`: substantially reduced
- `historical documentation mismatch`: still active
- `baseline promotion blocker`: still active

## Baseline Status

- baseline remains conditional
- 本次方向定性不改变 `multi_equal_weight_v1` 的 baseline 地位
- 在 `p98 source-selection feedback risk remains` 的前提下，baseline 仍不能升级为 unconditional gold standard

## Final Record

- classification: `registry documentation mismatch`
- executed behavior evidence: `supports ASC / reversal_rank`
- score direction blocker: `partially resolved for execution direction, not resolved for governance disclosure`
- baseline status: `conditional baseline`
- `p98 source-selection feedback risk remains`
- `no frozen test access`
