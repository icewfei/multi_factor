# Data Field Enrichment Blocked Field Remediation Plan

## Scope

本文档定义 `data_field_enrichment_v1` 中 blocked 字段的修复路线，只做 remediation planning，不实现策略，不训练，不回测，不跑 portfolio，不读取 frozen test，不生成 metrics/readout。

## Root Cause

- `listing_age_trading_days` 的根因是本地交易日历起点不足。
- 当前本地交易日历从 `2000-01-04` 开始，无法精确复原更早上市股票的 trading-day listing age。
- 对于 `2000-01-04` 之前上市的股票，`listing_age_trading_days` 无法从当前 contract 下精确复原。
- builder 选择 `fail-fast` 而不是 silent fallback，这是正确行为。

## Dependency

- `newly_listed_flag` 依赖 `listing_age_trading_days`。
- 因此 `newly_listed_flag` 继承 blocked 状态。
- 在 `listing_age_trading_days` 未修复前，`newly_listed_flag` 不得单独放行。

这里的核心约束是：newly_listed_flag 依赖 `listing_age_trading_days`，因此不存在脱离上游 blocked 字段的单独放行路径。

## Option 1: 补足更早历史交易日历

### Summary

方案 1 是补足更早历史交易日历，使 `listing_age_trading_days` 可以按原 contract 精确复原。

### Pros

- 保留原始 `trading-day` contract，不改字段语义。
- 不需要把 calendar-day proxy 冒充成 trading-day 字段。
- 泄漏风险最低，因为定义不变。

### Cons

- 需要补足更早历史交易日历来源，并审计其 point-in-time 绑定。
- 需要重新验证早期上市样本的 reproducibility。

### Leakage Risk

- 若使用后验修补、来源不清或未来修订版交易日历，可能把不可得历史知识伪装成原始可见状态。

### Fail-Fast

- 若更早历史交易日历无法证明来源、覆盖范围或 exchange 对齐，直接 fail-fast。

### New Contract Requirement

- 不需要新字段 contract，但需要更新 trading calendar binding 的治理记录和审计说明。

## Option 2: 新建 conservative calendar-day listing age proxy contract

### Summary

方案 2 是新建 `conservative calendar-day listing age proxy contract`，只提供独立 proxy，不冒充 `listing_age_trading_days`。

### Pros

- 不依赖补齐完整早期交易日历即可形成保守 proxy 边界。
- 可以更快为后续 diagnostic-only 讨论提供单独字段设计空间。

### Cons

- 不能与 `listing_age_trading_days` 混用。
- 不能保证与 trading-day 语义一致。
- 需要新增字段、单独 contract、单独 audit、单独 disclosure。

### Leakage Risk

- 最大风险是把 calendar-day proxy 当成 trading-day 字段 silent fallback。
- 另一个风险是将 proxy 误包装成 admission rule 或 alpha filter。

### Fail-Fast

- 若 proxy 字段名、contract、audit、disclosure 任何一项不独立，直接 fail-fast。

### New Contract Requirement

- 需要新 contract。
- 需要新字段名。
- 需要独立 decision record 批准其用途边界。

## Option 3: 继续禁用 blocked 字段

### Summary

方案 3 是继续禁用 `listing_age_trading_days` 与 `newly_listed_flag`，直到方案 1 或方案 2 完成。

### Pros

- 风险最低。
- 不引入额外语义漂移。
- 与当前 `conditional_pass` 结论完全一致。

### Cons

- downstream 失去 trading-day listing age 和次新标签字段。
- 某些 clean baseline / challenger 诊断切片需要延后。

### Leakage Risk

- 泄漏风险最低；主要风险反而来自绕过禁用规则的人工透传。

### Fail-Fast

- 一旦 downstream 请求使用 blocked 字段，直接 fail-fast。

### New Contract Requirement

- 不需要新 contract。

## Decision Boundary

- 在未完成修复前，blocked 字段不得进入研究链路。
- 在未完成修复前，`listing_age_trading_days` 不得进入模型、baseline、challenger、portfolio 或筛选规则。
- 在未完成修复前，`newly_listed_flag` 不得进入模型、baseline、challenger、portfolio 或筛选规则。
- 不允许 silent fallback。
- 不允许把 calendar-day proxy 直接替代 blocked 字段。

## Recommended Order

1. 先实现 downstream next-use guardrail，确保 blocked 字段 fail-fast。
2. 再在方案 1 和方案 2 之间做独立决策。
3. 若没有完成独立决策，则维持方案 3：继续禁用 blocked 字段。
