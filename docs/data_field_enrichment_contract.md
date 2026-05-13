# Data Field Enrichment Contract

## Scope

本文档定义统一的 `enriched security state / tradability metadata contract`，作为后续 `clean baseline / challenger` 研究的 `D0` 可见状态字段来源。本文档只定义 contract / schema / design，不下载新数据，不训练，不回测，不读取 frozen test，不生成 metrics/readout，不设计 `v4`，也不把字段设计包装成 alpha。

本文档坚持以下硬边界：

- `D0 visible only`
- `no frozen test access`
- `fail-fast`
- `not alpha / not strategy approval`

## Current Stage Position

当前阶段位置已经固定：

- `data field enrichment roadmap` 已提交。
- 当前项目不建议继续开 `v4`。
- `clean baseline family` 已收口，干净但不够强。
- `p98 baseline` 只是 `conditional reference only`。
- 下一阶段转向 `data contract / field enrichment`。
- 当前只做 contract/schema/design，不做数据下载或实现。

## Contract Goal

本 contract 的目标是定义一张统一的 `D0` 状态字段表，供未来 clean baseline / challenger 研究共享使用。该表不承担 alpha 生成职责，不承担策略批准职责，不承担任何回测 readout 产出职责。它只承担三件事：

1. 提供统一字段名和字段类型。
2. 提供统一的 `D0` 可见性规则。
3. 提供统一的 `fail-fast` 与审计输出契约。

## Canonical Entity

统一实体定义为 `enriched_security_state_daily_v1`。

- 主键：`snapshot_id + instrument + signal_date`
- `signal_date` 是 canonical 日期字段。
- `trade_date` 仅允许作为仓库别名存在；若提供，必须与 `signal_date` 相等。
- 任一字段若依赖 `D1+` 状态、执行结果、未来制度状态、future rebinding、或 frozen test 观察结果，直接越界。

## Covered Field Categories

contract 覆盖以下字段类别：

1. `identity fields`
2. `ST fields`
3. `suspension / no trade fields`
4. `limit status fields`
5. `tradability state fields`
6. `listing age fields`
7. `board / segment fields`
8. `audit/provenance fields`

## D0 Visibility Rules

所有字段都必须满足以下 `D0` 可见性规则：

- 只允许 `D0` 当日可见状态，或截至 `D0` 的历史累计状态。
- 不允许使用 `D1` 是否成交、`entry_filled_D1`、未来是否开板、未来 ST 变更、未来停牌恢复、未来股本修订等任何未来状态。
- `signal_date` 的状态字段可以使用 `D0` 日终行情、`D0` 生效制度、`D0` 生效证券状态、以及截至 `D0` 的历史映射。
- `listing_age_days` 与 `listing_age_trading_days` 只能由 `list_date` 与截至 `D0` 的交易日历推导。
- `d0_visible=true` 必须是审计字段，不允许省略。
- `no_frozen_test_access=true` 必须是审计字段，不允许省略。

## Fail-Fast Rules

以下情况必须直接 `fail-fast`：

- 字段没有 point-in-time 生效规则。
- 字段来源不能证明是 `D0` 可见。
- 字段依赖 `future state`、执行结果、或 frozen test。
- 字段枚举不稳定，或不同来源冲突而无优先级契约。
- `trade_date` 与 `signal_date` 不一致。
- `limit_rule_version` 无法由 `board_type / exchange / limit_pct_rule` 自洽解释。
- `listing_age_*` 无法由 `list_date` 与交易日历复原。
- `source_snapshot_id` 缺失，或与上游研究快照绑定不一致。
- `d0_visible=false` 或 `no_frozen_test_access=false`。

## Audit Outputs

本 contract 只定义未来必须产出的审计输出名称与断言，不在当前阶段生成任何 readout：

- `field_contract_audit.json`
- `field_source_binding_audit.json`
- `field_population_audit.json`

这些审计输出至少必须断言：

- 全部 required 字段存在。
- 每个字段都保留 `d0_visibility` 与 `fail_fast_condition` 契约。
- `d0_visible=true`
- `no_frozen_test_access=true`
- 无 future-state 字段接入
- 无 `metrics/readout`
- 无 `alpha` / 无 `strategy approval`

## Category Summary

高优先级类别是：

1. `ST fields`
2. `suspension / no trade fields`
3. `limit status fields`
4. `tradability state fields`
5. `listing age fields`

其中：

- `ST fields` 负责识别历史风险警示状态。
- `suspension / no trade fields` 负责识别停牌与无成交状态。
- `limit status fields` 负责识别涨跌停与一字限制。
- `tradability state fields` 负责把研究里隐含的可交易性拆成可审计布尔状态。
- `listing age fields` 负责识别次新与上市早期样本。

## Explicit Prohibitions

本 contract 明确禁止：

- 下载新数据。
- 训练模型。
- 回测。
- 读取 `frozen test`。
- 生成新的 `metrics/readout`。
- 把字段设计包装成 `alpha`。
- 把字段设计解释成 `strategy approval`。
- 设计 `v4` 或任何新策略。
- 使用未来状态。

## Final Status

该 contract 是统一字段来源约束，不是研究赢家声明，不是策略批准，不是 `OOS`，也不是 `frozen test` 结果。只有当字段来源、`D0` 可见性、`fail-fast` 条件和审计输出全部固定后，后续 clean baseline / challenger 才有继续推进的输入基础。
