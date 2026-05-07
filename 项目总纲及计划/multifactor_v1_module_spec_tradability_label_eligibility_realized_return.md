# 多因子项目 v1 模块规格书

模块：
- `tradability + 标签 + 样本资格矩阵 + 真实清算收益`

用途：
- 将 `/Users/wy/MiscProject/multi_factor/项目总纲及计划/项目总纲/new_multifactor_project_framework_v1.md` 与 `/Users/wy/MiscProject/multi_factor/项目总纲及计划/multifactor_v1_execution_plan.md` 中关于下周期第一实现模块的制度要求，翻译成可直接编码的工程规格
- 本文只定义输入、输出、字段、主键、计算顺序、边界样本处理与验收标准，不包含实现代码

权威关系：
- 总纲负责制度边界
- 实施计划负责优先级与阶段安排
- 本规格书负责该模块的可编码定义
- 若本规格书与总纲冲突，以总纲为准

适用版本：
- `v1`
- 截至 `2026-04-13`

---

## 1. 对应条款

本模块直接对应：

- 总纲 `3.1 ~ 3.5`：统一执行语义与 `tradability`
- 总纲 `4.1 ~ 4.4A`：主标签、样本资格矩阵、不可买样本处理、真实清算、终局事件
- 总纲 `5.1A`：独立数据源与 `snapshot_id` 绑定
- 实施计划 `4`：下周期首批实现名单的第 `1` 步

---

## 2. 模块边界

本模块负责：

- 生成正式 `tradability` 日频权威字段
- 生成 `D0 -> D1 -> D5` 锚定后的固定窗口标签
- 生成样本资格矩阵
- 生成实际退出路径与真实清算收益
- 为后续 `TopK + 现金保留 + 不补位`、`holdings.csv`、fixed test、`walk-forward` 提供稳定输入

本模块不负责：

- 排序建仓
- `TopK` 冻结
- 组合权重分配
- 交易成本扣减
- fixed test 汇总报告
- `walk-forward` 编排
- 因子预处理与模型训练

---

## 3. 数据源与运行主键

### 3.1 数据源约束

- 开发检查可读取 `/Users/wy/MiscProject/tushare_data/parquet_duckdb/data/current`
- 正式运行必须绑定 `/Users/wy/MiscProject/tushare_data/parquet_duckdb/data/snapshots/<snapshot_id>`
- 所有输出都必须记录 `snapshot_id`

### 3.2 运行主键

本模块输出至少绑定以下主键：

- `snapshot_id`
- `git_commit_hash`
- `git_dirty_flag`
- `git_diff_hash`
- `config_hash`
- `data_contract_hash`
- `execution_logic_hash`
- `factor_contract_hash`
- `environment_manifest_hash`
- `execution_logic_version`
- `run_id`

其中：

- 研究准备阶段可用临时 `run_id`
- 进入 fixed test / `walk-forward` / shadow tracking 后，`run_id` 必须替换为正式运行主键

---

## 4. 输入表

### 4.1 必需输入表

优先通过 DuckDB `serving` 视图读取：

- `serving.vw_calendar`
- `serving.vw_instruments_main_chinext`
- `serving.vw_bars_daily`
- `serving.vw_limit_rules_daily`
- `serving.vw_instrument_status_daily`
- `serving.vw_terminal_event_daily`

### 4.2 输入字段最低要求

#### 4.2.1 `vw_calendar`

最低字段：

- `trade_date`
- `next_trade_date_1`
- `next_trade_date_5`

若物理表未直接提供 `next_trade_date_1 / 5`，则必须由交易日历稳定派生。

#### 4.2.2 `vw_instruments_main_chinext`

最低字段：

- `trade_date`
- `instrument`
- `base_universe_member_flag`

#### 4.2.3 `vw_bars_daily`

最低字段：

- `trade_date`
- `instrument`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `amount`
- `adj_factor`
- `amount` 的单位固定为 `千元`
- `low_liquidity_amount_threshold_k_yuan = 5000` 表示低于 `500` 万元成交额

#### 4.2.4 `vw_limit_rules_daily`

最低字段：

- `trade_date`
- `instrument`
- `up_limit_price`
- `down_limit_price`

