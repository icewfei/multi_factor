# baseline p98 feedback risk decision record

## Scope

本记录用于正式冻结 `reversal_tail_exclude_p98_v1` 的 `source-selection feedback risk` 应如何定性，以及该结论对 baseline 治理地位的影响。本文档只基于已经完成的 baseline source-chain provenance audit、baseline c1/p98 source-chain rebuild、baseline status decision 和 score direction mismatch decision，不训练，不回测，不读取 `frozen test`，不生成新的 metrics/readout，不修改 baseline / challenger，不修改历史 registry，不把 trainval 当 `OOS`。

## Decision Summary

- `p98 source-selection feedback risk remains`
- `p98 is not clean baseline component`
- `multi_equal_weight_v1 remains conditional baseline`
- `no-p98 clean baseline rebuild is recommended`
- `trainval label-based diagnostics` 不能作为 clean baseline source selection 的无条件依据
- 后续报告必须披露 `p98 feedback risk`
- `no frozen test access`

## Evidence Boundary

本记录接受以下已完成、已冻结的证据边界：

- [baseline_source_chain_provenance_audit.md](/Users/wy/MiscProject/multi_factor/docs/baseline_source_chain_provenance_audit.md)
- [baseline_c1_p98_source_chain_rebuild.md](/Users/wy/MiscProject/multi_factor/docs/baseline_c1_p98_source_chain_rebuild.md)
- [multi_equal_weight_baseline_status_decision_record.md](/Users/wy/MiscProject/multi_factor/docs/multi_equal_weight_baseline_status_decision_record.md)
- [baseline_score_direction_mismatch_decision_record.md](/Users/wy/MiscProject/multi_factor/docs/baseline_score_direction_mismatch_decision_record.md)

当前证据边界明确包含：

- `c1 source-chain artifact rebuild` 已完成
- executed behavior 支持 `ASC / reversal_rank`
- registry `DESC` 已定性为 `historical documentation mismatch`
- baseline 仍是 `conditional baseline`
- `p98` tail-handling prereg 明确依赖 trainval label-based learnability diagnostics：
  - `median_daily_ic`
  - `top10_avg_label`
  - `top10_bot10_spread`
  - `label_5d_next_open_close`
- `no frozen test access`

这些证据足以做治理定性，但不足以把 trainval diagnostic selection 包装成 clean baseline provenance。

## Risk Classification

### 1. What The Risk Is

- `p98` score builder 本身没有被定性为 direct future leakage
- 当前问题不在于 builder 直接读了未来字段，而在于 `p98` 的 source selection / tail-handling promotion 依赖 trainval label-based learnability diagnostics
- 这意味着 `p98` 的进入 baseline 链条，不是无条件、feedback-free、pre-label-isolated 的 clean source selection

### 2. Why The Risk Remains

- prereg 已经把 `median_daily_ic`、`top10_avg_label`、`top10_bot10_spread`、`label_5d_next_open_close` 写进 learnability diagnostics
- 这些诊断口径本质上依赖 label outcome
- 即使它们属于 trainval diagnostic，而不是 frozen test，也仍然会把 label-based evidence 带入 source-selection judgment
- 因此 `p98 source-selection feedback risk remains`

### 3. What This Risk Is Not

- 这不是在宣称 `p98` builder 已证实存在 direct label leakage
- 这不是在宣称 trainval diagnosis 等于 `OOS`
- 这不是在宣称已经看过 `frozen test`
- 这不是在美化为“风险已经消失，只差披露”

## Formal Decision

当前正式治理定性为：

- `p98 source-selection feedback risk remains`
- `p98 is not clean baseline component`
- `p98` 不能继续被表述为 clean baseline 的组成部分
- `trainval label-based diagnostics` 不能作为 clean baseline source selection 的无条件依据

因此当前不能把 `p98 tail-handling` 当作 clean baseline component 保留在 baseline clean lineage 里。

## Baseline Status Impact

### 1. p98 Component Judgment

- `p98 is not clean baseline component`
- 在当前证据边界下，`p98` 只能被视为带有 source-selection feedback risk 的历史组件
- 它可以作为历史 baseline 链条的一部分被披露，但不能作为 clean baseline provenance 的合格组成部分被背书

### 2. multi_equal_weight_v1 Judgment

- `multi_equal_weight_v1 remains conditional baseline`
- `p98` 风险没有因为 `c1 rebuild` 或 score direction mismatch 收敛而自动消失
- 因此 `multi_equal_weight_v1` 仍只能保持 `conditional baseline`
- challenger 若输给当前 baseline，仍只能表述为 `did not beat conditional baseline`

### 3. Clean Baseline Judgment

- `no-p98 clean baseline rebuild is recommended`
- 如果后续需要 clean baseline，应当新建一个不把 `p98` 作为组件的 clean baseline rebuild
- 该 rebuild 应避免把 trainval label-based diagnostics 当作无条件 source-selection gate

## Required Disclosure

后续任何引用当前 baseline、`p98 tail-handling`、或 `multi_equal_weight_v1` 的报告，都必须写明：

- `p98 source-selection feedback risk remains`
- `p98 is not clean baseline component`
- `multi_equal_weight_v1 remains conditional baseline`
- `no frozen test access`
- `trainval label-based diagnostics` 不能作为 clean baseline source selection 的无条件依据
- 后续报告必须披露 `p98 feedback risk`

禁止表述：

- `p98 has been cleared as clean baseline component`
- `trainval learnability diagnostics are sufficient unconditional justification for clean baseline source selection`
- `current baseline is now unconditional clean baseline`
- `frozen test evidence cleared p98`

## What This Decision Does Not Do

本记录明确不做以下动作：

- 不修改 baseline / challenger
- 不修改历史 registry
- 不新建策略设计
- 不训练模型
- 不跑回测
- 不读取 `frozen test`
- 不生成 metrics/readout

## Next Step

- 第一建议：启动 `no-p98 clean baseline rebuild`
- 第二建议：在所有后续 baseline / challenger 报告中继续披露 `p98 feedback risk`
- 第三建议：在 clean baseline 重建前，继续把当前 baseline 仅表述为 `conditional baseline`

## Final Record

- p98 feedback risk status: `remains`
- p98 clean-component status: `not clean baseline component`
- current baseline status: `conditional baseline`
- clean-baseline recommendation: `no-p98 clean baseline rebuild`
- evidence boundary: `no frozen test access`
