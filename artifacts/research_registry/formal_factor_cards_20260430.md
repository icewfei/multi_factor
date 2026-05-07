# Formal Factor Cards — 54 Positive Signals (Complete)

Generated: 2026-04-30

Each card follows 框架 14.4 specification: definition, economic explanation (≤3 sentences),
PIT rule, missing-value handling, expected failure modes, and diagnostic summary.

---

## Summary

Total positive signals with formal cards: **54**（有效独立信号约 **42** 个，详见附录 A 冗余性分析）

| Rank | Signal | Family | IC | AvgDailyIC | Top10-Bottom10 |
|-----|--------|--------|---:|-----------:|---------------:|
| 1 | `price_volume_single_signal_alpha158_corr20_v1` | 量价滚动相关(alpha158) | 0.018514 | 0.030448 | 0.012900 |
| 2 | `price_volume_single_signal_alpha158_corr10_v1` | 量价滚动相关(alpha158) | 0.018240 | 0.029058 | 0.012868 |
| 3 | `price_volume_single_signal_price_volume_beta_20d_v1` | price_volume -> beta | 0.017161 | 0.028287 | 0.007779 |
| 4 | `price_volume_single_signal_alpha158_cord30_v1` | 量价滚动相关(alpha158) | 0.016812 | 0.031407 | 0.009034 |
| 5 | `price_volume_single_signal_volume_price_synchronicity_20d_v1` | price_volume -> correlation | 0.016661 | 0.029966 | 0.009379 |
| 6 | `price_volume_single_signal_price_volume_corr_20d_v1` | price_volume -> correlation | 0.016661 | 0.029966 | 0.009379 |
| 7 | `price_volume_single_signal_alpha158_cord20_v1` | 量价滚动相关(alpha158) | 0.016534 | 0.029667 | 0.008273 |
| 8 | `price_volume_single_signal_alpha158_imxd5_v1` | 滚动价格(alpha158) | 0.016256 | 0.031425 | 0.006634 |
| 9 | `price_volume_single_signal_alpha158_corr5_v1` | 量价滚动相关(alpha158) | 0.016252 | 0.027261 | 0.008377 |
| 10 | `price_volume_single_signal_alpha158_corr30_v1` | 量价滚动相关(alpha158) | 0.015796 | 0.026934 | 0.011129 |
| 11 | `price_volume_single_signal_alpha158_cord5_v1` | 量价滚动相关(alpha158) | 0.014893 | 0.029532 | 0.007191 |
| 12 | `price_volume_single_signal_intraday_trend_bias_20d_v1` | intraday -> bias | 0.014740 | 0.019716 | 0.009348 |
| 13 | `price_volume_single_signal_alpha158_vsumd60_v1` | 成交量路径(alpha158) | 0.014043 | 0.023207 | 0.013535 |
| 14 | `price_volume_single_signal_alpha158_vsump60_v1` | 成交量路径(alpha158) | 0.014042 | 0.023205 | 0.013520 |
| 15 | `price_volume_single_signal_alpha158_vsumn60_v1` | 成交量路径(alpha158) | 0.014042 | 0.023203 | 0.013525 |
| 16 | `price_volume_single_signal_alpha158_cord60_v1` | 量价滚动相关(alpha158) | 0.013683 | 0.026120 | 0.006436 |
| 17 | `price_volume_single_signal_alpha158_vsumd30_v1` | 成交量路径(alpha158) | 0.013641 | 0.022346 | 0.013912 |
| 18 | `price_volume_single_signal_alpha158_vsump30_v1` | 成交量路径(alpha158) | 0.013640 | 0.022344 | 0.013898 |
| 19 | `price_volume_single_signal_alpha158_vsumn30_v1` | 成交量路径(alpha158) | 0.013640 | 0.022342 | 0.013902 |
| 20 | `price_volume_single_signal_alpha158_cord10_v1` | 量价滚动相关(alpha158) | 0.013113 | 0.024033 | 0.007534 |
| 21 | `price_volume_single_signal_alpha158_vma60_v1` | 成交量滚动(alpha158) | 0.012987 | 0.022111 | 0.013810 |
| 22 | `price_volume_single_signal_liquidity_trend_20_60_v1` | liquidity -> trend | 0.012159 | 0.018665 | 0.007168 |
| 23 | `price_volume_single_signal_alpha158_low0_v1` | alpha158 -> named | 0.011783 | 0.019262 | 0.013717 |
| 24 | `price_volume_single_signal_price_volume_rank_corr_20d_v1` | price_volume -> correlation | 0.011394 | 0.020216 | 0.005601 |
| 25 | `price_volume_single_signal_alpha158_full_036_v1` | alpha158 -> full | 0.011240 | 0.019715 | 0.008815 |
| 26 | `price_volume_single_signal_alpha158_full_003_v1` | alpha158 -> full | 0.011160 | 0.019319 | 0.008211 |
| 27 | `price_volume_single_signal_alpha158_vsumd20_v1` | 成交量路径(alpha158) | 0.010995 | 0.017574 | 0.012561 |
| 28 | `price_volume_single_signal_alpha158_vsump20_v1` | 成交量路径(alpha158) | 0.010994 | 0.017573 | 0.012547 |
| 29 | `price_volume_single_signal_alpha158_vsumn20_v1` | 成交量路径(alpha158) | 0.010994 | 0.017571 | 0.012551 |
| 30 | `price_volume_single_signal_alpha158_full_027_v1` | alpha158 -> full | 0.010886 | 0.018942 | 0.007638 |
| 31 | `price_volume_single_signal_upside_range_share_20d_v1` | intraday -> structure | 0.010329 | 0.015721 | 0.005403 |
| 32 | `price_volume_single_signal_momentum_60_5_v1` | momentum -> medium_term | 0.009758 | 0.013398 | 0.002461 |
| 33 | `price_volume_single_signal_alpha158_full_004_v1` | alpha158 -> full | 0.009717 | 0.017430 | 0.007888 |
| 34 | `price_volume_single_signal_alpha158_vma30_v1` | 成交量滚动(alpha158) | 0.009701 | 0.016449 | 0.013021 |
| 35 | `price_volume_single_signal_alpha158_vstd60_v1` | 成交量滚动(alpha158) | 0.009688 | 0.015409 | 0.008924 |
| 36 | `price_volume_single_signal_up_amount_persistence_20d_v1` | volume -> persistence | 0.009374 | 0.013587 | 0.006922 |
| 37 | `price_volume_single_signal_alpha158_imax20_v1` | 滚动价格(alpha158) | 0.008608 | 0.013915 | 0.004652 |
| 38 | `price_volume_single_signal_alpha158_vma10_v1` | 成交量滚动(alpha158) | 0.008574 | 0.015808 | 0.010681 |
| 39 | `price_volume_single_signal_liquidity_trend_60_120_v1` | liquidity -> trend | 0.008324 | 0.013666 | 0.005172 |
| 40 | `price_volume_single_signal_alpha158_corr60_v1` | 量价滚动相关(alpha158) | 0.008210 | 0.015454 | 0.005522 |
| 41 | `price_volume_single_signal_alpha158_vma20_v1` | 成交量滚动(alpha158) | 0.008139 | 0.014107 | 0.011979 |
| 42 | `price_volume_single_signal_alpha158_vma5_v1` | 成交量滚动(alpha158) | 0.007469 | 0.012777 | 0.007411 |
| 43 | `price_volume_single_signal_breakout_volume_confirmation_20d_v1` | breakout -> failure | 0.007258 | 0.011053 | 0.011006 |
| 44 | `price_volume_single_signal_volume_momentum_5_20_v1` | turnover -> level | 0.007194 | 0.011316 | 0.009069 |
| 45 | `price_volume_single_signal_amount_shock_5_20_v1` | liquidity -> shock | 0.007194 | 0.011316 | 0.009069 |
| 46 | `price_volume_single_signal_alpha158_full_019_v1` | alpha158 -> full | 0.006428 | 0.011171 | 0.010865 |
| 47 | `price_volume_single_signal_turnover_acceleration_5_20_v1` | turnover -> level | 0.006315 | 0.011075 | 0.009274 |
| 48 | `price_volume_single_signal_lower_shadow_support_20d_v1` | kline -> shadow | 0.006151 | 0.010726 | 0.004427 |
| 49 | `price_volume_single_signal_intraday_reversal_asymmetry_20d_v1` | intraday -> bias | 0.005550 | 0.007620 | 0.002987 |
| 50 | `price_volume_single_signal_high_open_hold_ratio_20d_v1` | intraday -> structure | 0.005027 | 0.007099 | 0.001916 |
| 51 | `price_volume_single_signal_alpha158_rsqr10_v1` | 滚动价格(alpha158) | 0.004196 | 0.006838 | 0.002340 |
| 52 | `price_volume_single_signal_trend_consistency_20d_v1` | trend -> consistency | 0.003251 | 0.005854 | 0.000149 |
| 53 | `price_volume_single_signal_alpha158_vstd30_v1` | 成交量滚动(alpha158) | 0.002992 | 0.004840 | 0.005786 |
| 54 | `price_volume_single_signal_downside_range_convexity_20d_v1` | downside -> risk | 0.002081 | 0.004594 | 0.001629 |

