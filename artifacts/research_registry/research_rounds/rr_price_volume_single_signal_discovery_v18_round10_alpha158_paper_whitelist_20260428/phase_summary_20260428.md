# rr_price_volume_single_signal_discovery_v18_round10_alpha158_paper_whitelist_20260428 phase summary

## Summary

This round evaluated six whitelist-only Alpha158/literature-inspired atomic price-volume signals under the frozen `price_volume_v18_refresh_hysteresis` operational contract.

The final classification is:

- `price_volume_single_signal_amihud_illiquidity_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_turnover_concentration_hhi_20d_v1`: `signal_edge_negative`
- `price_volume_single_signal_close_to_vwap_bias_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_intraday_range_skew_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_gap_reversal_intensity_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_signed_dollar_flow_persistence_20d_v1`: `signal_edge_negative`
## Mixed signals

- `price_volume_single_signal_amihud_illiquidity_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.024665`
  - `avg_daily_ic(平均日IC) = 0.036689`
  - `positive_daily_ic_share(正IC日占比) = 0.644060`
  - `avg_label_top10(前10平均标签) = 0.006116`
  - `avg_label_rank11_20(11-20名平均标签) = 0.007397`

- `price_volume_single_signal_close_to_vwap_bias_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.016715`
  - `avg_daily_ic(平均日IC) = 0.021815`
  - `positive_daily_ic_share(正IC日占比) = 0.560661`
  - `avg_label_top10(前10平均标签) = 0.005720`
  - `avg_label_rank11_20(11-20名平均标签) = 0.006220`

- `price_volume_single_signal_intraday_range_skew_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.002082`
  - `avg_daily_ic(平均日IC) = 0.002195`
  - `positive_daily_ic_share(正IC日占比) = 0.495043`
  - `avg_label_top10(前10平均标签) = 0.003087`
  - `avg_label_rank11_20(11-20名平均标签) = 0.003865`

- `price_volume_single_signal_gap_reversal_intensity_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.001094`
  - `avg_daily_ic(平均日IC) = 0.000924`
  - `positive_daily_ic_share(正IC日占比) = 0.493390`
  - `avg_label_top10(前10平均标签) = 0.002917`
  - `avg_label_rank11_20(11-20名平均标签) = 0.003675`

## Rejected signals

- `price_volume_single_signal_turnover_concentration_hhi_20d_v1`
  - `full_sample_corr_ic(全样本IC) = -0.013125`
  - `avg_daily_ic(平均日IC) = -0.021195`
  - `positive_daily_ic_share(正IC日占比) = 0.391660`
  - `avg_label_top10(前10平均标签) = -0.003467`
  - `avg_label_rank11_20(11-20名平均标签) = -0.002496`
  - `avg_label_bottom10(后10平均标签) = 0.006145`

- `price_volume_single_signal_signed_dollar_flow_persistence_20d_v1`
  - `full_sample_corr_ic(全样本IC) = -0.003156`
  - `avg_daily_ic(平均日IC) = -0.005082`
  - `positive_daily_ic_share(正IC日占比) = 0.455776`
  - `avg_label_top10(前10平均标签) = 0.000600`
  - `avg_label_rank11_20(11-20名平均标签) = 0.001926`
  - `avg_label_bottom10(后10平均标签) = -0.000446`

## Decision

- `continue_pool_expansion(继续扩单信号池) = true`
- `reopen_family_construction(回到family构造) = false`
- reason: Round 10 produced zero clean positive whitelist keepers, so we should continue whitelist-only atomic discovery rather than reopening family construction.
