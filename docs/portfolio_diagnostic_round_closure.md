# Portfolio Diagnostic Round Closure

## Scope

本文档用于收口当前 `portfolio diagnostic round`。本文档只汇总本轮已经完成的 `trainval diagnostic-only` 研究，不做新实验，不训练，不跑回测，不读取 frozen test，不生成新的 metrics/readout，不设计 `v4` 参数，不修改 `confirmed5 / v2 / v3 / baseline`，也不把 trainval diagnosis 当 OOS。

## Completed Diagnostics

本轮 `diagnostic-only` 已完成以下方向：

1. `TopK head quality gate diagnosis`
2. `turnover-aware admission diagnosis`
3. `baseline overlap / divergence diagnosis`
4. `baseline divergence exposure diagnosis`

## Direction Conclusions

### 1. TopK Head Quality Gate

- `证据不足`
- `不建议进入 challenger`
- `不建议进入 TopK head quality gate challenger`

当前没有形成跨 `confirmed5 / v2` 共享、低自由度、可复用的弱 head 条件，因此不能安全规则化。

### 2. Turnover-Aware Admission

- `证据不足`
- `不建议进入 challenger`
- `不建议进入 turnover-aware admission challenger`

`confirmed5` 的确表现出 churn / entrant 弱化现象，但 `v2` 没有给出一致支持，`high churn` 惩罚也没有在 `train / validation` 稳定同向。

### 3. Baseline Overlap / Divergence

- `baseline-only names` 系统性优于 `nonlinear-only names`
- `baseline` 赢的日期主要来自 `divergence selection`
- `不建议进入 divergence-aware challenger`

这说明 baseline 的优势确实主要承载在 divergence names 上，但目前还不能压缩成一条安全、低自由度、可复用的 `divergence-aware` 规则。

### 4. Baseline Divergence Exposure

- `D0` 暴露差异存在
- `confirmed5 / v2` 没有共享的单一低自由度 exposure pattern
- `不建议进入 exposure rule challenger`

更具体地说：

- `baseline-only vs confirmed5-only` 的暴露差异和 `baseline-only vs v2-only` 的暴露差异方向并不统一
- 因此当前不能把 baseline divergence selection 的优势安全规则化成单一 `exposure rule`

## Why No New Challenger

本轮四个方向都没有产出当前可立项的新 challenger 证据：

- 没有稳定、低自由度、`D0` 可见、跨候选共享的 `TopK head quality gate`
- 没有稳定、低自由度、`train / validation` 同向的 `turnover-aware admission rule`
- 没有可安全压缩成规则的 `divergence-aware rule`
- 没有跨 `confirmed5 / v2` 共享的单一 `exposure rule`

因此当前结论必须固定为：

- `不建议开新 challenger / v4`

## Baseline Divergence Status

当前可以明确确认两件事：

1. `baseline` 确实赢在 `divergence selection`
2. 当前还没有找到可安全规则化的 `D0` 证据

也就是说：

- `baseline divergence 有现象`
- `规则证据不足`

这条边界必须保持清楚，不能把“有现象”提前包装成“已有规则”。

## Next-Stage Recommendation

如果后续还继续当前主题，下一阶段更适合做：

- `数据字段补全`
- `baseline 机制复核`

而不是继续围绕现有字段做规则挖掘。

更具体地说，下一阶段更合理的问题是：

- 当前缺失的字段是否值得补全，例如 `industry / ST / listing age / limit / suspension` 等
- baseline divergence selection 的优势，到底更多来自哪些尚未被当前诊断输入直接覆盖的机制
- baseline 本身是否存在需要单独复核的组合构造或选择机制

## Boundary

本文档继续固定以下边界：

- `不训练模型`
- `不跑回测`
- `不读取 frozen test`
- `不生成 metrics/readout`
- `不设计 v4 参数`
- `不围绕 validation 调参`
- `不宣称策略有效`
- `不把 trainval diagnosis 当 OOS`

## Final Status

- 本轮 `portfolio diagnostic round` 已完成并收口。
- 四个诊断方向都没有形成当前可安全立项的 challenger 证据。
- 当前不建议开新 challenger / `v4`。
- 后续如继续，更适合先做 `数据字段补全` 或 `baseline 机制复核`，而不是继续规则挖掘。