#### 4.2.5 `vw_instrument_status_daily`

最低字段：

- `trade_date`
- `instrument`
- `is_listed`
- `is_suspended`
- `is_st`
- `delisting_flag`

#### 4.2.6 `vw_terminal_event_daily`

最低字段：

- `trade_date`
- `instrument`
- `terminal_event_flag`
- `terminal_event_type`
- `terminal_event_date`
- `last_tradable_date`
- `cash_settlement_available`
- `cash_settlement_amount`
- `zero_recovery_recommended`

---

## 5. 输出表

本模块默认产出 4 张表。

### 5.1 `warehouse/market/tradability_daily.parquet`

用途：
- 作为研究层、执行层、影子跟踪共用的日频 `tradability` 权威表

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
| `is_listed` | BOOLEAN | 否 | 当日是否上市 |
| `is_suspended` | BOOLEAN | 否 | 当日是否停牌 |
| `no_trade` | BOOLEAN | 否 | `volume <= 0 or amount <= 0` |
| `low_liquidity_flag` | BOOLEAN | 否 | `amount < low_liquidity_amount_threshold_k_yuan` |
| `up_limit_price` | DOUBLE | 是 | 涨停价 |
| `down_limit_price` | DOUBLE | 是 | 跌停价 |
| `open_at_up_limit` | BOOLEAN | 否 | 开盘是否触及涨停 |
| `open_at_down_limit` | BOOLEAN | 否 | 开盘是否触及跌停 |
| `close_at_down_limit` | BOOLEAN | 否 | 收盘是否触及跌停 |
| `one_word_up_limit` | BOOLEAN | 否 | 一字涨停 |
| `one_word_down_limit` | BOOLEAN | 否 | 一字跌停 |
| `entry_buyable_open` | BOOLEAN | 否 | 对应总纲 `entry_buyable_D1_open` 的日频版 |
| `exit_sellable_close` | BOOLEAN | 否 | 对应总纲 `exit_sellable_D5_close` 的日频版 |
| `sellable_retry_next_open` | BOOLEAN | 否 | 对应总纲 `sellable_retry_next_open` 的日频版 |
| `tradability_rule_complete_flag` | BOOLEAN | 否 | 关键字段是否齐备 |
| `tradability_degraded_flag` | BOOLEAN | 否 | 是否因缺字段降级 |
| `tradability_degraded_reason` | VARCHAR | 是 | 缺失原因 |
| `snapshot_id` | VARCHAR | 否 | 数据快照 |
| `execution_logic_version` | VARCHAR | 否 | 执行语义版本 |

### 5.2 `warehouse/research/label_5d_daily.parquet`

用途：
- 记录 `D0` 锚定后的正式标签与标签可用性

粒度：
- `signal_date, instrument`

主键：
- `signal_date`
- `instrument`

字段：

| field | type | nullable | 说明 |
|---|---|---:|---|
| `signal_date` | DATE | 否 | `D0` |
| `instrument` | VARCHAR | 否 | 股票代码 |
| `entry_date` | DATE | 是 | `D1` |
| `planned_exit_date` | DATE | 是 | `D5` |
| `open_D1` | DOUBLE | 是 | 入场开盘价 |
| `close_D5` | DOUBLE | 是 | 计划退出收盘价 |
| `adj_factor_D1` | DOUBLE | 是 | `D1` 复权因子 |
| `adj_factor_D5` | DOUBLE | 是 | `D5` 复权因子 |
| `adj_open_base_D1` | DOUBLE | 是 | `open_D1 * adj_factor_D1` |
| `adj_close_base_D5` | DOUBLE | 是 | `close_D5 * adj_factor_D5` |
| `label_price_defined` | BOOLEAN | 否 | 价格层面的理论标签是否可计算 |
| `label_5d_next_open_close_raw` | DOUBLE | 是 | 理论固定窗口标签 |
| `label_usable_for_training` | BOOLEAN | 否 | 是否可用于主训练 / 主评估 |
| `label_training_value` | DOUBLE | 是 | 主训练 / 主评估口径标签；不可买样本记 `NaN` |
| `label_5d_next_open_close` | DOUBLE | 是 | 历史兼容 alias；若保留只能等于 `label_training_value` |
| `entry_tradeable` | BOOLEAN | 否 | `D1` 开盘可买 |
| `label_masked_reason` | VARCHAR | 是 | `ENTRY_NOT_TRADABLE` / `MISSING_PRICE` / `MISSING_ADJ` |
| `snapshot_id` | VARCHAR | 否 | 数据快照 |

