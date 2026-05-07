# 新多因子排序项目重建框架第一版总纲

用途：
- 把新项目的研究、验证、冻结评估、执行与影子跟踪制度固化为单一主文档
- 作为后续数据建设、因子研究、模型开发、回测审计、出单执行的统一章程

适用时间点：
- 截至 `2026-04-30`

---

## 总则：制度层次

本总纲中的规则分为两层：

1. **宪法级规则**
- 测试集冻结与权限控制
- 看过测试集即失去 OOS 资格
- 五阶段治理流程
- 确认性研究单维改动
- 失败证据保留
- 固定窗口收益与真实清算收益双口径报告
- `total equity` 与 `invested capital` 双口径报告
- `walk-forward` 必须存在且必须参与主线晋升

2. **参数级治理规则**
- 所有数值型门槛、预算、默认阈值、容忍误差都视为 `v1 governance defaults`
- 这些默认值写入本文末尾的：
  - **附录 A：治理参数表**
  - **附录 B：统计口径附录**
- 参数级治理规则允许在后续治理评审中版本化修订，但不得破坏宪法级规则

制度解释：
- 本总纲追求的是“原则硬、参数软；边界硬、阈值版本化；审计强、实现不僵”
- 后续实现不得把参数级默认值误当成不可修改真理，也不得把宪法级规则降级为可选建议

## 1. 项目目标

新项目的目标不是：
- 把历史回测做得尽可能高

新项目的目标是：
- 从头重建一个**低自由度、可审计、尽量抗过拟合**的多因子排序研究系统
- 复用当前项目已经被证明有价值的执行语义与治理经验
- 让“样本内研究、样本外验证、冻结评估、未来观察”四层边界在制度上和工程上同时成立

一句话：
- **先做一个可信、可复现、可审计的研究系统，再追求更强模型。**

---

## 2. 研究范围与执行边界

### 2.1 市场范围

新项目只覆盖：
- **A 股主板**
- **A 股创业板**

明确不做：
- 科创板
- 北交所

### 2.2 资金与执行对象

默认执行对象：
- 散户小资金

这意味着：
- `v1` 不建立 ADV / 容量模型
- 真实执行层只显式处理三类“不可能成交”状态：
  - 停牌
  - 涨停买不进
  - 跌停卖不出
- 所有其他交易摩擦统一由固定成本制度与审计字段处理

### 2.3 默认交易成本制度

正式 fixed test / walk-forward / shadow tracking 必须绑定一套默认成本口径。

正式成本 stress 也必须存在，并与默认成本口径分离。

`v1` 的默认成本参数写入附录 A，不在正文中视为永恒常数。

---

## 3. 执行语义与 tradability 白皮书

### 3.1 统一执行语义

新项目第一版直接继承当前项目里最成熟的执行语义：

- `D0` 收盘后出信号
- `D1` 开盘买入
- 持有到 `D5` 收盘
- `D5` 收盘优先卖出
- 若 `D5` 收盘因停牌或跌停无法卖出，则从后续每个开盘继续卖，直到卖出

统一原则：
- 涨停不能买
- 跌停不能卖
- 主板与创业板涨跌停制度必须按历史生效日单独处理
- 研究层回测、执行层出单、影子跟踪必须共用同一套 `tradability` 权威表

### 3.2 字段级执行规范

以下字段为正式权威定义：

- `entry_buyable_D1_open = is_listed_D1 & not is_suspended_D1 & not no_trade_D1 & not open_at_up_limit_D1`
- `exit_sellable_D5_close = is_listed_D5 & not is_suspended_D5 & not no_trade_D5 & not close_at_down_limit_D5`
- `sellable_retry_next_open = is_listed_t & not is_suspended_t & not no_trade_t & not open_at_down_limit_t`

辅助字段定义：

- `is_listed_t`：该交易日股票处于上市状态，未退市
- `is_suspended_t`：该交易日停牌
- `no_trade_t = (volume_t <= 0) or (amount_t <= 0)`
- `low_liquidity_flag_t = amount_t < low_liquidity_amount_threshold_k_yuan`
- `price_tick_quantize_t = Decimal("0.01")`
- `open_at_up_limit_t = quantize_half_up(open_t, price_tick_quantize_t) >= quantize_half_up(up_limit_price_t, price_tick_quantize_t)`
- `open_at_down_limit_t = quantize_half_up(open_t, price_tick_quantize_t) <= quantize_half_up(down_limit_price_t, price_tick_quantize_t)`
- `close_at_down_limit_t = quantize_half_up(close_t, price_tick_quantize_t) <= quantize_half_up(down_limit_price_t, price_tick_quantize_t)`
- `one_word_up_limit_t = open_at_up_limit_t & quantize_half_up(open_t, price_tick_quantize_t) = quantize_half_up(high_t, price_tick_quantize_t) = quantize_half_up(low_t, price_tick_quantize_t) = quantize_half_up(close_t, price_tick_quantize_t)`
- `one_word_down_limit_t = open_at_down_limit_t & quantize_half_up(open_t, price_tick_quantize_t) = quantize_half_up(high_t, price_tick_quantize_t) = quantize_half_up(low_t, price_tick_quantize_t) = quantize_half_up(close_t, price_tick_quantize_t)`

制度解释：
- `low_liquidity_flag_t` 是审计旗标，不直接阻止交易
- 由于 `vw_bars_daily.amount` 的单位为 `千元`，`low_liquidity_amount_threshold_k_yuan = 5000` 表示成交额低于 `500` 万元
- `no_trade_t` 与停牌一样，直接视为不可执行
- 所有价格比较必须统一使用 `Decimal` 与 `ROUND_HALF_UP`
- Python 默认 `round()` 不得用于交易所价格边界判定
- 涨跌停价、收盘封死、开盘触板、一字板判断都必须基于 `Decimal + ROUND_HALF_UP`

### 3.3 涨跌停制度

正式涨跌停规则固定为：

- 主板默认涨跌停：`10%`
- `ST` 股票涨跌停：`5%`
- 创业板在 `2020-08-24` 起涨跌停：`20%`
- 创业板在 `2020-08-24` 前沿用旧制度

所有规则必须按 `trade_date` 与 `ST` 历史状态生效，不允许用当前状态回看历史。

`v1` 的正式 ST 历史来源固定为：
- `namechange`

`v1` 的 ST 推导规则固定为：
- 若历史名称包含 `ST` 或 `*ST`，则该名称生效区间推导为 ST 区间
- 该区间必须进一步派生成：
  - `st_status_interval`
  - `instrument_status_daily.is_st`

制度解释：
- 对当前项目与新项目 `v1` 的执行目标而言，`namechange` 是历史 ST 时间序列与规则引擎的默认高可用来源
- 它足以支撑：
  - 历史涨跌停规则
  - `state_filter_pass_D0`
  - `tradability`
  - 回测与出单一致性
- 它本质上是“名称变更历史”推导出的 ST 状态，不等价于官方单独维护的每日 ST 状态真相表
- 因此 `v1` 必须把它标记为：
  - **高可用近似真相源**
  - 而不是理论上绝对完美的状态源

### 3.4 一字板、开盘封板、收盘封板、低成交的近似规则

正式近似规则固定为：

- `one_word_up_limit_t` 和 `one_word_down_limit_t` 作为审计字段保留
- 买入只看 `D1` 开盘是否可买，不因为盘中打开涨停而追加入场
- `D5` 收盘卖出只看 `close_at_down_limit_D5` 与停牌，不因为盘中曾经打开跌停而在收盘强制判成可卖
- 延迟退出只在后续每个开盘检查 `sellable_retry_next_open`
- `low_liquidity_flag_t` 只进入审计，不在 `v1` 中改变 `entry_buyable_D1_open` 或 `sellable_retry_next_open`

制度说明：
- `v1 tradability` 是**保守型、离散时点近似执行制度**
- 它服务于一致性、可审计性与回测 / 出单统一口径
- 它**不等价于订单簿级成交模拟**
- 开盘可买、收盘可卖、后续开盘延迟退出，都是制度化近似，不是微观成交还原

### 3.4A 开盘 / 收盘撮合微观审计

`v1` 默认不构建订单簿级成交模拟，但必须对开盘 / 收盘撮合依赖进行单独审计。

正式要求：

- 所有正式 fixed test、`walk-forward`、影子跟踪都必须附带一次开盘 / 收盘撮合敏感性摘要
- 敏感性摘要至少覆盖：
  - `D1` 开盘成交依赖
  - `D5` 收盘成交依赖
  - 开盘跳空对买入收益的影响
  - 收盘封板前后对退出收益的影响
  - 一字板样本与非一字板样本的贡献差异
- 正式审计必须并行报告：
  - 基准执行口径
  - 更保守的开盘 / 收盘撮合 stress 口径
- 若更保守撮合 stress 下相对收益显著恶化，则该候选方案必须标记为：
  - `auction_microstructure_sensitive = true`

制度解释：

- `v1` 可以接受“离散时点执行近似”，但不能接受“收益主要依赖理想撮合”
- 若收益主要来自开盘价或收盘价的理想成交，则必须在正式审计中显式披露
- 该项审计用于识别撮合敏感性，不直接替代主回测口径

### 3.5 `tradability` 缺失与 fallback 规则

正式规则：

- `tradability` 关键字段缺失时，系统不得静默 fallback 为“默认可交易”
- 若缺失字段影响买卖判断，则该轮研究/回测结果自动降级为：
  - **不可用于主线晋升**
  - **不可作为正式相对收益证据**
- 降级状态必须写入审计摘要

---

## 4. 标签、样本资格矩阵与真实清算审计

### 4.1 主标签定义

新项目第一版正式标签定义为：

- `adj_open_base_D1 = open_D1 * adj_factor_D1`
- `adj_close_base_D5 = close_D5 * adj_factor_D5`
- `label_5d_next_open_close_raw = adj_close_base_D5 / adj_open_base_D1 - 1`

其中：
- `D0` 为信号生成日
- `D1` 为下一交易日开盘买入日
- `D5` 为第 `5` 个持有交易日的收盘卖出日

制度解释：
- 标签、真实清算收益、价格路径类因子必须共用同一套 **base-adjusted price** 口径
- 统一基底定义为：
  - `adj_price_base_t = raw_price_t * adj_factor_t`
- 标签分子分母必须落在同一套 base-adjusted price 体系中
- 不允许标签使用一套复权基准、真实清算收益再使用另一套复权基准
- 该标签是**研究近似目标**，不是最终真实执行收益。

### 4.2 样本资格矩阵

新项目必须并行生成以下样本资格字段：

- `label_price_defined`
- `entry_tradeable`
- `planned_exit_tradeable`
- `actually_exited`
- `label_usable_for_training`
- `label_training_value`
- `train_mask_v1`
- `eval_mask_v1`
- `train_mask_conservative`
- `eval_mask_conservative`
- `feature_ready_D0`
- `universe_eligible_D0`
- `signal_emittable`
- `ranking_eligible_D0`
- `topk_frozen_D0`
- `execution_attempt_D1`
- `entry_filled_D1`
- `backtest_executable`
- `audit_included`

默认定义如下：

- `label_price_defined = open_D1 not null & close_D5 not null & adj_factor_D1 not null & adj_factor_D5 not null`
- `entry_tradeable = entry_buyable_D1_open`
- `planned_exit_tradeable = exit_sellable_D5_close`
- `actually_exited = actual_exit_date not null & actual_exit_date >= planned_exit_date`
- `label_usable_for_training = label_price_defined & entry_tradeable`
- `label_training_value = label_5d_next_open_close_raw if label_usable_for_training else NaN`
- `train_mask_v1 = label_usable_for_training`
- `eval_mask_v1 = label_usable_for_training`
- `train_mask_conservative = label_price_defined & entry_tradeable & planned_exit_tradeable`
- `eval_mask_conservative = label_price_defined & entry_tradeable & planned_exit_tradeable`
- `feature_ready_D0 = price_window_ready_D0 & core_features_complete_D0 & pit_state_complete_D0`
- `universe_eligible_D0 = base_universe_member_D0 & rules_filter_pass_D0 & state_filter_pass_D0`
- `price_window_ready_D0 = current enabled price-path feature lookback windows complete on D0`
- `core_features_complete_D0 = all required enabled features on D0 are non-null and finite`
- `pit_state_complete_D0 = required PIT state tables complete on D0; at minimum listing/delisting, suspension, ST; if industry or fundamental features are enabled, corresponding PIT fields must also be complete`
- `base_universe_member_D0 = member of the formal main-board and ChiNext research universe on D0 & not delisted`
- `rules_filter_pass_D0 = pass current version static rule filters, including listing-days threshold, feature coverage threshold, and hard rule filters`
- `state_filter_pass_D0 = pass current day state filters, including ST, suspension, and other state-based exclusion rules`
- `signal_emittable = feature_ready_D0 & universe_eligible_D0`
- `ranking_eligible_D0 = signal_emittable`
- `topk_frozen_D0 = membership(topk ranking over ranking_eligible_D0)`
- `execution_attempt_D1 = membership(topk_frozen_D0)`
- `entry_filled_D1 = execution_attempt_D1 & entry_tradeable`
- `backtest_executable = entry_filled_D1`
- `audit_included = signal_emittable`

制度解释：
- `train_mask_v1` 是主训练口径
- `train_mask_conservative` 与 `eval_mask_conservative` 是强制并行保守审计口径，不替代主训练口径
- 正式审计必须对比两套口径的样本覆盖率、IC / RankIC 方向、组合结果方向
- `planned_exit_tradeable` 不直接决定主训练资格，但必须进入保守审计
- `signal_emittable` 可以大于 `train_mask_v1`
- `label_price_defined` 只表示价格层面的理论标签可计算，不表示样本可用于训练
- `label_training_value` 是主训练 / 主评估口径的正式标签值
- `core_feature_row_available_D0` 不再作为规范级字段；若实现层需要，可仅作为内部聚合 alias，不得作为总纲层级定义
- 排序宇宙固定使用 `ranking_eligible_D0 = signal_emittable`
- `entry_tradeable` 只能在 `TopK` 冻结后于执行层生效，不得用于排序前过滤
- `backtest_executable` 表示“实际形成持仓的条目”，不是排序前候选资格
- 实现层必须保留 `price_window_ready_D0`、`core_features_complete_D0`、`pit_state_complete_D0`、`base_universe_member_D0`、`rules_filter_pass_D0`、`state_filter_pass_D0` 这些可审计子字段
- `audit_included` 必须覆盖延迟退出样本，不能只保留固定 `5` 日窗口内完成清算的样本

### 4.3 不可买样本处理规则

正式规则：

- 若 `D1` 开盘因涨停或停牌导致不可买，不直接删除样本
- 该样本保留 `label_5d_next_open_close_raw`
- 该样本 `label_training_value` 记 `NaN`
- 该样本不得进入 `train_mask_v1 / eval_mask_v1`
- 该样本仍保留在研究仓库中，用于覆盖率、可执行性、涨停买不进与信号分布审计

