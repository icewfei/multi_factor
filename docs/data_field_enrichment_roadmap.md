# Data Field Enrichment Roadmap

## Scope

本文档用于收口当前阶段后的 `data field enrichment roadmap`，明确下一阶段应优先补哪些 `D0` 可见状态字段，以支持后续 `clean baseline / challenger` 研究。本文档只定义字段补全优先级与数据契约边界，不训练，不回测，不读取 frozen test，不生成 metrics/readout，不设计新策略，也不把字段补全直接包装成 alpha。

本路线图坚持 `D0 visible only`、`no frozen test access`、`fail-fast` 三条硬约束：

- 只接受 `D0` 当日可见或截至 `D0` 的历史字段。
- 只讨论潜在数据源与字段契约；如果项目当前数据层没有现成来源，本阶段只记录缺口，不下载新数据。
- 本文档是 research data contract，不是 `alpha`，不是策略批准，`not alpha / not strategy approval`。

## Current Stage Context

当前阶段结论已固定：

- `p98 conditional baseline` 强，但不干净。
- `no-p98 / clean baseline family` 更干净，但 `TopK head quality` 不足。
- `nonlinear confirmed5 / v2 / v3` 均不晋级。
- `portfolio diagnostic round` 已收口。
- `clean baseline family` 已收口。
- 当前不建议继续开 `v4`，也不建议继续跑 `portfolio`。
- 下一阶段应补数据字段，而不是继续用现有字段硬造规则。

## Prioritization Rule

字段优先级按以下原则排序：

1. 先补能定义样本清洁度、交易状态、制度边界的字段。
2. 再补能稳定解释 `TopK head quality` 差异的横截面状态字段。
3. 可选风险暴露字段只做补充审计，不得反客为主变成隐性新模型。

当前建议的高优先级顺序：

1. `ST historical status`
2. `suspension / no trade status`
3. `limit up / limit down status`
4. `tradability state fields`
5. `listing age / IPO age`
6. `board type / exchange segment`
7. `industry / sector classification`
8. `liquidity quality fields`
9. `market cap / float cap fields`
10. `optional risk exposure fields`

## Global Guardrails

- `D0 visible only`：任何字段若无法证明是 `D0` 可见或 `D0` 历史滚动可见，直接拒绝纳入。
- `no frozen test access`：字段定义、字段映射、优先级排序都不能读取 `frozen test`。
- `fail-fast`：字段若没有 point-in-time 生效日期、没有稳定枚举、没有可审计来源、或无法与现有主键对齐，直接停止，不做“先接进来再说”。
- `not alpha / not strategy approval`：字段补全仅服务于 clean baseline / challenger 研究输入与诊断，不等于规则上线许可，更不等于有效策略声明。

## Detailed Roadmap

### 1. industry / sector classification

- 用途：补充稳定的行业横截面标签，用于 clean baseline 的行业分层审计、baseline 与 challenger 的 head composition 对照、以及后续 regime slice 的最小解释框架。
- 是否 D0 可见：是，但必须 `D0 visible only`；只能使用 `D0` 当日生效的行业分类或截至 `D0` 已知的历史映射。
- 潜在数据源：现有 security master、现有日频股票基础信息表、项目已持有的申万/中信/证监会行业映射快照；若当前仓库无本地来源，只记录字段契约，不下载新数据。
- 对 baseline / challenger 的价值：对 baseline，能识别 clean baseline 是否过度集中于少数行业；对 challenger，能判断 head weakness 是否只是行业暴露失衡，而不是模型本身无效。
- 泄漏风险：最大风险是使用事后回填的行业口径、忽略分类调整生效日、或把未来行业迁移回填到历史。
- fail-fast 要求：若无法提供 `effective_start_date / effective_end_date` 或等价 point-in-time 审计能力，则整类字段不进入研究主路径。
- 是否优先级高：高，但低于交易状态类字段。

### 2. ST historical status

- 用途：识别 `ST / *ST / 风险警示` 历史状态，清理不干净 baseline 暴露，并用于解释极端尾部损失与可交易性缺口。
- 是否 D0 可见：是，且必须 `D0 visible only`；只能使用 `D0` 时点已经生效的 ST 状态与截至 `D0` 的历史状态持续天数。
- 潜在数据源：现有证券状态表、交易所风险警示状态表、日频基础信息表中的 ST 标记与生效日期字段。
- 对 baseline / challenger 的价值：对 baseline，这是当前最直接的“脏样本识别器”；对 challenger，它能区分 head quality 弱是模型排序问题，还是制度性高风险样本混入。
- 泄漏风险：若只看当前名称是否含 `ST`，或使用后验整理后的状态表而无历史生效日期，极易把未来状态泄漏回过去。
- fail-fast 要求：若没有历史生效区间，或 `ST` 状态与证券简称推断互相冲突，则直接拒绝使用推断版字段。
- 是否优先级高：最高。