### 5.3 `warehouse/research/sample_eligibility_daily.parquet`

用途：
- 记录总纲 `4.2` 定义的样本资格矩阵

粒度：
- `signal_date, instrument`

主键：
- `signal_date`
- `instrument`

字段：

| field | type | nullable | 说明 |
|---|---|---:|---|
| `signal_date` | DATE | 否 | `D0` |
| `instrument` | VARCHAR | 否 | 股票代码 |
| `entry_date` | DATE | 是 | `D1` |
| `planned_exit_date` | DATE | 是 | `D5` |
| `label_price_defined` | BOOLEAN | 否 | 价格层面的理论标签可计算 |
| `entry_tradeable` | BOOLEAN | 否 | `D1` 可买 |
| `planned_exit_tradeable` | BOOLEAN | 否 | `D5` 收盘可卖 |
| `actually_exited` | BOOLEAN | 否 | 是否找到最终退出事件 |
| `label_usable_for_training` | BOOLEAN | 否 | 主训练 / 主评估口径样本资格 |
| `label_training_value` | DOUBLE | 是 | 主训练 / 主评估口径标签值 |
| `feature_ready_D0` | BOOLEAN | 否 | 特征准备完毕 |
| `price_window_ready_D0` | BOOLEAN | 否 | 价格窗口完备 |
| `core_features_complete_D0` | BOOLEAN | 否 | 核心特征完备 |
| `pit_state_complete_D0` | BOOLEAN | 否 | PIT 状态完备 |
| `universe_eligible_D0` | BOOLEAN | 否 | 宇宙合格 |
| `base_universe_member_D0` | BOOLEAN | 否 | 基础宇宙成员 |
| `rules_filter_pass_D0` | BOOLEAN | 否 | 静态规则过滤通过 |
| `state_filter_pass_D0` | BOOLEAN | 否 | 状态过滤通过 |
| `signal_emittable` | BOOLEAN | 否 | 可出信号 |
| `ranking_eligible_D0` | BOOLEAN | 否 | 可参与排序 |
| `topk_frozen_D0` | BOOLEAN | 否 | 初始默认 `false`，由下游填写 |
| `execution_attempt_D1` | BOOLEAN | 否 | 初始默认 `false`，由下游填写 |
| `entry_filled_D1` | BOOLEAN | 否 | 初始默认 `false`，由下游填写 |
| `backtest_executable` | BOOLEAN | 否 | 初始默认 `false`，由下游填写 |
| `audit_included` | BOOLEAN | 否 | 审计是否保留 |
| `train_mask_v1` | BOOLEAN | 否 | 主训练口径 |
| `eval_mask_v1` | BOOLEAN | 否 | 主评估口径 |
| `train_mask_conservative` | BOOLEAN | 否 | 保守训练口径 |
| `eval_mask_conservative` | BOOLEAN | 否 | 保守评估口径 |
| `mask_reason_json` | VARCHAR | 是 | 各类 mask 的置 false 原因 |
| `snapshot_id` | VARCHAR | 否 | 数据快照 |

### 5.4 `warehouse/research/execution_path_daily.parquet`

用途：
- 记录计划退出、延迟退出、终局事件处理与真实清算收益

粒度：
- `signal_date, instrument`

主键：
- `signal_date`
- `instrument`

字段：