### 4.4 固定持有与真实清算的双口径

研究层继续以固定 `5` 日标签作为主学习目标，但执行与审计层必须同时记录真实清算信息。

后续实现至少要求输出：
- `planned_exit_date`
- `actual_exit_date`
- `exit_delay_days`
- `execution_delayed_realized_return`

其中正式默认公式固定为：

- `adj_sell_base_actual_exit = actual_sell_price * adj_factor_actual_sell_date`
- `execution_delayed_realized_return = adj_sell_base_actual_exit / adj_open_base_D1 - 1`

正式报告必须同时展示：
- 固定窗口收益
- 退出延迟后的真实清算收益

审计摘要必须显式说明二者差异，禁止只展示理想固定窗口结果。
额外规则：
- `execution_delayed_realized_return` 只包含价格损益
- 不计无风险利息
- 不计延迟卖出期间资金时间价值
- 旧字段名 `liquidity_adjusted_realized_return` 仅允许作为实现兼容 alias；文档、审计与正式报告一律使用 `execution_delayed_realized_return`
- 该字段与 `label_5d_next_open_close` 必须共享同一套 base-adjusted price 口径

### 4.4A 退市与终局事件处理

若标的在持有窗口或延迟退出窗口中进入退市、终止上市、长期停牌或其他终局状态，系统不得将该样本静默删除。

正式要求：

- 必须显式记录：
  - `terminal_event_flag`
  - `terminal_event_type`
  - `terminal_event_date`
  - `terminal_exit_pricing_method`
- 若在终局事件发生前已存在可执行卖出时点，则继续按正式执行语义完成退出
- 若在终局事件发生前不存在可执行卖出时点，则必须按以下价格层级处理真实清算：
  1. 已知终局现金清算 / 转换现金流
  2. 终局前最后一个可交易日的可观测收盘价
  3. 若既无终局现金流也无可用最后交易价格，则按 `0` 价格保守处理
- 采用第 `2` 或第 `3` 层级时，必须额外记录：
  - `terminal_exit_approximation_flag`
  - `terminal_exit_conservative_flag`

正式报告必须单独披露：
- 终局事件样本数
- 终局事件样本收益贡献
- 终局事件对固定窗口收益与真实清算收益差异的贡献

制度解释：

- 退市与长期停牌样本往往是策略真实尾部风险的重要来源
- `v1` 不允许通过静默剔除极端坏样本来美化结果
- 终局事件的处理口径必须固定、可追溯、可复算

---

## 5. 数据架构、价格口径与 snapshot / PIT 制度

### 5.1 数据架构

新项目数据底座固定为：

- **Tushare -> 原始落地 -> Parquet 数据仓库 -> DuckDB 查询层**

各层职责固定为：

- `Tushare`：只负责数据获取
- 原始落地层：只保存下载原件
- Parquet 数据仓库：跨项目共享的独立权威数据源
- DuckDB 查询层：唯一正式查询入口

### 5.1A 数据源边界定义

正式定义：

- `/Users/wy/MiscProject/tushare_data/parquet_duckdb` 是独立数据仓库根，不属于任何单一研究项目的子目录
- 该数据源面向多个研究、回测、执行项目提供统一、可复现、可审计的数据服务
- 任一上层项目只能读取并绑定该数据源，不得把项目私有逻辑回写为基础真相层

边界规则：

- `data/current` 是稳定开发入口
- `data/snapshots/<snapshot_id>` 是不可变历史批次入口
- `data/meta/latest_snapshot.json` 与 `data/meta/snapshot_registry.json` 是正式元数据入口
- 正式研究、fixed test、`walk-forward`、影子跟踪必须绑定具体 `snapshot_id`，不得仅记录 `current`
- `current` 仅作为开发便利入口，不作为正式审计主键

仓库层次固定分为两层：

1. **跨项目共享的权威基础层**
- `warehouse/core`
- `warehouse/market`
- `warehouse/state`
- `warehouse/industry`
- `warehouse/fundamental`

2. **面向具体研究范式的派生契约层**
- `warehouse/research`

制度解释：

- 权威基础层承载交易日历、股票基础信息、日频行情、benchmark、涨跌停规则、`tradability`、ST / 状态层、行业归属、PIT 财务原始层等跨项目共享真相源
- `warehouse/research` 不是跨项目唯一真相层，而是派生 contract 层
- `warehouse/research` 允许承载标签、执行路径、样本资格矩阵等特定研究框架下的标准派生产物
- 不同项目若需要不同标签、执行语义或资格矩阵，应新增各自的派生 contract，不得篡改共享基础层
- 对外正式查询入口应优先使用 DuckDB `serving` 视图或标准 contract，不鼓励上层项目直接拼接底层 parquet 路径

### 5.2 数据纪律

1. 交易日历必须是独立权威表
2. 股票基础信息必须是独立权威表
3. `tradability` 必须是独立权威表
4. 特征与标签只允许从数据仓库生成
5. 不允许研究脚本绕开仓库直接临时拼数据
6. 每轮研究、每次 fixed test、每次 `walk-forward`、每次正式对外报告都必须绑定数据 `snapshot id`
7. 一切价格、财务、状态、行业归属都必须遵守 PIT（point-in-time）可见性约束
8. 项目运行环境必须固定并可审计，不允许在未记录环境变更的情况下切换 Python 环境

### 5.2A 运行环境基线

`v1` 项目默认固定运行环境为：

- `/opt/anaconda3/envs/quant_trade`
- `environment_manifest.json`

正式要求：

- 项目脚本、项目侧数据层、fixed test、`walk-forward`、影子跟踪默认都应在该环境下运行
- 若未来需要迁移环境，必须把新环境路径、核心依赖变化和切换日期写入正式变更记录
- fresh rerun 若使用了不同 Python 环境，默认不视为“同口径可复现”
- 每次正式运行都必须同时保存一份 `environment_manifest.json`
- `environment_manifest.json` 至少必须记录：
  - `python_version`
  - `duckdb_version`
  - `pyarrow_version`
  - `pandas_version`
  - `numpy_version`
  - `scikit_learn_version`
  - `lightgbm_version`
  - `xgboost_version`
  - `conda_env_export_hash`
  - `pip_freeze_hash`
  - `platform`
  - `cpu_arch`

制度解释：

- `snapshot id`、代码 / 配置 / 数据 contract 指纹、`execution logic version` 决定数据与逻辑可复现性
- 固定运行环境决定依赖解析、DuckDB/PyArrow 行为与脚本执行口径可复现性
- 因此运行环境属于项目可复现边界的一部分

### 5.3 数据 snapshot 制度

每轮研究、每次 fixed test、每次 `walk-forward`、每次正式报告都必须绑定：
- `raw_data_snapshot_id`
- `adj_factor_snapshot_id`
- `fundamental_snapshot_id`
- `industry_snapshot_id`
- `tradability_snapshot_id`

审计摘要必须同时记录：
- `git_commit_hash`
- `git_dirty_flag`
- `git_diff_hash`
- `config_hash`
- `data_contract_hash`
- `execution_logic_hash`
- `factor_contract_hash`
- `environment_manifest_hash`
- `execution logic version`
- `research tier`

正式快照约束：
- `snapshot_id` 默认与 ETL 产物批次绑定
- 一旦进入确认性研究，对应 `snapshot_id` 的 Parquet 分区必须视为只读
- 后续 ETL 只能生成新的 `snapshot_id`
- 不得覆盖已进入确认性研究的历史分区

### 5.3A 正式评估 `attempt_id` 与输入自包含制度

任一次正式评估 rerun、fresh rerun、fixed test rerun、`walk-forward` rerun、影子跟踪 rerun，都必须生成新的：
- `attempt_id`

正式要求：
- `attempt_id` 是正式评估主键的一部分，不得只用 `run_id` 指代一次 rerun
- 正式验收、失败证据、审计摘要、评估报告都必须绑定到具体 `attempt_id`
- 任一次正式 `attempt_id` 都必须引用该 attempt 自身冻结的输入文件，不得直接依赖 run 根目录下可被后续覆盖的可变输入
- 正式 attempt 必须在独立目录中保留：
  - 输入快照
  - 输出产物
  - attempt manifest
  - attempt 验收报告

制度解释：
- `run_id` 表示同一轮项目运行身份
- `attempt_id` 表示该运行身份下的第几次正式重跑
- 若缺少 `attempt_id` 与自包含输入快照，历史结果即使保留了文件路径，也不视为严格可复现

### 5.4 PIT 约束

正式 PIT 规则固定为：

- 价格类 PIT：只能使用当时可见的价格、成交、涨跌停、停牌信息
- 财务类 PIT：只能按公告可见时间进入特征
- 即使 `ann_date` 当天可见，也必须在下一个交易日才允许进入 `signal_emittable`
- 正式规则：
  - `finance_feature_effective_date = next_trade_date(ann_date)`
- 状态类 PIT：ST、停牌、行业归属、上市/退市状态都必须按当时可见时间追溯

`v1` 的 ST 状态 PIT 来源固定为：
- `namechange`

`v1` 必须至少保留以下 ST 原始审计字段：
- `name`
- `start_date`
- `end_date`
- `ann_date`
- `change_reason`
- `st_source = namechange`
- `st_inference_method`

`v1` 的 ST 状态标准化产物固定为：
- `st_status_interval`
- `instrument_status_daily.is_st`

正式规则：
- `st_status_interval` 必须由 `namechange` 的历史名称区间推导
- `instrument_status_daily.is_st` 必须由 `st_status_interval` 日频展开得到
- 若未来拿到更官方、更细粒度的 ST 状态表，只能作为新的治理版本替换，不得在 `v1` 内混用不同来源

制度解释：
- `finance_feature_effective_date = next_trade_date(ann_date)` 是 **v1 的保守统一近似**
- 它不等价于精确市场可见时点还原
- 该规则优先服务于防未来信息泄露，而不是还原分钟级传播时点
- `namechange` 作为 ST 来源是 `v1` 的保守工程近似
- 它优先服务于历史状态一致性、规则引擎可落地与 PIT 可追溯性

任何违反 PIT 的实验结果不得用于确认性研究、主线晋升或正式对外汇报。

### 5.5 价格口径与复权规则

新项目从第一天起就明确区分三类价格使用域：

- 执行域：只用原始价格
- 研究域：价格路径类特征与标签使用 `raw price + adj_factor`
- 元数据域：公司行为、交易规则、状态历史独立管理

执行域硬约束：

- 成交价格、成交金额、股数、手续费、印花税、涨跌停判断全部使用 `raw price / raw notional`
- 不得使用复权价格模拟真实成交现金流
- 不得同时使用复权成交价与公司行为现金流，避免重复计算公司行为收益

研究域硬约束：

- `base-adjusted price` 只用于标签、价格路径因子、收益率对齐与真实清算收益比较
- 不得把 `base-adjusted price` 直接拿来驱动真实成交现金流

仓库层真相源固定为：
- `raw OHLC`
- `adj_factor`
- `snapshot id`

仓库层长期保留：
- `open`
- `high`
- `low`
- `close`
- `pre_close`
- `volume`
- `amount`
- `adj_factor`
- `adj_open_base = open * adj_factor`
- `adj_high_base = high * adj_factor`
- `adj_low_base = low * adj_factor`
- `adj_close_base = close * adj_factor`
- 若共享视图中仍存在历史兼容字段 `adj_open / adj_high / adj_low / adj_close`
  - 本项目正式解释为 `adj_open_base / adj_high_base / adj_low_base / adj_close_base`
  - 不表示项目依赖静态前复权价表或静态后复权价表

### 5.6 连续价格工程实现

新项目**不物化** `as_of_date × 全历史` 的动态前复权全矩阵。

正式实现方式固定为：

1. 仓库层保留：
- 原始 OHLC
- `adj_factor`
- `adj_close_base`

2. 价格路径类因子与标签默认直接使用 base-adjusted price：
- `adj_open_base`
- `adj_high_base`
- `adj_low_base`
- `adj_close_base`

3. 若需要展示型前复权价格，再由查询层按 `as_of_date` 轻量再锚定：
- `adj_close_base_d = close_d * adj_factor_d`
- `front_adj_close_d_asof = adj_close_base_d / adj_factor_asof`

4. 高频复用的滚动价格路径类因子直接物化为 Parquet 特征列，避免重复动态重算

制度解释：
- 因子可复现性的真相源是 `raw OHLC + adj_factor + snapshot id`
- 不是某张静态前复权价格表
- 价格路径类因子的默认收益表达，优先使用 base-adjusted price 的比例变化，而不是依赖任意 `as_of_date` 锚点
- 其中 `d` 表示被展示的历史价格日期，`asof` 表示展示锚定日期
- 展示型前复权价格仅用于展示，不作为研究真相源

### 5.7 因子计算口径规则

不同类型因子使用不同价格口径：

1. 价格路径类因子
- 使用 `raw price + adj_factor`

2. 交易执行类因子 / 规则
- 只使用原始价格

3. 流动性与成交类因子
- 只使用原始成交与基础交易字段

4. 估值 / 财务类因子
- 只使用 PIT 基础字段或财务字段

额外纪律：
- 不允许全项目统一只用前复权价
- 不允许所有研究只用原始价格
- 不允许不同模块自行决定价格口径
- 标签、真实清算收益、价格路径类因子三者必须共用 base-adjusted price 口径

### 5.7A 因子预处理与中性化合同

`v1` 必须把因子预处理视为正式研究 contract，而不是实现细节。

正式要求：

- 所有正式因子都必须明确记录以下预处理步骤：
  - 缺失值处理
  - 无穷值 / 非有限值处理
  - 去极值规则
  - 标准化规则
  - 是否执行中性化
  - 若执行中性化，所使用的暴露集合与回归口径
- 预处理顺序必须固定，并在同一轮研究中保持一致
- 预处理统计量不得使用未来区间信息或全样本回看统计量
- 允许的默认中性化对象仅限：
  - 行业
  - 市值
  - `beta`
- 若研究中使用中性化，必须在因子卡与预注册中事先声明
- 若研究中不使用中性化，也必须在因子卡中显式声明 `neutralization = none`

默认纪律：

- 横截面标准化与去极值优先于时序级随意变换
- 缺失值默认不做跨期填充
- 不允许通过对测试集重新拟合预处理规则来改善结果
- 不允许在不同候选方案之间随意切换预处理合同而不登记为单独改动维度

制度解释：

- 同一因子在不同预处理合同下可能呈现完全不同结果
- 因此预处理必须像标签定义和执行语义一样被正式治理
- 中性化是可选研究维度，不是默认免费自由度

---

## 6. 时间切分、purge gap 与结果隔离

### 6.1 固定时间分层

新项目固定采用：

