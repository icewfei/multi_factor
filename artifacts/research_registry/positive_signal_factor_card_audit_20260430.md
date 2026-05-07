# Positive Signal Factor Card Audit (20260430)

## Summary

- `historical_positive_signal_count(历史正向信号数) = 54`
- `factor_card_md_present_count(正式因子卡Markdown已建数) = 54`
- `factor_card_json_present_count(正式因子卡JSON已建数) = 54`
- `legacy_positive_card_registry_present_count(旧正向因子卡注册表已覆盖数) = 54`
- `current_keeper_count(当前保留信号数) = 3`
- `active_confirmatory_winner(活跃确认性赢家) = none`
- `strict_confirmatory_winner(严格确认性赢家) = none`

## Current Keepers

- `price_volume_single_signal_alpha158_cord30_v1`: `high-quality reserve atomic keeper(高质量储备原子信号)`
- `price_volume_single_signal_alpha158_corr30_v1`: `reserve atomic keeper(储备原子信号)`
- `price_volume_single_signal_alpha158_vsumd60_v1`: `reserve atomic keeper(储备原子信号)`

## Card Coverage Check

- `formal_factor_cards_20260430.md`: `54/54`
- `formal_factor_cards_20260430.json`: `54/54`
- `factor_card_registry_20260430.json` positive entries: `54/54`

## Positive Signal Inventory

