# Formal Factor Cards — 25 Positive Signals

Generated: 2026-04-29 10:23

Each card follows 框架 14.4 specification: definition, economic explanation (≤3 sentences),
PIT rule, missing-value handling, expected failure modes, and diagnostic summary.

---

## Summary

Total positive signals with formal cards: **25**

| Rank | Signal | Family | IC | Top10-Bottom10 | Monotonic |
|-----|--------|--------|----:|---------------:|:---------:|
| 1 | `price_volume_single_signal_price_volume_beta_20d_v1` | price_volume -> beta | 0.0172 | 0.0078 | ✓ |
| 2 | `price_volume_single_signal_volume_price_synchronicity_20d_v1` | price_volume -> correlation | 0.0167 | 0.0094 | ✓ |
| 3 | `price_volume_single_signal_price_volume_corr_20d_v1` | price_volume -> correlation | 0.0167 | 0.0094 | ✓ |
| 4 | `price_volume_single_signal_intraday_trend_bias_20d_v1` | intraday -> bias | 0.0147 | 0.0093 | ✓ |
| 5 | `price_volume_single_signal_liquidity_trend_20_60_v1` | liquidity -> trend | 0.0122 | 0.0072 | ✓ |
| 6 | `price_volume_single_signal_alpha158_low0_v1` | alpha158 -> named | 0.0118 | 0.0137 | ✓ |
| 7 | `price_volume_single_signal_price_volume_rank_corr_20d_v1` | price_volume -> correlation | 0.0114 | 0.0056 | ✓ |
| 8 | `price_volume_single_signal_alpha158_full_036_v1` | alpha158 -> full | 0.0112 | 0.0088 | ✓ |
| 9 | `price_volume_single_signal_alpha158_full_003_v1` | alpha158 -> full | 0.0112 | 0.0082 | ✓ |
| 10 | `price_volume_single_signal_alpha158_full_027_v1` | alpha158 -> full | 0.0109 | 0.0076 | ✓ |
| 11 | `price_volume_single_signal_upside_range_share_20d_v1` | intraday -> structure | 0.0103 | 0.0054 | ✓ |
| 12 | `price_volume_single_signal_momentum_60_5_v1` | momentum -> medium_term | 0.0098 | 0.0025 | ✓ |
| 13 | `price_volume_single_signal_alpha158_full_004_v1` | alpha158 -> full | 0.0097 | 0.0079 | ✓ |
| 14 | `price_volume_single_signal_up_amount_persistence_20d_v1` | volume -> persistence | 0.0094 | 0.0069 | ✓ |
| 15 | `price_volume_single_signal_liquidity_trend_60_120_v1` | liquidity -> trend | 0.0083 | 0.0052 | ✓ |
| 16 | `price_volume_single_signal_breakout_volume_confirmation_20d_v1` | breakout -> failure | 0.0073 | 0.0110 | ✓ |
| 17 | `price_volume_single_signal_volume_momentum_5_20_v1` | turnover -> level | 0.0072 | 0.0091 | ✓ |
| 18 | `price_volume_single_signal_amount_shock_5_20_v1` | liquidity -> shock | 0.0072 | 0.0091 | ✓ |
| 19 | `price_volume_single_signal_alpha158_full_019_v1` | alpha158 -> full | 0.0064 | 0.0109 | ✓ |
| 20 | `price_volume_single_signal_turnover_acceleration_5_20_v1` | turnover -> level | 0.0063 | 0.0093 | ✓ |
| 21 | `price_volume_single_signal_lower_shadow_support_20d_v1` | kline -> shadow | 0.0062 | 0.0044 | ✓ |
| 22 | `price_volume_single_signal_intraday_reversal_asymmetry_20d_v1` | intraday -> bias | 0.0055 | 0.0030 | ✓ |
| 23 | `price_volume_single_signal_high_open_hold_ratio_20d_v1` | intraday -> structure | 0.0050 | 0.0019 | ✓ |
| 24 | `price_volume_single_signal_trend_consistency_20d_v1` | trend -> consistency | 0.0033 | 0.0001 | ✓ |
| 25 | `price_volume_single_signal_downside_range_convexity_20d_v1` | downside -> risk | 0.0021 | 0.0016 | ✓ |

---

# Detailed Factor Cards

## price_volume_single_signal_price_volume_beta_20d_v1

**Family:** price_volume -> beta
**Field:** `price_volume_beta_20d_raw`
**Ranking direction:** DESC (higher beta ranks higher)

### Formula

```
COVAR_SAMP(pct_ret, dlog_amount) OVER 20d / VAR_SAMP(dlog_amount) OVER 20d, where dlog_amount = LN(amount) - LAG(LN(amount))
```

### Economic Explanation