| field | type | nullable | 说明 |
|---|---|---:|---|
| `signal_date` | DATE | 否 | `D0` |
| `instrument` | VARCHAR | 否 | 股票代码 |
| `entry_date` | DATE | 是 | `D1` |
| `planned_exit_date` | DATE | 是 | `D5` |
| `actual_exit_date` | DATE | 是 | 实际退出日 |
| `actual_exit_event_type` | VARCHAR | 是 | `D5_CLOSE` / `RETRY_OPEN` / `TERMINAL_CASH` / `TERMINAL_LAST_CLOSE` / `TERMINAL_ZERO` / `UNRESOLVED` |
| `actual_exit_price_field` | VARCHAR | 是 | `close` / `open` / `cash_settlement_amount` / `last_tradable_close` / `zero` |
| `actual_sell_price` | DOUBLE | 是 | 实际退出名义价格 |
| `adj_factor_actual_exit` | DOUBLE | 是 | 实际退出日复权因子 |
| `adj_sell_base_actual_exit` | DOUBLE | 是 | `actual_sell_price * adj_factor_actual_exit` |
| `exit_delay_days` | INTEGER | 是 | 相对 `planned_exit_date` 的延迟天数 |
| `actually_exited` | BOOLEAN | 否 | 是否成功定价退出 |
| `execution_delayed_realized_return` | DOUBLE | 是 | 真实清算收益 |
| `terminal_event_flag` | BOOLEAN | 否 | 是否命中过终局事件 |
| `terminal_event_type` | VARCHAR | 是 | 终局事件类型 |
| `terminal_event_date` | DATE | 是 | 终局事件日 |
| `terminal_exit_pricing_method` | VARCHAR | 是 | `cash_settlement` / `last_tradable_close` / `zero_recovery` |
| `terminal_exit_approximation_flag` | BOOLEAN | 否 | 是否近似定价 |
| `terminal_exit_conservative_flag` | BOOLEAN | 否 | 是否保守归零 |
| `execution_path_status` | VARCHAR | 否 | `PLANNED_EXIT` / `DELAYED_EXIT` / `TERMINAL_EXIT` / `OPEN_UNRESOLVED` / `NO_ENTRY` |
| `snapshot_id` | VARCHAR | 否 | 数据快照 |
| `execution_logic_version` | VARCHAR | 否 | 执行语义版本 |

---

## 6. 规范化实现约定

为消除总纲文字中的实现歧义，本规格书固定以下工程约定：

1. `label_price_defined` 只表示价格层面的理论标签可计算，不表示样本可用于训练
- 即：`open_D1`、`close_D5`、`adj_factor_D1`、`adj_factor_D5` 均存在时，`label_price_defined = true`

2. 不可买样本保留理论标签，但主训练 / 主评估标签置空
- `label_5d_next_open_close_raw` 保留理论值
- `label_training_value` 在 `entry_tradeable = false` 时写为 `NaN`
- 若实现层保留历史兼容字段 `label_5d_next_open_close`，其值只能等于 `label_training_value`
- 这样同时满足总纲 `4.2` 的理论可计算定义和 `4.3` 的不可买样本屏蔽要求

3. `sample_eligibility_daily` 是训练 / 评估 / 审计的唯一 mask 权威表
- 训练、验证、固定测试统计均不得绕过该表自行拼 mask

4. `execution_path_daily` 是真实清算收益的唯一权威表
- 后续 `holdings.csv`、组合日报、fixed test 报告只能引用这里的退出事件与真实清算字段

---

## 7. 计算顺序

### Step 1. 锚定 `D0 / D1 / D5`

对每个 `signal_date = D0`、`instrument`：

- 从交易日历得到 `entry_date = next_trade_date_1(D0)`
- 从交易日历得到 `planned_exit_date = next_trade_date_5(D0)`

若 `D1` 或 `D5` 超出可用交易日历范围：

- `label_price_defined = false`
- `label_5d_next_open_close_raw = null`
- `label_usable_for_training = false`
- `label_training_value = NaN`
- `entry_tradeable = false`
- `execution_path_status = OPEN_UNRESOLVED`

### Step 2. 生成日频 `tradability_daily`

对每个 `trade_date, instrument`：

- 读取状态层、行情、涨跌停规则
- 统一按 `Decimal + ROUND_HALF_UP` 判断边界价格
- 计算：
  - `no_trade`
  - `low_liquidity_flag`
  - `open_at_up_limit`
  - `open_at_down_limit`
  - `close_at_down_limit`
  - `one_word_up_limit`
  - `one_word_down_limit`
  - `entry_buyable_open`
  - `exit_sellable_close`
  - `sellable_retry_next_open`

若买卖判断所需关键字段缺失：

