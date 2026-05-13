# Portfolio Diagnostic Round Decision Record

## Scope

本记录用于固定当前 `portfolio diagnostic round` 的收口结论。本文档只汇总已经存在的 `trainval diagnostic-only` 证据，不做新实验，不训练，不跑回测，不读取 frozen test，不生成新的 metrics/readout，不设计 `v4` 参数，不修改 `confirmed5 / v2 / v3 / baseline`，也不把 trainval diagnosis 当 OOS。

## Decision Context

当前研究背景已经固定：

- `confirmed5 / v2 / v3` 均不晋级
- `next research roadmap` 已完成
- 当前只允许 `diagnostic-only research`
- 当前不允许直接开新 challenger / `v4`

本轮 portfolio diagnostic round 只收口以下三个方向：

1. `TopK head quality gate`
2. `turnover-aware admission`
3. `baseline overlap / divergence`

## Decision Summary

当前轮决策必须固定为：

- `不建议启动 TopK head quality gate challenger`
- `不建议启动 turnover-aware admission challenger`
- `不建议直接启动 divergence-aware challenger`
- `divergence` 方向值得继续做 `exposure decomposition`
- 当前不应开新 challenger / `v4`
- 如果继续，下一步应先研究 `baseline divergence names` 的 `D0` 暴露来源

## Evidence Chain

### 1. TopK Head Quality Gate

当前诊断结论已经固定为：

- `TopK head quality gate diagnosis 已完成`
- `证据不足`
- `不建议进入 challenger`

原因不是“完全没有现象”，而是：

- 已检查的 `score dispersion / score gap / score concentration / pool separation / D0 exposures` 没有在 `confirmed5` 与 `v2` 上形成共享、低自由度、可复用的弱 head 条件。
- `confirmed5` 与 `v2` 的弱状态更多呈现为 `candidate-specific` 暴露差异，而不是单一的、稳定的 `gate` 触发条件。
- 因此它不能被压缩成一个现在就可立项的 `TopK head quality gate challenger`。

### 2. Turnover-Aware Admission

当前诊断结论已经固定为：

- `turnover-aware admission diagnosis 已完成`
- `证据不足`
- `不建议进入 challenger`

这条方向被否定的关键原因是：

- `confirmed5` 的确表现出更高 churn，且 validation 中 `new entrants` 明显弱于 `retained names`。
- 但 `v2` 没有给出同方向、同强度的支持。
- 更关键的是，`high churn vs low churn` 的日级 realized return 差异在 `train / validation` 间没有稳定同向。

因此当前更准确的表述不是“admission rule 已被证实”，而是：

- `confirmed5` 存在 churn / entrant 弱化现象
- 但它还不足以沉淀成跨失败 nonlinear 候选可复用的低自由度 `admission rule`

### 3. Baseline Overlap / Divergence

当前诊断结论已经固定为：

- `baseline-only names` 系统性优于 `nonlinear-only names`
- `divergence spread` 在 `train / validation` 同方向
- `baseline` 赢的日期主要来自 `divergence selection`

这说明：

- `baseline` 的优势并不主要来自 overlap names
- `baseline` 更像赢在 divergence names 的选择质量

但该方向当前仍然不能直接变成规则，原因是：

- `confirmed5` 与 `v2` 的 divergence names 在 `D0` 暴露结构上并不一致
- 这意味着“baseline 更擅长 divergence selection”是一个已观察到的现象，但还不是一个已压缩完成的低自由度 `divergence-aware rule`
- 因此当前仍然 `不建议直接启动 divergence-aware challenger`

## Why The First Two Directions Are Rejected

前两个方向当前被否定，不是因为它们完全没有诊断价值，而是因为它们都没有跨 `confirmed5 / v2` 形成：

- 稳定
- 低自由度
- `D0` 可见
- `train / validation` 同方向
- 可复用到新 challenger 设计的规则证据

更具体地说：

- `TopK head quality gate` 缺少共享弱状态
- `turnover-aware admission` 缺少稳定 churn 惩罚证据

因此这两个方向目前都只能停留在 `diagnostic-only`，不能进入 challenger 立项。

## Why Divergence Has A Real Phenomenon But Not Yet A Rule

`divergence` 方向和前两个方向不同，它已经有明确现象：

- `baseline-only` 相对 `nonlinear-only` 的收益差为正
- 该差异在 `train / validation` 同方向
- baseline 赢的日期主要来自 divergence spread

但它仍然不能直接成为规则，原因在于：

- 目前只能说 `divergence selection` 是 baseline edge 的主要承载位置
- 还不能说“某个统一的 D0 暴露条件”就是 divergence edge 的来源
- 如果现在直接立一个 `divergence-aware challenger`，本质上仍然是在现象层跳到规则层，证据链还不够短、还不够低自由度

因此当前必须明确写成：

- `divergence 有现象`
- `规则证据不足`

## Current Decision

当前轮决策固定如下：

- `不建议进入 challenger`
- `不建议进入 TopK head quality gate challenger`
- `不建议进入 turnover-aware admission challenger`
- `不建议进入 divergence-aware challenger`
- `不建议开新 challenger / v4`

这是一个 `trainval diagnostic-only decision`，不是 `OOS`，不是 frozen test，不是 formal strategy approval。

## Next-Step Recommendation

如果继续当前研究，下一步建议固定为：

- 先做 `baseline divergence exposure decomposition`
- 优先研究 `baseline divergence names` 的 `D0` 暴露来源
- 先回答 baseline 在 divergence names 上到底更像赢在什么暴露结构
- 在没有把 divergence edge 压缩成低自由度证据之前，不进入新 challenger / 新 manifest / `v4`

换句话说，当前最合理的下一步不是继续发明规则，而是先补完：

- `baseline divergence exposure decomposition`

## Boundary

本文档继续固定以下边界：

- `不训练模型`
- `不跑回测`
- `不读取 frozen test`
- `不生成 metrics/readout`
- `不设计 v4 参数`
- `不修改 confirmed5 / v2 / v3 / baseline`
- `不围绕 validation 调参`
- `不把 trainval diagnosis 当 OOS`
- `不宣称策略有效`

## Final Status

- 本轮 `portfolio diagnostic round` 已收口。
- 三个 diagnostic 方向都没有产生当前可立项的 challenger 证据。
- `divergence` 方向保留为下一步值得继续诊断的方向，但目前仍停留在“有现象、规则证据不足”。
- 当前不建议开新 challenger。
