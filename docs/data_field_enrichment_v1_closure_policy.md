# Data Field Enrichment V1 Closure Policy

## Scope

本文档用于收口 `data_field_enrichment_v1` 从 `conditional_pass` 到“可安全接入研究链路”的 next-use governance。本文档只定义使用边界、blocked 字段处理和 downstream guardrail，不训练，不回测，不跑 portfolio，不读取 frozen test，不生成 metrics/readout，不把 `conditional_pass` 包装成 `full pass`，也不把字段补全包装成 alpha。

## Fixed Status

当前状态已经固定：

- `data_field_enrichment_v1` 的 `final_status = conditional_pass`。
- `data_field_enrichment_v1` 是 `conditional enrichment layer`，不是 `full pass` enrichment layer。
- 大多数字段已经 audit pass，可以作为后续 `diagnostic / clean baseline / challenger` 的 `D0` 状态输入。
- `listing_age_trading_days` blocked。
- `newly_listed_flag` blocked。
- builder 保持 `no silent fallback`，这是正确行为。
- 当前不能把 `conditional_pass` 包装成 `full pass`。

## Next-Use Policy

允许的 next use 只限于已通过审计的 pass 字段，且用途只限于后续 `diagnostic / clean baseline / challenger` 的 `D0` 状态输入、状态切片、或治理校验。

可继续使用的 pass 字段为：

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

禁止使用的 blocked 字段为：

- `listing_age_trading_days`
- `newly_listed_flag`

## Mandatory Boundaries

- blocked 字段不得进入模型。
- blocked 字段不得进入 `baseline`。
- blocked 字段不得进入 `challenger`。
- blocked 字段不得进入 `portfolio`。
- blocked 字段不得进入筛选规则。
- blocked 字段不得作为 clean baseline admission 或 exclusion rule。
- `listing_age_trading_days` blocked 期间，不能用任何 silent fallback 冒充该字段。
- `newly_listed_flag` blocked 期间，不能继续透传到 downstream 研究链路。

## Governance Notes

- `data_field_enrichment_v1` 只是 `conditional enrichment layer`，不是 alpha。
- 本结论 `not alpha / not strategy approval / not OOS`。
- 本结论不构成策略批准，不构成部署批准，不构成 `OOS` 结论。
- `no frozen test access` 仍然是硬边界。
- 任何想读取 frozen test、训练模型、回测、跑 portfolio 的动作都不属于本文档批准范围。
- `no silent fallback` 是必须保留的 builder contract，不能改成静默降级。

## Closure Decision

当前 closure 决定如下：

1. 保留 `conditional_pass`，不得升级为 `full pass`。
2. 允许 pass 字段进入后续 `diagnostic / clean baseline / challenger` 的 `D0` 状态输入。
3. 保持 `listing_age_trading_days` blocked。
4. 保持 `newly_listed_flag` blocked。
5. 在 blocked 字段修复完成前，downstream 必须依赖显式 guardrail fail-fast 拦截。