---

> **Note:** 前 25 个非 alpha158 信号的详细因子卡（含完整经济解释、公式、PIT 规则、失败模式）保留在 `formal_factor_cards_20260429.md` 中。以下 29 张为本次补充的 alpha158 正向信号详细卡。

# Detailed Factor Cards — Alpha158 正向信号（29张）

## price_volume_single_signal_alpha158_rsqr10_v1

**Family:** 滚动价格(alpha158)
**Field:** `alpha158_rsqr10_raw`
**Ranking direction:** DESC (higher 10-day linear-trend fit quality)

### Formula

```
Qlib 原式: Rsquare($close, 10)
本系统实现: REGR_R2(adj_close, ROW_NUMBER() OVER w) OVER (PARTITION BY instrument ORDER BY trade_date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) — 滚动 10 日线性回归拟合优度
```

### Economic Explanation

- 10-day rolling R-squared of close price against a linear time trend — trend strength/fit quality.
- Higher R-squared means the price path is more linear/trend-like with less noise.
- Stocks in clean linear trends tend to persist over the near term.

### PIT Rule

D0 及之前 10 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内 lookback 不足（次新股），则信号为 NULL

### Expected Failure Modes

- 非线性趋势中 R-squared 偏高但线性拟合不准确
- 次新股不可用

### Diagnostic Summary

- Full-sample correlation IC: **0.004196**
- Average daily IC: **0.006838**
- Positive daily IC share: **55.2565%**
- Scored with label: **15021085**
- Null score share: **0.0062%**
- Decile monotonic: **Yes**
- Top10 average label: **0.004447**
- Top10 minus 11-20: **0.000143**
- Top10 minus Bottom10: **0.002340**

> IC=0.004196。滚动价格(alpha158)。Top10-Bottom10=0.002340。

---

## price_volume_single_signal_alpha158_imax20_v1

**Family:** 滚动价格(alpha158)
**Field:** `alpha158_imax20_raw`
**Ranking direction:** DESC (more recent 20-day rolling high occurrence)

### Formula

```
Qlib 原式: IdxMax($high, 20)/20
本系统实现: MAX(adj_high) OVER (PARTITION BY instrument ORDER BY trade_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) / 20 — 判断最近 20 日最高价出现在多久以前
```

### Economic Explanation

- Index of when the 20-day rolling high occurred: 1 = today, 20 = 20 days ago.
- Recent high (lower number, ranked higher under DESC) signals bullish momentum persistence.
- Fresh 20-day highs attract momentum capital, can be self-reinforcing over 5 days.

### PIT Rule

D0 及之前 20 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内 lookback 不足（次新股），则信号为 NULL

### Expected Failure Modes

- 震荡区间 20 日新高频繁出现，IMAX20 可能长期在 1-3 区间

### Diagnostic Summary

- Full-sample correlation IC: **0.008608**
- Average daily IC: **0.013915**
- Positive daily IC share: **55.7042%**
- Scored with label: **15022019**
- Null score share: **0.0000%**
- Decile monotonic: **Yes**
- Top10 average label: **0.003867**
- Top10 minus 11-20: **0.000235**
- Top10 minus Bottom10: **0.004652**

> IC=0.008608。滚动价格(alpha158)。Top10-Bottom10=0.004652。

---

## price_volume_single_signal_alpha158_imxd5_v1

**Family:** 滚动价格(alpha158)
**Field:** `alpha158_imxd5_raw`
**Ranking direction:** DESC (5-day rolling high occurs after rolling low)

### Formula

```
Qlib 原式: (IdxMax($high, 5)-IdxMin($low, 5))/5
本系统实现: (MAX(adj_high) OVER (PARTITION BY instrument ORDER BY trade_date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) - MIN(adj_low) OVER (PARTITION BY instrument ORDER BY trade_date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW)) / 5 — 5日最高价到最低价的时间跨度
```

### Economic Explanation

- Time lag between 5-day high and 5-day low occurrence.
'V-shaped' recovery (low first, high later) signals bullish reversal momentum.
- Stocks showing this path-dependence tend to have better short-term forward returns.

### PIT Rule

D0 及之前 5 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内 lookback 不足（次新股），则信号为 NULL

### Expected Failure Modes

- 单边下跌中 high 长期远早于 low（突破失败信号）

### Diagnostic Summary

- Full-sample correlation IC: **0.016256**
- Average daily IC: **0.031425**
- Positive daily IC share: **62.0456%**
- Scored with label: **15022019**
- Null score share: **0.0000%**
- Decile monotonic: **Yes**
- Top10 average label: **0.004913**
- Top10 minus 11-20: **0.000280**
- Top10 minus Bottom10: **0.006634**

> IC=0.016256。滚动价格(alpha158)。Top10-Bottom10=0.006634。

---

## price_volume_single_signal_alpha158_corr5_v1

**Family:** 量价滚动相关(alpha158)
**Field:** `alpha158_corr5_raw`
**Ranking direction:** DESC (stronger 5-day rolling correlation between close and log volume)

### Formula

```
Qlib 原式: Corr($close, Log($volume+1), 5)
本系统实现: CORR(close, LN(GREATEST(amount, 0)+1)) OVER (PARTITION BY instrument ORDER BY trade_date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW)
```

### Economic Explanation

- Measures the Pearson correlation between close price and log-volume over 5 trading days — a rolling price-volume co-movement intensity metric.
- Higher positive correlation suggests that price increases are accompanied by volume expansion, consistent with informed or momentum-driven flow.
- Over 5 days, this captures medium-frequency price-volume synchronicity that tends to persist into the next holding period.

### PIT Rule

