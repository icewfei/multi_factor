# Data Enrichment Next-Use Guardrail Decision Record

## Decision

`data_field_enrichment_v1` 的 next-use guardrail 已实现，并且已经把文档约束落成代码门禁。

该 guardrail 只读取 next-use policy 和下游 request JSON，不读取市场数据，不读取 frozen test，不训练，不回测，不跑 portfolio，不生成 formal metrics/readout。

## What The Guardrail Enforces

- blocked fields 会 `fail-fast`。
- `listing_age_trading_days` 请求会被直接 blocked。
- `newly_listed_flag` 请求会被直接 blocked。
- 未知字段请求会被直接 blocked。
- `conditional_pass` 必须披露。
- 若 request 试图声称 `full_pass`，会被直接 blocked。
- `portfolio / screening` 使用当前不允许。
- `no frozen test access` 必须为 true。
- `no silent fallback` 是硬边界。

## Current Boundary

当前 `data_field_enrichment_v1` 仍然只是 `conditional enrichment layer`。

这不是 alpha。

这不是 strategy approval。

这不是 OOS。

blocked 字段不会被放行，也不会被 silent fallback 伪装成 allowed 字段。

## Next Step

如果后续要接入 `clean baseline / challenger`，必须先通过该 guardrail。

如果 request 无法通过 guardrail，就不允许进入后续 clean baseline / challenger / diagnostic 链路。
