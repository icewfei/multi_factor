# multi_equal_weight_v1 Baseline Status Decision Record

## Scope

本记录用于冻结 `multi_equal_weight_v1` 在当前阶段的治理地位。本文档只基于已经完成的 baseline mechanism audit、baseline source-chain provenance audit 和既有 same-contract comparison 结论，不新增实验，不训练，不回测，不读取 `frozen test`，不生成新的 metrics/readout，不修改 baseline / challenger。

## Decision Summary

- `multi_equal_weight_v1` 当前只能作为 `conditional baseline`
- `multi_equal_weight_v1` 当前 `not unconditional gold standard`
- downstream same-contract comparison 仍然可用，但必须同步披露 baseline provenance blocker
- challenger 若输给 baseline，只能表述为 `did not beat conditional baseline`，不能表述为绝对失败
- baseline 上游 source-chain 补齐之前，不得升级 baseline 地位
- 当前不建议继续开新 challenger
- 下一步应优先补 baseline `c1 / p98` source-chain artifacts，或重建一个 clean baseline
- `no frozen test access`

## Evidence Boundary

- [multi_equal_weight_baseline_mechanism_audit.md](/Users/wy/MiscProject/multi_factor/docs/multi_equal_weight_baseline_mechanism_audit.md)
- [baseline_source_chain_provenance_audit.md](/Users/wy/MiscProject/multi_factor/docs/baseline_source_chain_provenance_audit.md)

当前可接受的证据边界是：

- baseline mechanism audit 已完成，并且没有发现直接 future function / label leakage / realized return leakage
- baseline downstream same-contract comparison 暂时仍可用
- 但这些证据都属于 trainval / governance 层，不是 `OOS`，不是 `frozen test`

## Status Decision

### 1. Why It Remains Usable

- `multi_equal_weight_v1` 的可见 score builder 没有发现直接未来函数、label 泄漏或 realized return 泄漏。
- 当前仍可把它保留为后续 challenger 的比较门槛，因为 downstream same-contract comparison 口径仍然成立。
- 这个“可用”结论只支持 `conditional baseline`，不支持 unconditional promotion。

### 2. Why It Is Not Gold Standard

- upstream source-chain provenance 结论是 `blocked`
- `exploratory_cross_horizon_c1_reversal_only` 当前不能完整 artifact-level 复验
- registry `score_rule` 与 implementation 存在 `score_rule direction mismatch`
- `p98` tail-handling chain 存在 `source-selection feedback risk`

因此：

- `multi_equal_weight_v1` 不能被表述为 `unconditional gold standard`
- `multi_equal_weight_v1` 只能被表述为 `conditional baseline`

## Required Disclosure

后续任何 challenger 报告只要继续与 `multi_equal_weight_v1` 比较，必须同时披露以下 blocker：

- `upstream source-chain provenance blocked`
- `score_rule direction mismatch`
- `source-selection feedback risk`
- baseline comparison 只说明 challenger 是否超过当前 `conditional baseline`
- baseline provenance 未补齐前，比较结果不得上升为“gold standard defeat”
- `no frozen test access`

## Required Language

允许表述：

- `did not beat conditional baseline`
- `weaker than the current conditional baseline under same-contract comparison`
- `baseline comparison remains usable with disclosure`

禁止表述：

- `failed absolutely`
- `lost to gold standard baseline`
- `baseline is validated as unconditional gold standard`
- `trainval comparison proves OOS weakness`
- `frozen test evidence exists`

## Challenger Interpretation Rule

- 后续 challenger 如果没有超过 `multi_equal_weight_v1`，只能解释为：`未超过当前 conditional baseline`
- 不能把“输给 baseline”改写成策略方向的绝对失败
- 在 baseline provenance blocker 仍存在时，baseline defeat 不是最终研究封口证据

## Upgrade Gate

只有在以下条件满足后，`multi_equal_weight_v1` 才有资格讨论升级：

- `exploratory_cross_horizon_c1_reversal_only` 的 source-chain artifacts 可本地重验到 artifact / manifest / audit 级别
- registry `score_rule` 与 executed implementation 的方向差异被消解
- `p98` source selection 链条可以被更干净地重建，或被一个 clean baseline 替代

在此之前：

- baseline 地位冻结为 `conditional baseline`
- `not unconditional gold standard`

## Next Step

- 第一优先级：补 baseline `c1 / p98` source-chain artifact rebuild
- 备选路径：clean baseline rebuild
- 当前不建议继续开新 challenger，因为新的 challenger 仍会锚定在一个 provenance blocked 的 baseline 上
- `no frozen test access`

## Final Record

- current baseline status: `conditional baseline`
- current gold-standard status: `not unconditional gold standard`
- same-contract baseline comparison: `remains usable with disclosure`
- baseline upgrade status: `blocked until source-chain evidence is repaired`