- **训练集**：`2010-01 ~ 2018-12`
- **验证集**：`2019-01 ~ 2021-12`
- **测试集（冻结保留集）**：`2022-01 ~ 2025-12`
- **观察区 / 准实盘区**：`2026-至今`

分层目标：

- 训练集：学习跨周期的粗糙规律
- 验证集：筛少数候选并观察风格迁移适应性
- 测试集：冻结评估与正式验收
- 观察区：只做未来运行与影子跟踪

### 6.2 核心纪律

1. 训练集
- 只用于研究与候选生成

2. 验证集
- 只用于确认性研究的少数候选比较

3. 测试集（冻结保留集）
- 主线冻结前不得查看
- 只允许在主线候选冻结后评测
- 查看后永久失去 OOS 资格

4. 观察区
- 不并入正式研究评估
- 只用于未来运行与影子跟踪

### 6.3 `purge gap` 硬规则

正式制度：
- `purge gap` 必须存在，且默认满足 `purge_gap_default >= holding_period`
- `v1` 默认值写入附录 A，不在正文中视为永恒常数

正式要求：
- 训练 / 验证边界自动 purge `purge_gap_default`
- 验证 / 测试边界自动 purge `purge_gap_default`
- 训练集内部滚动验证也自动 purge `purge_gap_default`
- 所有时间切分脚本必须自动处理 purge，不允许人工决定
- 所有正式 fixed test / `walk-forward` 必须附带一次更保守的 `purge gap` 敏感性摘要
- 敏感性摘要只用于审计，不回流主训练优化

### 6.4 测试集加密托管与结果权限控制

测试集（冻结保留集）必须实施物理隔离。

正式制度：

1. 测试集原始研究数据单独加密存放，不默认挂到日常研究仓库
2. 只有**确认性研究**，且生成固定 `fixed_test_run_id` 后，才能调用独立评测脚本
3. 独立评测脚本默认只返回受限摘要，不返回：
- 完整净值曲线
- 逐日持仓
- 逐日信号
- 可反推样本外微调方向的日级细节
4. 一旦测试集结果被查看，该 `fixed_test_run_id` 立即标记为“已消耗样本外资格”
5. 在 fixed test 首次正式查看前，任何 `walk-forward` 运行不得生成、返回或展示包含 `2022-2025` 区间信息的训练、验证、测试、稳定性或候选比较摘要
6. fixed test 消耗前，不允许使用 `wf_2022 / wf_2023 / wf_2024 / wf_2025` 的结果筛选候选

边界澄清：

- 确认性研究的日常比较默认发生在验证集，不默认开放测试集
- 测试集只用于主线候选冻结后的正式 `fixed test` 验收
- 不允许把测试集当作确认性研究中的常规比较环境反复查看
- fixed test 消耗后，`walk-forward` 才可作为年度部署模拟运行
- fixed test 消耗后，`walk-forward` 结果必须进入样本外可见性审计，但不得回流同一主线继续调参

### 6.5 验证集访问预算

确认性研究的验证集访问规则由附录 A 的 `v1 governance defaults` 约束，正文只保留不可变边界：

- 验证集访问必须有预算上限
- 默认摘要只返回：
  - 全期年化收益
  - 全期年化相对收益
  - 最大回撤
  - 全期夏普 / IR
  - 资本使用效率摘要
  - 粗颗粒稳定性摘要：
    - 月度正收益占比
    - 收益集中度指标
- 锁定 rerun 后只允许查看同口径摘要
- 确认性研究阶段默认不返回：
  - 分年度具体收益值
  - 分月份具体收益值
  - 逐日净值曲线
  - 逐日持仓
  - 逐日信号
- `validation_debug_detail_forbidden = true`
- `test_debug_detail_forbidden = true`
- `train_debug_detail_allowed = true`
- `synthetic_debug_detail_allowed = true`

验证集查看事件定义固定为：
- 一次 `validation_view_budget` 消耗，指一次**新的验证集摘要产物被生成并返回给研究者**
- 计数主键固定为：
  - `research_round_id`
  - `candidate_scheme_id`
  - `git_commit_hash`
  - `git_dirty_flag`
  - `git_diff_hash`
  - `config_hash`
  - `data_contract_hash`
  - `execution_logic_hash`
  - `factor_contract_hash`
  - `environment_manifest_hash`
  - `snapshot id`
  - `execution logic version`
  - `summary schema version`
- 重复打开、重复查看、重复导出同一摘要产物，不重复消耗预算
- 同口径 locked rerun 若重新生成了新的验证摘要产物，则额外消耗 `1` 次预算
- 除首次评估与锁定 rerun 外，不允许继续生成新的验证摘要产物

制度解释：

- 验证集用于候选比较与确认性收缩
- 测试集用于冻结验收
- 二者都属于正式样本外证据，但承担不同角色，不得混作同一种日常调参资源

---

## 7. 研究分层、版本树、预注册与预算

### 7.1 五阶段治理流程

新项目从第一天起固定分为五个阶段：

1. 研究阶段
2. 验证阶段
3. 冻结评估阶段
4. 执行阶段
5. 影子跟踪阶段

任何策略要升级为正式主线，必须完整走完以上五个阶段。

### 7.2 探索性研究

探索性研究的正式权限边界：

- 只允许使用训练集与训练集内部滚动验证
- 允许版本树
- 允许多候选并行
- 结果不能直接用于主线晋升

预算上限：
- 由附录 A 的探索性研究治理参数表约束

必须登记：
- 研究目的
- 候选池范围
- 版本树节点说明
- 终止条件

### 7.3 确认性研究

确认性研究的正式权限边界：

- 必须预注册
- 必须单维改动
- 才允许进入验证集与测试集
- 必须绑定固定 `fixed_test_run_id`

预算上限：
- 由附录 A 的确认性研究治理参数表约束
- 超预算后强制结束该轮研究，不得扩候选继续试

### 7.4 版本树式研究

新项目禁止在一条主线上来回覆盖式修改。

正式要求：
- 每个研究轮次必须基于一个冻结 commit，或等价的代码 / 配置 / 数据 contract 指纹与 source snapshot，开若干实验分支
- 每个分支只承载一个清晰改动方向
- 所有分支统一对比
- 不允许在同一条主线上反复涂抹、回改、重命名后继续比较

### 7.5 预注册与不可变实验清单

确认性研究必须预注册，且预注册记录在第 `1` 次验证集结果返回后即不可修改。

预注册至少包括：
- `research_round_id`
- `research tier`
- 研究问题
- 允许改动的唯一核心维度
- 候选方案列表
- `candidate_scheme_id` 列表
- 候选因子列表
- 结果解释标准
- 将使用到的时间分区
- `fixed_test_run_id`
- `git_commit_hash`
- `git_dirty_flag`
- `git_diff_hash`
- `config_hash`
- `data_contract_hash`
- `execution_logic_hash`
- `factor_contract_hash`
- `environment_manifest_hash`
- 数据 `snapshot id`
- `execution logic version`
- `governance_approver_id`

若上述任一项发生变化，必须开新一轮 `research_round_id`，不得在原轮次中途改写。
额外规则：
- `candidate_scheme_id` 必须在确认性研究开始前生成并写入预注册记录
- 首次验证集结果返回后，`candidate_scheme_id` 列表不得新增、删除、重命名或重排

结果解释标准的正式要求：
- 必须写成布尔表达式
- 必须绑定具体阈值
- 例如：
  - `(sharpe_ratio > 1.5) AND (max_drawdown < 0.2) AND (annual_relative_return > 0.01)`
- 若布尔表达式不成立，则该轮确认性研究自动归档为失败
- 不允许事后解释“接近达标也算通过”

### 7.6 研究前过拟合风险评估卡

任何主线级研究启动前，必须先完成一页“过拟合风险评估卡”。

必须回答：
- 这轮研究是探索性还是确认性
- 这轮研究改哪个核心维度
- 是否同时改多个核心维度
- 会新增多少候选方案
- 是否会触碰验证集 / 测试集边界
- 是否会产生新的样本外结果可见性
- 是否会新增一个需要长期维护的结构复杂度层
- 是否已有更简单对照能回答同类问题
- 这轮研究结束后，主线搜索空间累计增加多少

风险评估卡不通过，则该轮研究不得启动。

---

## 8. 因子入围制度与模型路线

### 8.1 第一版因子总量上限

正式要求：
- 第一版确认性候选因子总数必须有上限
- 探索性候选池总数必须有上限
- `v1` 默认值见附录 A

### 8.2 候选池来源白名单

确认性研究中的候选因子只能来自以下白名单：

- 已登记基础风格因子
- 已登记技术因子
- 有明确经济解释且满足 PIT 的新增因子

`Alpha158` 等大因子池不得整包进入主线候选池。

允许的例外方式：

- 可以参考 `Alpha158`、论文因子库或其他经典来源提供候选定义
- 但进入正式研究前，必须先完成因子卡、去重、预算占用与预注册约束
- 进入确认性研究的对象必须是少量、命名稳定、经济解释明确的候选，而不是整包导入的大池扫描结果

### 8.3 因子入围标准

新因子进入确认性研究前，必须同时满足：

- 覆盖率达到附录 A 的最低要求
- 有不超过 `3` 句的经济解释
- 在训练集内部子时期方向一致
- 与已入围因子的相关性不高于附录 A 的治理上限；若不满足，必须提供保留理由并占用一个确认性预算名额

确认性研究开始前，候选因子名单冻结，不得中途换人。

### 8.4 基线模型制度

第一阶段正式基线固定为：
- 线性排序模型

可接受形式：
- 标准化后线性加权
- 线性回归
- 岭回归
- 弹性网络

### 8.5 树模型制度

第二阶段才允许引入：
- 受限 `LightGBM / XGBoost`

树模型只能作为线性基线的挑战者，不能作为第一天的默认正式主线。

树模型想晋升，必须额外满足：
- 满足附录 A 中的树模型稳定性默认门槛
- 且正式主线晋升时同时接受否决项与综合项审查

---

## 9. 组合构建、现金保留与资本使用效率

### 9.1 组合构建原则

继续沿用：
- **TopK + 现金保留 + 不强行满仓**

### 9.2 `TopK` 规则

新项目第一版正式主线默认：
- **`TopK = 10`**

并且：
- `TopK` 不作为第一版正式主线搜索维度
- 若以后研究别的 `TopK`，只能作为独立支线对照
- 每次正式 fixed test / `walk-forward` 必须附带 `TopK` 轻扰动审计摘要
- `v1` 默认轻扰动集合见附录 A

### 9.2A `D1` 不可买时的组合执行规则

`D0` 收盘选出的 `TopK` 候选组合在 `D1` 开盘前即冻结。

排序与执行链路固定为：
1. `D0` 仅按 `ranking_eligible_D0 = signal_emittable` 排序
2. 从 `ranking_eligible_D0` 中冻结 `topk_frozen_D0`
3. `D1` 开盘执行时才应用 `entry_tradeable`
4. `entry_filled_D1 = execution_attempt_D1 & entry_tradeable`
5. 买不进的缺口保留现金，不补位

正式执行规则：
- `topk_frozen_D0` 固定按 `model_score_D0` 从高到低排序
- 若 `model_score_D0` 并列，固定按 `instrument` 字典序升序打破并列
- 若 `ranking_eligible_D0` 中出现空值、非有限值或不可比较分数，则该条目不得进入 `topk_frozen_D0`，并必须在审计摘要中记录为排序异常
- `D1` 开盘只尝试买入 `D0` 已冻结的 `TopK` 标的
- 若某只 `TopK` 标的在 `D1` 开盘不可买：
  - 该标的本次买单直接失效
  - 该仓位对应资金保留为现金
- **不得顺位补位**
- **不得在 `D1` 盘中改买下一名**
- **不得在后续交易日为这一缺口补开新仓**

制度解释：
- `v1` 的正式组合规则是“冻结候选、执行过滤、现金保留”
- 其目标是避免研究层因为 `D1` 当天不可买而在执行层引入新的排序自由度
- 明确禁止在排序前用 `entry_tradeable` 过滤宇宙
- 明确禁止因 `D1` 不可买而在执行层顺位补位
- 正式审计必须输出：
  - `unfilled_topk_count`
  - `unfilled_topk_weight`
  - `unfilled_entry_reason_breakdown`

### 9.2B 目标权重、集中度与换手口径

`v1` 必须将目标权重、实现权重与换手口径写成正式合同。

`v1` 默认不采用 daily rolling cohort。

`v1` 正式主线采用：

- `rebalance_frequency_trading_days = 5`
- `holding_period_trading_days = 5`
- `daily_rolling_cohort_enabled_v1 = false`
- 单 cohort 持仓
- `TopK = 10`

正式目标权重规则：

- `D0` 冻结后的每个 `TopK` 标的默认目标权重为：
  - `target_weight_D0 = 1 / TopK`
- 若某个冻结标的在 `D1` 开盘不可买：
  - 该标的目标权重对应资金保留为现金
  - 其余已成交标的不得因为缺口而再归一到更高权重
- 持有期内不做额外再平衡

延迟退出资金占用规则：

- 正常情况下，同一时点只存在一个主动建仓 cohort
- 若 `D5` 收盘无法卖出，旧仓继续占用资金
- 新一轮调仓只能使用真实可用现金
- 不得假设旧仓资金已经释放
- 不得因为旧仓应卖未卖而隐性融资开新仓
- 不得产生隐性杠杆

制度解释：

- `target_weight_D0 = 1 / TopK` 定义的是单 cohort 内的目标权重
- 当前 `v1` 默认主线是“单 cohort + 延迟退出现金锁定”
- 历史 `5/10 cohort` 探索属于旧研究轨迹，不代表当前 `v1` 默认主线
- 若未来研究 daily rolling cohort、固定 tranche 或其他资本分摊合同，必须作为独立治理版本，不得在 `v1` 默认主线中混用

正式换手口径：

- 日度换手必须显式输出
- 默认定义为：
  - `turnover_daily = (buy_notional_daily + sell_notional_daily) / lag_total_equity`
- 正式报告至少必须同时输出：
  - 平均日换手
  - 调仓日换手分布
  - 买入换手与卖出换手分解

正式集中度审计：

- 每次正式 fixed test、`walk-forward`、影子跟踪都必须输出：
  - `max_single_name_weight`
  - `top3_weight`
  - `portfolio_herfindahl_index`
  - 行业权重分布
- 若组合集中度异常升高，审计摘要必须显式说明原因

制度解释：

- `TopK + 现金保留` 只解决了“是否补位”的问题，不自动等于“权重合同已完整”
- 目标权重、实现权重与换手定义若不统一，回测结果将无法跨版本审计

### 9.2C 小资金、整手交易与最低佣金

`v1` 默认以小资金散户为执行对象，因此回测必须显式处理：