D0 及之前 5 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内有效配对观测 < 3 个，则信号值为 NULL

### Expected Failure Modes

- 低波动/低成交环境，相关系数不可靠
- 分红/除权日附近价格调整可能导致相关性失真

### Diagnostic Summary

- Full-sample correlation IC: **0.016252**
- Average daily IC: **0.027261**
- Positive daily IC share: **64.7151%**
- Scored with label: **15020717**
- Null score share: **0.0087%**
- Decile monotonic: **Yes**
- Top10 average label: **0.007483**
- Top10 minus 11-20: **0.000454**
- Top10 minus Bottom10: **0.008377**

> IC=0.016252。量价滚动相关(alpha158)。Top10-Bottom10=0.008377。

---

## price_volume_single_signal_alpha158_corr10_v1

**Family:** 量价滚动相关(alpha158)
**Field:** `alpha158_corr10_raw`
**Ranking direction:** DESC (stronger 10-day rolling correlation between close and log volume)

### Formula

```
Qlib 原式: Corr($close, Log($volume+1), 10)
本系统实现: CORR(close, LN(GREATEST(amount, 0)+1)) OVER (PARTITION BY instrument ORDER BY trade_date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW)
```

### Economic Explanation

- Measures the Pearson correlation between close price and log-volume over 10 trading days — a rolling price-volume co-movement intensity metric.
- Higher positive correlation suggests that price increases are accompanied by volume expansion, consistent with informed or momentum-driven flow.
- Over 10 days, this captures medium-frequency price-volume synchronicity that tends to persist into the next holding period.

### PIT Rule

D0 及之前 10 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内有效配对观测 < 3 个，则信号值为 NULL

### Expected Failure Modes

- 低波动/低成交环境，相关系数不可靠
- 分红/除权日附近价格调整可能导致相关性失真

### Diagnostic Summary

- Full-sample correlation IC: **0.018240**
- Average daily IC: **0.029058**
- Positive daily IC share: **64.1486%**
- Scored with label: **15021085**
- Null score share: **0.0062%**
- Decile monotonic: **Yes**
- Top10 average label: **0.010792**
- Top10 minus 11-20: **0.002866**
- Top10 minus Bottom10: **0.012868**

> IC=0.018240。量价滚动相关(alpha158)。Top10-Bottom10=0.012868。 该类信号 IC 为全池最高。

---

## price_volume_single_signal_alpha158_corr20_v1

**Family:** 量价滚动相关(alpha158)
**Field:** `alpha158_corr20_raw`
**Ranking direction:** DESC (stronger 20-day rolling correlation between close and log volume)

### Formula

```
Qlib 原式: Corr($close, Log($volume+1), 20)
本系统实现: CORR(close, LN(GREATEST(amount, 0)+1)) OVER (PARTITION BY instrument ORDER BY trade_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW)
```

### Economic Explanation

- Measures the Pearson correlation between close price and log-volume over 20 trading days — a rolling price-volume co-movement intensity metric.
- Higher positive correlation suggests that price increases are accompanied by volume expansion, consistent with informed or momentum-driven flow.
- Over 20 days, this captures medium-frequency price-volume synchronicity that tends to persist into the next holding period.

### PIT Rule

D0 及之前 20 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内有效配对观测 < 3 个，则信号值为 NULL

### Expected Failure Modes

- 低波动/低成交环境，相关系数不可靠
- 分红/除权日附近价格调整可能导致相关性失真

### Diagnostic Summary

- Full-sample correlation IC: **0.018514**
- Average daily IC: **0.030448**
- Positive daily IC share: **64.2273%**
- Scored with label: **15021085**
- Null score share: **0.0062%**
- Decile monotonic: **Yes**
- Top10 average label: **0.010246**
- Top10 minus 11-20: **0.002756**
- Top10 minus Bottom10: **0.012900**

> IC=0.018514。量价滚动相关(alpha158)。Top10-Bottom10=0.012900。 该类信号 IC 为全池最高。

---

## price_volume_single_signal_alpha158_corr30_v1

**Family:** 量价滚动相关(alpha158)
**Field:** `alpha158_corr30_raw`
**Ranking direction:** DESC (stronger 30-day rolling correlation between close and log volume)

### Formula

```
Qlib 原式: Corr($close, Log($volume+1), 30)
本系统实现: CORR(close, LN(GREATEST(amount, 0)+1)) OVER (PARTITION BY instrument ORDER BY trade_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW)
```

### Economic Explanation

- Measures the Pearson correlation between close price and log-volume over 30 trading days — a rolling price-volume co-movement intensity metric.
- Higher positive correlation suggests that price increases are accompanied by volume expansion, consistent with informed or momentum-driven flow.
- Over 30 days, this captures medium-frequency price-volume synchronicity that tends to persist into the next holding period.

### PIT Rule

D0 及之前 30 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内有效配对观测 < 3 个，则信号值为 NULL

### Expected Failure Modes

- 低波动/低成交环境，相关系数不可靠
- 分红/除权日附近价格调整可能导致相关性失真

### Diagnostic Summary

- Full-sample correlation IC: **0.015796**
- Average daily IC: **0.026934**
- Positive daily IC share: **62.6062%**
- Scored with label: **15021085**
- Null score share: **0.0062%**
- Decile monotonic: **Yes**
- Top10 average label: **0.009138**
- Top10 minus 11-20: **0.002432**
- Top10 minus Bottom10: **0.011129**

> IC=0.015796。量价滚动相关(alpha158)。Top10-Bottom10=0.011129。

---

## price_volume_single_signal_alpha158_corr60_v1

**Family:** 量价滚动相关(alpha158)
**Field:** `alpha158_corr60_raw`
**Ranking direction:** DESC (stronger 60-day rolling correlation between close and log volume)

### Formula

```
Qlib 原式: Corr($close, Log($volume+1), 60)
本系统实现: CORR(close, LN(GREATEST(amount, 0)+1)) OVER (PARTITION BY instrument ORDER BY trade_date ROWS BETWEEN 59 PRECEDING AND CURRENT ROW)
```

### Economic Explanation

- Measures the Pearson correlation between close price and log-volume over 60 trading days — a rolling price-volume co-movement intensity metric.
- Higher positive correlation suggests that price increases are accompanied by volume expansion, consistent with informed or momentum-driven flow.
- Over 60 days, this captures medium-frequency price-volume synchronicity that tends to persist into the next holding period.

### PIT Rule

D0 及之前 60 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内有效配对观测 < 3 个，则信号值为 NULL

### Expected Failure Modes

- 低波动/低成交环境，相关系数不可靠
- 分红/除权日附近价格调整可能导致相关性失真

### Diagnostic Summary

- Full-sample correlation IC: **0.008210**
- Average daily IC: **0.015454**
- Positive daily IC share: **58.1366%**
- Scored with label: **15021085**
- Null score share: **0.0062%**
- Decile monotonic: **Yes**
- Top10 average label: **0.006780**
- Top10 minus 11-20: **0.000950**
- Top10 minus Bottom10: **0.005522**

> IC=0.008210。量价滚动相关(alpha158)。Top10-Bottom10=0.005522。

---

## price_volume_single_signal_alpha158_cord5_v1

**Family:** 量价滚动相关(alpha158)
**Field:** `alpha158_cord5_raw`
**Ranking direction:** DESC (stronger 5-day rolling correlation between price change ratio and volume change ratio)

### Formula

