# rr_alpha158_exact_keeper_composability_screen_20260428 phase summary

## Summary

This round screens four consolidated Alpha158 exact keepers against the frozen v18 core family using a static three-component overlay-style screen only.

- `promising_count(较有希望数量) = 0`
- `mixed_count(混合数量) = 4`
- `overlap_drop_tolerance(重叠下降容忍阈值) = 0.2`

## Results

- `price_volume_screen_alpha158_corr20_composability_v1`: `composability_screen_mixed`
  - `field(字段) = alpha158_corr20_raw`
  - `screen_full_sample_corr_ic(筛查全样本IC) = 0.019527`
  - `screen_top10_minus_rank11_20(筛查前10减11-20) = 0.003073`
  - `reference_avg_top10_overlap_next_day(参考次日前10平均重叠) = 7.223071`
  - `screen_avg_top10_overlap_next_day(筛查次日前10平均重叠) = 6.876407`

- `price_volume_screen_alpha158_cord30_composability_v1`: `composability_screen_mixed`
  - `field(字段) = alpha158_cord30_raw`
  - `screen_full_sample_corr_ic(筛查全样本IC) = 0.017734`
  - `screen_top10_minus_rank11_20(筛查前10减11-20) = 0.001975`
  - `reference_avg_top10_overlap_next_day(参考次日前10平均重叠) = 7.223071`
  - `screen_avg_top10_overlap_next_day(筛查次日前10平均重叠) = 7.110932`

- `price_volume_screen_alpha158_vma60_composability_v1`: `composability_screen_mixed`
  - `field(字段) = alpha158_vma60_raw`
  - `screen_full_sample_corr_ic(筛查全样本IC) = 0.015952`
  - `screen_top10_minus_rank11_20(筛查前10减11-20) = 0.000858`
  - `reference_avg_top10_overlap_next_day(参考次日前10平均重叠) = 7.223071`
  - `screen_avg_top10_overlap_next_day(筛查次日前10平均重叠) = 5.068827`

- `price_volume_screen_alpha158_vsumd60_composability_v1`: `composability_screen_mixed`
  - `field(字段) = alpha158_vsumd60_raw`
  - `screen_full_sample_corr_ic(筛查全样本IC) = 0.015818`
  - `screen_top10_minus_rank11_20(筛查前10减11-20) = 0.001277`
  - `reference_avg_top10_overlap_next_day(参考次日前10平均重叠) = 7.223071`
  - `screen_avg_top10_overlap_next_day(筛查次日前10平均重叠) = 5.399155`

## Decision

Advance only `composability_screen_promising` candidates into later overlay or restrained family tests.
Keep `composability_screen_mixed` candidates as standalone keepers only until further evidence appears.