- Measures the sensitivity of daily return to daily log-amount change over a 20-day window — a price-volume slope beta.
- Stocks where returns are more sensitive to volume changes tend to have stronger subsequent short-term performance, consistent with informed trading amplification.
- Higher values indicate the stock's return moves more per unit of volume innovation, which may signal the presence of informed or momentum-driven capital.

### PIT Rule

D0 及之前 20 个交易日可见的 pct_chg 和 amount；不含 future 信息

### Missing / Non-Finite Handling

若 VAR_SAMP(dlog_amount) <= 1e-12 或任一输入缺失，则该信号值为 NULL

### Expected Failure Modes

- 在低成交或一字板时期，dlog_amount 接近 0，beta 不可定义
- 极端 outlier 期间 beta 可能被少数日子的量价关系主导

### Diagnostic Summary

- Full-sample correlation IC: **0.017161**
- Average daily IC: **0.028287**
- Positive daily IC share: **60.81%**
- Scored with label: **15020218**
- Null score share: **0.01%**
- Decile monotonic: **Yes**
- Top10 average label: **0.008462**
- Top10 minus 11-20: **0.000737**
- Top10 minus Bottom10: **0.007779**

> 正向信号中 IC 最高 (0.0172)。属于量价关系类。

---

## price_volume_single_signal_volume_price_synchronicity_20d_v1

**Family:** price_volume -> correlation
**Field:** `volume_price_synchronicity_20d_raw`
**Ranking direction:** DESC (higher synchronicity ranks higher)

### Formula

```
CORR(pct_ret, log_amount - prev_log_amount) OVER 20d, where prev_log_amount = LAG(LN(amount))
```

### Economic Explanation