- 初始资金
- `100` 股整数手买入
- 卖出零股 / 剩余股处理
- 最低佣金
- 资金不足导致的部分未成交
- 整手约束导致的剩余现金

正式执行规则：

- `initial_capital_default` 与 `small_capital_stress_initial_capital` 见附录 A
- 目标权重必须先转为 `raw notional`，再转为股数，再按整手约束下取整
- 买入默认要求 `buy_round_lot_required = true`
- 卖出默认允许 `sell_residual_lot_allowed = true`
- `min_commission` 必须在整手取整后按真实成交金额计算
- 当可用现金不足以完成目标买单时，允许部分未成交与剩余现金
- 成交金额、佣金、印花税、现金变化全部基于 `raw price / raw notional` 计算
- 不得使用复权价格模拟现金流

### 9.3 高现金制度

现金保留本身不是错误，但必须审计资本使用效率。

正式报告必须同时输出：
- 平均现金权重
- 平均投资仓位
- 中位数投资仓位
- 满仓日占比
- 低仓位日占比
- invested capital 口径收益
- total equity 与 invested capital 的收益分解

正式现金来源解释表必须同时输出：
- `cash_reason`
- `cash_weight`
- `cash_event_count`
- `cash_weight_share_of_total`

`cash_reason` 默认枚举值固定为：
- `NO_SIGNAL`
- `LIMIT_UP_UNBUYABLE`
- `SUSPENSION`
- `FILTERED_OUT`
- `LOT_SIZE_RESIDUAL`
- `INSUFFICIENT_CASH_DUE_TO_DELAYED_EXIT`

正式统计口径：

- `cash_event_count` 表示在正式 `TopK + 现金保留` 合同下，对应原因触发的现金缺口事件次数
- `cash_weight` 表示对应原因累计形成的现金权重总量
- `cash_weight_share_of_total` 的分母固定为同一正式评估中全部 `cash_weight` 的总和
- `NO_SIGNAL` 只用于“冻结后可买候选数不足 `TopK`”导致的剩余现金
- `FILTERED_OUT` 只用于“已冻结候选在执行层之外被正式合同排除”的情况，不得与 `NO_SIGNAL` 混用
- `LOT_SIZE_RESIDUAL` 只用于整手约束导致的剩余现金
- `INSUFFICIENT_CASH_DUE_TO_DELAYED_EXIT` 只用于旧仓延迟退出导致的新仓资金不足

制度解释：
- 高现金若显著美化风险指标，必须单独解释
- 任何正式报告都不得只给 total equity 口径而不附 invested capital 口径
- 熊市阶段必须特别检查被动空仓占比是否异常上升
- 所有正式 fixed test 必须附带低流动性暴露摘要，至少覆盖：
  - `low_liquidity_flag = True` 样本的收益贡献占比
  - 这类样本的平均持仓权重占比
  - 这类样本在 alpha 中的贡献占比
- 若低流动性暴露过高，审计摘要必须标红

---

## 10. 回测、benchmark、walk-forward 与主线晋升评分卡

### 10.1 正式 fixed test 输出标准

每次正式 fixed test 至少必须输出：

1. `metrics.json`
2. `backtest_daily.csv`
3. `holdings.csv`
4. `trade_statistics_summary.json`
5. 分年度收益表
6. 持有期收益分布表
7. 现金来源解释表
8. 数据口径摘要
9. 审计摘要
10. 资本使用效率组
11. 实际清算字段
12. 低流动性暴露摘要
13. `TopK` 轻扰动审计摘要
14. 成本 stress 摘要
15. 简版收益归因摘要

推荐正式文件名：
- `data_contract_summary.json`
- `audit_summary.json`
- `cash_source_explanation.csv`
- `low_liquidity_exposure_summary.json`
- `cost_stress_summary.json`
- `return_attribution_summary.json`

`holdings.csv` 至少必须包含：
- `planned_exit_date`
- `actual_exit_date`
- `exit_delay_days`
- `execution_delayed_realized_return`

字段单位、量纲与小数/百分数读法以附录 E 为准；若运行产物、共享视图或项目侧 schema 的字段名与附录 E 不一致，以附录 E 的量纲定义和字段分类作为审计解释口径。

### 10.2 benchmark 制度

默认正式主 benchmark 固定为：
- **中证全指全收益**

同时必须存在：
- 一个**辅助解释 benchmark**
- 该 benchmark 只用于审计附录，不用于主线晋升判定
- 其目标是更贴近“主板 + 创业板 + 当前可投资宇宙”的解释口径

正式规则：
- 所有正式报告必须同时展示绝对收益与相对收益
- 若 total-return benchmark 不可得：
  - 相对指标自动降级为“非正式相对收益”
  - 该轮结果不得用于主线晋升

审计摘要必须记录：
- benchmark 名称
- total-return / price 口径
- 是否发生 fallback
- fallback 是否触发降级

### 10.2A 风险暴露与收益归因

正式报告不得只展示净值与相对收益，还必须解释收益来自什么暴露。

`v1` 的正式归因框架至少包括两层：

1. **描述性风险暴露审计**
2. **收益来源归因摘要**

描述性风险暴露审计至少覆盖：
- 行业主动权重
- 市值暴露偏移
- 波动率暴露偏移
- 流动性暴露偏移
- 若相关字段可用，则同时覆盖：
  - value
  - profitability / quality
  - investment

收益来源归因摘要至少覆盖：
- benchmark 收益贡献
- 现金拖累
- 选股超额收益
- 低流动性样本贡献

`v1` 归因制度分层固定为：

1. **简版收益归因摘要**
2. **扩展暴露 / 风险归因**

正式要求：
- `v1` fixed test 至少必须完成简版收益归因摘要
- 简版收益归因摘要已经足以支持固定测试阶段的“收益来源是否明显依赖现金、benchmark 或低流动性”的审计判断
- `v1` 不强制在第一天引入 Barra 式完整风险模型
- 但若要对外宣称“alpha 来源清晰”或进入更高等级主线晋升审查，则不得只停留在简版归因

正式纪律：

- 若候选方案的超额收益主要来自单一已知风格暴露或单一行业偏置，不得直接表述为“稳定 stock selection alpha”
- 若收益主要来自低流动性或高不可交易暴露，必须在审计摘要中标记为：
  - `exposure_driven_or_liquidity_driven = true`
- `v1` 默认要求先做描述性归因，不强制引入完整 Barra 式风险模型；但不得完全缺席暴露审计

制度解释：

- 相对 benchmark 跑赢并不自动等于选股能力
- 对多因子排序系统而言，暴露归因是判断“真 alpha”与“隐藏风格押注”的最低要求

### 10.3 walk-forward 的正式地位

`walk-forward` 不是附加审计，而是主线晋升必要框架。

正式角色定义：

- fixed test 回答：冻结候选在完整 `2022-2025` 区间是否通过正式验收
- `walk-forward` 回答：若按年度重训协议部署，结果是否稳定
- 当 `walk-forward` 与 fixed test 共用历史样本区间时，不得被解释为独立样本外证据
- `walk-forward` 的正式作用是年度部署协议稳定性、重训敏感性与窗口漂移审计
- `walk-forward` 不增加 fixed test 的“独立显著性信心”，只用于检查部署路径脆弱性

正式主线晋升前，必须同时通过：
- 固定测试集评估
- `walk-forward` 评估

每轮 `walk-forward` 必须绑定：
- `git_commit_hash`
- `git_dirty_flag`
- `git_diff_hash`
- `config_hash`
- `data_contract_hash`
- `execution_logic_hash`
- `factor_contract_hash`
- `environment_manifest_hash`
- `data snapshot id`
- `execution logic version`
- `research tier`

### 10.3A `walk-forward v1` 窗口生成协议

`walk-forward v1` 固定采用：
- **anchored expanding windows**
- **年度重训步长**
- **测试窗口长度 = 1 个自然年**

`v1` 默认窗口协议固定为：
- `wf_2022`：
  - train = `2010-01 ~ 2018-12`
  - valid = `2019-01 ~ 2021-12`
  - test = `2022-01 ~ 2022-12`
- `wf_2023`：
  - train = `2010-01 ~ 2019-12`
  - valid = `2020-01 ~ 2022-12`
  - test = `2023-01 ~ 2023-12`
- `wf_2024`：
  - train = `2010-01 ~ 2020-12`
  - valid = `2021-01 ~ 2023-12`
  - test = `2024-01 ~ 2024-12`
- `wf_2025`：
  - train = `2010-01 ~ 2021-12`
  - valid = `2022-01 ~ 2024-12`
  - test = `2025-01 ~ 2025-12`

正式要求：
- 每个 `walk-forward` 窗口都必须继续执行 `purge_gap_default`
- `walk-forward` 的训练、验证、测试窗口不得人工重配
- 若未来要升级窗口协议，必须作为新的治理版本处理，不得在 `v1` 内混用

制度解释：
- 固定测试集用于“冻结验收”
- `walk-forward` 用于“年度推进部署模拟”
- 在 `wf_2023 / wf_2024 / wf_2025` 中，较早年份可以进入后续窗口的 train 或 valid，因为这些年份在该部署模拟时点已经是历史数据
- `walk-forward` 不是第二份独立冻结保留集，不得把 fixed test 与 `walk-forward` 表述为“两份相互独立的样本外证明”
- 二者互补，但都必须按固定协议执行；`walk-forward` 的作用是部署协议稳定性审计，不是第二份独立 OOS 证明
- 在 fixed test 首次正式查看前，不得生成、返回或展示任何包含 `2022-2025` 信息的 `walk-forward` 摘要
- fixed test 消耗前，不得使用 `wf_2022 / wf_2023 / wf_2024 / wf_2025` 结果筛选候选
- `walk-forward` 结果一旦被正式查看，也必须进入样本外结果可见性与研究空间审计记录
- 不得在查看 `walk-forward` 后，把窗口表现当作新的调参回馈通道继续细磨同一主线

每轮正式主线晋升前，必须做至少 `1` 个窗口级 fresh rerun 一致性审计。

若窗口级 fresh rerun 与原窗口结果不一致，则整轮 `walk-forward` 自动降级，不得继续作为正式晋升证据。

### 10.4 正式主线晋升评分卡

正式主线晋升改为两层机制：

**第一层：否决项**
- PIT 违规
- 测试集泄漏或越权查看
- fresh rerun 不可复现
- 成本 stress 后相对收益翻负
- 流动性压力测试偏差超过治理参数表上限
- 平均投资仓位过低且未获资本使用效率豁免
- 树模型种子稳定性严重失衡

**第二层：综合项**
- 测试集年化相对收益
- 相对收益显著性指标（`t-stat`）
- 年度正收益覆盖
- 最大回撤相对线性基线
- `walk-forward` 正窗口比例
- 拼接样本外 `IR`
- `TopK` / 成本轻扰动稳定性
- 资本使用效率

综合项的正式布尔定义固定为：
- `pass_annual_relative_return = annual_relative_return >= annual_relative_return_min`
- `pass_relative_return_t_stat = relative_return_t_stat >= relative_return_t_stat_min`
- `pass_positive_test_years = positive_test_years_count >= positive_test_years_count_min`
- `pass_drawdown_vs_linear_baseline = max_drawdown_delta_vs_linear_baseline <= max_drawdown_vs_linear_baseline_delta_max`
- `pass_walk_forward_positive_window_ratio = walk_forward_positive_window_ratio >= walk_forward_positive_window_ratio_min`
- `pass_walk_forward_ir = walk_forward_ir >= walk_forward_ir_min`
- `pass_topk_and_cost_perturbation_stability = topk_8_relative_return >= topk_perturbation_relative_return_floor & topk_12_relative_return >= topk_perturbation_relative_return_floor & cost_stress_relative_return >= cost_perturbation_relative_return_floor`
- `pass_capital_efficiency = avg_invested_weight >= avg_invested_weight_floor OR approved_capital_efficiency_waiver = true`

其中资本使用效率豁免规则固定为：
- `approved_capital_efficiency_waiver = true` 仅当存在一条正式豁免记录时方可成立
- 豁免记录必须绑定：
  - `research_round_id`
  - `candidate_scheme_id`
  - `git_commit_hash`
  - `git_dirty_flag`
  - `git_diff_hash`
  - `config_hash`
  - `data_contract_hash`
  - `execution_logic_hash`
  - `factor_contract_hash`
  - `environment_manifest_hash`
  - `snapshot id`
  - `execution logic version`
- 豁免审批人固定为：
  - 预注册中事先登记的 `governance_approver_id`
- 模型实现者不得在结果返回后自行设置豁免
- 豁免作用域固定为：
  - 单一确认性研究轮次
  - 单一候选方案
  - 单一次正式评估结果
- 豁免记录至少必须包含：
  - `approver_id`
  - `approval_timestamp`
  - `waiver_reason`
  - `supporting_evidence`
  - `disclosure_required = true`
- 任何正式报告若使用了该豁免，必须在审计摘要中显式披露豁免原因与作用域

核心分组通过规则固定为：
- `pass_return_quality_group = pass_annual_relative_return & pass_relative_return_t_stat & pass_positive_test_years`
- `pass_stability_group = pass_drawdown_vs_linear_baseline & pass_walk_forward_positive_window_ratio & pass_walk_forward_ir`
- `pass_execution_group = pass_topk_and_cost_perturbation_stability & pass_capital_efficiency`

综合项总通过规则固定为：
- `composite_pass_count = sum(pass_annual_relative_return, pass_relative_return_t_stat, pass_positive_test_years, pass_drawdown_vs_linear_baseline, pass_walk_forward_positive_window_ratio, pass_walk_forward_ir, pass_topk_and_cost_perturbation_stability, pass_capital_efficiency)`
- `pass_promotion_composite = pass_return_quality_group & pass_stability_group & pass_execution_group & (composite_pass_count >= promotion_composite_total_pass_threshold)`

默认晋升规则：
- 先全部通过否决项
- 再在综合项中同时满足：
  - 核心综合项分组门槛
  - 总体综合项通过门槛
- fixed test 回答“冻结验收是否通过”
- `walk-forward` 回答“年度重训部署协议是否稳定、是否存在明显窗口漂移或重训敏感性”
- 二者必须同时通过，但证据角色不同，且不得被表述为两份相互独立的样本外证明
- 树模型想晋升时，还必须满足附录 A 中的树模型稳定性默认门槛
- 所有显著性指标与 `IR` 的统计定义以附录 B 为准

仅凭：
- fixed test 好看
- 某一年特别好
- 口头解释“更有潜力”

不得晋升主线。

### 10.4A 多重检验与研究空间调整审计

`v1` 必须承认研究空间会放大伪发现概率，因此名义显著性不能单独作为正式证据。

正式要求：

- 所有确认性研究必须同时记录：
  - 原始候选因子数
  - 原始策略变体数
  - 确认性候选方案数
  - 实际生成的验证摘要数
  - 研究者已查看的样本外摘要数