### 3. listing age / IPO age

- 用途：识别次新股、上市初期样本、以及可能导致 head quality 不稳定的上市年龄偏差。
- 是否 D0 可见：是，且必须 `D0 visible only`；`listing_age_days_D0` 只能由 `ipo_date` 与 `D0` 计算。
- 潜在数据源：现有 security master 的 `ipo_date`、上市日期字段、交易所基础信息快照。
- 对 baseline / challenger 的价值：对 baseline，可检验 clean baseline 是否被次新风格污染；对 challenger，可判断模型弱头部是否集中出现在上市年龄过短的名字上。
- 泄漏风险：若使用退市后补录的上市信息修订版、未处理借壳/重新上市口径、或使用未来板块迁移后的日期字段，都会污染历史。
- fail-fast 要求：若 `ipo_date` 缺失率高、同一证券存在多个冲突上市日期、或无法定义借壳/重组口径，则不进入主字段集。
- 是否优先级高：高。

### 4. board type / exchange segment

- 用途：识别主板、创业板、科创板、北交所等制度分段，用于解释涨跌停制度、流动性结构、样本可交易性与 head composition 差异。
- 是否 D0 可见：是，且必须 `D0 visible only`；只能使用 `D0` 当日已知的板块/交易所分段。
- 潜在数据源：现有 security master 的 `exchange_code / board_type / segment`，交易所上市板块字段。
- 对 baseline / challenger 的价值：对 baseline，可识别 baseline 优势是否来自某些制度段暴露；对 challenger，可为 limit / suspension / liquidity 字段提供分段解释上下文。
- 泄漏风险：若使用当前静态板块标签覆盖历史、忽略板块迁移时点，或用未来制度认知反推历史限制，会导致错误归因。
- fail-fast 要求：若板块枚举不稳定、没有迁移生效日期、或与涨跌停制度字段不能自洽，则该类字段不能进主路径。
- 是否优先级高：高。

### 5. limit up / limit down status

- 用途：识别 `D0` 是否触及涨停/跌停、是否收在涨跌停价、是否一字板，用于解释头部名字为何名义可选但实际难交易，或为何尾部损失具有制度性。
- 是否 D0 可见：是，且必须 `D0 visible only`；只能基于 `D0` 当日行情与 `D0` 当日制度边界计算。
- 潜在数据源：现有日频行情表、涨跌停价格字段、交易状态表、板块制度字段。
- 对 baseline / challenger 的价值：对 baseline，可识别 baseline 强度是否来自 limit regime 暴露；对 challenger，可帮助定义 clean baseline 不应混入的制度性交易障碍。
- 泄漏风险：若混入 `D1` 开盘成交结果、用未来是否开板的信息回看 `D0`、或未按板块制度计算限价，都会引入泄漏或伪标签。
- fail-fast 要求：若无法稳定获得 `limit_price_up / limit_price_down` 或无法按板块制度复原 `D0` 限价口径，则不要用近似规则硬猜。
- 是否优先级高：最高。

### 6. suspension / no trade status

- 用途：识别停牌、全天无成交、仅有报价无成交等状态，用于定义 clean universe、解释不可交易样本、以及对齐 ranking 与 execution 之间的状态断层。
- 是否 D0 可见：是，且必须 `D0 visible only`；只能使用 `D0` 日终已知的停牌/无成交状态。
- 潜在数据源：现有交易状态表、日频行情的 `volume / amount / trade_count`、交易所停牌状态字段。
- 对 baseline / challenger 的价值：对 baseline，这是 clean baseline 的核心清洗字段；对 challenger，这是判断 head quality 弱是否被不可交易样本污染的基础状态。
- 泄漏风险：若用 `D1` 恢复交易信息回填 `D0`，或把“最终成交失败”误当成 `D0` 停牌标签，会把执行结果污染进输入。
- fail-fast 要求：若停牌枚举与成交数据矛盾，或没有办法区分“停牌”与“正常交易但零成交”，则必须先停在契约澄清阶段。
- 是否优先级高：最高。

### 7. liquidity quality fields

- 用途：补充对流动性质量的低自由度刻画，如过去若干日成交额、换手率、零成交天数、成交稳定度，用于解释 `TopK head quality` 与部署容量差异。
- 是否 D0 可见：是，且必须 `D0 visible only`；只能使用 `D0` 及以前的滚动统计，不得跨过 `D0`。
- 潜在数据源：现有日频行情表、成交额/成交量/换手率字段、项目已有 rolling panel。
- 对 baseline / challenger 的价值：对 baseline，可判断 clean baseline 弱头部是否其实是低流动性噪声；对 challenger，可作为后续 diagnostic-only slice 的共同解释字段。
- 泄漏风险：若滚动窗口错误包含 `D1+`，或用未来成交稳定性定义当前流动性质量，都会直接泄漏。
- fail-fast 要求：若 rolling 口径不能明确审计到“截至 `D0`”，或字段定义高度依赖临时脚本拼接，则不进入正式字段白名单。
- 是否优先级高：高，但排在显式制度状态之后。