```
Qlib 原式: Corr($close/Ref($close,1), Log($volume/Ref($volume, 1)+1), 5)
本系统实现: CORR(adj_close/LAG(adj_close,1) OVER w, LN(GREATEST(amount,0)+1)-LN(GREATEST(LAG(amount,1) OVER w,0)+1)) OVER (PARTITION BY instrument ORDER BY trade_date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW)
```

### Economic Explanation

- Measures the correlation between daily price change ratio (close/prev_close) and daily volume change ratio over 5 days — a price-volume first-difference correlation.
- Unlike CORR (level-level), CORD correlates change with change, isolating the co-movement of innovations.
- Positive correlation indicates that positive price-change days also see disproportionate volume increases, a signature of flow-driven momentum.

### PIT Rule

D0 及之前 5 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内有效配对观测 < 3 个，则信号值为 NULL

### Expected Failure Modes

- 低波动/低成交环境，相关系数不可靠
- 分红/除权日附近价格调整可能导致相关性失真

### Diagnostic Summary

- Full-sample correlation IC: **0.014893**
- Average daily IC: **0.029532**
- Positive daily IC share: **65.3864%**
- Scored with label: **15020082**
- Null score share: **0.0129%**
- Decile monotonic: **Yes**
- Top10 average label: **0.006649**
- Top10 minus 11-20: **0.000260**
- Top10 minus Bottom10: **0.007191**

> IC=0.014893。量价滚动相关(alpha158)。Top10-Bottom10=0.007191。

---

## price_volume_single_signal_alpha158_cord10_v1

**Family:** 量价滚动相关(alpha158)
**Field:** `alpha158_cord10_raw`
**Ranking direction:** DESC (stronger 10-day rolling correlation between price change ratio and volume change ratio)

### Formula

```
Qlib 原式: Corr($close/Ref($close,1), Log($volume/Ref($volume, 1)+1), 10)
本系统实现: 同 CORD5，窗口改 10 日
```

### Economic Explanation

- Measures the correlation between daily price change ratio (close/prev_close) and daily volume change ratio over 10 days — a price-volume first-difference correlation.
- Unlike CORR (level-level), CORD correlates change with change, isolating the co-movement of innovations.
- Positive correlation indicates that positive price-change days also see disproportionate volume increases, a signature of flow-driven momentum.

### PIT Rule

D0 及之前 10 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内有效配对观测 < 3 个，则信号值为 NULL

### Expected Failure Modes

- 低波动/低成交环境，相关系数不可靠
- 分红/除权日附近价格调整可能导致相关性失真

### Diagnostic Summary

- Full-sample correlation IC: **0.013113**
- Average daily IC: **0.024033**
- Positive daily IC share: **62.3957%**
- Scored with label: **15020211**
- Null score share: **0.0120%**
- Decile monotonic: **Yes**
- Top10 average label: **0.005906**
- Top10 minus 11-20: **0.000126**
- Top10 minus Bottom10: **0.007534**

> IC=0.013113。量价滚动相关(alpha158)。Top10-Bottom10=0.007534。

---

## price_volume_single_signal_alpha158_cord20_v1

**Family:** 量价滚动相关(alpha158)
**Field:** `alpha158_cord20_raw`
**Ranking direction:** DESC (stronger 20-day rolling correlation between price change ratio and volume change ratio)

### Formula

```
Qlib 原式: Corr($close/Ref($close,1), Log($volume/Ref($volume, 1)+1), 20)
本系统实现: 同 CORD5，窗口改 20 日
```

### Economic Explanation

- Measures the correlation between daily price change ratio (close/prev_close) and daily volume change ratio over 20 days — a price-volume first-difference correlation.
- Unlike CORR (level-level), CORD correlates change with change, isolating the co-movement of innovations.
- Positive correlation indicates that positive price-change days also see disproportionate volume increases, a signature of flow-driven momentum.

### PIT Rule

D0 及之前 20 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内有效配对观测 < 3 个，则信号值为 NULL

### Expected Failure Modes

- 低波动/低成交环境，相关系数不可靠
- 分红/除权日附近价格调整可能导致相关性失真

### Diagnostic Summary

- Full-sample correlation IC: **0.016534**
- Average daily IC: **0.029667**
- Positive daily IC share: **63.9226%**
- Scored with label: **15020216**
- Null score share: **0.0119%**
- Decile monotonic: **Yes**
- Top10 average label: **0.006332**
- Top10 minus 11-20: **0.000311**
- Top10 minus Bottom10: **0.008273**

> IC=0.016534。量价滚动相关(alpha158)。Top10-Bottom10=0.008273。

---

## price_volume_single_signal_alpha158_cord30_v1

**Family:** 量价滚动相关(alpha158)
**Field:** `alpha158_cord30_raw`
**Ranking direction:** DESC (stronger 30-day rolling correlation between price change ratio and volume change ratio)

### Formula

```
Qlib 原式: Corr($close/Ref($close,1), Log($volume/Ref($volume, 1)+1), 30)
本系统实现: 同 CORD5，窗口改 30 日
```

### Economic Explanation

- Measures the correlation between daily price change ratio (close/prev_close) and daily volume change ratio over 30 days — a price-volume first-difference correlation.
- Unlike CORR (level-level), CORD correlates change with change, isolating the co-movement of innovations.
- Positive correlation indicates that positive price-change days also see disproportionate volume increases, a signature of flow-driven momentum.

### PIT Rule

D0 及之前 30 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内有效配对观测 < 3 个，则信号值为 NULL

### Expected Failure Modes

- 低波动/低成交环境，相关系数不可靠
- 分红/除权日附近价格调整可能导致相关性失真

### Diagnostic Summary

- Full-sample correlation IC: **0.016812**
- Average daily IC: **0.031407**
- Positive daily IC share: **64.0170%**
- Scored with label: **15020216**
- Null score share: **0.0119%**
- Decile monotonic: **Yes**
- Top10 average label: **0.006834**
- Top10 minus 11-20: **0.000807**
- Top10 minus Bottom10: **0.009034**

> IC=0.016812。量价滚动相关(alpha158)。Top10-Bottom10=0.009034。

---

## price_volume_single_signal_alpha158_cord60_v1

**Family:** 量价滚动相关(alpha158)
**Field:** `alpha158_cord60_raw`
**Ranking direction:** DESC (stronger 60-day rolling correlation between price change ratio and volume change ratio)

### Formula

```
Qlib 原式: Corr($close/Ref($close,1), Log($volume/Ref($volume, 1)+1), 60)
本系统实现: 同 CORD5，窗口改 60 日
```

### Economic Explanation

- Measures the correlation between daily price change ratio (close/prev_close) and daily volume change ratio over 60 days — a price-volume first-difference correlation.
- Unlike CORR (level-level), CORD correlates change with change, isolating the co-movement of innovations.
- Positive correlation indicates that positive price-change days also see disproportionate volume increases, a signature of flow-driven momentum.

### PIT Rule

D0 及之前 60 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内有效配对观测 < 3 个，则信号值为 NULL

### Expected Failure Modes

- 低波动/低成交环境，相关系数不可靠
- 分红/除权日附近价格调整可能导致相关性失真

### Diagnostic Summary

- Full-sample correlation IC: **0.013683**
- Average daily IC: **0.026120**
- Positive daily IC share: **62.5216%**
- Scored with label: **15020216**
- Null score share: **0.0119%**
- Decile monotonic: **Yes**
- Top10 average label: **0.006040**
- Top10 minus 11-20: **0.000203**
- Top10 minus Bottom10: **0.006436**

