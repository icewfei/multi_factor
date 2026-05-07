# 共享数据源与本项目字段单位审查

更新时间：2026-04-18  
审查范围：

- 共享数据源 `/Users/wy/MiscProject/tushare_data/parquet_duckdb` 当前正式 `serving` 视图
- 本项目 `/Users/wy/MiscProject/multi_factor` 当前实际消费和产出的核心字段
- Tushare Pro 官方口径核对以当前项目真正用到的字段为主，不追求一次性穷举所有财报原始行项目

## 一、结论先看

这次审查最重要的结论有 6 条：

1. `daily/index_daily/fund_daily` 一类行情接口中的 `amount` 单位是 `千元`
2. `daily/index_daily` 中 `vol` 单位是 `手`
3. `daily_basic` 中 `total_mv/circ_mv` 单位是 `万元`
4. `daily_basic` 中 `total_share/float_share/free_share` 单位是 `万股`
5. 本项目大多数收益字段都使用 `小数收益率`，不是百分数
   - 例如 `0.05 = 5%`
6. 本项目大多数权重字段都使用 `0-1` 的组合权重，不是百分数
   - 例如 `0.10 = 10%`

## 二、官方来源

本次主要核对的官方来源：

- [A股日线行情 `daily`](https://tushare.pro/document/2?doc_id=27)
- [每日指标 `daily_basic`](https://tushare.pro/document/2?doc_id=32)
- [股票列表 `stock_basic`](https://tushare.pro/document/2?doc_id=25)
- [复权因子 `adj_factor`](https://tushare.pro/document/2?doc_id=28)
- [每日涨跌停价格 `stk_limit`](https://tushare.pro/document/2?doc_id=183)
- [指数日线行情 `index_daily`](https://tushare.pro/document/2?doc_id=95)
- [指数成分和权重 `index_weight`](https://tushare.pro/document/2?doc_id=96)
- [财务指标 `fina_indicator`](https://tushare.pro/document/2?doc_id=79)
- [利润表 `income`](https://tushare.pro/document/2?doc_id=33)
- [资产负债表 `balancesheet`](https://tushare.pro/document/2?doc_id=36)
- [现金流量表 `cashflow`](https://tushare.pro/document/2?doc_id=44)
- [个股资金流向 `moneyflow`](https://tushare.pro/document/2?doc_id=170)

## 三、Tushare 原始字段单位

### 1. `stock_basic`

| 字段 | 单位 / 类型 | 说明 |
|---|---|---|
| `ts_code` | 代码 | 无量纲 |
| `symbol` | 代码 | 无量纲 |
| `name/fullname/enname/cnspell` | 文本 | 无量纲 |
| `area/industry/market/exchange/curr_type/list_status/is_hs/act_name/act_ent_type` | 枚举 / 文本 | 无量纲 |
| `list_date/delist_date` | 日期字符串 `YYYYMMDD` | 无量纲 |

说明：

- `stock_basic` 基本不承载数值量纲字段
- 官方也明确：旧版里的 `PE/PB/股本` 等字段要去 `daily_basic` 拿

### 2. `daily`

| 字段 | 单位 | 说明 |
|---|---|---|
| `open/high/low/close/pre_close/change` | 元/股 | A股价格口径 |
| `pct_chg` | `%` | 官方直接定义为涨跌幅 |
| `vol` | 手 | 官方直接定义 |
| `amount` | 千元 | 官方直接定义 |

### 3. `daily_basic`

| 字段 | 单位 | 说明 |
|---|---|---|
| `close` | 元/股 | 当日收盘价 |
| `turnover_rate/turnover_rate_f` | `%` | 换手率 |
| `volume_ratio` | 比值 | 无量纲 |
| `pe/pe_ttm/pb/ps/ps_ttm/pcf_ncf_ttm` | 倍 / 比值 | 无量纲估值倍数 |
| `dv_ratio/dv_ttm` | `%` | 股息率 |
| `total_share/float_share/free_share` | 万股 | 官方直接定义 |
| `total_mv/circ_mv` | 万元 | 官方直接定义 |

### 4. `adj_factor`

| 字段 | 单位 | 说明 |
|---|---|---|
| `adj_factor` | 复权因子 | 无量纲 |

### 5. `stk_limit`

| 字段 | 单位 | 说明 |
|---|---|---|
| `pre_close/up_limit/down_limit` | 元/股 | 股票价格口径 |

### 6. `index_daily`

| 字段 | 单位 | 说明 |
|---|---|---|
| `close/open/high/low/pre_close/change` | 指数点位 | 不是元 |
| `pct_chg` | `%` | 指数涨跌幅 |
| `vol` | 手 | 官方直接定义 |
| `amount` | 千元 | 官方直接定义 |

### 7. `index_weight`

| 字段 | 单位 | 说明 |
|---|---|---|
| `weight` | 权重 | 官方只写“权重”，未明确单位 |

说明：

- 从官方样例看，沪深300成分股 `weight` 常见值如 `0.8656`、`1.1330`
- 结合指数成分权重习惯，更合理的解释是：**百分比权重点数**，总和接近 `100`
- 这一条是**基于样例和行业习惯的推断**，不是官网显式写死

### 8. `moneyflow`

| 字段 | 单位 | 说明 |
|---|---|---|
| `*_vol` | 手 | 官方直接定义 |
| `*_amount` | 万元 | 官方直接定义 |

### 9. 财报和财务指标

#### `fina_indicator`

| 字段 | 单位 | 说明 |
|---|---|---|
| `eps/dt_eps/total_revenue_ps/revenue_ps/capital_rese_ps/surplus_rese_ps/undist_profit_ps` | 元/股 | “每股”口径 |
| `gross_margin` | `%` 或毛利率口径 | 官方写“毛利”，实务上按毛利率理解时应视为百分比口径使用，使用前建议复核样本值 |
| `current_ratio/quick_ratio/cash_ratio/assets_turn` | 倍 / 次 / 比值 | 无量纲 |
| `roe/roe_dt/roa_yearly/q_roe/q_dt_roe` | `%` 或收益率口径 | 建议按百分比理解，使用前核对样本值 |
| `q_sales_yoy/q_op_qoq/netprofit_yoy/dt_netprofit_yoy` | `%` | 同比 / 环比增长率 |

#### `income / balancesheet / cashflow`

这三张表的原始行项目很多，**不适合在这里假装一次性写全并保证 100% 无误**。当前可以安全确认的是：

- `ann_date/f_ann_date/end_date`：日期字符串
- `report_type/comp_type/end_type`：枚举
- `basic_eps/diluted_eps` 一类：元/股
- `revenue/total_revenue/net_profit/money_cap/n_cashflow_act` 一类金额字段：
  - 官方在三大报表文档里大多未在每一列旁边重复写单位
  - 但按 Tushare A 股财报接口习惯，应按 **金额字段** 使用
  - 若你后续要直接使用某个具体原始财报字段，建议针对该字段二次核文档或样本值

结论：

- 当前项目还没有直接消费这些 `financial_statement_raw_pit` 行项目
- 若后面要大规模使用基本面原始字段，建议再单独做一版：
  - `balancesheet/income/cashflow/fina_indicator` 字段级单位字典

## 四、共享数据源 `serving` 视图字段单位

以下是当前项目真正消费的共享视图。

### 1. `serving.vw_calendar`

| 字段 | 单位 / 类型 |
|---|---|
| `trade_date/prev_trade_date/next_trade_date/next_trade_date_1/next_trade_date_5` | 日期字符串 `YYYYMMDD` |

### 2. `serving.vw_instruments_main_chinext`

| 字段 | 单位 / 类型 |
|---|---|
| `ts_code/symbol/name/board/list_status/...` | 代码 / 文本 / 枚举 |
| `list_date/delist_date` | 日期字符串 |

### 3. `serving.vw_bars_daily`

| 字段 | 单位 |
|---|---|
| `open/high/low/close/pre_close/change` | 元/股 |
| `pct_chg` | `%` |
| `vol` | 手 |
| `amount` | 千元 |
| `adj_factor` | 无量纲 |
| `turnover_rate/turnover_rate_f` | `%` |
| `volume_ratio` | 比值 |
| `total_mv/circ_mv` | 万元 |
| `adj_open/adj_high/adj_low/adj_close` | 复权价格口径，量纲仍按“元/股”理解 |

说明：

- `adj_* = 原始价格 × adj_factor`
- 因为 `adj_factor` 无量纲，所以 `adj_*` 仍然是价格量纲

### 4. `serving.vw_benchmark_daily` / `serving.vw_benchmark_aux_daily`

| 字段 | 单位 |
|---|---|
| `close` | 指数点位 |
| `daily_return` | 小数收益率 |
| `is_total_return` | 布尔 |

说明：

- 这里的 `daily_return` 在共享层已经被计算成 `close / prev_close - 1`
- 所以它是 `0-1` 小数收益率，不是 `%`

### 5. `serving.vw_limit_rules_daily`

| 字段 | 单位 |
|---|---|
| `up_limit_price_t/down_limit_price_t/pre_close` | 元/股 |
| `price_tick_quantize_t` | 元/股的最小价格刻度 |

### 6. `serving.vw_tradability_daily`

| 字段 | 单位 / 类型 |
|---|---|
| `is_listed_t/is_suspended_t/is_st_t/no_trade_t/...` | 布尔 |
| `entry_buyable_D1_open/exit_sellable_D5_close/sellable_retry_next_open` | 布尔 |
| `tradability_degraded_flag` | 布尔 |
| `tradability_degraded_reason` | 文本 |
| `low_liquidity_flag_t` | 布尔 |

低流动性标志的当前正确口径应理解为：

- `amount` 单位是 `千元`
- 阈值 `5_000`
- 即：**成交额低于 500 万元**

### 7. `serving.vw_instrument_status_daily`

| 字段 | 单位 / 类型 |
|---|---|
| `is_listed_t/is_suspended_t/is_st_t` | 布尔 |
| `trade_date` | 日期字符串 |

### 8. `serving.vw_terminal_event_daily`

| 字段 | 单位 / 类型 |
|---|---|
| `terminal_event_flag/cash_settlement_flag/contract_degraded_flag` | 布尔 |
| `terminal_event_type/source/...` | 文本 / 枚举 |
| `event_date/last_trade_date` | 日期字符串 |

说明：

- 当前共享源是“delist-only degraded truth”
- `cash_settlement_amount` 当前并未稳定提供，不能假定已有统一金额单位

### 9. `serving.vw_labels_daily`

| 字段 | 单位 |
|---|---|
| `open_D1/close_D5` | 元/股 |
| `adj_factor_D1/adj_factor_D5` | 无量纲 |
| `adj_open_base_D1/adj_close_base_D5` | 复权价格口径，元/股 |
| `label_5d_next_open_close_raw/label_5d_next_open_close` | 小数收益率 |
| `label_defined` | 布尔 |
| `label_masked_reason` | 文本 |

说明：

- `label_5d_next_open_close = adj_close_base_D5 / adj_open_base_D1 - 1`
- 所以 `0.05 = 5%`

### 10. `serving.vw_execution_path_daily`

| 字段 | 单位 |
|---|---|
| `actual_sell_price` | 元/股 |
| `exit_delay_days` | 天数 |
| `execution_delayed_realized_return` | 小数收益率 |
| `actual_exit_event_type/actual_exit_price_field/execution_path_status/terminal_event_type` | 文本 / 枚举 |
| `terminal_event_flag/terminal_exit_approximation_flag/terminal_exit_conservative_flag` | 布尔 |

### 11. `serving.vw_sample_eligibility_daily`

| 字段 | 单位 / 类型 |
|---|---|
| `entry_date/planned_exit_date` | 日期字符串 |
| `entry_tradeable/planned_exit_tradeable/actually_exited/...` | 布尔 |
| `mask_reason_json` | JSON 文本 |

### 12. `serving.vw_st_status_interval` / `serving.vw_industry_membership_interval`

| 字段 | 单位 / 类型 |
|---|---|
| 代码、名称、行业名、推断方法 | 文本 / 枚举 |
| 生效开始 / 结束日期 | 日期字符串 |

## 五、本项目字段单位

### 1. `project_label_panel`

| 字段 | 单位 |
|---|---|
| `open_D1/close_D5` | 元/股 |
| `adj_factor_D1/adj_factor_D5` | 无量纲 |
| `adj_open_base_D1/adj_close_base_D5` | 元/股 |
| `label_5d_next_open_close_raw/label_5d_next_open_close` | 小数收益率 |

### 2. `project_execution_panel`

| 字段 | 单位 |
|---|---|
| `actual_sell_price` | 元/股 |
| `exit_delay_days` | 天数 |
| `execution_delayed_realized_return` | 小数收益率 |

### 3. `model_scores_D0`

| 字段 | 单位 |
|---|---|
| `model_score_D0` | 无量纲分数 |
| `reversal_rank/momentum_rank/lowvol_rank/liquidity_rank` | 百分位 rank，取值通常在 `[0,1]` |
| `score_component_count` | 个数 |

说明：

- `liquidity_rank` 现在应按“更高流动性 -> 更大 rank”理解

### 4. `ranking_state_daily` / `execution_state_daily`

| 字段 | 单位 |
|---|---|
| `model_score_D0` | 无量纲分数 |
| `rank_position/topk_threshold_rank` | 名次 / 个数 |
| `target_weight_D0` | 组合目标权重（0-1） |
| `execution_attempt_D1/entry_filled_D1/backtest_executable` | 布尔 |

### 5. 组合层

| 字段 | 单位 |
|---|---|
| `target_weight_D0/entry_fill_weight/opening_weight/closing_weight/cash_weight/invested_weight/max_single_name_weight/top3_weight` | 权重（0-1） |
| `portfolio_herfindahl_index` | 无量纲 |
| `turnover_daily/buy_notional_daily/sell_notional_daily` | 规范化权重口径，不是人民币金额 |
| `weight_mapping_multiplier` | 无量纲乘子 |

### 6. fixed test 产物

| 字段 | 单位 |
|---|---|
| `portfolio_daily_return/benchmark_return_daily/relative_return_daily` | 小数收益率 |
| `equity/benchmark_equity` | 净值指数（通常初始为 1） |
| `total_return/annualized_return/annual_relative_return/max_drawdown` | 小数收益率 |
| `daily_volatility/annualized_volatility/relative_ir/sharpe_ratio` | 无量纲或收益率派生统计量 |
| `avg_cash_weight/avg_invested_weight/avg_turnover_daily` | 0-1 比例 |
| `stress_open_bp/stress_close_bp` | 基点（bp） |
| `low_liquidity_weight_share/low_liquidity_contribution_share_of_strategy/low_liquidity_alpha_contribution_share` | 0-1 比例 |

注意：

- 项目 fixed test 里几乎所有“return”字段都是 **小数**，不是 `%`
- 唯一明确不是小数收益率的，是 `*_bp` 这类基点字段

## 六、当前最重要的应用提醒

### 1. `amount`

当前项目里最容易踩坑的字段就是 `amount`。

统一记法：

- `daily/index_daily`：`amount` 单位 = `千元`
- `moneyflow`：`*_amount` 单位 = `万元`
- `daily_basic` 的 `total_mv/circ_mv` 单位 = `万元`

### 2. 不要把“小数收益率”当百分数

例如：

- `label_5d_next_open_close = 0.05`
- `execution_delayed_realized_return = -0.03`
- `annual_relative_return = -0.0529`

都应该读成：

- `5%`
- `-3%`
- `-5.29%`

而不是：

- `0.05%`
- `-0.03%`
- `-0.0529%`

### 3. 不要把“权重”当人民币金额

例如：

- `target_weight_D0 = 0.10`
- `cash_weight = 0.85`

读法是：

- `10%` 的组合权重
- `85%` 的现金占比

不是：

- `0.10 元`
- `0.85 元`

## 七、仍需二次扩展的部分

如果你后面要大量使用共享数据源的基本面原始层，还建议继续做一轮单独扩展：

- `financial_statement_raw_pit` 字段级单位字典
- `fina_indicator_pit` 全字段单位字典
- benchmark 原始下载表的字段级单位字典

当前这版已经足够覆盖：

- 共享数据源当前正式 `serving` 视图
- 本项目当前实际运行、评估、审计会用到的核心字段

## 八、`fina_indicator_pit` 完整字段单位字典

当前表位置：

- `/Users/wy/MiscProject/tushare_data/parquet_duckdb/data/current/warehouse/fundamental/fina_indicator_pit.parquet`

当前列数：`26`

| 字段 | 单位 / 类型 | 依据 |
|---|---|---|
| `snapshot_id` | 字符串 | 共享快照主键 |
| `ts_code` | 代码 | 股票代码 |
| `ann_date` | 日期字符串 `YYYYMMDD` | 公告日期 |
| `end_date` | 日期字符串 `YYYYMMDD` | 报告期 |
| `pit_available_date` | 日期字符串 `YYYYMMDD` | PIT 可用日期 |
| `eps` | 元/股 | 官方 `fina_indicator` |
| `dt_eps` | 元/股 | 官方 `fina_indicator` |
| `total_revenue_ps` | 元/股 | 官方 `fina_indicator` |
| `revenue_ps` | 元/股 | 官方 `fina_indicator` |
| `capital_rese_ps` | 元/股 | 官方 `fina_indicator` |
| `surplus_rese_ps` | 元/股 | 官方 `fina_indicator` |
| `undist_profit_ps` | 元/股 | 官方 `fina_indicator` |
| `gross_margin` | `%` 口径 | 官方描述为毛利/毛利率口径，按百分比理解 |
| `current_ratio` | 倍 | 官方 `fina_indicator` |
| `quick_ratio` | 倍 | 官方 `fina_indicator` |
| `cash_ratio` | 倍 / 比值 | 官方 `fina_indicator` |
| `assets_turn` | 次 | 官方 `fina_indicator` |
| `roe` | `%` 口径 | 净资产收益率 |
| `roe_dt` | `%` 口径 | 扣非 ROE |
| `roa_yearly` | `%` 口径 | 总资产收益率 |
| `q_roe` | `%` 口径 | 单季度 ROE |
| `q_dt_roe` | `%` 口径 | 单季度扣非 ROE |
| `q_sales_yoy` | `%` | 单季度营业收入同比增长率 |
| `q_op_qoq` | `%` | 单季度营业利润环比增长率 |
| `netprofit_yoy` | `%` | 归母净利润同比增长率 |
| `dt_netprofit_yoy` | `%` | 扣非净利润同比增长率 |

使用提醒：

- 这张表里除日期/代码外，基本可以分成三类：
  - 每股口径：`元/股`
  - 比率 / 周转：`% / 倍 / 次`
  - 增长率：`%`
- 当前项目如需把这些字段并入模型，建议统一先转换成：
  - `%` 类保留原百分比语义，或显式除以 `100`
  - `元/股` 类保留原数值

## 九、`financial_statement_raw_pit` 完整字段单位字典

当前表位置：

- `/Users/wy/MiscProject/tushare_data/parquet_duckdb/data/current/warehouse/fundamental/financial_statement_raw_pit.parquet`

当前列数：`321`

这张表来自三大报表原始 PIT 层：

- `balancesheet`
- `income`
- `cashflow`

由于列数很多，最稳妥、也最适合后续应用的方式，是按**完整规则字典**覆盖全部字段，而不是伪装成每列都从官网逐字摘到了单位说明。

### 1. 元数据 / 日期 / 枚举字段

以下字段**不属于数值量纲字段**：

| 字段 | 单位 / 类型 |
|---|---|
| `snapshot_id` | 字符串 |
| `statement_type` | 枚举：`balance/income/cashflow` |
| `ts_code` | 股票代码 |
| `ann_date` | 日期字符串 `YYYYMMDD` |
| `f_ann_date` | 日期字符串 `YYYYMMDD` |
| `end_date` | 日期字符串 `YYYYMMDD` |
| `report_type` | 枚举 |
| `comp_type` | 枚举 |
| `end_type` | 枚举 |
| `pit_available_date` | 日期字符串 `YYYYMMDD` |
| `update_flag` | 字符串标志 |

### 2. 每股字段

| 字段 | 单位 |
|---|---|
| `basic_eps` | 元/股 |
| `diluted_eps` | 元/股 |

### 3. 股本数量字段

| 字段 | 单位 | 说明 |
|---|---|---|
| `total_share` | 股本数量 | 官方写“期末总股本”，未像 `daily_basic` 那样明示 `万股`；建议按股本数量字段理解，使用前可抽样核对量级 |

### 4. 金额字段

除上面三类以外，这张表中的其余数值字段，统一按**金额字段（元）**理解。

这是基于两点：

- `balancesheet / income / cashflow` 在 Tushare A 股三大报表里承载的是原始财务报表行项目
- 官方对这些行项目虽然没有逐列重复写单位，但其语义是财务报表金额项；例如利润表快报接口 `express` 明确 `revenue/operate_profit/total_profit/n_income` 为 `元`

完整金额字段如下。

#### 4.1 资产负债表金额字段（元）

```text
cap_rese | undistr_porfit | surplus_rese | special_rese | money_cap | trad_asset | notes_receiv | accounts_receiv | oth_receiv | prepayment | div_receiv | int_receiv | inventories | amor_exp | nca_within_1y | sett_rsrv | loanto_oth_bank_fi | premium_receiv | reinsur_receiv | reinsur_res_receiv | pur_resale_fa | oth_cur_assets | total_cur_assets | fa_avail_for_sale | htm_invest
lt_eqt_invest | invest_real_estate | time_deposits | oth_assets | lt_rec | fix_assets | cip | const_materials | fixed_assets_disp | produc_bio_assets | oil_and_gas_assets | intan_assets | r_and_d | goodwill | lt_amor_exp | defer_tax_assets | decr_in_disbur | oth_nca | total_nca | cash_reser_cb | depos_in_oth_bfi | prec_metals | deriv_assets | rr_reins_une_prem | rr_reins_outstd_cla
rr_reins_lins_liab | rr_reins_lthins_liab | refund_depos | ph_pledge_loans | refund_cap_depos | indep_acct_assets | client_depos | client_prov | transac_seat_fee | invest_as_receiv | total_assets | lt_borr | st_borr | cb_borr | depos_ib_deposits | loan_oth_bank | trading_fl | notes_payable | acct_payable | adv_receipts | sold_for_repur_fa | comm_payable | payroll_payable | taxes_payable | int_payable
div_payable | oth_payable | acc_exp | deferred_inc | st_bonds_payable | payable_to_reinsurer | rsrv_insur_cont | acting_trading_sec | acting_uw_sec | non_cur_liab_due_1y | oth_cur_liab | total_cur_liab | bond_payable | lt_payable | specific_payables | estimated_liab | defer_tax_liab | defer_inc_non_cur_liab | oth_ncl | total_ncl | depos_oth_bfi | deriv_liab | depos | agency_bus_liab | oth_liab
prem_receiv_adva | depos_received | ph_invest | reser_une_prem | reser_outstd_claims | reser_lins_liab | reser_lthins_liab | indept_acc_liab | pledge_borr | indem_payable | policy_div_payable | total_liab | treasury_share | ordin_risk_reser | forex_differ | invest_loss_unconf | minority_int | total_hldr_eqy_exc_min_int | total_hldr_eqy_inc_min_int | total_liab_hldr_eqy | lt_payroll_payable | oth_comp_income | oth_eqt_tools | oth_eqt_tools_p_shr | lending_funds
acc_receivable | st_fin_payable | payables | hfs_assets | hfs_sales | cost_fin_assets | fair_value_fin_assets | contract_assets | contract_liab | accounts_receiv_bill | accounts_pay | oth_rcv_total | fix_assets_total | cip_total | oth_pay_total | long_pay_total | debt_invest | oth_debt_invest
```

说明：

- `treasury_share` 在会计语义上是库存股科目，按金额字段处理
- `oth_eqt_tools_p_shr` 虽带 `_p_shr`，但在该报表上下文中仍按权益金额科目处理更稳妥；如后续使用该字段，建议额外抽样核对

#### 4.2 利润表金额字段（元）

```text
total_revenue | revenue | int_income | prem_earned | comm_income | n_commis_income | n_oth_income | n_oth_b_income | prem_income | out_prem | une_prem_reser | reins_income | n_sec_tb_income | n_sec_uw_income | n_asset_mg_income | oth_b_income | fv_value_chg_gain | invest_income | ass_invest_income | forex_gain | total_cogs | oper_cost | int_exp | comm_exp | biz_tax_surchg
sell_exp | admin_exp | fin_exp | assets_impair_loss | prem_refund | compens_payout | reser_insur_liab | div_payt | reins_exp | oper_exp | compens_payout_refu | insur_reser_refu | reins_cost_refund | other_bus_cost | operate_profit | non_oper_income | non_oper_exp | nca_disploss | total_profit | income_tax | n_income | n_income_attr_p | minority_gain | oth_compr_income | t_compr_income
compr_inc_attr_p | compr_inc_attr_m_s | ebit | ebitda | insurance_exp | undist_profit | distable_profit | rd_exp | fin_exp_int_exp | fin_exp_int_inc | transfer_surplus_rese | transfer_housing_imprest | transfer_oth | adj_lossgain | withdra_legal_surplus | withdra_legal_pubfund | withdra_biz_devfund | withdra_rese_fund | withdra_oth_ersu | workers_welfare | distr_profit_shrhder | prfshare_payable_dvd | comshare_payable_dvd | capit_comstock_div | continued_net_profit
```

#### 4.3 现金流量表金额字段（元）

```text
net_profit | finan_exp | c_fr_sale_sg | recp_tax_rends | n_depos_incr_fi | n_incr_loans_cb | n_inc_borr_oth_fi | prem_fr_orig_contr | n_incr_insured_dep | n_reinsur_prem | n_incr_disp_tfa | ifc_cash_incr | n_incr_disp_faas | n_incr_loans_oth_bank | n_cap_incr_repur | c_fr_oth_operate_a | c_inf_fr_operate_a | c_paid_goods_s | c_paid_to_for_empl | c_paid_for_taxes | n_incr_clt_loan_adv | n_incr_dep_cbob | c_pay_claims_orig_inco | pay_handling_chrg | pay_comm_insur_plcy
oth_cash_pay_oper_act | st_cash_out_act | n_cashflow_act | oth_recp_ral_inv_act | c_disp_withdrwl_invest | c_recp_return_invest | n_recp_disp_fiolta | n_recp_disp_sobu | stot_inflows_inv_act | c_pay_acq_const_fiolta | c_paid_invest | n_disp_subs_oth_biz | oth_pay_ral_inv_act | n_incr_pledge_loan | stot_out_inv_act | n_cashflow_inv_act | c_recp_borrow | proc_issue_bonds | oth_cash_recp_ral_fnc_act | stot_cash_in_fnc_act | free_cashflow | c_prepay_amt_borr | c_pay_dist_dpcp_int_exp | incl_dvd_profit_paid_sc_ms | oth_cashpay_ral_fnc_act
stot_cashout_fnc_act | n_cash_flows_fnc_act | eff_fx_flu_cash | n_incr_cash_cash_equ | c_cash_equ_beg_period | c_cash_equ_end_period | c_recp_cap_contrib | incl_cash_rec_saims | uncon_invest_loss | prov_depr_assets | depr_fa_coga_dpba | amort_intang_assets | lt_amort_deferred_exp | decr_deferred_exp | incr_acc_exp | loss_disp_fiolta | loss_scr_fa | loss_fv_chg | invest_loss | decr_def_inc_tax_assets | incr_def_inc_tax_liab | decr_inventories | decr_oper_payable | incr_oper_payable | others
im_net_cashflow_oper_act | conv_debt_into_cap | conv_copbonds_due_within_1y | fa_fnc_leases | im_n_incr_cash_equ | net_dism_capital_add | net_cash_rece_sec | credit_impa_loss | use_right_asset_dep | oth_loss_asset | end_bal_cash | beg_bal_cash | end_bal_cash_equ | beg_bal_cash_equ
```

### 5. 应用建议

如果你后面要在研究里直接消费 `financial_statement_raw_pit`，建议遵守下面这套最稳的规则：

- 先把所有金额字段显式当作“元”处理
- 如需和 `daily_basic.total_mv/circ_mv` 这类 `万元` 字段混算，先统一量纲
- 如需和“每股”字段混算，先明确是否要除以股本
- `total_share` 在真正进模型前，建议抽样核一遍量级，确认是“股”还是“万股”存储

这一版已经把这两张 PIT 表的字段单位覆盖完整了；后面如果你愿意，我可以继续把它们整理成一份更适合程序引用的 `csv/json` 版字段单位字典。 