- 每轮正式主线晋升材料必须至少包含一项研究空间调整审计：
  - `DSR`（Deflated Sharpe Ratio）
  - `PBO`（Probability of Backtest Overfitting）
  - `White Reality Check / SPA` 中的一种等价替代
- `t-stat`、`IR`、年度正收益覆盖只能作为名义统计证据，不得替代研究空间调整审计
- 若名义统计指标通过，但研究空间调整审计未通过，则该轮结果最多只能记为：
  - **探索性证据**
  - 不得作为正式主线晋升依据

有效试验数的正式要求：

- 每轮研究都必须给出一个保守的 `effective_trials_estimate`
- 该估计不得小于以下对象中的最大值：
  - 原始候选因子数
  - 原始策略变体数
  - 确认性候选方案数
  - 实际生成的验证摘要数

制度解释：

- 研究者看过的候选越多，样本内“看起来显著”的结果越可能只是搜索产物
- `v1` 不要求从第一天起把所有高级检验都做到最复杂，但必须把“研究空间调整”升级为正式审计项目

### 10.5 再现性检查

正式审计必须包括：

- **结构一致性**
  - 行数、主键集合、持仓集合、调仓日集合一致
- **经济一致性**
  - 关键指标差异必须落在附录 A 的治理容忍范围内
- **位级一致性**
  - 仅在显式 deterministic / single-thread 参考运行模式下要求
- 树模型额外执行固定种子稳定性检查，默认种子集合与标准见附录 A
- 所有涉及涨跌停边界的再现性检查，都必须使用 `Decimal + ROUND_HALF_UP`

制度解释：
- 不同模式下不默认追求位级一致
- 正式审计优先保证结构一致性与经济一致性

### 10.6 失败证据保留

失败分支不得删除。

最低限度元数据必须保留：
- commit
- `snapshot ids`
- `research tier`
- 改动点
- 关键指标
- 失败原因
- 时间戳

正式主线报告应能追溯：
- 当前赢家从多少候选中胜出
- 失败分支各自因为什么被淘汰

---

## 11. 执行阶段与影子跟踪制度

### 11.1 执行阶段

执行阶段只承担真实执行职责：
- 日常 `generate_orders`
- 正式出单归档
- 不承载研究优化功能

### 11.2 影子跟踪阶段

影子跟踪是主线可信度恢复的核心环节。

正式制度：
- 每个交易日收盘后更新影子结果
- 每周归档一次周度摘要
- 每月归档一次月度摘要
- 影子跟踪记录必须沿用与正式回测一致的执行逻辑与审计字段

### 11.3 影子跟踪输出

影子跟踪至少输出：
- 当日信号与订单摘要
- 实际可交易性审计
- 平均投资仓位
- 延迟退出统计
- 相对 benchmark 摘要
- 与历史 fixed test 同口径的关键对照指标

### 11.4 影子跟踪最低观察期与复盘触发器

正式主线进入“可讨论实盘资格提升”前，必须满足附录 A 中的最低影子观察期要求。

任一触发器出现，必须进入复盘而不是继续优化：
- shadow 相对收益在附录 A 规定的观察窗口内转负
- 平均投资仓位在附录 A 规定的观察窗口内跌破下限
- 延迟退出占比在附录 A 规定的连续周数内高于上限
- 新旧执行语义或 `snapshot id` 不一致

### 11.5 Stage 3 跌停流动性压力测试

冻结评估阶段必须额外运行一次跌停流动性压力测试回放。

正式规则：
- 假设 `D5` 收盘跌停即触发延迟卖出
- 后续仅允许按“每个开盘继续尝试卖出”的制度回放
- 压力测试结果必须单独写入审计摘要

若压力测试下：
- `execution_delayed_realized_return`
- 与固定窗口收益

之间偏差超过附录 A 的治理上限，则该候选主线自动标记为：
- **高流动性依赖**

且默认不得直接晋升正式主线

---

## 12. 非协商规则

以下规则在 `v1` 中属于宪法级非协商边界：

1. 测试集加密托管
2. 测试集看过即失去 OOS 资格
3. 必须存在 `purge gap` 机制
4. 确认性研究单维改动
5. 主线晋升必须同时经过固定测试集与 `walk-forward`
6. 报告必须同时展示固定窗口收益与真实清算收益
7. 报告必须同时展示 total equity 与 invested capital 口径
8. 失败证据必须保留
9. `tradability` 与 benchmark fallback 不得静默发生
10. 参数级阈值必须版本化治理，不得伪装成永恒常数
11. 不得使用复权价格模拟真实成交现金流
12. 不得重复计算公司行为收益

---

## 13. 编码实施优先级

### 13.1 `P0` 必须先实现

1. 交易日历权威表
2. 股票基础表与主板 / 创业板 universe
3. `raw OHLC + adj_factor + adj_price_base`
4. `adj_open/adj_high/adj_low/adj_close` 到 `adj_*_base` 的项目侧 alias
5. `D0 / D1 / D5` 日期映射
6. `tradability` 权威表
7. `Decimal + ROUND_HALF_UP` 涨跌停判断
8. `label_price_defined`
9. `label_5d_next_open_close_raw`
10. `label_usable_for_training`
11. `D1` 不可买现金保留
12. `D5` 卖不出延迟退出
13. 每 `5` 个交易日调仓一次
14. 单 cohort 持仓
15. `TopK` 冻结
16. 不补位
17. 初始资金
18. 买入整手
19. 最低佣金
20. 旧仓延迟退出资金占用
21. 不隐性加杠杆
22. fixed test 最小 artifacts
23. PIT 自检
24. 随机标签安慰剂测试
25. 随机分数安慰剂测试
26. run manifest
27. environment manifest
28. 失败证据保留

### 13.2 `P1` 紧随其后

1. 跌停流动性压力测试
2. 树模型稳定性标准改写
3. 验证集粗颗粒稳定性摘要
4. 预注册布尔表达式
5. 简版风险暴露与收益归因摘要
6. 小资金 stress 运行

### 13.3 `P2` 再进入扩展审计

1. 多重检验与研究空间调整审计
2. 统计显著性门槛的扩展实现
3. 复杂风险暴露 / 收益归因
4. DSR / PBO / SPA 等高级统计审计

---

## 14. 研究推进操作蓝图

本节属于**操作层研究蓝图**，用于指导后续在不破坏总纲治理边界的前提下，持续推进研究。

### 14.1 研究目标的操作化解释

后续研究推进的首要目标不是：
- 尽快把历史回测做高

后续研究推进的首要目标是：
- 先建立一套能够**稳定淘汰坏想法**的研究工作流
- 在低自由度前提下，逐步积累少量可信因子与简单可解释基线
- 让每一轮研究都能回答一个明确问题，而不是同时试很多方向后挑最好看的结果

制度解释：
- 经验研究中，样本外衰减是常态而不是例外
- 多候选、多信号、多轮筛选会显著提高“把噪音误当成 alpha”的风险
- 因此 `v1` 必须优先建设“会否决、会止损、会保留失败证据”的研究流程，而不是优先追求复杂模型

### 14.2 正式研究顺序

`v1` 的正式研究顺序固定为：

1. **系统自检阶段**
2. **单因子探索阶段**
3. **小因子池线性基线阶段**
4. **确认性研究阶段**
5. **冻结评估与 `walk-forward` 阶段**
6. **影子跟踪阶段**

推进纪律：
- 上一阶段的最低要求未达成，不得跳级推进下一阶段
- 不允许在系统自检未完成时直接进入复杂模型比较
- 不允许在单因子证据不足时直接堆叠大量因子做组合优化

### 14.3 系统自检阶段

在正式因子研究前，必须先完成一轮系统自检。

最低自检项包括：
- 数据质量检查
- 标签与执行语义一致性检查
- `tradability` 与样本资格矩阵一致性检查
- benchmark 对齐检查
- 成本、`TopK`、持有期、`purge gap` 基础配置检查

正式要求至少包含以下安慰剂 / 反证测试：
- 随机打乱标签后，模型结果不得仍显著为正
- 随机打乱排序分数后，组合结果不得仍显著为正
- 将关键特征整体滞后后，结果不得异常改善
- 将关键特征整体超前后，若结果显著改善，应视为未来信息泄漏风险警报
- 主口径与保守口径结果方向必须可解释，若方向相反，研究不得继续晋升
- 低流动性样本剥离后，若 alpha 大幅消失，必须标记为高流动性依赖风险

任一自检未通过：
- 该轮研究不得进入正式因子筛选
- 必须先修复数据、标签、执行语义或审计链路，再重新开始

### 14.4 单因子探索阶段

`v1` 的正式研究起点固定为：
- 先做单因子研究，再做多因子组合

单因子阶段的目标不是：
- 找到单因子回测最高者

单因子阶段的目标是：
- 确认该因子是否具有可解释性、覆盖率、方向稳定性与可交易性

每个候选因子在进入正式探索前，必须先形成一张**因子卡**。

因子卡至少包含：
- 因子名称
- 精确定义公式
- 预期方向
- 不超过 `3` 句的经济解释
- 所需原始字段
- `price_domain = raw_price / base_adjusted_price / raw_amount / fundamental_pit`
- PIT 生效规则
- 缺失值处理规则
- 去极值 / 标准化规则
- 预期失败模式

单因子阶段必须并行审计：
- 覆盖率
- RankIC / IC 方向
- 分组单调性
- 训练集内部子时期方向一致性
- 主口径与保守口径方向一致性
- 低流动性暴露
- 被少数日期或少数股票主导的集中度风险

若单因子出现以下任一情况，默认不进入下一阶段：
- 经济解释无法清楚写出
- 覆盖率不达标
- 训练集内部子时期方向频繁翻转
- 主要收益来自低流动性或高不可交易样本
- 主口径有效而保守口径方向失真

### 14.5 第一版候选方向优先级

`v1` 第一批研究方向应控制在少量高解释度大类中，默认研究顺序为：

1. `quality / profitability`
2. `investment`
3. `value`
4. `liquidity / trading frictions`
5. `low-risk / volatility`
6. `momentum` 作为挑战者方向

制度解释：
- 第一批方向应优先覆盖经典、可解释、跨市场较常见的大类因子
- 对 A 股短持有期系统而言，流动性与交易摩擦方向必须被重点审计，因为它既可能提供信息，也可能制造伪 alpha
- 上述顺序只是默认研究推进顺序，不等价于正式冻结候选名单
- 若实际数据可得性、治理修复优先级或当前问题定义发生变化，执行计划可以对研究顺序做版本化调整，但不得突破本总纲的制度边界

### 14.6 小因子池线性基线阶段

只有当单因子阶段已经筛出少量存活因子后，才允许进入多因子基线。

`v1` 默认要求：
- 先用 `3 ~ 5` 个存活因子构建第一版正式线性基线
- 先做简单可解释组合，再讨论更复杂模型

第一阶段可接受的组合形式：
- 标准化后等权线性组合
- 岭回归
- 弹性网络

默认禁止：
- 在第一版正式主线尚未形成前，用大规模候选池直接训练复杂树模型
- 因单因子证据不足而靠组合堆叠掩盖单因子弱点

### 14.7 确认性研究的具体工作法

每轮确认性研究只允许回答一个清晰问题，例如：
- 新增某一个候选因子是否优于现有基线
- 某一种标准化方式是否优于旧方式
- 某一个线性模型形式是否优于当前主线基线

正式纪律：
- 一轮确认性研究只允许改一个核心维度
- 每轮候选方案数必须受附录 A 预算约束
- 首次验证集结果返回前，候选列表、通过标准、时间分区、`snapshot id`、代码 / 配置 / 数据 contract 指纹、执行逻辑版本必须冻结
- 若研究者希望同时改多个核心维度，必须拆成多轮研究，不得并入同一轮确认性研究

### 14.8 每日 / 每周研究节奏

建议的日常研究节奏固定为：

1. 每日先看数据与审计，再看收益
2. 每周只回答一个明确研究问题
3. 每周只形成一个正式结论：
   - `KEEP`
   - `INCONCLUSIVE`
   - `REJECT`

制度解释：
- 新手最常见的问题不是做得不够多，而是一次并行过多研究问题
- `v1` 必须优先压缩并行度，让每一轮结论可追溯、可解释、可复现

### 14.9 正式看板的观察顺序

正式研究中，结果查看顺序固定建议为：

1. PIT 与数据完整性
2. 覆盖率与样本资格
3. 单因子方向性与单调性
4. 主口径 / 保守口径一致性
5. 低流动性暴露与可交易性
6. 投资仓位与现金来源
7. 固定测试与 `walk-forward` 的综合表现
8. 年化收益、Sharpe、`IR` 等汇总指标

制度解释：
- 任何把收益指标放在前面、把数据质量与可交易性放在后面的研究顺序，都容易产生回测美化偏差

### 14.10 明确应避免的研究行为

以下行为在 `v1` 中默认视为高过拟合风险：

- 一开始就研究大因子池
- 在测试集或观察区反复微调
- 同时改多个核心维度
- 因某一年特别好就放宽通过标准
- 主要依赖低流动性样本解释 alpha
- 只看 `total equity`，不看 `invested capital`
- 单因子证据弱却直接上复杂模型
- 删除失败实验记录

### 14.11 第一版建议推进节奏

若按自然月推进，`v1` 建议节奏为：

1. **第 1 月**
- 完成数据、标签、`tradability`、benchmark、自检与安慰剂测试

2. **第 2 月**
- 完成第一批少量单因子卡与训练集内筛选

3. **第 3 月**
- 用少量存活因子建立线性基线

4. **第 4 月**
- 只开启 `1` 轮确认性研究，并严格控制候选方案数

5. **之后**
- 进入验证摘要、locked rerun、fixed test、`walk-forward` 与影子跟踪

该节奏是默认建议节奏，不是强制日历承诺；但若推进明显快于此节奏，必须额外审查是否实际增加了过拟合风险。

---

## 15. 当前留待实施阶段细化的项目

本文件已经定死制度边界，以下内容留到实施阶段补成代码与 schema。

项目管理层面的当前周期安排、低额度周期冻结策略、下周期首批实现名单、研究顺序与 Codex 节流规则，不属于本总纲的宪法级内容，统一维护在：

- `/Users/wy/MiscProject/multi_factor/项目总纲及计划/multifactor_v1_execution_plan.md`

引用关系：

- 本总纲负责长期稳定、可复现、可审计的制度边界
- 实施计划文件负责当前周期与下一阶段的执行安排
- 若两者发生冲突，以本总纲为准

1. 第一版 `<= 10` 个候选因子具体名单
2. 第一阶段线性基线的具体实现形式
3. 第二阶段受限 `LightGBM / XGBoost` 的具体超参数上限
4. 数据仓库最小表结构与字段清单
5. 影子跟踪与主线晋升的自动化脚本接口
6. 新增条款的实施检查清单见附录 C
7. 新增条款的数据表 / 字段 / schema 设计见附录 D