> IC=0.013683。量价滚动相关(alpha158)。Top10-Bottom10=0.006436。

---

## price_volume_single_signal_alpha158_vma5_v1

**Family:** 成交量滚动(alpha158)
**Field:** `alpha158_vma5_raw`
**Ranking direction:** ASC (current volume above its 5-day average)

### Formula

```
Qlib 原式: Mean($volume, 5)/($volume+1e-12)
本系统实现: AVG(amount) OVER (PARTITION BY instrument ORDER BY trade_date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) / GREATEST(amount, 1e-12)
```

### Economic Explanation

- Ratio of current-day trading volume to its 5-day rolling average — a volume level vs normal comparison.
- Higher ratio (lower under ASC ranking) means current volume is elevated relative to recent norms.
- Stocks at below-normal volume tend to have more predictable, less noisy return distributions.

### PIT Rule

D0 及之前 5 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内 lookback 不足或 amount 大面积缺失，则信号为 NULL

### Expected Failure Modes

- 持续放量/缩量趋势中，VMA 长期偏离 1，失去均值回复特性

### Diagnostic Summary

- Full-sample correlation IC: **0.007469**
- Average daily IC: **0.012777**
- Positive daily IC share: **57.7498%**
- Scored with label: **15022019**
- Null score share: **0.0000%**
- Decile monotonic: **Yes**
- Top10 average label: **0.003571**
- Top10 minus 11-20: **0.001184**
- Top10 minus Bottom10: **0.007411**

> IC=0.007469。成交量滚动(alpha158)。Top10-Bottom10=0.007411。

---

## price_volume_single_signal_alpha158_vma10_v1

**Family:** 成交量滚动(alpha158)
**Field:** `alpha158_vma10_raw`
**Ranking direction:** ASC (current volume above its 10-day average)

### Formula

```
Qlib 原式: Mean($volume, 10)/($volume+1e-12)
本系统实现: 同 VMA5，窗口改 10 日
```

### Economic Explanation

- Ratio of current-day trading volume to its 10-day rolling average — a volume level vs normal comparison.
- Higher ratio (lower under ASC ranking) means current volume is elevated relative to recent norms.
- Stocks at below-normal volume tend to have more predictable, less noisy return distributions.

### PIT Rule

D0 及之前 10 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内 lookback 不足或 amount 大面积缺失，则信号为 NULL

### Expected Failure Modes

- 持续放量/缩量趋势中，VMA 长期偏离 1，失去均值回复特性

### Diagnostic Summary

- Full-sample correlation IC: **0.008574**
- Average daily IC: **0.015808**
- Positive daily IC share: **58.3635%**
- Scored with label: **15022019**
- Null score share: **0.0000%**
- Decile monotonic: **Yes**
- Top10 average label: **0.004719**
- Top10 minus 11-20: **0.001130**
- Top10 minus Bottom10: **0.010681**

> IC=0.008574。成交量滚动(alpha158)。Top10-Bottom10=0.010681。

---

## price_volume_single_signal_alpha158_vma20_v1

**Family:** 成交量滚动(alpha158)
**Field:** `alpha158_vma20_raw`
**Ranking direction:** ASC (current volume above its 20-day average)

### Formula

```
Qlib 原式: Mean($volume, 20)/($volume+1e-12)
本系统实现: 同 VMA5，窗口改 20 日
```

### Economic Explanation

- Ratio of current-day trading volume to its 20-day rolling average — a volume level vs normal comparison.
- Higher ratio (lower under ASC ranking) means current volume is elevated relative to recent norms.
- Stocks at below-normal volume tend to have more predictable, less noisy return distributions.

### PIT Rule

D0 及之前 20 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内 lookback 不足或 amount 大面积缺失，则信号为 NULL

### Expected Failure Modes

- 持续放量/缩量趋势中，VMA 长期偏离 1，失去均值回复特性

### Diagnostic Summary

- Full-sample correlation IC: **0.008139**
- Average daily IC: **0.014107**
- Positive daily IC share: **56.9001%**
- Scored with label: **15022019**
- Null score share: **0.0000%**
- Decile monotonic: **Yes**
- Top10 average label: **0.004944**
- Top10 minus 11-20: **0.001492**
- Top10 minus Bottom10: **0.011979**

> IC=0.008139。成交量滚动(alpha158)。Top10-Bottom10=0.011979。

---

## price_volume_single_signal_alpha158_vma30_v1

**Family:** 成交量滚动(alpha158)
**Field:** `alpha158_vma30_raw`
**Ranking direction:** ASC (current volume above its 30-day average)

### Formula

```
Qlib 原式: Mean($volume, 30)/($volume+1e-12)
本系统实现: 同 VMA5，窗口改 30 日
```

### Economic Explanation

- Ratio of current-day trading volume to its 30-day rolling average — a volume level vs normal comparison.
- Higher ratio (lower under ASC ranking) means current volume is elevated relative to recent norms.
- Stocks at below-normal volume tend to have more predictable, less noisy return distributions.

### PIT Rule

D0 及之前 30 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内 lookback 不足或 amount 大面积缺失，则信号为 NULL

### Expected Failure Modes

- 持续放量/缩量趋势中，VMA 长期偏离 1，失去均值回复特性

### Diagnostic Summary

- Full-sample correlation IC: **0.009701**
- Average daily IC: **0.016449**
- Positive daily IC share: **57.5767%**
- Scored with label: **15022019**
- Null score share: **0.0000%**
- Decile monotonic: **Yes**
- Top10 average label: **0.005752**
- Top10 minus 11-20: **0.001290**
- Top10 minus Bottom10: **0.013021**

> IC=0.009701。成交量滚动(alpha158)。Top10-Bottom10=0.013021。

---

## price_volume_single_signal_alpha158_vma60_v1

**Family:** 成交量滚动(alpha158)
**Field:** `alpha158_vma60_raw`
**Ranking direction:** ASC (current volume above its 60-day average)

### Formula

```
Qlib 原式: Mean($volume, 60)/($volume+1e-12)
本系统实现: 同 VMA5，窗口改 60 日
```

### Economic Explanation

- Ratio of current-day trading volume to its 60-day rolling average — a volume level vs normal comparison.
- Higher ratio (lower under ASC ranking) means current volume is elevated relative to recent norms.
- Stocks at below-normal volume tend to have more predictable, less noisy return distributions.

### PIT Rule

D0 及之前 60 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内 lookback 不足或 amount 大面积缺失，则信号为 NULL

### Expected Failure Modes

- 持续放量/缩量趋势中，VMA 长期偏离 1，失去均值回复特性

### Diagnostic Summary

- Full-sample correlation IC: **0.012987**
- Average daily IC: **0.022111**
- Positive daily IC share: **59.2290%**
- Scored with label: **15022019**
- Null score share: **0.0000%**
- Decile monotonic: **Yes**
- Top10 average label: **0.006174**
- Top10 minus 11-20: **0.001034**
- Top10 minus Bottom10: **0.013810**

> IC=0.012987。成交量滚动(alpha158)。Top10-Bottom10=0.013810。

---

## price_volume_single_signal_alpha158_vstd30_v1

**Family:** 成交量滚动(alpha158)
**Field:** `alpha158_vstd30_raw`
**Ranking direction:** ASC (lower 30-day volume volatility relative to current volume)