### 8. tradability state fields

- 用途：把当前项目里分散的可交易性判断拆成可审计子状态，例如 `ranking_eligible_D0`、`price_limit_blocked_D0`、`suspended_D0`、`has_valid_quote_D0`、`entry_blocker_known_D0`。
- 是否 D0 可见：是，且必须 `D0 visible only`；所有子状态都只能由 `D0` 当日或更早字段派生。
- 潜在数据源：现有 `project panels`、执行状态 schema、行情表、交易状态表、板块制度字段。
- 对 baseline / challenger 的价值：对 baseline，可把“干净”定义从单一黑箱掩码变成可分解状态；对 challenger，可避免未来又把不同 blocker 混成一个 admission rule。
- 泄漏风险：若把 `D1` 实际能否成交、`entry_filled_D1`、或任何执行结果字段反向写成 `D0 tradability`，会把 outcome 包装成输入。
- fail-fast 要求：若任一 tradability 子状态依赖 `D1` 结果、冻结测试结论、或无法拆分成可审计布尔枚举，则直接拒绝。
- 是否优先级高：最高。

### 9. market cap / float cap fields

- 用途：补充市值与流通市值口径，用于解释 baseline 与 challenger 是否在小盘暴露、容量约束、以及头部集中度上存在系统差异。
- 是否 D0 可见：是，且必须 `D0 visible only`；只能使用 `D0` 当日已知收盘口径与截至 `D0` 已知股本信息。
- 潜在数据源：现有日频估值表、股本表、`total_mv / float_mv / shares_outstanding / float_shares` 字段。
- 对 baseline / challenger 的价值：对 baseline，可识别 baseline 强势是否只是小盘偏置；对 challenger，可帮助拆分“模型弱”与“容量不兼容”。
- 泄漏风险：若使用未来股本变更回填历史、复权后口径不一致、或用后验流通股口径覆盖 `D0`，会产生隐藏泄漏。
- fail-fast 要求：若股本口径无法 point-in-time 对齐，或总市值与流通市值的计算口径互相冲突，则不能进正式白名单。
- 是否优先级高：中高。

### 10. optional risk exposure fields

- 用途：补充可选的风险暴露审计字段，如历史波动率、beta、跳空风险、收益波动分层；仅用于诊断 baseline / challenger 的风险画像，不用于直接产出新规则。
- 是否 D0 可见：是，但必须严格 `D0 visible only`；只能由 `D0` 及以前收益序列构造。
- 潜在数据源：现有日收益面板、项目已有 rolling return 数据、现有风险暴露快照。
- 对 baseline / challenger 的价值：对 baseline，可识别 baseline 优势是否只是风险暴露换来的；对 challenger，可解释某些 head weakness 是否实为高波动尾部风险。
- 泄漏风险：若用未来收益、未来 realized vol、或事后定义的 tail label 反向构造暴露，将直接越界。
- fail-fast 要求：若字段定义需要未来收益、或其自由度过高导致接近“隐性新模型”，则直接降级为可选，不进入主路径。
- 是否优先级高：否，属于 optional。

## Recommended Delivery Order

建议按以下顺序补契约，不做实现承诺，不开新实验：

1. 先定义 `ST historical status`、`suspension / no trade status`、`limit up / limit down status`、`tradability state fields` 的字段字典与点时生效规则。
2. 再定义 `listing age / IPO age`、`board type / exchange segment`、`industry / sector classification` 的基础主数据映射。
3. 然后补 `liquidity quality fields` 与 `market cap / float cap fields` 的滚动口径审计。
4. 最后才补 `optional risk exposure fields`，且仅保留 diagnostic-only 用途。

## Explicit Prohibitions

本路线图明确禁止：

- 下载新数据。
- 训练模型。
- 回测。
- 读取 `frozen test`。
- 生成任何新的 `metrics/readout`。
- 把字段补全包装成 `alpha`。
- 把字段补全解释成 `strategy approval`。
- 借字段补全之名设计新 `v4`、新 admission rule、或任何新部署规则。

## Final Recommendation

下一阶段的正确动作不是继续硬造 baseline/challenger 规则，而是先把 `D0` 可见状态字段补干净。只有当这些字段具备 point-in-time 可审计性，并且通过 `fail-fast` 审核后，后续 clean baseline / challenger 研究才有继续推进的基础。
