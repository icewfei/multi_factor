# rr_price_volume_single_signal_discovery_v18_round5_20260425 phase summary

## Summary

This round evaluated ten orthogonal atomic price-volume signals under the frozen `price_volume_v18_refresh_hysteresis` operational contract.

The final classification is:

- `price_volume_single_signal_signed_amount_imbalance_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_turnover_acceleration_5_20_v1`: `signal_edge_positive`
- `price_volume_single_signal_volume_price_synchronicity_20d_v1`: `signal_edge_positive`
- `price_volume_single_signal_trend_efficiency_60d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_range_compression_10_40_v1`: `signal_edge_negative`
- `price_volume_single_signal_breakout_failure_pressure_20d_v1`: `signal_edge_negative`
- `price_volume_single_signal_downside_gap_recovery_10d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_up_amount_persistence_20d_v1`: `signal_edge_positive`
- `price_volume_single_signal_turnover_stability_20d_v1`: `signal_edge_negative`
- `price_volume_single_signal_intraday_recovery_skew_20d_v1`: `signal_edge_mixed`

## Newly retained clean positive keepers

- `price_volume_single_signal_turnover_acceleration_5_20_v1`
  - `full_sample_corr_ic(全样本IC) = 0.006315`
  - `avg_daily_ic(平均日IC) = 0.011075`
  - `positive_daily_ic_share(正IC日占比) = 0.561133`
  - `avg_label_top10(前10平均标签) = 0.002816`
  - `avg_label_rank11_20(11-20名平均标签) = 0.002374`
  - `avg_label_bottom10(后10平均标签) = -0.006457`

- `price_volume_single_signal_volume_price_synchronicity_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.016661`
  - `avg_daily_ic(平均日IC) = 0.029966`
  - `positive_daily_ic_share(正IC日占比) = 0.636764`
  - `avg_label_top10(前10平均标签) = 0.007764`
  - `avg_label_rank11_20(11-20名平均标签) = 0.006709`
  - `avg_label_bottom10(后10平均标签) = -0.001614`

- `price_volume_single_signal_up_amount_persistence_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.009374`
  - `avg_daily_ic(平均日IC) = 0.013587`
  - `positive_daily_ic_share(正IC日占比) = 0.549174`
  - `avg_label_top10(前10平均标签) = 0.006377`
  - `avg_label_rank11_20(11-20名平均标签) = 0.005613`
  - `avg_label_bottom10(后10平均标签) = -0.000546`

## Mixed signals

- `price_volume_single_signal_signed_amount_imbalance_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.007297`
  - `avg_daily_ic(平均日IC) = 0.013883`
  - `positive_daily_ic_share(正IC日占比) = 0.547286`
  - `avg_label_top10(前10平均标签) = 0.003251`
  - `avg_label_rank11_20(11-20名平均标签) = 0.004183`

- `price_volume_single_signal_trend_efficiency_60d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.008624`
  - `avg_daily_ic(平均日IC) = 0.014350`
  - `positive_daily_ic_share(正IC日占比) = 0.544120`
  - `avg_label_top10(前10平均标签) = -0.000591`
  - `avg_label_rank11_20(11-20名平均标签) = 0.003123`

- `price_volume_single_signal_downside_gap_recovery_10d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.004330`
  - `avg_daily_ic(平均日IC) = 0.005501`
  - `positive_daily_ic_share(正IC日占比) = 0.538086`
  - `avg_label_top10(前10平均标签) = 0.003726`
  - `avg_label_rank11_20(11-20名平均标签) = 0.003834`

- `price_volume_single_signal_intraday_recovery_skew_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.005507`
  - `avg_daily_ic(平均日IC) = 0.007581`
  - `positive_daily_ic_share(正IC日占比) = 0.509520`
  - `avg_label_top10(前10平均标签) = 0.004645`
  - `avg_label_rank11_20(11-20名平均标签) = 0.004063`

## Rejected signals

- `price_volume_single_signal_range_compression_10_40_v1`
  - `full_sample_corr_ic(全样本IC) = -0.003399`
  - `avg_daily_ic(平均日IC) = -0.003309`
  - `positive_daily_ic_share(正IC日占比) = 0.483084`
  - `avg_label_top10(前10平均标签) = -0.002053`
  - `avg_label_rank11_20(11-20名平均标签) = -0.000413`
  - `avg_label_bottom10(后10平均标签) = 0.003911`

- `price_volume_single_signal_breakout_failure_pressure_20d_v1`
  - `full_sample_corr_ic(全样本IC) = -0.006629`
  - `avg_daily_ic(平均日IC) = -0.010484`
  - `positive_daily_ic_share(正IC日占比) = 0.458379`
  - `avg_label_top10(前10平均标签) = -0.000766`
  - `avg_label_rank11_20(11-20名平均标签) = 0.000982`
  - `avg_label_bottom10(后10平均标签) = 0.004129`

- `price_volume_single_signal_turnover_stability_20d_v1`
  - `full_sample_corr_ic(全样本IC) = -0.015466`
  - `avg_daily_ic(平均日IC) = -0.027256`
  - `positive_daily_ic_share(正IC日占比) = 0.397860`
  - `avg_label_top10(前10平均标签) = -0.005670`
  - `avg_label_rank11_20(11-20名平均标签) = -0.002341`
  - `avg_label_bottom10(后10平均标签) = 0.003324`

## Decision

- `continue_pool_expansion(继续扩单信号池) = false`
- `reopen_family_construction(回到family构造) = true`
- reason: Round 5 produced at least one new clean positive keeper, which is enough new information to reopen family construction with a disciplined one-step composition or screening test.