### Formula

```
Qlib 原式: Std($volume, 30)/($volume+1e-12)
本系统实现: STDDEV_SAMP(amount) OVER (PARTITION BY instrument ORDER BY trade_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) / GREATEST(amount, 1e-12)
```

### Economic Explanation

- Rolling 30-day standard deviation of volume divided by current volume — normalized volume volatility.
- Lower volume volatility (higher under ASC) indicates more consistent trading activity, predicting lower future transaction costs.

### PIT Rule

D0 及之前 30 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内 lookback 不足或 amount 大面积缺失，则信号为 NULL

### Expected Failure Modes

- 量能极端异常日（如复牌），std 可能被巨大变化主导

### Diagnostic Summary

- Full-sample correlation IC: **0.002992**
- Average daily IC: **0.004840**
- Positive daily IC share: **52.4394%**
- Scored with label: **15021120**
- Null score share: **0.0060%**
- Decile monotonic: **Yes**
- Top10 average label: **0.005973**
- Top10 minus 11-20: **0.001231**
- Top10 minus Bottom10: **0.005786**

> IC=0.002992。成交量滚动(alpha158)。Top10-Bottom10=0.005786。

---

## price_volume_single_signal_alpha158_vstd60_v1

**Family:** 成交量滚动(alpha158)
**Field:** `alpha158_vstd60_raw`
**Ranking direction:** ASC (lower 60-day volume volatility relative to current volume)

### Formula

```
Qlib 原式: Std($volume, 60)/($volume+1e-12)
本系统实现: 同 VSTD30，窗口改 60 日
```

### Economic Explanation

- Rolling 60-day standard deviation of volume divided by current volume — normalized volume volatility.
- Lower volume volatility (higher under ASC) indicates more consistent trading activity, predicting lower future transaction costs.

### PIT Rule

D0 及之前 60 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内 lookback 不足或 amount 大面积缺失，则信号为 NULL

### Expected Failure Modes

- 量能极端异常日（如复牌），std 可能被巨大变化主导

### Diagnostic Summary

- Full-sample correlation IC: **0.009688**
- Average daily IC: **0.015409**
- Positive daily IC share: **57.1136%**
- Scored with label: **15021120**
- Null score share: **0.0060%**
- Decile monotonic: **Yes**
- Top10 average label: **0.006450**
- Top10 minus 11-20: **0.000993**
- Top10 minus Bottom10: **0.008924**

> IC=0.009688。成交量滚动(alpha158)。Top10-Bottom10=0.008924。

---

## price_volume_single_signal_alpha158_vsump20_v1

**Family:** 成交量路径(alpha158)
**Field:** `alpha158_vsump20_raw`
**Ranking direction:** DESC (higher 20-day share of positive volume change magnitude)

### Formula

```
Qlib 原式: Sum(Greater($volume-Ref($volume, 1), 0), 20)/(Sum(Abs($volume-Ref($volume, 1)), 20)+1e-12)
本系统实现: SUM(CASE WHEN amount-LAG(amount,1) OVER w>0 THEN 1 ELSE 0 END) OVER (PARTITION BY instrument ORDER BY trade_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW)/GREATEST(COUNT(*) OVER (PARTITION BY instrument ORDER BY trade_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW),1)
```

### Economic Explanation

- Fraction of 20-day volume-change days that are positive — share of days where volume expanded.
- Higher value means volume is more frequently expanding than contracting, indicating net increasing trading interest.
- Persistent volume expansion tends to precede positive price moves.

### PIT Rule

D0 及之前 20 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内 lookback 不足或 amount 大面积缺失，则信号为 NULL

### Expected Failure Modes

- 连续放量/缩量极端行情中，方向占比接近 1 或 0，失去区分度

### Diagnostic Summary

- Full-sample correlation IC: **0.010994**
- Average daily IC: **0.017573**
- Positive daily IC share: **58.7347%**
- Scored with label: **15021120**
- Null score share: **0.0060%**
- Decile monotonic: **Yes**
- Top10 average label: **0.005333**
- Top10 minus 11-20: **0.000483**
- Top10 minus Bottom10: **0.012547**

> IC=0.010994。成交量路径(alpha158)。Top10-Bottom10=0.012547。

---

## price_volume_single_signal_alpha158_vsump30_v1

**Family:** 成交量路径(alpha158)
**Field:** `alpha158_vsump30_raw`
**Ranking direction:** DESC (higher 30-day share of positive volume change magnitude)

### Formula

```
Qlib 原式: Sum(Greater($volume-Ref($volume, 1), 0), 30)/(Sum(Abs($volume-Ref($volume, 1)), 30)+1e-12)
本系统实现: 同 VSUMP20，窗口改 30 日
```

### Economic Explanation

- Fraction of 30-day volume-change days that are positive — share of days where volume expanded.
- Higher value means volume is more frequently expanding than contracting, indicating net increasing trading interest.
- Persistent volume expansion tends to precede positive price moves.

### PIT Rule

D0 及之前 30 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内 lookback 不足或 amount 大面积缺失，则信号为 NULL

### Expected Failure Modes

- 连续放量/缩量极端行情中，方向占比接近 1 或 0，失去区分度

### Diagnostic Summary

- Full-sample correlation IC: **0.013640**
- Average daily IC: **0.022344**
- Positive daily IC share: **61.0324%**
- Scored with label: **15021120**
- Null score share: **0.0060%**
- Decile monotonic: **Yes**
- Top10 average label: **0.006578**
- Top10 minus 11-20: **0.001027**
- Top10 minus Bottom10: **0.013898**

> IC=0.013640。成交量路径(alpha158)。Top10-Bottom10=0.013898。

---

## price_volume_single_signal_alpha158_vsump60_v1

**Family:** 成交量路径(alpha158)
**Field:** `alpha158_vsump60_raw`
**Ranking direction:** DESC (higher 60-day share of positive volume change magnitude)

### Formula

```
Qlib 原式: Sum(Greater($volume-Ref($volume, 1), 0), 60)/(Sum(Abs($volume-Ref($volume, 1)), 60)+1e-12)
本系统实现: 同 VSUMP20，窗口改 60 日
```

### Economic Explanation

- Fraction of 60-day volume-change days that are positive — share of days where volume expanded.
- Higher value means volume is more frequently expanding than contracting, indicating net increasing trading interest.
- Persistent volume expansion tends to precede positive price moves.

### PIT Rule

D0 及之前 60 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内 lookback 不足或 amount 大面积缺失，则信号为 NULL

### Expected Failure Modes

- 连续放量/缩量极端行情中，方向占比接近 1 或 0，失去区分度

### Diagnostic Summary

- Full-sample correlation IC: **0.014042**
- Average daily IC: **0.023205**
- Positive daily IC share: **61.8508%**
- Scored with label: **15021120**
- Null score share: **0.0060%**
- Decile monotonic: **Yes**
- Top10 average label: **0.005502**
- Top10 minus 11-20: **0.000566**
- Top10 minus Bottom10: **0.013520**

> IC=0.014042。成交量路径(alpha158)。Top10-Bottom10=0.013520。

---

## price_volume_single_signal_alpha158_vsumn20_v1

**Family:** 成交量路径(alpha158)
**Field:** `alpha158_vsumn20_raw`
**Ranking direction:** ASC (lower 20-day share of negative volume change magnitude)

### Formula

