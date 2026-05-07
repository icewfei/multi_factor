# price_volume_single_signal_momentum_20_5_v1 signal-edge diagnosis

- full_sample_corr_ic(全样本IC): `0.007226`
- avg_daily_ic(平均日IC): `0.008331`
- median_daily_ic(中位日IC): `0.004728`
- positive_daily_ic_share(正IC日占比): `0.515549`

## Top Slice
- avg_label_top10(前10平均标签): `0.000268`
- avg_label_rank11_20(11-20名平均标签): `0.003301`
- avg_label_bottom10(后10平均标签): `0.001003`
- top10_minus_rank11_20(前10减11-20): `-0.003032`

## Cutoff Gap
- avg_rank10_11_score_gap(第10/11名平均分数间距): `0.000535`
- median_rank10_11_score_gap(第10/11名中位分数间距): `0.000445`
- days_gap_lt_0_001(间距<0.001的天数): `6075` / `6342`

## Notes
- Manual direct diagnosis path used because the generic builder path was abnormally slow for this candidate.