这些内容可以细化，但不得违反本总纲中已写死的时间切分、权限控制、预算门槛、tradability 规则与主线晋升评分卡。

---

## 16. 第一版框架的核心精神

这个新项目第一版，核心不是：
- 先做最强模型

而是：
- 先建一个**低自由度、边界清晰、样本内/外制度严格、真实执行语义统一、结果权限受控、可复现可审计**的研究系统

只有第一版系统是干净的，后续再引入：
- 更复杂因子
- 更复杂模型
- 更复杂优化器

才有意义。

---

## 附录 A：治理参数表

以下参数均为 `v1 governance defaults`，属于**参数级治理规则**，可以在后续治理评审中版本化修订，但不得违背正文里的宪法级规则。

参数使用纪律：

- 参数级默认值服务于 `v1` 治理一致性，不主张被表述为跨阶段、跨市场、跨策略的永恒常数
- 任何参数级默认值若在后续研究中需要调整，必须记录变更依据、适用范围与生效时间
- 若参数调整会改变正式通过 / 失败判断，该调整必须先完成治理评审，再进入新一轮研究

### A.1 成本与流动性审计默认值

- `initial_capital_default = 300000`
- `small_capital_stress_initial_capital = 100000`
- `buy_lot_size = 100`
- `buy_round_lot_required = true`
- `sell_residual_lot_allowed = true`
- `min_commission_applies_after_lot_rounding = true`
- `buy_commission_default = 0.0003`
- `sell_commission_default = 0.0003`
- `sell_stamp_duty_default = 0.0010`
- `slippage_default = 0.0005`
- `min_commission_default = 5.0`
- `buy_commission_stress = 0.0005`
- `sell_commission_stress = 0.0005`
- `sell_stamp_duty_stress = 0.0010`
- `slippage_stress = 0.0010`
- `min_commission_stress = 5.0`
- `low_liquidity_amount_threshold_k_yuan = 5000`
- `low_liquidity_amount_threshold_yuan = 5000000`

### A.2 时间切分与访问预算

- `purge_gap_default = 5`
- `purge_gap_sensitivity = {7, 10}`
- `validation_view_budget = 2`
- `validation_debug_detail_forbidden = true`
- `test_debug_detail_forbidden = true`
- `train_debug_detail_allowed = true`
- `synthetic_debug_detail_allowed = true`

### A.3 探索性 / 确认性研究预算

- `exploratory_max_raw_candidate_factors = 30`
- `exploratory_max_strategy_variants = 12`
- `exploratory_max_version_tree_generations = 2`
- `confirmatory_max_candidate_schemes = 3`

### A.4 因子入围默认阈值

- `confirmatory_factor_count_max = 10`
- `exploratory_factor_pool_max = 30`
- `factor_min_coverage = 0.85`
- `factor_max_abs_corr = 0.80`

### A.5 组合与稳定性审计默认值

- `topk_default = 10`
- `topk_stability_audit_set = {8, 12}`
- `avg_invested_weight_floor = 0.60`
- `rebalance_frequency_trading_days = 5`
- `holding_period_trading_days = 5`
- `daily_rolling_cohort_enabled_v1 = false`
- `holding_cohort_count_rule = single_active_cohort_with_delayed_exit_cash_lock`
- `liquidity_stress_gap_bps_max = 200`
- `topk_perturbation_relative_return_floor = 0.00`
- `cost_perturbation_relative_return_floor = 0.00`
- `low_liquidity_weight_share_warning = 0.20`
- `low_liquidity_alpha_contribution_share_warning = 0.50`

### A.6 主线晋升综合项默认门槛

- `annual_relative_return_min = 0.01`
- `relative_return_t_stat_min = 1.5`
- `test_year_count_fixed = 4`
- `positive_test_years_count_min = 3`
- `max_drawdown_vs_linear_baseline_delta_max = 0.05`
- `walk_forward_positive_window_ratio_min = 0.75`
- `walk_forward_ir_min = 0.30`
- `promotion_composite_core_groups = {return_quality, stability, execution}`
- `promotion_composite_core_group_requirement = pass_all_core_groups`
- `promotion_composite_total_pass_threshold = 5`

综合项分组固定为：
- `return_quality = {annual_relative_return, t_stat, positive_test_years}`
- `stability = {max_drawdown_vs_linear_baseline, walk_forward_positive_window_ratio, walk_forward_ir}`
- `execution = {topk_and_cost_perturbation_stability, capital_efficiency}`

### A.7 树模型稳定性默认参数

- `tree_model_seed_count = 3`
- `tree_model_seed_generation_rule = deterministic_hash(research_round_id, model_name, ordinal_index)`
- `tree_seed_positive_median_required = true`
- `tree_seed_relative_return_std_multiplier_max = 1.5`
- `tree_seed_majority_not_worse_than_linear = true`
- `tree_model_realized_seed_list_must_be_logged = true`

### A.8 再现性容忍度默认分级

- `structural_consistency = exact`
- `economic_consistency_return_tolerance_bp = 5`
- `economic_consistency_drawdown_tolerance_bp = 10`
- `economic_consistency_turnover_tolerance_bp = 10`
- `bitwise_consistency = deterministic_single_thread_only`

### A.9 影子跟踪默认触发器

- `shadow_observation_min_trading_days = 120`
- `shadow_observation_min_calendar_months = 6`
- `shadow_negative_relative_return_window_days = 60`
- `shadow_low_invested_weight_window_days = 20`
- `shadow_delay_exit_ratio_alert_weeks = 4`
- `shadow_low_invested_weight_floor = 0.50`
- `shadow_delay_exit_ratio_alert = 0.10`

### A.10 多重检验与研究空间审计默认值

- `research_space_strict_t_stat_reference = 3.0`
- `dsr_required_for_formal_promotion = true`
- `pbo_audit_required_if_effective_trials_estimate_ge = 10`
- `effective_trials_estimate_floor_rule = max(raw_candidate_factor_count, strategy_variant_count, candidate_scheme_count, validation_summary_count_generated)`

### A.11 因子预处理、暴露与组合审计默认值

- `factor_winsor_mad_clip_default = 5.0`
- `factor_standardization_default = cross_sectional_robust_zscore`
- `factor_missing_imputation_default = none`
- `factor_neutralization_default = none`
- `single_name_target_weight_cap_default = 1 / topk_default`
- `top3_weight_warning = 0.40`
- `industry_active_weight_warning = 0.20`
- `style_descriptor_exposure_warning_z = 1.0`
- `fixed_test_minimum_attribution_layer = summary`
- `attempt_input_snapshot_required = true`

### A.12 撮合敏感性与终局事件默认值

- `auction_open_slippage_stress_bp = 20`
- `auction_close_slippage_stress_bp = 20`
- `auction_sensitivity_relative_return_floor = 0.00`
- `terminal_exit_pricing_hierarchy = {cash_settlement, last_tradable_close, zero_recovery}`
- `terminal_event_disclosure_required = true`

---

## 附录 B：统计口径附录

所有正式显著性与稳定性指标必须绑定以下统一统计定义，不允许在不同实验中私自更换。

### B.1 相对收益序列

- 正式显著性检验默认基于**日频相对收益序列**
- 日频相对收益定义为：
  - `relative_return_daily = strategy_return_daily - benchmark_return_daily`
- 价格路径类收益默认基于 **base-adjusted price** 构造
- base-adjusted price 统一定义为：
  - `adj_price_base_t = raw_price_t * adj_factor_t`

### B.2 年化方式

- 日频收益年化默认采用：
  - `annualization_factor = 252`
- 测试集年化相对收益固定定义为：
  - `strategy_nav_test = cumprod(1 + strategy_return_daily)`
  - `benchmark_nav_test = cumprod(1 + benchmark_return_daily)`
  - `annual_relative_return = (strategy_nav_test_end / benchmark_nav_test_end)^(252 / n_effective_days) - 1`
- `n_effective_days` 固定为测试集内策略收益与 benchmark 收益同时可定义的有效交易日数
- 不允许使用“日频相对收益均值直接年化”替代正式 `annual_relative_return`

### B.2A 测试年度相对收益定义

- 每个自然年 `y` 的年度相对收益固定定义为：
  - `strategy_nav_y = cumprod_y(1 + strategy_return_daily)`
  - `benchmark_nav_y = cumprod_y(1 + benchmark_return_daily)`
  - `year_relative_return_y = strategy_nav_y_end / benchmark_nav_y_end - 1`
- `positive_test_years_count = count(year_relative_return_y > 0 over all effective test years)`
- `effective_test_years_count` 固定定义为满足有效交易日要求的正式测试年度个数
- `v1` 正式主线默认测试年度总数固定为：
  - `effective_test_years_count = test_year_count_fixed = 4`
- 若某自然年内有效交易日不足以构成正式测试年度，则该年不得计入 `positive_test_years_count`

### B.2B `TopK` / 成本扰动收益定义

- `topk_8_relative_return`、`topk_12_relative_return`、`cost_stress_relative_return` 的统计口径必须与正式 `annual_relative_return` 完全一致
- 唯一允许变化的维度分别为：
  - `TopK = 8`
  - `TopK = 12`
  - `cost_stress` 参数集
- 这三个指标均固定定义为对应扰动条件下：
  - `perturbed_strategy_nav_end / perturbed_benchmark_nav_end` 按正式 `annual_relative_return` 公式年化后的相对收益
- 不允许对这些扰动指标使用与正式主口径不同的聚合频率、年化公式或 benchmark 口径
- `TopK` 轻扰动与成本 stress 的审计结论默认分为：
  - `pass`
  - `warning`
  - `fail`
- `v1` 默认判定规则：
  - `topk_8_relative_return < topk_perturbation_relative_return_floor` 或 `topk_12_relative_return < topk_perturbation_relative_return_floor` 记为 `fail`
  - `cost_stress_relative_return < cost_perturbation_relative_return_floor` 记为 `fail`
  - 其余低于正式主口径但未跌破 floor 的情况可记为 `warning`

### B.2C 现金来源解释统计定义

- `cash_event_count` 固定统计为：
  - 正式 `TopK + 现金保留 + 不补位` 合同下，对应 `cash_reason` 触发的现金缺口事件次数
- `cash_weight_total` 固定统计为：
  - 对应 `cash_reason` 在正式单 cohort + 延迟退出现金锁定合同下累计形成的现金权重总量
- `cash_weight_share_of_total` 固定定义为：
  - `cash_weight_total / sum(cash_weight_total over all cash_reason)`
- `cash_reason = NO_SIGNAL` 仅用于冻结后候选数不足 `TopK`
- `cash_reason = FILTERED_OUT` 不得用于替代 `NO_SIGNAL` 或执行失败原因
- `cash_reason = LOT_SIZE_RESIDUAL` 仅用于整手约束导致的剩余现金
- `cash_reason = INSUFFICIENT_CASH_DUE_TO_DELAYED_EXIT` 仅用于旧仓延迟退出导致的新仓资金不足

### B.3 `t-stat` 计算方式

- 正式测试集相对收益的 `t-stat` 使用 **Newey-West HAC**
- 检验对象固定为：
  - 日频相对收益序列均值是否显著大于 `0`
- 默认滞后阶数：
  - `nw_lag = purge_gap_default`
- `v1` 默认取：
  - `nw_lag = 5`
- 缺失日处理规则：
  - 仅在策略收益与 benchmark 收益同时可定义的交易日上计算
- 零波动处理规则：
  - 若相对收益标准差为 `0`，则 `t-stat` 记为不可定义，不得视为通过

### B.4 `IR` 计算方式

- `IR` 默认基于日频相对收益序列计算
- 年化方式：
  - `IR = mean(relative_return_daily) / std(relative_return_daily) * sqrt(252)`
- 缺失日与对齐规则：
  - 与 `t-stat` 使用同一组有效交易日
- 零波动处理规则：
  - 若 `std(relative_return_daily) = 0`，则 `IR` 记为不可定义，不得视为通过

### B.5 walk-forward 拼接样本外曲线

- `walk-forward` 的样本外曲线采用**非重叠窗口顺序拼接**
- 只使用各窗口的正式样本外部分
- 不允许把训练段或验证段收益拼入样本外曲线

### B.6 统计解释原则

- 显著性指标服务于审计，不替代经济解释
- `t-stat`、`IR`、窗口正收益比例必须联立解释
- 任何只依赖单一统计值的晋升结论都无效

### B.7 粗颗粒稳定性摘要定义

- 月度正收益占比：
  - `monthly_positive_ratio = 正相对收益月份数 / 有效月份数`
- 收益集中度指标：
  - `return_concentration_ratio = top_3_positive_months_relative_pnl / total_positive_relative_pnl`
  - 若 `total_positive_relative_pnl <= 0`，则该指标记为不可定义

制度解释：
- 验证集默认不返回年度相对收益正负号向量
- 粗颗粒稳定性摘要的目标是帮助识别脆弱性，而不是提供可反推调参方向的年份级反馈

---

## 附录 C：新增条款实施检查清单

本文把总纲新增的 6 项条款翻译成实施检查清单，目标是让后续研发按“可交付物 + 完成标准”推进，而不是按口头理解推进。

适用条款：

- `3.4A` 开盘 / 收盘撮合微观审计
- `4.4A` 退市与终局事件处理
- `5.7A` 因子预处理与中性化合同
- `9.2B` 目标权重、集中度与换手口径
- `10.2A` 风险暴露与收益归因
- `10.4A` 多重检验与研究空间调整审计

### C.0 通用前置条件

- [ ] 每轮正式运行都能固定 `snapshot_id`
- [ ] 每轮正式运行都能固定 `git_commit_hash / git_dirty_flag / git_diff_hash / config_hash / data_contract_hash / execution_logic_hash / factor_contract_hash / environment_manifest_hash`
- [ ] 每轮正式运行都能固定 `execution_logic_version`
- [ ] 训练 / 验证 / 测试 / 观察区切分脚本已经自动处理 `purge gap`
- [ ] `fixed_test_run_id`、`research_round_id`、`candidate_scheme_id` 已能唯一标识一次研究与一次正式评估
- [ ] `holdings.csv`、`metrics.json`、`trade_statistics_summary.json`、审计摘要已经具备稳定输出骨架

通用完成标准：

- [ ] 新增条款的全部输出都能挂到同一个运行主键
- [ ] 新增条款不会破坏既有 `TopK + 现金保留 + 不补位` 语义
- [ ] 新增条款全部进入审计摘要，而不是只存在于调试日志

### C.1 开盘 / 收盘撮合微观审计

#### C.1.1 数据准备

- [ ] 为每笔计划买入 / 卖出记录基准成交字段
- [ ] 为每笔计划买入 / 卖出记录保守撮合 stress 成交字段
- [ ] 标记开盘跳空、一字板、收盘封板、延迟退出等状态