- Captures the correlation between daily return and the log-amount innovation (deviation from prior day's log amount) over 20 days.
- High positive correlation means returns and volume-surprise move together — a signature of informed-flow-driven price moves.
- Stocks with stronger return-volume co-movement tend to have higher subsequent returns, consistent with information-flow theory.

### PIT Rule

D0 及之前 20 个交易日可见的 pct_chg 和 amount

### Missing / Non-Finite Handling

若 CORR 的输入序列 < 3 个有效配对观测，则为 NULL

### Expected Failure Modes

- 在低波动环境中，pct_ret 和 amount 变化都极小，相关性不稳定
- 分红/除权日前后若调整因子不一致可能导致量价关系失真

### Diagnostic Summary

- Full-sample correlation IC: **0.016661**
- Average daily IC: **0.029966**
- Positive daily IC share: **63.68%**
- Scored with label: **15021120**
- Null score share: **0.01%**
- Decile monotonic: **Yes**
- Top10 average label: **0.007764**
- Top10 minus 11-20: **0.001056**
- Top10 minus Bottom10: **0.009379**

> IC=0.0167，与 price_volume_corr 几乎等价(同一机制)

---

## price_volume_single_signal_price_volume_corr_20d_v1

**Family:** price_volume -> correlation
**Field:** `price_volume_corr_20d_raw`
**Ranking direction:** DESC

### Formula

```
CORR(pct_ret, dlog_amount) OVER 20d, where dlog_amount = LN(amount) - LAG(LN(amount))
```

### Economic Explanation

- Pearson correlation between daily return and log-amount first-difference over 20 days.
- Lower-level alternative to volume_price_synchronicity; empirically nearly equivalent.
- Positive correlation suggests volume-confirmed price moves that may persist.

### PIT Rule

D0 及之前 20 个交易日的 pct_chg 和 amount

### Missing / Non-Finite Handling

少于 3 个有效配对时为 NULL

### Expected Failure Modes

极低成交环境不稳定；与 synchronicity 存在共线性

### Diagnostic Summary

- Full-sample correlation IC: **0.016661**
- Average daily IC: **0.029966**
- Positive daily IC share: **63.68%**
- Scored with label: **15021120**
- Null score share: **0.01%**
- Decile monotonic: **Yes**
- Top10 average label: **0.007764**
- Top10 minus 11-20: **0.001056**
- Top10 minus Bottom10: **0.009379**

> IC=0.0167。与 volume_price_synchronicity 几乎重复，选其一即可。

---

## price_volume_single_signal_intraday_trend_bias_20d_v1

**Family:** intraday -> bias
**Field:** `intraday_trend_bias_20d_raw`
**Ranking direction:** DESC (stronger intraday uptrend ranks higher)

### Formula

```
AVG(close/open - 1.0) OVER 20d
```

### Economic Explanation

- Measures the average intraday return (close vs open) over the past 20 days — the typical direction of intraday price drift.
- A positive bias means the stock tends to drift higher during the day, which may reflect persistent order-flow imbalance or informed accumulation.
- Stocks with stronger intraday uptrend bias show subsequent outperformance, consistent with intraday momentum spilling over to the next holding period.

### PIT Rule

D0 可见的开盘价和收盘价

### Missing / Non-Finite Handling

若开/收盘价任一缺失，该日不计入；全部缺失则信号为 NULL

### Expected Failure Modes

- 跳空开盘日 intraday return 可能被开盘跳空扭曲
- 在趋势反转时点，positive bias 可能变为负向预测

### Diagnostic Summary

- Full-sample correlation IC: **0.014740**
- Average daily IC: **0.019716**
- Positive daily IC share: **55.59%**
- Scored with label: **15022019**
- Null score share: **0.00%**
- Decile monotonic: **Yes**
- Top10 average label: **0.005909**
- Top10 minus 11-20: **0.000308**
- Top10 minus Bottom10: **0.009348**

> IC=0.0147。简洁且解释清晰的日内信号。

---

## price_volume_single_signal_liquidity_trend_20_60_v1

**Family:** liquidity -> trend
**Field:** `liquidity_trend_20_60_raw`
**Ranking direction:** DESC (improving liquidity ranks higher)

### Formula

```
AVG(LN(amount+1)) OVER 20d - AVG(LN(amount+1)) OVER 60d
```

### Economic Explanation

- Measures the recent 20-day average log-amount minus the longer 60-day average — a liquidity momentum/gradient proxy.
- A positive value indicates liquidity (trading activity) is improving relative to its recent history, which tends to attract more trading interest and reduce execution costs.
- Stocks with improving liquidity profiles have better subsequent returns, possibly reflecting increasing investor attention or improving information environment.

### PIT Rule

D0 及之前 60 个交易日的 amount；以千元为单位(同 tushare daily.amount)

### Missing / Non-Finite Handling

若 60 日 lookback 不足(如次新股)，则信号为 NULL

### Expected Failure Modes

- 次新股或长期停牌后复牌初期，lookback 不足导致信号不可用
- 流动性趋势可能在市场整体缩量时大面积转负

### Diagnostic Summary

- Full-sample correlation IC: **0.012159**
- Average daily IC: **0.018665**
- Positive daily IC share: **57.92%**
- Scored with label: **15022019**
- Null score share: **0.00%**
- Decile monotonic: **Yes**
- Top10 average label: **0.005774**
- Top10 minus 11-20: **0.000174**
- Top10 minus Bottom10: **0.007168**

> IC=0.0122。核心 baseline 变量，流动性趋势类。

---

## price_volume_single_signal_alpha158_low0_v1

**Family:** alpha158 -> named
**Field:** `alpha158_low0_raw`
**Ranking direction:** DESC

### Formula

```
qlib Alpha158 定义: (low - vwap) / (close + vwap) 的 20 日变体或其等价公式
```

### Economic Explanation

- alpha158 因子体系中以最低价(low)为核心的定价偏离类因子。
- 衡量日内低价相对于成交量加权均价(vwap)的偏离程度，反映日内吸收卖压的能力。
- 较低的偏离(价格在 vwap 附近获得支撑)预示后续正向收益。

### PIT Rule

D0 及之前 20 个交易日的 low, close, amount, vwap

### Missing / Non-Finite Handling

任一核心字段缺失则该值为 NULL

### Expected Failure Modes

极端行情下 low 价格可能失真；需注意 qlib 实现与该项目的口径差异

### Diagnostic Summary

- Full-sample correlation IC: **0.011783**
- Average daily IC: **0.019262**
- Positive daily IC share: **59.97%**
- Scored with label: **15022019**
- Null score share: **0.00%**
- Decile monotonic: **Yes**
- Top10 average label: **0.006667**
- Top10 minus 11-20: **0.001949**
- Top10 minus Bottom10: **0.013717**

> IC=0.0118。alpha158 体系中入围 strongest positive 的命名信号。

---

## price_volume_single_signal_price_volume_rank_corr_20d_v1

**Family:** price_volume -> correlation
**Field:** `price_volume_rank_corr_20d_raw`
**Ranking direction:** DESC (stronger rank correlation ranks higher)

### Formula

```
CORR(SIGN(pct_ret), SIGN(dlog_amount)) OVER 20d, where dlog_amount = LN(amount) - LAG(LN(amount))
```

### Economic Explanation

- Rank-based (sign-level) correlation between return direction and volume-surprise direction over 20 days.
- Reduces the impact of magnitude outliers compared to Pearson-based price-volume correlations.
- Positive sign-correlation means return and volume-surprise tend to move in the same direction — a robust indicator of directional flow.

### PIT Rule

D0 及之前 20 个交易日的 pct_chg 和 amount

### Missing / Non-Finite Handling

少于 5 个有效日则为 NULL

### Expected Failure Modes

在大量一字板交易日，所有 SIGN 为 0，相关系数不可定义

### Diagnostic Summary

- Full-sample correlation IC: **0.011394**
- Average daily IC: **0.020216**
- Positive daily IC share: **62.68%**
- Scored with label: **15021120**
- Null score share: **0.01%**
- Decile monotonic: **Yes**
- Top10 average label: **0.005890**
- Top10 minus 11-20: **0.000131**
- Top10 minus Bottom10: **0.005601**

> IC=0.0114。量价类信号的稳健版本。

---

## price_volume_single_signal_alpha158_full_036_v1

**Family:** alpha158 -> full
**Field:** `alpha158 全集中编号 036 的信号`
**Ranking direction:** DESC

### Formula

```
alpha158 全集定义，见 /Users/wy/MiscProject/multi_factor/artifacts/research_registry/alpha158_qlib_full_definition_manifest_20260428.json
```

### Economic Explanation

- alpha158 全因子集中表现最好的之一，属于 price-volume 量价派生类。
- 具体经济含义需映射回 qlib Alpha158 特征定义。

### PIT Rule

D0 及之前可见的行情数据

### Missing / Non-Finite Handling

alpha158 标准缺失处理规则

### Expected Failure Modes

alpha158 全集中部分因子在 A 股特定时期可能过拟合

### Diagnostic Summary

- Full-sample correlation IC: **0.011240**
- Average daily IC: **0.019715**
- Positive daily IC share: **59.31%**
- Scored with label: **15022019**
- Null score share: **0.00%**
- Decile monotonic: **Yes**
- Top10 average label: **0.007208**
- Top10 minus 11-20: **0.001024**
- Top10 minus Bottom10: **0.008815**

> IC=0.0112。alpha158_full 系列中 Top 正向信号。

---

## price_volume_single_signal_alpha158_full_003_v1

**Family:** alpha158 -> full
**Field:** `alpha158 全集 003`
**Ranking direction:** DESC

### Formula

```
见 alpha158 qlib 全集清单
```

### Economic Explanation

- alpha158 全集中表现较强的因子之一。
- 具体含义需查 alpha158 特征字典。

### PIT Rule

D0 及之前

### Missing / Non-Finite Handling

标准 alpha158 规则

### Expected Failure Modes

需单独验证独立性，避免与其它信号高度冗余

### Diagnostic Summary

- Full-sample correlation IC: **0.011160**
- Average daily IC: **0.019319**
- Positive daily IC share: **59.08%**
- Scored with label: **15021120**
- Null score share: **0.01%**
- Decile monotonic: **Yes**
- Top10 average label: **0.004796**
- Top10 minus 11-20: **0.000500**
- Top10 minus Bottom10: **0.008211**

> IC=0.0112。与 036 属于同批次。

---

## price_volume_single_signal_alpha158_full_027_v1

**Family:** alpha158 -> full
**Field:** `alpha158 全集 027`
**Ranking direction:** DESC

### Formula

```
见 alpha158 qlib 全集清单
```

### Economic Explanation

- alpha158 全集中表现较强的因子之一。
- 具体含义需查 alpha158 特征字典。

### PIT Rule

D0 及之前

### Missing / Non-Finite Handling

标准 alpha158 规则

### Expected Failure Modes

需单独验证独立性

### Diagnostic Summary

- Full-sample correlation IC: **0.010886**
- Average daily IC: **0.018942**
- Positive daily IC share: **59.51%**
- Scored with label: **15022019**
- Null score share: **0.00%**
- Decile monotonic: **Yes**
- Top10 average label: **0.006253**
- Top10 minus 11-20: **0.000777**
- Top10 minus Bottom10: **0.007638**

> IC=0.0109。alpha158 系列。

---

## price_volume_single_signal_upside_range_share_20d_v1

**Family:** intraday -> structure
**Field:** `upside_range_share_20d_raw`
**Ranking direction:** DESC (higher upside share ranks higher)

### Formula

```
SUM(upside_range_daily) OVER 20d / SUM((high-low)/close) OVER 20d, where upside_range_daily = CASE WHEN pct_ret > 0 AND adj_close > 0 THEN (adj_high - adj_low) / adj_close ELSE 0 END
```

### Economic Explanation

- Measures the fraction of total 20-day range that occurred on up-days — the upside participation share.
- A higher share indicates that the stock's price range expansion happens disproportionately on up-days, suggesting bullish price discovery.
- Stocks with higher upside range share tend to have higher forward returns, consistent with the idea that up-day volatility is information-rich.

### PIT Rule

D0 及之前 20 个交易日的 adj_open/adj_high/adj_low/adj_close

### Missing / Non-Finite Handling

若 20 日总 range 为 0，则为 NULL

### Expected Failure Modes

- 在横盘震荡期，upside_range_share 可能失去区分度
- 除权日附近 adj_price 可能导致 range 计算短暂失真

### Diagnostic Summary

- Full-sample correlation IC: **0.010329**
- Average daily IC: **0.015721**
- Positive daily IC share: **55.15%**
- Scored with label: **15021902**
- Null score share: **0.01%**
- Decile monotonic: **Yes**
- Top10 average label: **0.004096**
- Top10 minus 11-20: **0.000131**
- Top10 minus Bottom10: **0.005403**

> IC=0.0103。日内结构类。

---

## price_volume_single_signal_momentum_60_5_v1

**Family:** momentum -> medium_term
**Field:** `momentum_60_5_raw`
**Ranking direction:** DESC (stronger momentum ranks higher)

### Formula

```
adj_close(D-5) / adj_close(D-60) - 1.0
```

### Economic Explanation

- Classic medium-term momentum: cumulative base-adjusted return from 60 trading days ago to 5 trading days ago (skipping the most recent week to avoid short-term reversal contamination).
- The 5-day skip separates momentum from the short-term reversal effect.
- Stocks with stronger 60-5 day momentum tend to continue outperforming over the next 5-day holding period.

### PIT Rule

D0 可见的 adj_close；D-60 和 D-5 的复权价格

### Missing / Non-Finite Handling

若 D-5 或 D-60 的 adj_close 缺失，则为 NULL

### Expected Failure Modes

- 在市场剧烈反转时期(如 2015 年股灾)，momentum 可能大幅回撤
- 次新股 lookback 不足导致信号不可用

### Diagnostic Summary

- Full-sample correlation IC: **0.009758**
- Average daily IC: **0.013398**
- Positive daily IC share: **52.36%**
- Scored with label: **14888004**
- Null score share: **0.89%**
- Decile monotonic: **Yes**
- Top10 average label: **0.004282**
- Top10 minus 11-20: **-0.001201**
- Top10 minus Bottom10: **0.002461**

> IC=0.0098。标准中期动量因子。

---

## price_volume_single_signal_alpha158_full_004_v1

**Family:** alpha158 -> full
**Field:** `alpha158 全集 004`
**Ranking direction:** DESC

### Formula

```
见 alpha158 qlib 全集清单
```

### Economic Explanation

- alpha158 全集中表现较强的因子之一。
- 具体含义需查 alpha158 特征字典。

### PIT Rule

D0 及之前

### Missing / Non-Finite Handling

标准 alpha158 规则

### Expected Failure Modes

需验证与其它 alpha158 信号的冗余程度

### Diagnostic Summary

- Full-sample correlation IC: **0.009717**
- Average daily IC: **0.017430**
- Positive daily IC share: **58.80%**
- Scored with label: **15021120**
- Null score share: **0.01%**
- Decile monotonic: **Yes**
- Top10 average label: **0.004321**
- Top10 minus 11-20: **0.000122**
- Top10 minus Bottom10: **0.007888**

> IC=0.0097。alpha158 系列。

---

## price_volume_single_signal_up_amount_persistence_20d_v1

**Family:** volume -> persistence
**Field:** `up_amount_persistence_20d_raw`
**Ranking direction:** DESC (more persistent up-volume ranks higher)

### Formula

```
AVG(CASE WHEN pct_ret > 0 AND amount > AVG(amount) OVER 20d THEN 1.0 ELSE 0.0 END) OVER 20d
```

### Economic Explanation

- Measures the frequency of up-days that are accompanied by above-average trading volume — up-volume persistence.
- Consistent up-volume suggests that buying pressure is not only present but sustained with conviction (high participation).
- Stocks where up-days reliably coincide with above-average volume tend to have better subsequent performance.

### PIT Rule

D0 及之前 20 个交易日的 pct_chg 和 amount

### Missing / Non-Finite Handling

若金额数据大面积缺失，则为 NULL

### Expected Failure Modes

- 在低成交环境，amount > 20d 均值的条件可能过于宽松
- 在持续放量下跌中可能产生反向信号(放量下跌也被计入)

### Diagnostic Summary

- Full-sample correlation IC: **0.009374**
- Average daily IC: **0.013587**
- Positive daily IC share: **54.92%**
- Scored with label: **15022019**
- Null score share: **0.00%**
- Decile monotonic: **Yes**
- Top10 average label: **0.006377**
- Top10 minus 11-20: **0.000764**
- Top10 minus Bottom10: **0.006922**

> IC=0.0094。量价确认类信号。

---

## price_volume_single_signal_liquidity_trend_60_120_v1

**Family:** liquidity -> trend
**Field:** `liquidity_trend_60_120_raw`
**Ranking direction:** DESC (improving liquidity ranks higher)

### Formula

```
AVG(LN(amount+1)) OVER 60d - AVG(LN(amount+1)) OVER 120d
```

### Economic Explanation

- Longer-horizon version of liquidity trend, comparing 60-day to 120-day average log-amount.
- Captures persistent shifts in liquidity regime rather than short-term fluctuations.
- A positive value indicates a structural improvement in trading activity.

### PIT Rule

D0 及之前 120 个交易日的 amount

### Missing / Non-Finite Handling

若 120 日 lookback 不足则为 NULL

### Expected Failure Modes

更长的 lookback 意味着对近期变化反应更慢，可能在流动性拐点处滞后

### Diagnostic Summary

- Full-sample correlation IC: **0.008324**
- Average daily IC: **0.013666**
- Positive daily IC share: **55.52%**
- Scored with label: **15022019**
- Null score share: **0.00%**
- Decile monotonic: **Yes**
- Top10 average label: **0.006167**
- Top10 minus 11-20: **0.000441**
- Top10 minus Bottom10: **0.005172**

> IC=0.0083。流动性趋势的长期版本。

---

## price_volume_single_signal_breakout_volume_confirmation_20d_v1

**Family:** breakout -> failure
**Field:** `breakout_volume_confirmation_20d_raw`
**Ranking direction:** DESC

### Formula

```
breakout_proximity_20d_raw * amount_shock_5_20_raw, 其中 breakout_proximity = adj_close / MAX(adj_close) OVER 20d_prev, amount_shock = AVG(LN(amount)) OVER 5d - AVG(LN(amount)) OVER 20d
```

### Economic Explanation

- Combines price proximity to recent high (breakout proximity) with a short-term volume surge (amount shock).
- A stock near its 20-day high that simultaneously experiences a volume surge is showing breakout confirmation — the price move is backed by volume.
- Breakouts confirmed by volume shocks tend to be more genuine and have better forward returns.

### PIT Rule

D0 及之前的 adj_close 和 amount

### Missing / Non-Finite Handling

若 breakout_proximity 或 amount_shock 任一 NULL，则乘积为 NULL

### Expected Failure Modes

- 在持续上涨末期可能产生假突破信号(volume-confirmed false breakout)
- 次新股缺乏 20 日 lookback 不可用

### Diagnostic Summary

- Full-sample correlation IC: **0.007258**
- Average daily IC: **0.011053**
- Positive daily IC share: **55.46%**
- Scored with label: **15021120**
- Null score share: **0.01%**
- Decile monotonic: **Yes**
- Top10 average label: **0.004263**
- Top10 minus 11-20: **0.002292**
- Top10 minus Bottom10: **0.011006**

> IC=0.0073。突破确认类信号。

---

## price_volume_single_signal_volume_momentum_5_20_v1

**Family:** turnover -> level
**Field:** `volume_momentum_5_20_raw`
**Ranking direction:** DESC

### Formula

```
AVG(LN(amount)) OVER 5d - AVG(LN(amount)) OVER 20d
```

### Economic Explanation

- Short-term volume momentum: the 5-day average log-amount relative to the 20-day average.
- A positive value means volume has accelerated in the past week relative to the past month.
- Volume acceleration often precedes increased volatility and directional price moves.

### PIT Rule

D0 及之前 20 个交易日的 amount

### Missing / Non-Finite Handling

lookback 不足则为 NULL

### Expected Failure Modes

在量能均值回归期可能产生反向信号

### Diagnostic Summary

- Full-sample correlation IC: **0.007194**
- Average daily IC: **0.011316**
- Positive daily IC share: **55.78%**
- Scored with label: **15022019**
- Null score share: **0.00%**
- Decile monotonic: **Yes**
- Top10 average label: **0.003593**
- Top10 minus 11-20: **0.000464**
- Top10 minus Bottom10: **0.009069**

> IC=0.0072。与 amount_shock_5_20 几乎等价。

---

## price_volume_single_signal_amount_shock_5_20_v1

**Family:** liquidity -> shock
**Field:** `amount_shock_5_20_raw`
**Ranking direction:** DESC

### Formula

```
AVG(LN(amount)) OVER 5d - AVG(LN(amount)) OVER 20d
```

### Economic Explanation

- Identical formula to volume_momentum_5_20_raw — a 5/20-day log-amount ratio measuring short-term volume surge.
- Positive value = recent volume is above normal (a 'shock' relative to recent history).
- Volume shocks often precede increased price movement.

### PIT Rule

D0 及之前 20 个交易日的 amount

### Missing / Non-Finite Handling

lookback 不足则为 NULL

### Expected Failure Modes

与 volume_momentum_5_20 完全等价，选其一即可

### Diagnostic Summary

- Full-sample correlation IC: **0.007194**
- Average daily IC: **0.011316**
- Positive daily IC share: **55.78%**
- Scored with label: **15022019**
- Null score share: **0.00%**
- Decile monotonic: **Yes**
- Top10 average label: **0.003593**
- Top10 minus 11-20: **0.000464**
- Top10 minus Bottom10: **0.009069**

> IC=0.0072。与 volume_momentum_5_20 等价。

---

## price_volume_single_signal_alpha158_full_019_v1

**Family:** alpha158 -> full
**Field:** `alpha158 全集 019`
**Ranking direction:** DESC

### Formula

```
见 alpha158 qlib 全集清单
```

### Economic Explanation

- alpha158 全集中表现较强的因子之一。
- 具体含义需查 alpha158 特征字典。

### PIT Rule

D0 及之前

### Missing / Non-Finite Handling

标准 alpha158 规则

### Expected Failure Modes

需验证独立性

### Diagnostic Summary

- Full-sample correlation IC: **0.006428**
- Average daily IC: **0.011171**
- Positive daily IC share: **55.67%**
- Scored with label: **15022019**
- Null score share: **0.00%**
- Decile monotonic: **Yes**
- Top10 average label: **0.004858**
- Top10 minus 11-20: **0.001960**
- Top10 minus Bottom10: **0.010865**

> IC=0.0064。alpha158 系列。Top10-Bottom10 差值较大(0.0109)

---

## price_volume_single_signal_turnover_acceleration_5_20_v1

**Family:** turnover -> level
**Field:** `turnover_acceleration_5_20_raw`
**Ranking direction:** DESC

### Formula

```
AVG(LN(turnover_rate+1)) OVER 5d - AVG(LN(turnover_rate+1)) OVER 20d
```

### Economic Explanation

- Turnover rate acceleration: the 5-day average log-turnover relative to the 20-day average.
- Instead of raw amount, uses turnover_rate which normalizes for free-float shares — a cleaner measure of trading intensity per unit of outstanding equity.
- Rising turnover rate suggests increasing speculative interest or distribution activity.

### PIT Rule

D0 及之前 20 个交易日的 turnover_rate

### Missing / Non-Finite Handling

lookback 不足则为 NULL

### Expected Failure Modes

换手率在机构大额交易时可能失真(大宗交易不计入换手率)

### Diagnostic Summary

- Full-sample correlation IC: **0.006315**
- Average daily IC: **0.011075**
- Positive daily IC share: **56.11%**
- Scored with label: **15022019**
- Null score share: **0.00%**
- Decile monotonic: **Yes**
- Top10 average label: **0.002816**
- Top10 minus 11-20: **0.000442**
- Top10 minus Bottom10: **0.009274**

> IC=0.0063。金额的替代指标。

---

## price_volume_single_signal_lower_shadow_support_20d_v1

**Family:** kline -> shadow
**Field:** `lower_shadow_support_20d_raw`
**Ranking direction:** DESC

### Formula

```
AVG(CASE WHEN (high-low) > 1e-12 AND pct_ret < 0 THEN (close - low) / (high - low) ELSE NULL END) OVER 20d
```

### Economic Explanation

- On down-days, measures where the close sits within the daily range: a higher value means the close is near the high despite a negative return — indicating buying support during the session.
- This 'lower shadow support' reflects the ability of buyers to lift prices off the intraday low.
- Stocks that show consistent buying support on down-days tend to have better forward returns.

### PIT Rule

D0 及之前 20 个交易日的 adj_high/adj_low/adj_close 和 pct_chg

### Missing / Non-Finite Handling

若非下跌日或无 range 数据则该日不计入；全部缺失则为 NULL

### Expected Failure Modes

- 在连续涨停/跌停日(range 极窄)可能不可定义
- 仅以下跌日为条件，样本量可能不足

### Diagnostic Summary

- Full-sample correlation IC: **0.006151**
- Average daily IC: **0.010726**
- Positive daily IC share: **54.56%**
- Scored with label: **15021902**
- Null score share: **0.01%**
- Decile monotonic: **Yes**
- Top10 average label: **0.005563**
- Top10 minus 11-20: **0.000543**
- Top10 minus Bottom10: **0.004427**

> IC=0.0062。K 线形态类。

---

## price_volume_single_signal_intraday_reversal_asymmetry_20d_v1

**Family:** intraday -> bias
**Field:** `intraday_reversal_asymmetry_20d_raw`
**Ranking direction:** DESC

### Formula

```
AVG(down_recovery_part) OVER 20d - AVG(up_fade_part) OVER 20d
```

### Economic Explanation

- Measures the asymmetry between how much a stock recovers from intraday dips vs how much it fades from intraday highs.
- A positive value means the stock tends to recover from intraday weakness more than it gives back intraday gains — a bullish intraday resilience pattern.
- This intraday reversal asymmetry captures the balance of buying vs selling pressure within the trading day.

### PIT Rule

D0 及之前 20 个交易日的 1 分钟或日频 OHLC

### Missing / Non-Finite Handling

若 intraday high/low 数据不可得，则为 NULL

### Expected Failure Modes

在趋势非常强劲的单边市，日内反转可能不频繁，导致信号趋近于 0

### Diagnostic Summary

- Full-sample correlation IC: **0.005550**
- Average daily IC: **0.007620**
- Positive daily IC share: **53.42%**
- Scored with label: **15019043**
- Null score share: **0.02%**
- Decile monotonic: **Yes**
- Top10 average label: **0.004405**
- Top10 minus 11-20: **0.000208**
- Top10 minus Bottom10: **0.002987**

> IC=0.0055。K 线日内结构类。

---

## price_volume_single_signal_high_open_hold_ratio_20d_v1

**Family:** intraday -> structure
**Field:** `high_open_hold_ratio_20d_raw`
**Ranking direction:** DESC

### Formula

```
AVG(hold_quality_part) OVER 20d
```

### Economic Explanation

- Measures whether stocks tend to open high and sustain those gains (rather than fade) — a proxy for 'high open hold' quality.
- A high ratio suggests the opening price is a fair reflection of informed demand, not just an overnight gap that fades.
- Stocks that hold their open levels intraday tend to have better short-term forward returns.

### PIT Rule

D0 及之前 20 个交易日的 adj_open, adj_high, adj_low, adj_close

### Missing / Non-Finite Handling

若日内 range 为 0 则不计入该日

### Expected Failure Modes

在开盘跳空巨大的事件日(财报/政策)可能失真

### Diagnostic Summary

- Full-sample correlation IC: **0.005027**
- Average daily IC: **0.007099**
- Positive daily IC share: **54.63%**
- Scored with label: **14995985**
- Null score share: **0.17%**
- Decile monotonic: **Yes**
- Top10 average label: **0.004374**
- Top10 minus 11-20: **0.000004**
- Top10 minus Bottom10: **0.001916**

> IC=0.0050。开盘质量类信号。

---

## price_volume_single_signal_trend_consistency_20d_v1

**Family:** trend -> consistency
**Field:** `trend_consistency_20d_raw`
**Ranking direction:** DESC (more consistent up-days ranks higher)

### Formula

```
AVG(CASE WHEN pct_ret > 0 THEN 1.0 ELSE 0.0 END) OVER 20d
```

### Economic Explanation

- The simplest trend measure: the fraction of up-days over the past 20 trading days.
- A value above 0.5 means more days were positive than negative — a consistent short-term uptrend without requiring the magnitude to be large.
- Directional consistency is a robust trend indicator that is less sensitive to outliers than cumulative return.

### PIT Rule

D0 及之前 20 个交易日的 pct_chg

### Missing / Non-Finite Handling

若交易日不足 20 日，则基于实际可用天数计算

### Expected Failure Modes

- 在低波动窄幅震荡期，>0.5 的胜率可能是随机波动而非真实趋势
- 在市场快速反转时可能提供延迟信号

### Diagnostic Summary

- Full-sample correlation IC: **0.003251**
- Average daily IC: **0.005854**
- Positive daily IC share: **51.49%**
- Scored with label: **15022019**
- Null score share: **0.00%**
- Decile monotonic: **Yes**
- Top10 average label: **0.002143**
- Top10 minus 11-20: **-0.001237**
- Top10 minus Bottom10: **0.000149**

> IC=0.0033。最简洁的趋势信号。

---

## price_volume_single_signal_downside_range_convexity_20d_v1

**Family:** downside -> risk
**Field:** `downside_range_convexity_20d_raw`
**Ranking direction:** ASC (lower convexity ranks higher)

### Formula

```
AVG(POWER(downside_range_pressure_daily, 2)) OVER 20d / AVG(downside_range_pressure_daily) OVER 20d (convexity measure of downside tail shape)
```

### Economic Explanation

- Measures the convexity/nonlinearity of downside range pressure — a tail-shape proxy for downside risk.
- Lower convexity means downside range is more linear and predictable, less prone to tail events.
- Stocks with less convex downside tails (more 'normal' downside behavior) tend to have better forward returns, as extreme tail risk is penalized.

### PIT Rule

D0 及之前 20 个交易日

### Missing / Non-Finite Handling

若 AVG(downside_range_pressure) <= 1e-12 则为 NULL

### Expected Failure Modes

- 在长期横盘期间，range convexity 接近 0，信号失去区分度
- 凸度指标对极端事件敏感，可能受少数交易日主导

### Diagnostic Summary

- Full-sample correlation IC: **0.002081**
- Average daily IC: **0.004594**
- Positive daily IC share: **52.51%**
- Scored with label: **15019007**
- Null score share: **0.02%**
- Decile monotonic: **Yes**
- Top10 average label: **0.003632**
- Top10 minus 11-20: **0.000141**
- Top10 minus Bottom10: **0.001629**

> IC=0.0021。下行尾部风险类。

---