- `tradability_rule_complete_flag = false`
- `tradability_degraded_flag = true`
- `tradability_degraded_reason` 写明缺失字段

### Step 3. 生成标签表

对每个 `signal_date, instrument`：

- 关联 `D1` 与 `D5` 的行情和复权因子
- 计算：
  - `adj_open_base_D1 = open_D1 * adj_factor_D1`
  - `adj_close_base_D5 = close_D5 * adj_factor_D5`
  - `label_5d_next_open_close_raw = adj_close_base_D5 / adj_open_base_D1 - 1`
- `label_price_defined = true` 的条件：
  - `open_D1` 非空
  - `close_D5` 非空
  - `adj_factor_D1` 非空
  - `adj_factor_D5` 非空

随后根据 `entry_tradeable` 生成主训练 / 主评估标签：

- `label_usable_for_training = label_price_defined & entry_tradeable`
- 若 `label_usable_for_training = false`，则 `label_training_value = NaN`
- 若 `label_usable_for_training = true`，则 `label_training_value = label_5d_next_open_close_raw`
- 若实现层保留 `label_5d_next_open_close`，则其值只能等于 `label_training_value`

### Step 4. 生成样本资格矩阵

按总纲 `4.2` 固定以下逻辑：

- `entry_tradeable = tradability_daily[D1].entry_buyable_open`
- `planned_exit_tradeable = tradability_daily[D5].exit_sellable_close`
- `feature_ready_D0 = price_window_ready_D0 & core_features_complete_D0 & pit_state_complete_D0`
- `universe_eligible_D0 = base_universe_member_D0 & rules_filter_pass_D0 & state_filter_pass_D0`
- `signal_emittable = feature_ready_D0 & universe_eligible_D0`
- `ranking_eligible_D0 = signal_emittable`
- `topk_frozen_D0 = false`
- `execution_attempt_D1 = false`
- `entry_filled_D1 = false`
- `backtest_executable = false`
- `audit_included = signal_emittable`
- `label_usable_for_training = label_price_defined & entry_tradeable`
- `train_mask_v1 = label_usable_for_training`
- `eval_mask_v1 = label_usable_for_training`
- `train_mask_conservative = label_price_defined & entry_tradeable & planned_exit_tradeable`
- `eval_mask_conservative = label_price_defined & entry_tradeable & planned_exit_tradeable`

说明：

- 本模块只生成下游可填充前的默认值
- `topk_frozen_D0 / execution_attempt_D1 / entry_filled_D1 / backtest_executable` 在本模块阶段只应为占位字段，不应抢先推断

### Step 5. 生成实际退出路径

仅对满足以下条件的样本计算真实清算路径：

- `label_price_defined = true`
- `entry_tradeable = true`

退出逻辑固定为：

1. 若 `D5` 收盘 `exit_sellable_close = true`
- `actual_exit_date = planned_exit_date`
- `actual_exit_event_type = D5_CLOSE`
- `actual_exit_price_field = close`
- `actual_sell_price = close_D5`

2. 若 `D5` 收盘不可卖
- 从 `planned_exit_date` 之后的每个交易日按时间顺序搜索
- 只检查该日开盘 `sellable_retry_next_open`
- 找到首个可卖日后：
  - `actual_exit_date = t`
  - `actual_exit_event_type = RETRY_OPEN`
  - `actual_exit_price_field = open`
  - `actual_sell_price = open_t`

3. 若延迟搜索过程中命中终局事件且在终局前不存在可卖时点
- 按总纲 `4.4A` 的价格层级定价：
  - 优先 `cash_settlement_amount`
  - 其次 `last_tradable_close`
  - 最后 `0`

### Step 6. 计算真实清算收益

若 `actual_exit_date` 与 `actual_sell_price` 已定：

- `adj_sell_base_actual_exit = actual_sell_price * adj_factor_actual_exit`
- `execution_delayed_realized_return = adj_sell_base_actual_exit / adj_open_base_D1 - 1`
- `exit_delay_days = trading_day_count(planned_exit_date, actual_exit_date) - 1`

若 `entry_tradeable = false`：

- `execution_path_status = NO_ENTRY`
- `actual_exit_date = null`
- `execution_delayed_realized_return = null`

