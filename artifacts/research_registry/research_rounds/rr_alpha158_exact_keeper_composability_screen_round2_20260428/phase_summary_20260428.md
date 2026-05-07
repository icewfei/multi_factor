# rr_alpha158_exact_keeper_composability_screen_round2_20260428 phase summary

## Summary

This round screens four consolidated Alpha158 exact keepers against the frozen v18 core family using a static three-component overlay-style screen only.

- `promising_count(较有希望数量) = 0`
- `mixed_count(混合数量) = 4`
- `overlap_drop_tolerance(重叠下降容忍阈值) = 0.2`

## Results

- `price_volume_screen_alpha158_imxd5_composability_v1`: `composability_screen_mixed`
  - `field(字段) = alpha158_imxd5_raw`
  - `screen_full_sample_corr_ic(筛查全样本IC) = 0.019926`
  - `screen_top10_minus_rank11_20(筛查前10减11-20) = -0.000731`
  - `reference_avg_top10_overlap_next_day(参考次日前10平均重叠) = 7.223071`
  - `screen_avg_top10_overlap_next_day(筛查次日前10平均重叠) = 3.945599`

- `price_volume_screen_alpha158_low0_composability_v1`: `composability_screen_mixed`
  - `field(字段) = alpha158_low0_raw`
  - `screen_full_sample_corr_ic(筛查全样本IC) = 0.016402`
  - `screen_top10_minus_rank11_20(筛查前10减11-20) = 0.001290`
  - `reference_avg_top10_overlap_next_day(参考次日前10平均重叠) = 7.223071`
  - `screen_avg_top10_overlap_next_day(筛查次日前10平均重叠) = 2.037826`

- `price_volume_screen_alpha158_rsqr10_composability_v1`: `composability_screen_mixed`
  - `field(字段) = alpha158_rsqr10_raw`
  - `screen_full_sample_corr_ic(筛查全样本IC) = 0.013495`
  - `screen_top10_minus_rank11_20(筛查前10减11-20) = -0.000420`
  - `reference_avg_top10_overlap_next_day(参考次日前10平均重叠) = 7.223071`
  - `screen_avg_top10_overlap_next_day(筛查次日前10平均重叠) = 3.859495`

- `price_volume_screen_alpha158_vstd60_composability_v1`: `composability_screen_mixed`
  - `field(字段) = alpha158_vstd60_raw`
  - `screen_full_sample_corr_ic(筛查全样本IC) = 0.015203`
  - `screen_top10_minus_rank11_20(筛查前10减11-20) = 0.001411`
  - `reference_avg_top10_overlap_next_day(参考次日前10平均重叠) = 7.223071`
  - `screen_avg_top10_overlap_next_day(筛查次日前10平均重叠) = 5.570682`

## Decision

Advance only `composability_screen_promising` candidates into later overlay or restrained family tests.
Keep `composability_screen_mixed` candidates as standalone keepers only until further evidence appears.