| Candidate | Current Tier | Family | IC | AvgDailyIC | Formal MD Card | Formal JSON Card | Legacy Positive Registry |
|---|---|---|---:|---:|---|---|---|
| `price_volume_single_signal_alpha158_cord30_v1` | `high-quality reserve atomic keeper(高质量储备原子信号)` | 量价滚动相关(alpha158) | 0.016812 | 0.031407 | yes | yes | yes |
| `price_volume_single_signal_alpha158_corr30_v1` | `reserve atomic keeper(储备原子信号)` | 量价滚动相关(alpha158) | 0.015796 | 0.026934 | yes | yes | yes |
| `price_volume_single_signal_alpha158_vsumd60_v1` | `reserve atomic keeper(储备原子信号)` | 成交量路径(alpha158) | 0.014043 | 0.023207 | yes | yes | yes |
| `price_volume_single_signal_alpha158_corr20_v1` | `historical_positive_only` | 量价滚动相关(alpha158) | 0.018514 | 0.030448 | yes | yes | yes |
| `price_volume_single_signal_alpha158_corr10_v1` | `historical_positive_only` | 量价滚动相关(alpha158) | 0.018240 | 0.029058 | yes | yes | yes |
| `price_volume_single_signal_price_volume_beta_20d_v1` | `historical_positive_only` | price_volume -> beta | 0.017161 | 0.028287 | yes | yes | yes |
| `price_volume_single_signal_price_volume_corr_20d_v1` | `historical_positive_only` | price_volume -> correlation | 0.016661 | 0.029966 | yes | yes | yes |
| `price_volume_single_signal_volume_price_synchronicity_20d_v1` | `historical_positive_only` | price_volume -> correlation | 0.016661 | 0.029966 | yes | yes | yes |
| `price_volume_single_signal_alpha158_cord20_v1` | `historical_positive_only` | 量价滚动相关(alpha158) | 0.016534 | 0.029667 | yes | yes | yes |
| `price_volume_single_signal_alpha158_imxd5_v1` | `historical_positive_only` | 滚动价格(alpha158) | 0.016256 | 0.031425 | yes | yes | yes |
| `price_volume_single_signal_alpha158_corr5_v1` | `historical_positive_only` | 量价滚动相关(alpha158) | 0.016252 | 0.027261 | yes | yes | yes |
| `price_volume_single_signal_alpha158_cord5_v1` | `historical_positive_only` | 量价滚动相关(alpha158) | 0.014893 | 0.029532 | yes | yes | yes |
| `price_volume_single_signal_intraday_trend_bias_20d_v1` | `historical_positive_only` | intraday -> bias | 0.014740 | 0.019716 | yes | yes | yes |
| `price_volume_single_signal_alpha158_vsumn60_v1` | `historical_positive_only` | 成交量路径(alpha158) | 0.014042 | 0.023203 | yes | yes | yes |
| `price_volume_single_signal_alpha158_vsump60_v1` | `historical_positive_only` | 成交量路径(alpha158) | 0.014042 | 0.023205 | yes | yes | yes |
| `price_volume_single_signal_alpha158_cord60_v1` | `historical_positive_only` | 量价滚动相关(alpha158) | 0.013683 | 0.026120 | yes | yes | yes |
| `price_volume_single_signal_alpha158_vsumd30_v1` | `historical_positive_only` | 成交量路径(alpha158) | 0.013641 | 0.022346 | yes | yes | yes |
| `price_volume_single_signal_alpha158_vsumn30_v1` | `historical_positive_only` | 成交量路径(alpha158) | 0.013640 | 0.022342 | yes | yes | yes |
| `price_volume_single_signal_alpha158_vsump30_v1` | `historical_positive_only` | 成交量路径(alpha158) | 0.013640 | 0.022344 | yes | yes | yes |
| `price_volume_single_signal_alpha158_cord10_v1` | `historical_positive_only` | 量价滚动相关(alpha158) | 0.013113 | 0.024033 | yes | yes | yes |
| `price_volume_single_signal_alpha158_vma60_v1` | `historical_positive_only` | 成交量滚动(alpha158) | 0.012987 | 0.022111 | yes | yes | yes |
| `price_volume_single_signal_liquidity_trend_20_60_v1` | `historical_positive_only` | liquidity -> trend | 0.012159 | 0.018665 | yes | yes | yes |
| `price_volume_single_signal_alpha158_low0_v1` | `historical_positive_only` | alpha158 -> named | 0.011783 | 0.019262 | yes | yes | yes |
| `price_volume_single_signal_price_volume_rank_corr_20d_v1` | `historical_positive_only` | price_volume -> correlation | 0.011394 | 0.020216 | yes | yes | yes |
| `price_volume_single_signal_alpha158_full_036_v1` | `historical_positive_only` | alpha158 -> full | 0.011240 | 0.019715 | yes | yes | yes |
| `price_volume_single_signal_alpha158_full_003_v1` | `historical_positive_only` | alpha158 -> full | 0.011160 | 0.019319 | yes | yes | yes |
| `price_volume_single_signal_alpha158_vsumd20_v1` | `historical_positive_only` | 成交量路径(alpha158) | 0.010995 | 0.017574 | yes | yes | yes |
| `price_volume_single_signal_alpha158_vsumn20_v1` | `historical_positive_only` | 成交量路径(alpha158) | 0.010994 | 0.017571 | yes | yes | yes |
| `price_volume_single_signal_alpha158_vsump20_v1` | `historical_positive_only` | 成交量路径(alpha158) | 0.010994 | 0.017573 | yes | yes | yes |
| `price_volume_single_signal_alpha158_full_027_v1` | `historical_positive_only` | alpha158 -> full | 0.010886 | 0.018942 | yes | yes | yes |
| `price_volume_single_signal_upside_range_share_20d_v1` | `historical_positive_only` | intraday -> structure | 0.010329 | 0.015721 | yes | yes | yes |
| `price_volume_single_signal_momentum_60_5_v1` | `historical_positive_only` | momentum -> medium_term | 0.009758 | 0.013398 | yes | yes | yes |
| `price_volume_single_signal_alpha158_full_004_v1` | `historical_positive_only` | alpha158 -> full | 0.009717 | 0.017430 | yes | yes | yes |
| `price_volume_single_signal_alpha158_vma30_v1` | `historical_positive_only` | 成交量滚动(alpha158) | 0.009701 | 0.016449 | yes | yes | yes |
| `price_volume_single_signal_alpha158_vstd60_v1` | `historical_positive_only` | 成交量滚动(alpha158) | 0.009688 | 0.015409 | yes | yes | yes |
| `price_volume_single_signal_up_amount_persistence_20d_v1` | `historical_positive_only` | volume -> persistence | 0.009374 | 0.013587 | yes | yes | yes |
| `price_volume_single_signal_alpha158_imax20_v1` | `historical_positive_only` | 滚动价格(alpha158) | 0.008608 | 0.013915 | yes | yes | yes |
| `price_volume_single_signal_alpha158_vma10_v1` | `historical_positive_only` | 成交量滚动(alpha158) | 0.008574 | 0.015808 | yes | yes | yes |
| `price_volume_single_signal_liquidity_trend_60_120_v1` | `historical_positive_only` | liquidity -> trend | 0.008324 | 0.013666 | yes | yes | yes |
| `price_volume_single_signal_alpha158_corr60_v1` | `historical_positive_only` | 量价滚动相关(alpha158) | 0.008210 | 0.015454 | yes | yes | yes |
| `price_volume_single_signal_alpha158_vma20_v1` | `historical_positive_only` | 成交量滚动(alpha158) | 0.008139 | 0.014107 | yes | yes | yes |
| `price_volume_single_signal_alpha158_vma5_v1` | `historical_positive_only` | 成交量滚动(alpha158) | 0.007469 | 0.012777 | yes | yes | yes |
| `price_volume_single_signal_breakout_volume_confirmation_20d_v1` | `historical_positive_only` | breakout -> failure | 0.007258 | 0.011053 | yes | yes | yes |
| `price_volume_single_signal_amount_shock_5_20_v1` | `historical_positive_only` | liquidity -> shock | 0.007194 | 0.011316 | yes | yes | yes |
| `price_volume_single_signal_volume_momentum_5_20_v1` | `historical_positive_only` | turnover -> level | 0.007194 | 0.011316 | yes | yes | yes |
| `price_volume_single_signal_alpha158_full_019_v1` | `historical_positive_only` | alpha158 -> full | 0.006428 | 0.011171 | yes | yes | yes |
| `price_volume_single_signal_turnover_acceleration_5_20_v1` | `historical_positive_only` | turnover -> level | 0.006315 | 0.011075 | yes | yes | yes |
| `price_volume_single_signal_lower_shadow_support_20d_v1` | `historical_positive_only` | kline -> shadow | 0.006151 | 0.010726 | yes | yes | yes |
| `price_volume_single_signal_intraday_reversal_asymmetry_20d_v1` | `historical_positive_only` | intraday -> bias | 0.005550 | 0.007620 | yes | yes | yes |
| `price_volume_single_signal_high_open_hold_ratio_20d_v1` | `historical_positive_only` | intraday -> structure | 0.005027 | 0.007099 | yes | yes | yes |
| `price_volume_single_signal_alpha158_rsqr10_v1` | `historical_positive_only` | 滚动价格(alpha158) | 0.004196 | 0.006838 | yes | yes | yes |
| `price_volume_single_signal_trend_consistency_20d_v1` | `historical_positive_only` | trend -> consistency | 0.003251 | 0.005854 | yes | yes | yes |
| `price_volume_single_signal_alpha158_vstd30_v1` | `historical_positive_only` | 成交量滚动(alpha158) | 0.002992 | 0.004840 | yes | yes | yes |
| `price_volume_single_signal_downside_range_convexity_20d_v1` | `historical_positive_only` | downside -> risk | 0.002081 | 0.004594 | yes | yes | yes |

## Gaps

- `formal_factor_cards_20260430.md` 已覆盖全部 `54` 只历史正向信号。
- `formal_factor_cards_20260430.json` 已覆盖 `54` 只，仍缺 `0` 只。
- `factor_card_registry_20260430.json` 已覆盖 `54` 只正向信号。
- 当前 `reserve atomic keeper(储备原子信号)` / `high-quality reserve atomic keeper(高质量储备原子信号)` 的层级，主要写在阶段收口文档里，还没有完全回填到 candidate registry 的结构化状态字段。

