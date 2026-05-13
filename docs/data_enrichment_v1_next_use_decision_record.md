# Data Enrichment V1 Next-Use Decision Record

## Decision Scope

本 decision record 用于固定 `data_field_enrichment_v1` 的 next-use 结论。本文档只做治理决策，不训练，不回测，不跑 portfolio，不读取 frozen test，不生成 metrics/readout。

## Decision

- `data_field_enrichment_v1` 可以作为 `conditional enrichment layer` 使用。
- 该层只批准 pass 字段进入后续 `diagnostic / clean baseline / challenger` 的 `D0` 状态输入。
- 该层不是 `full pass`。
- 该层不是 alpha。
- 该层不是策略批准。
- 该层不是 `OOS`。

## Allowed Fields

允许字段以 `configs/data_field_enrichment/enrichment_next_use_policy_v1.json` 中的 `allowed_fields` 为准，包括：

- `snapshot_id`
- `instrument`
- `trade_date`
- `signal_date`
- `is_st`
- `st_source`
- `st_effective_start`
- `st_effective_end`
- `is_suspended`
- `no_trade_flag`
- `volume_zero_flag`
- `amount_zero_flag`
- `is_limit_up`
- `is_limit_down`
- `open_at_up_limit`
- `close_at_down_limit`
- `limit_rule_version`
- `entry_buyable`
- `exit_sellable`
- `sellable_retry_next_open`
- `list_date`
- `listing_age_days`
- `board_type`
- `exchange`
- `limit_pct_rule`
- `source_snapshot_id`
- `build_time`
- `builder_version`
- `d0_visible`
- `no_frozen_test_access`

## Blocked Fields

以下字段 blocked：

- `listing_age_trading_days`
- `newly_listed_flag`

blocked 字段修复前不得使用。

## Mandatory Downstream Rule

- downstream 必须遵守 next-use policy。
- downstream 必须显式拒绝 blocked 字段。
- downstream 不得把 `conditional_pass` 解释为 `full pass`。
- downstream 不得实现 silent fallback。
- downstream 不得读取 frozen test。

## Next Step

如果继续推进，优先顺序应为：

1. 先实现 `next-use guardrail`。
2. 或先补交易日历，再重新审计 `listing_age_trading_days`。

在上述两条至少完成一条前，不得放行 blocked 字段。