若到 snapshot 末端仍未找到可卖或终局定价依据：

- `execution_path_status = OPEN_UNRESOLVED`
- `actual_exit_event_type = UNRESOLVED`
- `actual_exit_date = null`
- `execution_delayed_realized_return = null`

---

## 8. 边界样本处理

### 8.1 `D1` 不可买

处理规则：

- 保留 `label_5d_next_open_close_raw`
- `label_training_value = NaN`
- `train_mask_v1 / eval_mask_v1 / conservative masks = false`
- `execution_path_status = NO_ENTRY`
- 该样本仍保留在 `sample_eligibility_daily` 与标签表中

### 8.2 `D5` 不可卖但后续开盘可卖

处理规则：

- `planned_exit_tradeable = false`
- 搜索首个后续可卖开盘
- `execution_path_status = DELAYED_EXIT`
- 真实清算收益按实际退出日计算

### 8.3 长期停牌 / 退市 / 终止上市

处理规则：

- 不允许静默删样本
- 必须写出 `terminal_event_flag`
- 若终局前无可卖时点，按 `cash_settlement -> last_tradable_close -> zero` 顺序定价
- 使用第 2 或第 3 层级时必须打近似或保守标记

### 8.4 缺失行情或复权因子

处理规则：

- 若 `open_D1 / close_D5 / adj_factor_D1 / adj_factor_D5` 任一缺失：
  - `label_price_defined = false`
  - `label_5d_next_open_close_raw = null`
  - `label_training_value = NaN`
  - 主 / 保守 mask 全部置 false

### 8.5 `tradability` 关键字段缺失

处理规则：

- 不得静默当作可交易
- 相关买卖布尔字段统一置 `false`
- `tradability_degraded_flag = true`
- 本轮运行必须可被上层审计识别为降级结果

### 8.6 snapshot 末端仍未退出

处理规则：

- 记录为 `OPEN_UNRESOLVED`
- 不得伪造退出价格
- 该样本保留在审计集合中

---

## 9. 验收标准

### 9.1 结构验收

- 4 张表都能稳定落地
- 主键唯一，无重复行
- 每张表都带 `snapshot_id`
- `execution_path_daily` 带 `execution_logic_version`

### 9.2 逻辑验收

- `entry_tradeable` 只能来自 `tradability_daily`
- `train_mask_v1 / eval_mask_v1` 与总纲逻辑一致
- 不可买样本不会被静默删除
- 延迟退出样本能正确搜索首个后续可卖开盘
- 终局事件样本能回溯到唯一的定价方法

### 9.3 一致性验收

- 同一 `snapshot_id + git_commit_hash + git_dirty_flag + git_diff_hash + config_hash + data_contract_hash + execution_logic_hash + factor_contract_hash + environment_manifest_hash + execution_logic_version` rerun 输出完全一致
- `label_training_value` 与 `execution_delayed_realized_return` 共用同一套 base-adjusted 价格口径
- 下游 `holdings.csv` 不得重算真实清算收益，只能引用 `execution_path_daily`

### 9.4 审计验收

- 能统计 `label_price_defined` 覆盖率
- 能统计 `label_usable_for_training` 覆盖率
- 能统计 `entry_tradeable` 覆盖率
- 能统计 `planned_exit_tradeable` 覆盖率
- 能统计延迟退出占比
- 能统计终局事件样本数与占比
- 能统计 `tradability_degraded_flag` 为真的样本数

---

## 10. 非目标

以下内容明确不属于本模块首版实施范围：

- 订单簿级成交模拟
- 组合层权重与现金管理
- 成本扣减后的组合净值
- 风险暴露与收益归因
- `DSR` / `PBO` / `White Reality Check / SPA`
- 树模型与复杂模型训练

---

## 11. 建议实现顺序

建议开发顺序固定为：

1. 先做 `tradability_daily`
2. 再做 `label_5d_daily`
3. 再做 `sample_eligibility_daily`
4. 最后做 `execution_path_daily`

原因：

- `tradability_daily` 是后面 3 张表的共同依赖
- 标签与样本资格必须先稳定，真实清算收益才能避免口径漂移
- 真实清算路径依赖边界样本处理，是本模块中最容易出错的一层
