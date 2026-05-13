# Listing Age Conservative Proxy Boundary

## Scope

本文档只定义未来可能存在的 conservative proxy 边界，不实现 proxy，不放行 blocked 字段，不训练，不回测，不跑 portfolio，不读取 frozen test。

## Boundary Rule

- 如果未来想用 `calendar-day listing_age proxy`，必须是独立字段。
- 该 proxy 不得冒充 `listing_age_trading_days`。
- 该 proxy 不是对 blocked 字段的 silent fallback。

## Suggested Field Names

- `listing_age_calendar_days`
- `newly_listed_calendar_proxy`

## Mandatory Governance

- 必须单独 contract。
- 必须单独 audit。
- 必须单独 disclosure。
- 必须单独说明该 proxy 只代表 `calendar-day` 语义，不代表 `trading-day` 语义。
- 不能 silent fallback 到 `listing_age_trading_days`。

## Non-Substitution Rule

- `listing_age_calendar_days` 不能直接替代 `listing_age_trading_days`。
- `newly_listed_calendar_proxy` 不能直接替代 `newly_listed_flag`。
- conservative proxy 不能用于替代 blocked 字段，除非通过独立决策记录批准。
- 在独立决策记录批准前，proxy 只能被视为未来候选设计边界。

## Prohibited Uses

- 不得把 proxy 字段回填到原 `listing_age_trading_days` 列名。
- 不得把 proxy 字段包装成原 contract 已修复。
- 不得把 proxy 字段直接接入模型、baseline、challenger、portfolio 或筛选规则，除非先通过独立 decision record。