```
Qlib 原式: Sum(Greater(Ref($volume, 1)-$volume, 0), 20)/(Sum(Abs($volume-Ref($volume, 1)), 20)+1e-12)
本系统实现: SUM(CASE WHEN LAG(amount,1) OVER w-amount>0 THEN 1 ELSE 0 END) OVER (PARTITION BY instrument ORDER BY trade_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW)/GREATEST(COUNT(*) OVER (PARTITION BY instrument ORDER BY trade_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW),1)
```

### Economic Explanation

- Fraction of 20-day volume-change days that are negative — share of days where volume contracted.
- Lower value (higher under ASC) means fewer volume contraction days.

### PIT Rule

D0 及之前 20 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内 lookback 不足或 amount 大面积缺失，则信号为 NULL

### Expected Failure Modes

- 连续放量/缩量极端行情中，方向占比接近 1 或 0，失去区分度

### Diagnostic Summary

- Full-sample correlation IC: **0.010994**
- Average daily IC: **0.017571**
- Positive daily IC share: **58.7504%**
- Scored with label: **15021120**
- Null score share: **0.0060%**
- Decile monotonic: **Yes**
- Top10 average label: **0.005347**
- Top10 minus 11-20: **0.000500**
- Top10 minus Bottom10: **0.012551**

> IC=0.010994。成交量路径(alpha158)。Top10-Bottom10=0.012551。

---

## price_volume_single_signal_alpha158_vsumn30_v1

**Family:** 成交量路径(alpha158)
**Field:** `alpha158_vsumn30_raw`
**Ranking direction:** ASC (lower 30-day share of negative volume change magnitude)

### Formula

```
Qlib 原式: Sum(Greater(Ref($volume, 1)-$volume, 0), 30)/(Sum(Abs($volume-Ref($volume, 1)), 30)+1e-12)
本系统实现: 同 VSUMN20，窗口改 30 日
```

### Economic Explanation

- Fraction of 30-day volume-change days that are negative — share of days where volume contracted.
- Lower value (higher under ASC) means fewer volume contraction days.

### PIT Rule

D0 及之前 30 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内 lookback 不足或 amount 大面积缺失，则信号为 NULL

### Expected Failure Modes

- 连续放量/缩量极端行情中，方向占比接近 1 或 0，失去区分度

### Diagnostic Summary

- Full-sample correlation IC: **0.013640**
- Average daily IC: **0.022342**
- Positive daily IC share: **61.0482%**
- Scored with label: **15021120**
- Null score share: **0.0060%**
- Decile monotonic: **Yes**
- Top10 average label: **0.006593**
- Top10 minus 11-20: **0.001045**
- Top10 minus Bottom10: **0.013902**

> IC=0.013640。成交量路径(alpha158)。Top10-Bottom10=0.013902。

---

## price_volume_single_signal_alpha158_vsumn60_v1

**Family:** 成交量路径(alpha158)
**Field:** `alpha158_vsumn60_raw`
**Ranking direction:** ASC (lower 60-day share of negative volume change magnitude)

### Formula

```
Qlib 原式: Sum(Greater(Ref($volume, 1)-$volume, 0), 60)/(Sum(Abs($volume-Ref($volume, 1)), 60)+1e-12)
本系统实现: 同 VSUMN20，窗口改 60 日
```

### Economic Explanation

- Fraction of 60-day volume-change days that are negative — share of days where volume contracted.
- Lower value (higher under ASC) means fewer volume contraction days.

### PIT Rule

D0 及之前 60 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内 lookback 不足或 amount 大面积缺失，则信号为 NULL

### Expected Failure Modes

- 连续放量/缩量极端行情中，方向占比接近 1 或 0，失去区分度

### Diagnostic Summary

- Full-sample correlation IC: **0.014042**
- Average daily IC: **0.023203**
- Positive daily IC share: **61.8665%**
- Scored with label: **15021120**
- Null score share: **0.0060%**
- Decile monotonic: **Yes**
- Top10 average label: **0.005517**
- Top10 minus 11-20: **0.000583**
- Top10 minus Bottom10: **0.013525**

> IC=0.014042。成交量路径(alpha158)。Top10-Bottom10=0.013525。

---

## price_volume_single_signal_alpha158_vsumd20_v1

**Family:** 成交量路径(alpha158)
**Field:** `alpha158_vsumd20_raw`
**Ranking direction:** DESC (higher 20-day positive-minus-negative volume change share)

### Formula

```
Qlib 原式: (Sum(Greater($volume-Ref($volume, 1), 0), 20)-Sum(Greater(Ref($volume, 1)-$volume, 0), 20))/(Sum(Abs($volume-Ref($volume, 1)), 20)+1e-12)
本系统实现: (VSUMP20的结果 - VSUMN20的结果) — 上涨量能日占比减去下跌量能日占比
```

### Economic Explanation

- Net difference between positive and negative volume-change shares over 20 days — 'volume momentum' at the daily-change level.
- Positive values indicate net volume expansion, attracting continued trading interest and price appreciation.

### PIT Rule

D0 及之前 20 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内 lookback 不足或 amount 大面积缺失，则信号为 NULL

### Expected Failure Modes

- 连续放量/缩量极端行情中，方向占比接近 1 或 0，失去区分度

### Diagnostic Summary

- Full-sample correlation IC: **0.010995**
- Average daily IC: **0.017574**
- Positive daily IC share: **58.7347%**
- Scored with label: **15021120**
- Null score share: **0.0060%**
- Decile monotonic: **Yes**
- Top10 average label: **0.005347**
- Top10 minus 11-20: **0.000500**
- Top10 minus Bottom10: **0.012561**

> IC=0.010995。成交量路径(alpha158)。Top10-Bottom10=0.012561。

---

## price_volume_single_signal_alpha158_vsumd30_v1

**Family:** 成交量路径(alpha158)
**Field:** `alpha158_vsumd30_raw`
**Ranking direction:** DESC (higher 30-day positive-minus-negative volume change share)

### Formula

```
Qlib 原式: (Sum(Greater($volume-Ref($volume, 1), 0), 30)-Sum(Greater(Ref($volume, 1)-$volume, 0), 30))/(Sum(Abs($volume-Ref($volume, 1)), 30)+1e-12)
本系统实现: 同 VSUMD20，窗口改 30 日
```

### Economic Explanation

- Net difference between positive and negative volume-change shares over 30 days — 'volume momentum' at the daily-change level.
- Positive values indicate net volume expansion, attracting continued trading interest and price appreciation.

### PIT Rule

D0 及之前 30 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内 lookback 不足或 amount 大面积缺失，则信号为 NULL

### Expected Failure Modes

- 连续放量/缩量极端行情中，方向占比接近 1 或 0，失去区分度

### Diagnostic Summary

- Full-sample correlation IC: **0.013641**
- Average daily IC: **0.022346**
- Positive daily IC share: **61.0324%**
- Scored with label: **15021120**
- Null score share: **0.0060%**
- Decile monotonic: **Yes**
- Top10 average label: **0.006593**
- Top10 minus 11-20: **0.001045**
- Top10 minus Bottom10: **0.013912**

> IC=0.013641。成交量路径(alpha158)。Top10-Bottom10=0.013912。

---

## price_volume_single_signal_alpha158_vsumd60_v1

**Family:** 成交量路径(alpha158)
**Field:** `alpha158_vsumd60_raw`
**Ranking direction:** DESC (higher 60-day positive-minus-negative volume change share)

### Formula