#### C.1.2 计算逻辑

- [ ] 基准口径继续沿用总纲正式执行语义
- [ ] 保守口径至少加入 `auction_open_slippage_stress_bp`
- [ ] 保守口径至少加入 `auction_close_slippage_stress_bp`
- [ ] 对 `D1` 开盘买入与 `D5` 收盘卖出分别计算敏感性差异
- [ ] 对延迟退出样本单独计算撮合敏感性差异

#### C.1.3 输出物

- [ ] `auction_sensitivity_summary.json`
- [ ] 审计摘要中新增 `auction_microstructure_sensitive`
- [ ] 审计摘要中新增基准口径与保守口径的相对收益对比

#### C.1.4 完成标准

- [ ] 任一次正式 fixed test 都能输出撮合敏感性摘要
- [ ] 任一次 `walk-forward` 都能输出撮合敏感性摘要
- [ ] 任一次影子跟踪周报 / 月报都能输出撮合敏感性摘要

### C.2 退市与终局事件处理

#### C.2.1 数据准备

- [ ] 构建日频 `terminal_event_flag`
- [ ] 构建 `terminal_event_type`
- [ ] 构建 `terminal_event_date`
- [ ] 构建 `last_tradable_date`
- [ ] 若数据可得，构建 `cash_settlement_amount`

#### C.2.2 执行逻辑

- [ ] 若终局事件发生前已有可执行退出时点，继续按正式执行语义退出
- [ ] 若无可执行退出时点，则按总纲规定的价格层级选择终局清算价
- [ ] 对采用近似价格的样本打上 `terminal_exit_approximation_flag`
- [ ] 对采用 `0` 价格保守处理的样本打上 `terminal_exit_conservative_flag`

#### C.2.3 输出物

- [ ] `holdings.csv` 扩展终局事件字段
- [ ] 审计摘要新增终局事件样本数和收益贡献
- [ ] 正式报告新增“终局事件对固定窗口收益与真实清算收益差异的贡献”

#### C.2.4 完成标准

- [ ] 退市 / 长停牌 / 终止上市样本不会被静默删除
- [ ] 所有终局样本都能回溯到明确的定价方法
- [ ] 终局样本的处理口径跨 rerun 一致

### C.3 因子预处理与中性化合同

#### C.3.1 因子定义

- [ ] 每个启用因子都有唯一 `factor_name`
- [ ] 每个启用因子都有唯一 `factor_version`
- [ ] 每个启用因子都有因子卡
- [ ] 因子卡包含缺失值处理、去极值、标准化、中性化声明

#### C.3.2 预处理实现

- [ ] 缺失值处理规则实现为可配置 contract
- [ ] 无穷值 / 非有限值处理规则实现为可配置 contract
- [ ] 去极值规则实现为可配置 contract
- [ ] 标准化规则实现为可配置 contract
- [ ] 中性化规则实现为可配置 contract
- [ ] 预处理顺序固定且可复算
- [ ] 预处理统计量只使用允许的时间窗口

#### C.3.3 输出物

- [ ] `factor_definition_registry`
- [ ] `factor_preprocess_contract`
- [ ] `factor_preprocessed_daily`
- [ ] run 级 `factor_contracts.json`

#### C.3.4 完成标准

- [ ] 同一因子同一版本在同一 `snapshot_id` 下重复运行结果一致
- [ ] 任一候选方案使用了不同预处理合同，都能被审计识别为单独改动维度
- [ ] 因子卡和实际代码配置没有漂移

### C.4 目标权重、集中度与换手口径

#### C.4.1 权重实现

- [ ] `target_weight_D0 = 1 / TopK` 写成正式实现
- [ ] 不可买样本保留现金，不对已成交标的再归一
- [ ] 持有期内不做额外再平衡
- [ ] `portfolio_weights_daily` 能区分目标权重与实际权重

#### C.4.2 换手实现

- [ ] `turnover_daily = (buy_notional_daily + sell_notional_daily) / lag_total_equity` 实现完成
- [ ] 能输出平均日换手
- [ ] 能输出调仓日换手分布
- [ ] 能分解买入换手与卖出换手

#### C.4.3 集中度实现

- [ ] 能输出 `max_single_name_weight`
- [ ] 能输出 `top3_weight`
- [ ] 能输出 `portfolio_herfindahl_index`
- [ ] 能输出行业权重分布

#### C.4.4 完成标准

- [ ] 换手、权重、集中度的计算口径在 fixed test / `walk-forward` / shadow tracking 中一致
- [ ] `TopK + 现金保留` 与目标权重合同之间无冲突
- [ ] 组合集中度异常时，审计摘要能自动标记

### C.5 风险暴露与收益归因

#### C.5.1 风险描述子准备

- [ ] 行业归属可用于日频主动权重计算
- [ ] 市值描述子可用于暴露偏移计算
- [ ] 波动率描述子可用于暴露偏移计算
- [ ] 流动性描述子可用于暴露偏移计算
- [ ] 若字段可得，value / profitability / investment 描述子可用于暴露偏移计算

#### C.5.2 归因逻辑

- [ ] 能输出描述性风险暴露审计
- [ ] 能输出收益来源归因摘要
- [ ] 能区分 benchmark 收益贡献、现金拖累、选股超额收益、低流动性样本贡献
- [ ] 当收益主要来自单一行业或单一风格偏置时，自动标注 `exposure_driven_or_liquidity_driven`

#### C.5.3 输出物

- [ ] `risk_exposure_daily.csv`
- [ ] `return_attribution_daily.csv`
- [ ] `risk_exposure_summary.json`
- [ ] 审计摘要中新增暴露驱动标记

#### C.5.4 完成标准

- [ ] 任一次正式 fixed test 都能输出暴露审计与收益归因
- [ ] 任一次 `walk-forward` 都能输出暴露审计与收益归因
- [ ] 风险暴露结果可以和 `serving` 层标准字段回连复算

### C.6 多重检验与研究空间调整审计

#### C.6.1 研究空间计数

- [ ] 记录原始候选因子数
- [ ] 记录原始策略变体数
- [ ] 记录确认性候选方案数
- [ ] 记录实际生成的验证摘要数
- [ ] 记录研究者已查看的样本外摘要数
- [ ] 计算保守的 `effective_trials_estimate`

#### C.6.2 统计审计

- [ ] 保留名义 `t-stat`
- [ ] 保留名义 `IR`
- [ ] 实现 `DSR` 或等价审计
- [ ] 当 `effective_trials_estimate` 超阈值时，实现 `PBO` 或 `White Reality Check / SPA`

#### C.6.3 输出物

- [ ] `research_space_audit.json`
- [ ] 审计摘要新增 `effective_trials_estimate`
- [ ] 审计摘要新增 `research_space_adjustment_pass`

#### C.6.4 完成标准

- [ ] 名义统计显著但研究空间调整不通过时，系统会自动降级为探索性证据
- [ ] 正式晋升材料能同时展示名义统计与研究空间调整统计
- [ ] rerun 时研究空间计数不会因展示方式变化而漂移

### C.7 总体发布门槛

- [ ] 六项新增条款全部接入 `fixed test`
- [ ] 六项新增条款全部接入 `walk-forward`
- [ ] 影子跟踪至少接入撮合敏感性、目标权重 / 换手、暴露审计三项
- [ ] 全部新增字段都出现在 run 级 schema 或审计摘要中
- [ ] 所有新增输出都能通过 `snapshot_id + git_commit_hash + git_dirty_flag + git_diff_hash + config_hash + data_contract_hash + execution_logic_hash + factor_contract_hash + environment_manifest_hash + execution_logic_version + run_id` 回溯

若上述任一项未完成：

- 该系统版本仍可用于内部探索
- 但不得宣称已完成总纲新增条款的正式落地

---

## 附录 D：新增条款数据表与 Schema 设计

本文把总纲新增的 6 项条款拆成具体数据表、字段和输出 artifact 设计。

目标：

- 让 `parquet_duckdb` 的共享基础层与 `multi_factor` 的派生 contract 层有清晰边界
- 让 run 级输出字段稳定、可审计、可复算
- 让 fixed test、`walk-forward`、shadow tracking 共用同一套主键与 schema 习惯

### D.1 设计原则

- 共享真相源优先放在权威层
- 策略专属衍生结果优先放在 `warehouse/research` 或 run artifact
- 所有表都必须有明确粒度
- 所有 run artifact 都必须绑定同一组主键
- `serving` 视图仍是正式查询入口

### D.2 主键与路径约定

#### D.2.1 运行主键

- `snapshot_id`
- `code_hash`
- `execution_logic_version`
- `research_round_id`
- `candidate_scheme_id`
- `fixed_test_run_id` 或 `wf_run_id` 或 `shadow_run_id`

#### D.2.2 物理路径约定

共享仓库扩展表建议放在：

- `data/snapshots/<snapshot_id>/warehouse/state/`
- `data/snapshots/<snapshot_id>/warehouse/research/`

run 级产物建议放在：

- `artifacts/fixed_test/<fixed_test_run_id>/`
- `artifacts/walk_forward/<wf_run_id>/`
- `artifacts/shadow_tracking/<shadow_run_id>/`

#### D.2.3 官方查询入口

新增共享表落地后，应同步暴露为：

- `serving.vw_terminal_event_daily`
- `serving.vw_factor_definition_registry`
- `serving.vw_factor_preprocess_contract`
- `serving.vw_factor_preprocessed_daily`
- `serving.vw_style_descriptor_daily`

### D.3 共享仓库扩展表

#### D.3.1 `warehouse/state/terminal_event_daily.parquet`

用途：
- 记录 instrument 日频终局状态，作为退市 / 长停牌 / 终止上市审计的共享状态层

粒度：
- `trade_date, instrument`

主键：
- `trade_date`
- `instrument`

字段：

| field | type | nullable | 说明 |
|---|---|---:|---|
| `trade_date` | DATE | 否 | 交易日 |
| `instrument` | VARCHAR | 否 | 股票代码 |
| `terminal_event_flag` | BOOLEAN | 否 | 当日是否处于终局事件窗口 |
| `terminal_event_type` | VARCHAR | 是 | `DELISTING` / `TERMINATION` / `LONG_SUSPENSION` / `CASH_MERGER` / `OTHER` |
| `terminal_event_date` | DATE | 是 | 终局事件生效日 |
| `last_tradable_date` | DATE | 是 | 最后可交易日 |
| `cash_settlement_available` | BOOLEAN | 否 | 是否存在明确现金清算 |
| `cash_settlement_amount` | DOUBLE | 是 | 若存在现金清算，对应单位价格或回收价值 |
| `zero_recovery_recommended` | BOOLEAN | 否 | 是否建议按 `0` 价格保守处理 |
| `event_source` | VARCHAR | 否 | 来源表或规则引擎 |
| `event_source_snapshot_id` | VARCHAR | 否 | 来源 snapshot |
| `record_updated_at` | TIMESTAMP | 否 | 记录生成时间 |

#### D.3.2 `warehouse/research/factor_definition_registry.parquet`

用途：
- 承载因子卡中的业务定义与经济解释

粒度：
- `factor_name, factor_version`

字段：

| field | type | nullable | 说明 |
|---|---|---:|---|
| `factor_name` | VARCHAR | 否 | 因子名称 |
| `factor_version` | VARCHAR | 否 | 因子版本 |
| `factor_family` | VARCHAR | 否 | `quality` / `value` / `momentum` 等 |
| `expected_sign` | VARCHAR | 否 | 预期方向 |
| `formula_text` | VARCHAR | 否 | 精确公式 |
| `economic_rationale` | VARCHAR | 否 | 最多 3 句的经济解释 |
| `source_fields_json` | VARCHAR | 否 | 所需原始字段 |
| `price_domain` | VARCHAR | 否 | `raw_price` / `base_adjusted_price` / `raw_amount` / `fundamental_pit` |
| `pit_rule` | VARCHAR | 否 | PIT 生效规则 |
| `lookback_spec_json` | VARCHAR | 是 | lookback 配置 |
| `failure_mode_notes` | VARCHAR | 是 | 预期失败模式 |
| `enabled_in_v1` | BOOLEAN | 否 | 是否在 v1 启用 |
| `contract_hash` | VARCHAR | 否 | 定义 hash |
| `created_at` | TIMESTAMP | 否 | 创建时间 |

#### D.3.3 `warehouse/research/factor_preprocess_contract.parquet`

用途：
- 承载因子预处理和中性化合同

粒度：
- `factor_name, factor_version, preprocess_contract_version`

字段：

| field | type | nullable | 说明 |
|---|---|---:|---|
| `factor_name` | VARCHAR | 否 | 因子名称 |
| `factor_version` | VARCHAR | 否 | 因子版本 |
| `preprocess_contract_version` | VARCHAR | 否 | 预处理合同版本 |
| `missing_imputation_method` | VARCHAR | 否 | 默认 `none` |
| `non_finite_handling_method` | VARCHAR | 否 | 非有限值处理 |
| `winsor_method` | VARCHAR | 否 | 如 `mad_clip` |
| `winsor_param` | DOUBLE | 是 | 去极值参数 |
| `standardization_method` | VARCHAR | 否 | 如 `cross_sectional_robust_zscore` |
| `neutralization_method` | VARCHAR | 否 | `none` / `ols_residualization` |
| `neutralization_features_json` | VARCHAR | 是 | 中性化暴露集合 |
| `fit_scope` | VARCHAR | 否 | 统计量拟合范围 |
| `train_only_fit_required` | BOOLEAN | 否 | 是否只能在训练窗口拟合 |
| `notes` | VARCHAR | 是 | 备注 |
| `contract_hash` | VARCHAR | 否 | 合同 hash |

#### D.3.4 `warehouse/research/factor_preprocessed_daily.parquet`

用途：
- 记录正式启用因子的逐日预处理结果，支撑 rerun 与审计

粒度：
- `trade_date, instrument, factor_name, factor_version`

字段：

| field | type | nullable | 说明 |
|---|---|---:|---|
| `trade_date` | DATE | 否 | 交易日 |
| `instrument` | VARCHAR | 否 | 股票代码 |
| `factor_name` | VARCHAR | 否 | 因子名称 |
| `factor_version` | VARCHAR | 否 | 因子版本 |
| `snapshot_id` | VARCHAR | 否 | 数据 snapshot |
| `raw_value` | DOUBLE | 是 | 原始值 |
| `raw_missing_flag` | BOOLEAN | 否 | 原始值是否缺失 |
| `winsorized_value` | DOUBLE | 是 | 去极值后数值 |
| `standardized_value` | DOUBLE | 是 | 标准化后数值 |
| `neutralized_value` | DOUBLE | 是 | 中性化后数值 |
| `final_model_value` | DOUBLE | 是 | 最终送入模型的数值 |
| `clipped_flag` | BOOLEAN | 否 | 是否被去极值 |
| `neutralized_flag` | BOOLEAN | 否 | 是否执行中性化 |
| `preprocessing_status` | VARCHAR | 否 | `OK` / `MISSING` / `REJECTED` |

