# rr_price_volume_single_signal_discovery_v18_round7_orthogonal_20260425 phase summary

## Summary

This round evaluated ten more orthogonal atomic price-volume signals under the frozen `price_volume_v18_refresh_hysteresis` operational contract after explicitly treating round 6 as a standardization-and-dedup pass.

The final classification is:

- `price_volume_single_signal_return_autocorr_20d_v1`: `signal_edge_negative`
- `price_volume_single_signal_amount_autocorr_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_downside_volume_skew_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_upside_range_share_20d_v1`: `signal_edge_positive`
- `price_volume_single_signal_intraday_trend_bias_20d_v1`: `signal_edge_positive`
- `price_volume_single_signal_return_skew_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_amount_volatility_20d_v1`: `signal_edge_negative`
- `price_volume_single_signal_downside_gap_frequency_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_high_low_break_balance_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_downside_absorption_ratio_20d_v1`: `signal_edge_mixed`

## Newly retained clean positive keepers

- `price_volume_single_signal_upside_range_share_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.010329`
  - `avg_daily_ic(平均日IC) = 0.015721`
  - `positive_daily_ic_share(正IC日占比) = 0.551534`
  - `avg_label_top10(前10平均标签) = 0.004096`
  - `avg_label_rank11_20(11-20名平均标签) = 0.003965`
  - `avg_label_bottom10(后10平均标签) = -0.001307`

- `price_volume_single_signal_intraday_trend_bias_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.014740`
  - `avg_daily_ic(平均日IC) = 0.019716`
  - `positive_daily_ic_share(正IC日占比) = 0.555940`
  - `avg_label_top10(前10平均标签) = 0.005909`
  - `avg_label_rank11_20(11-20名平均标签) = 0.005601`
  - `avg_label_bottom10(后10平均标签) = -0.003439`

## Mixed signals

- `price_volume_single_signal_amount_autocorr_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.009756`
  - `avg_daily_ic(平均日IC) = 0.013687`
  - `positive_daily_ic_share(正IC日占比) = 0.578691`
  - `avg_label_top10(前10平均标签) = 0.005089`
  - `avg_label_rank11_20(11-20名平均标签) = 0.005323`

- `price_volume_single_signal_downside_volume_skew_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.006697`
  - `avg_daily_ic(平均日IC) = 0.012988`
  - `positive_daily_ic_share(正IC日占比) = 0.543981`
  - `avg_label_top10(前10平均标签) = 0.003118`
  - `avg_label_rank11_20(11-20名平均标签) = 0.004200`

- `price_volume_single_signal_return_skew_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.009823`
  - `avg_daily_ic(平均日IC) = 0.014188`
  - `positive_daily_ic_share(正IC日占比) = 0.587819`
  - `avg_label_top10(前10平均标签) = 0.002094`
  - `avg_label_rank11_20(11-20名平均标签) = 0.003052`

- `price_volume_single_signal_downside_gap_frequency_20d_v1`
  - `full_sample_corr_ic(全样本IC) = -0.002335`
  - `avg_daily_ic(平均日IC) = 0.002236`
  - `positive_daily_ic_share(正IC日占比) = 0.510936`
  - `avg_label_top10(前10平均标签) = 0.000704`
  - `avg_label_rank11_20(11-20名平均标签) = 0.003179`

- `price_volume_single_signal_high_low_break_balance_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.010611`
  - `avg_daily_ic(平均日IC) = 0.016597`
  - `positive_daily_ic_share(正IC日占比) = 0.550747`
  - `avg_label_top10(前10平均标签) = 0.001716`
  - `avg_label_rank11_20(11-20名平均标签) = 0.004666`

- `price_volume_single_signal_downside_absorption_ratio_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.005857`
  - `avg_daily_ic(平均日IC) = 0.008072`
  - `positive_daily_ic_share(正IC日占比) = 0.543824`
  - `avg_label_top10(前10平均标签) = 0.002743`
  - `avg_label_rank11_20(11-20名平均标签) = 0.004441`

## Rejected signals

- `price_volume_single_signal_return_autocorr_20d_v1`
  - `full_sample_corr_ic(全样本IC) = -0.005212`
  - `avg_daily_ic(平均日IC) = -0.009544`
  - `positive_daily_ic_share(正IC日占比) = 0.446176`
  - `avg_label_top10(前10平均标签) = 0.000651`
  - `avg_label_rank11_20(11-20名平均标签) = 0.001485`
  - `avg_label_bottom10(后10平均标签) = 0.001358`

- `price_volume_single_signal_amount_volatility_20d_v1`
  - `full_sample_corr_ic(全样本IC) = -0.017632`
  - `avg_daily_ic(平均日IC) = -0.028194`
  - `positive_daily_ic_share(正IC日占比) = 0.344193`
  - `avg_label_top10(前10平均标签) = -0.004945`
  - `avg_label_rank11_20(11-20名平均标签) = -0.001260`
  - `avg_label_bottom10(后10平均标签) = 0.005832`

## Decision

- `continue_pool_expansion(继续扩单信号池) = false`
- `reopen_family_construction(回到family构造) = true`
- reason: Round 7 produced at least one genuinely orthogonal clean positive keeper, which is enough new information to justify a later composability screen under the frozen v18 baseline.