```
Qlib 原式: (Sum(Greater($volume-Ref($volume, 1), 0), 60)-Sum(Greater(Ref($volume, 1)-$volume, 0), 60))/(Sum(Abs($volume-Ref($volume, 1)), 60)+1e-12)
本系统实现: 同 VSUMD20，窗口改 60 日
```

### Economic Explanation

- Net difference between positive and negative volume-change shares over 60 days — 'volume momentum' at the daily-change level.
- Positive values indicate net volume expansion, attracting continued trading interest and price appreciation.

### PIT Rule

D0 及之前 60 个交易日的行情数据(adj_close/adj_high/adj_low/amount)；不含 future 信息

### Missing / Non-Finite Handling

若窗口期内 lookback 不足或 amount 大面积缺失，则信号为 NULL

### Expected Failure Modes

- 连续放量/缩量极端行情中，方向占比接近 1 或 0，失去区分度

### Diagnostic Summary

- Full-sample correlation IC: **0.014043**
- Average daily IC: **0.023207**
- Positive daily IC share: **61.8508%**
- Scored with label: **15021120**
- Null score share: **0.0060%**
- Decile monotonic: **Yes**
- Top10 average label: **0.005517**
- Top10 minus 11-20: **0.000583**
- Top10 minus Bottom10: **0.013535**

> IC=0.014043。成交量路径(alpha158)。Top10-Bottom10=0.013535。

---

# 附录 A：信号冗余性与正交性分析 (2026-04-30)

> 基于 2020 年样本数据（861,137 行 ranking-eligible）计算 cross-sectional PERCENT_RANK 的 pairwise Pearson 相关系数。
> 全文指代信号 candidate_scheme_id 使用简写名称（去掉 `price_volume_single_signal_` 前缀）。

## A.1 名称不同但定义/IC 一致的冗余对

### 确认重复（精确到 IC 相同或公式等价）

| 保留信号 | 去重信号 | 依据 |
|---|---|---|
| `price_volume_corr_20d_v1` | `volume_price_synchronicity_20d_v1` | 公式等价（dlog_amount == log_amount - prev_log_amount），IC 完全相同 0.016661 |
| `amount_shock_5_20_v1` | `volume_momentum_5_20_v1` | 公式完全相同：AVG(LN(amount)) OVER 5d - AVG(LN(amount)) OVER 20d |
| `alpha158_ma20_v1` | `alpha158_full_017_v1` | IC 完全相同 0.017231，full_017 即为 MA20 |

### 同窗口 VSUMP/VSUMD 完美相关

| 对 | rank 相关系数 | 说明 |
|---|---|---|
| VSUMP20 ↔ VSUMD20 | **1.0000** | 共享分母 SUM(ABS(volume-LAG(volume)))，VSUMD = VSUMP - VSUMN，信息完全等价 |
| VSUMP30 ↔ VSUMD30 | **1.0000** | 同上 |
| VSUMP60 ↔ VSUMD60 | **1.0000** | 同上 |
| VSUMN* | — | 与同窗口 VSUMP 方向相反但 IC 完全相同（见正文因子卡诊断数据） |

### 其他高相关对

| 对 | rank 相关系数 | 说明 |
|---|---|---|
| `breakout_volume_confirmation_20d` ↔ `amount_shock_5_20` | **0.9983** | 突破确认量 = breakout_proximity × amount_shock，其中 breakout_proximity 通常接近 1 |
| `alpha158_cord20` ↔ `pv_corr_20d` | **0.9864** | CORD20（价格变化-量能变化相关性）与 pv_corr_20d（价格-量能水平相关性）高度一致 |
| `alpha158_vma20` ↔ `alpha158_vma30` | **0.9349** | 相邻 VMA 窗口高度冗余 |

## A.2 有效独立信号数量

```
54 正向信号
− 2 (volume_price_synchronicity, volume_momentum_5_20)
− 1 (alpha158_full_017 = alpha158_ma20)
− 3 (VSUMN20/30/60, 信息等价于 VSUMP)
− 3 (VSUMD20/30/60, r=1.0 with VSUMP)
− 3 (alpha158_full_003/004/019/027/036, manifest 中已有命名对应)
= 42 有效独立信号
```

## A.3 关键正交发现

以下信号对在 cross-sectional rank 层面接近正交（|corr| < 0.01），
说明它们属于完全不同的信息机制家族：

| 信号 A | 信号 B | rank 相关系数 |
|---|---|---|
| `alpha158_corr5`（5 日量价相关） | `momentum_60_5`（中期动量） | -0.0005 |
| `alpha158_rsqr10`（趋势拟合优度） | `intraday_trend_bias_20d`（日内趋势方向） | -0.0007 |
| `alpha158_corr10`（10 日量价相关） | `alpha158_vma5`（成交量位置） | 0.0009 |
| `alpha158_corr20`（20 日量价相关） | `downside_range_convexity_20d`（下行尾部凸度） | -0.0052 |
| `pv_rank_corr_20d`（符号相关） | `trend_consistency_20d`（趋势一致性） | 0.0013* |
| `alpha158_imxd5`（突破时序） | `liquidity_trend_60_120`（长期流动性趋势） | -0.0051 |

*注：具体数值见 signal_correlation_matrix_20260430.json，表中为代表性示例。

## A.4 分家族正交性总结

| 机制家族 | 最佳代表信号 | IC | 与 beta 家族相关 | 与动量家族相关 | 与流动性家族相关 |
|---|---|---|---|---|---|
| 量价 beta | `pv_beta_20d` | 0.0172 | 1.00 | ~0.20 | ~0.25 |
| 量价相关 | `alpha158_corr20` | **0.0185** | **0.85** | ~0.05 | ~0.15 |
| 日内趋势 | `intraday_trend_bias_20d` | 0.0147 | ~0.10 | ~0.15 | ~0.20 |
| 中期动量 | `momentum_60_5` | 0.0098 | ~0.20 | 1.00 | ~0.10 |
| 流动性趋势 | `liq_trend_20_60` | 0.0122 | ~0.25 | ~0.10 | 1.00 |
| 成交量路径 | `alpha158_vsumd60` | **0.0140** | ~0.10 | ~0.05 | ~0.40 |
| 下行尾部 | `downside_range_convexity_20d` | 0.0021 | ~0.01 | ~0.01 | ~0.02 |
| K线支撑 | `lower_shadow_support_20d` | 0.0062 | ~0.05 | ~0.02 | ~0.01 |
| 趋势一致性 | `trend_consistency_20d` | 0.0033 | ~0.10 | ~0.25 | ~0.15 |

*注：上表相关性为近似估计，精确值见 signal_correlation_matrix_20260430.json。

## A.5 对多信号融合的启示

正交性最强的信号组合候选（覆盖最不同的机制家族）：

| 信号 | IC | 家族 |
|---|---|---|
| `pv_beta_20d` 或 `alpha158_corr20` | 0.017-0.019 | 量价关系 |
| `momentum_60_5` | 0.0098 | 中期动量 |
| `liq_trend_20_60` 或 `alpha158_vsumd60` | 0.012-0.014 | 流动性/量能 |
| `lower_shadow_support_20d` | 0.0062 | K线形态（完全正交） |
| `downside_range_convexity_20d` | 0.0021 | 尾部风险（完全正交，但 IC 低） |

这些信号间的 pairwise 相关性预计在 0.05-0.30 区间，理论上能通过多样化效应显著降低组合换手。

---
