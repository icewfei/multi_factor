# Data Field Enrichment V1 Decision Record

## Current Status

`data_field_enrichment_v1` 当前状态为 `conditional_pass`。

真实 trainval smoke gate 已在本地 snapshot `warehouse_20260429_trainval_20211231` 上完成，builder 与 audit 都已跑通，且没有读取 frozen test，没有训练，没有回测，没有跑 portfolio。

当前审计结论：

- `row_count = 11219145`
- `instrument_count = 4370`
- `signal_date range = 2000-01-04 ~ 2021-12-31`
- `d0_visible_all_true = true`
- `no_frozen_test_access = true`
- `final_status = conditional_pass`

## Usable Fields

以下字段当前可用于后续 `clean baseline / challenger` 的共享输入层：

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

这些字段当前处于 `pass`，可以进入后续 clean baseline / challenger 的输入准备与诊断层，但这不等于策略批准。

## Unavailable Fields

以下字段当前不可用：

- `listing_age_trading_days`
- `newly_listed_flag`

原因不是 future leak，也不是 frozen test，而是本地 `warehouse/core/calendar.parquet` 的历史起点为 `2000-01-04`。对于更早上市的股票，无法在当前本地 source 上精确复原完整 `listing_age_trading_days`。builder 没有静默回退，也没有编造字段，而是把这两个字段显式保留为 `blocked`。

当前 `blocked` 字段行级缺口：

- `listing_age_trading_days`: `4353900` rows null / blocked
- `newly_listed_flag`: `4353900` rows null / blocked

当前 `missing_source / blocked` 结论：

- `missing_source`: `none`
- `blocked`: `listing_age_trading_days`, `newly_listed_flag`

## Boundary Statements

这不是 alpha。

这不是 strategy approval。

本流程不读取 frozen test。

本流程不训练，不回测，不跑 portfolio。

本流程不把字段补全包装成 alpha，也不把字段补全解释成策略有效。

## Next Step

下一步建议：

1. 后续 `clean baseline / challenger` 只消费当前 `pass` 字段，不消费 `listing_age_trading_days` 与 `newly_listed_flag`。
2. 若本地已存在更早历史的交易日历来源，可在不下载新数据的前提下补齐 `listing_age_trading_days`，然后仅重跑 builder + audit。
3. 若本地没有更早历史日历来源，则应把 `listing_age_trading_days` 与 `newly_listed_flag` 从当前主路径中显式降级，而不是做近似回填或静默裁剪。