#### D.3.5 `warehouse/research/style_descriptor_daily.parquet`

用途：
- 为风险暴露与收益归因提供日频描述子

粒度：
- `trade_date, instrument`

字段：

| field | type | nullable | 说明 |
|---|---|---:|---|
| `trade_date` | DATE | 否 | 交易日 |
| `instrument` | VARCHAR | 否 | 股票代码 |
| `industry_code` | VARCHAR | 是 | 当日行业归属 |
| `log_mkt_cap` | DOUBLE | 是 | 市值描述子 |
| `beta_252d` | DOUBLE | 是 | 市场 beta |
| `realized_vol_252d` | DOUBLE | 是 | 波动率描述子 |
| `turnover_20d` | DOUBLE | 是 | 换手率描述子 |
| `amount_20d` | DOUBLE | 是 | 成交额描述子 |
| `amihud_20d` | DOUBLE | 是 | 流动性描述子 |
| `value_proxy` | DOUBLE | 是 | value 描述子 |
| `profitability_proxy` | DOUBLE | 是 | quality / profitability 描述子 |
| `investment_proxy` | DOUBLE | 是 | investment 描述子 |
| `descriptor_snapshot_id` | VARCHAR | 否 | 描述子生成所用 snapshot |

### D.4 Run 级 artifact 设计

#### D.4.1 `holdings.csv` 扩展字段

现有 `holdings.csv` 至少扩展以下字段：

| field | type | 说明 |
|---|---|---|
| `run_id` | VARCHAR | 运行主键 |
| `position_id` | VARCHAR | 单笔持仓主键 |
| `target_weight_D0` | DOUBLE | `D0` 冻结目标权重 |
| `entry_fill_weight` | DOUBLE | 实际建仓权重 |
| `terminal_event_flag` | BOOLEAN | 是否命中过终局事件 |
| `terminal_event_type` | VARCHAR | 终局事件类型 |
| `terminal_event_date` | DATE | 终局事件日期 |
| `terminal_exit_pricing_method` | VARCHAR | `cash_settlement` / `last_tradable_close` / `zero_recovery` |
| `terminal_exit_approximation_flag` | BOOLEAN | 是否使用近似终局价格 |
| `terminal_exit_conservative_flag` | BOOLEAN | 是否按 `0` 价格保守处理 |

#### D.4.2 `portfolio_weights_daily.csv`

用途：
- 审计目标权重、开盘后实际权重、收盘后实际权重

粒度：
- `run_id, trade_date, instrument`

字段：

| field | type | 说明 |
|---|---|---|
| `run_id` | VARCHAR | 运行主键 |
| `run_type` | VARCHAR | `fixed_test` / `walk_forward` / `shadow` |
| `trade_date` | DATE | 交易日 |
| `instrument` | VARCHAR | 股票代码 |
| `target_weight_D0` | DOUBLE | 冻结目标权重 |
| `opening_weight` | DOUBLE | 日初实际权重 |
| `closing_weight` | DOUBLE | 日末实际权重 |
| `entry_filled_flag` | BOOLEAN | 是否成交建仓 |
| `delayed_exit_flag` | BOOLEAN | 是否处于延迟退出状态 |

#### D.4.3 `portfolio_daily_summary.csv`

粒度：
- `run_id, trade_date`

字段：

| field | type | 说明 |
|---|---|---|
| `run_id` | VARCHAR | 运行主键 |
| `trade_date` | DATE | 交易日 |
| `cash_weight` | DOUBLE | 现金权重 |
| `invested_weight` | DOUBLE | 已投资权重 |
| `max_single_name_weight` | DOUBLE | 单票最大权重 |
| `top3_weight` | DOUBLE | 前三大持仓权重和 |
| `portfolio_herfindahl_index` | DOUBLE | 组合 HHI |
| `industry_active_weight_max` | DOUBLE | 最大行业主动权重 |

#### D.4.4 `turnover_daily.csv`

粒度：
- `run_id, trade_date`

字段：

| field | type | 说明 |
|---|---|---|
| `run_id` | VARCHAR | 运行主键 |
| `trade_date` | DATE | 交易日 |
| `buy_notional_daily` | DOUBLE | 当日买入金额 |
| `sell_notional_daily` | DOUBLE | 当日卖出金额 |
| `turnover_daily` | DOUBLE | `(buy + sell) / lag_total_equity` |
| `rebalance_event_flag` | BOOLEAN | 是否为调仓日 |

#### D.4.5 `risk_exposure_daily.csv`

粒度：
- `run_id, trade_date`

字段：

| field | type | 说明 |
|---|---|---|
| `run_id` | VARCHAR | 运行主键 |
| `trade_date` | DATE | 交易日 |
| `industry_active_weight_max` | DOUBLE | 最大行业主动权重 |
| `size_exposure_z` | DOUBLE | 市值暴露偏移 |
| `beta_exposure_z` | DOUBLE | beta 暴露偏移 |
| `volatility_exposure_z` | DOUBLE | 波动率暴露偏移 |
| `liquidity_exposure_z` | DOUBLE | 流动性暴露偏移 |
| `value_exposure_z` | DOUBLE | value 暴露偏移 |
| `profitability_exposure_z` | DOUBLE | quality / profitability 暴露偏移 |
| `investment_exposure_z` | DOUBLE | investment 暴露偏移 |

#### D.4.6 `return_attribution_daily.csv`

粒度：
- `run_id, trade_date`

字段：

| field | type | 说明 |
|---|---|---|
| `run_id` | VARCHAR | 运行主键 |
| `trade_date` | DATE | 交易日 |
| `strategy_return_daily` | DOUBLE | 策略日收益 |
| `benchmark_return_daily` | DOUBLE | benchmark 日收益 |
| `benchmark_contribution_daily` | DOUBLE | benchmark 收益贡献 |
| `cash_drag_daily` | DOUBLE | 现金拖累 |
| `selection_alpha_daily` | DOUBLE | 选股超额收益 |
| `low_liquidity_contribution_daily` | DOUBLE | 低流动性样本贡献 |
| `unexplained_return_daily` | DOUBLE | 未解释项 |

#### D.4.7 `auction_sensitivity_summary.json`

最小字段：

- `run_id`
- `baseline_annual_relative_return`
- `auction_stress_annual_relative_return`
- `entry_open_slippage_stress_bp`
- `exit_close_slippage_stress_bp`
- `auction_microstructure_sensitive`
- `one_word_board_contribution`
- `delayed_exit_sensitivity_contribution`

#### D.4.8 `research_space_audit.json`

最小字段：

- `research_round_id`
- `candidate_scheme_id`
- `run_id`
- `raw_candidate_factor_count`
- `raw_strategy_variant_count`
- `confirmatory_candidate_scheme_count`
- `validation_summary_count_generated`
- `oos_summary_count_viewed`
- `effective_trials_estimate`
- `nominal_t_stat`
- `nominal_ir`
- `dsr`
- `pbo`
- `reality_check_method`
- `research_space_adjustment_pass`

#### D.4.9 `factor_contracts.json`

最小字段：

- `snapshot_id`
- `code_hash`
- `execution_logic_version`
- `factor_name`
- `factor_version`
- `preprocess_contract_version`
- `neutralization_method`
- `winsor_method`
- `standardization_method`

### D.5 Serving 视图扩展建议

新增共享表后，建议对外暴露：

- `serving.vw_terminal_event_daily`
- `serving.vw_factor_definition_registry`
- `serving.vw_factor_preprocess_contract`
- `serving.vw_factor_preprocessed_daily`
- `serving.vw_style_descriptor_daily`

### D.6 依赖关系

- `terminal_event_daily` 依赖上市/退市、停牌、公司行为与状态层
- `factor_definition_registry` 与 `factor_preprocess_contract` 依赖研究注册流程
- `factor_preprocessed_daily` 依赖 `bars_daily`、财务 PIT、行业归属与预处理合同
- `style_descriptor_daily` 依赖 `bars_daily`、`daily_basic`、行业归属
- `risk_exposure_daily` 依赖 `portfolio_weights_daily` 与 `style_descriptor_daily`
- `return_attribution_daily` 依赖日度持仓、benchmark、低流动性标签与组合日收益
- `research_space_audit.json` 依赖治理主键、研究轮次登记、验证查看事件和正式统计结果

### D.7 最小实施顺序

1. 先实现共享仓库表：
- `terminal_event_daily`
- `factor_definition_registry`
- `factor_preprocess_contract`
- `style_descriptor_daily`

2. 再实现 run 级 artifact：
- `portfolio_weights_daily.csv`
- `portfolio_daily_summary.csv`
- `turnover_daily.csv`
- `risk_exposure_daily.csv`
- `return_attribution_daily.csv`
- `auction_sensitivity_summary.json`
- `research_space_audit.json`

3. 最后实现高成本表：
- `factor_preprocessed_daily`

制度解释：

- `factor_preprocessed_daily` 数据量最大，应该在前置 contract、run artifact 和治理链路稳定后再落地
- 其余表先落地，就已经足以支撑大多数新增条款的审计要求

## 附录 E：字段单位字典

本文对“字段单位”的治理目标不是追求百科全书式罗列，而是保证：

- 共享数据源当前正式 `serving` 视图的关键字段量纲明确
- 本项目当前实际运行、评估、审计字段的量纲明确
- 未来程序读取时有稳定、机器可读的单位字典

本附录本身就是字段单位的权威人类可读版本，后续即使外部审查稿或机器导出文件被删除，也不影响总纲的完整性。

如需程序直接读取，可在项目内额外维护 `JSON / CSV` 副本，但这些副本只是导出镜像，不是本总纲的必要依赖。

### E.1 核心量纲规则

以下规则在 `v1` 中固定：

- `daily/index_daily` 的 `amount` 单位为 `千元`
- `daily/index_daily` 的 `vol` 单位为 `手`
- `daily_basic.total_mv/circ_mv` 单位为 `万元`
- `daily_basic.total_share/float_share/free_share` 单位为 `万股`
- 共享层和项目侧绝大多数 `*_return`、`label_*`、`daily_return`、`annual_relative_return` 字段都使用**小数收益率**
- 项目侧绝大多数 `*_weight` 字段都使用 `0-1` 组合权重，而不是百分数字符串或人民币金额

### E.2 共享视图量纲摘要

当前项目正式消费的共享视图，量纲固定为：

- `serving.vw_calendar`
  - 日期字段：`YYYYMMDD`
- `serving.vw_instruments_main_chinext`
  - 代码 / 文本 / 日期，无数值量纲
- `serving.vw_bars_daily`
  - `open/high/low/close/pre_close/change`：元/股
  - `pct_chg`：`%`
  - `vol`：手
  - `amount`：千元
  - `adj_factor`：无量纲
  - `turnover_rate/turnover_rate_f`：`%`
  - `volume_ratio`：比值
  - `total_mv/circ_mv`：万元
  - `adj_open/adj_high/adj_low/adj_close`：历史兼容字段，在本项目中解释为 `adj_open_base/adj_high_base/adj_low_base/adj_close_base`，量纲仍按元/股理解
- `serving.vw_benchmark_daily` / `serving.vw_benchmark_aux_daily`
  - `close`：指数点位
  - `daily_return`：小数收益率
- `serving.vw_limit_rules_daily`
  - 涨跌停价格与最小价格刻度：元/股
- `serving.vw_tradability_daily`
  - 可交易性、状态和降级字段：布尔 / 文本
  - `low_liquidity_flag_t`：基于 `amount` 的布尔审计字段；若定义为“低于 500 万元”，则阈值应为 `5_000`
- `serving.vw_labels_daily`
  - `open_D1/close_D5`：元/股
  - `adj_factor_*`：无量纲
  - `adj_open_base_D1/adj_close_base_D5`：元/股
  - `label_5d_next_open_close*`：小数收益率
- `serving.vw_execution_path_daily`
  - `actual_sell_price`：元/股
  - `exit_delay_days`：天数
  - `execution_delayed_realized_return`：小数收益率
- `serving.vw_sample_eligibility_daily`
  - 日期、布尔与 JSON 文本，不承载金额或价格量纲

### E.3 本项目字段量纲摘要

本项目当前核心字段量纲固定为：

- `project_label_panel`
  - 价格字段：元/股
  - `adj_factor_*`：无量纲
  - 标签字段：小数收益率
- `project_execution_panel`
  - `actual_sell_price`：元/股
  - `exit_delay_days`：天数
  - `execution_delayed_realized_return`：小数收益率
- `model_scores_D0`
  - `model_score_D0`：无量纲分数
  - `*_rank`：`[0,1]` 百分位 rank
- `ranking_state_daily` / `execution_state_daily`
  - `target_weight_D0`：`0-1` 权重
  - 排名与阈值：名次 / 个数
- 组合层和 fixed test
  - `cash_weight/invested_weight/entry_fill_weight/opening_weight/closing_weight`：`0-1` 权重
  - `portfolio_daily_return/benchmark_return_daily/relative_return_daily`：小数收益率
  - `stress_open_bp/stress_close_bp`：基点（bp）

### E.4 基本面 PIT 层量纲规则

当前基本面 PIT 层按下述规则使用：

- `fina_indicator_pit`
  - 元数据字段：
    - `snapshot_id`：字符串
    - `ts_code`：代码
    - `ann_date/end_date/pit_available_date`：日期字符串 `YYYYMMDD`
  - `eps/*_ps`：元/股
  - `gross_margin/roe/*_yoy/*_qoq`：百分比口径
  - `current_ratio/quick_ratio/cash_ratio/assets_turn`：倍 / 次 / 比值
- `financial_statement_raw_pit`
  - 元数据与日期字段：字符串 / 日期
  - `basic_eps/diluted_eps`：元/股
  - `total_share`：股本数量字段
  - `cap_rese/money_cap/total_assets/total_liab/revenue/total_revenue/operate_profit/total_profit/n_income/net_profit/n_cashflow_act/free_cashflow/end_bal_cash/end_bal_cash_equ` 等三大报表行项目：默认按金额字段（元）理解
  - 其余三大报表行项目默认按金额字段（元）理解；若某个具体字段在研究中被单独使用，允许再做字段级二次核验，但不得在未经说明的情况下混用万元、千元和元

### E.5 使用纪律

- 任何涉及 `amount`、`market value`、`share count` 的跨表运算，必须先统一量纲
- 任何涉及收益汇报的表或图，必须明确写清“当前字段是小数收益率还是百分数展示值”
- 任何新增共享视图或项目侧 artifact，如引入新的金额 / 价格 / 权重字段，都必须同步补入本附录，并在需要时再导出机器字典副本
