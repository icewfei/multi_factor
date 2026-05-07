# Price-Volume Round8 + Composability Phase Decision (20260428)

## Decision

`price_volume_v18_refresh_hysteresis` continues as `working_reference(工作基准)`, and the current price-volume family tuning line stays paused.

## Why

- `round8` did add two new `signal_edge_positive(正向信号边际优势)` keepers:
  - `price_volume_single_signal_intraday_reversal_asymmetry_20d_v1`
  - `price_volume_single_signal_high_open_hold_ratio_20d_v1`
- But both later failed to clear clean composability promotion:
  - `rr_price_volume_intraday_reversal_asymmetry_composability_screen_20260428`
    - `classification(分类) = composability_screen_mixed`
    - `reference_avg_top10_overlap_next_day(参考次日前10平均重叠) = 7.223071`
    - `screen_avg_top10_overlap_next_day(筛查次日前10平均重叠) = 6.870378`
    - `overlap_drop(重叠下降) = -0.352693`
  - `rr_price_volume_high_open_hold_ratio_composability_screen_20260428`
    - `classification(分类) = composability_screen_mixed`
    - `reference_avg_top10_overlap_next_day(参考次日前10平均重叠) = 7.223071`
    - `screen_avg_top10_overlap_next_day(筛查次日前10平均重叠) = 7.140072`
    - `overlap_drop(重叠下降) = -0.082998`

The repeated pattern remains:

- standalone edge can be positive,
- static score layer can improve in parts,
- but additive monotonicity and/or head stability still degrade at promotion stage.

## Next Direction

1. Keep `v18` frozen as active `working_reference(工作基准)`.
2. Do not open a new family round from these two keepers.
3. Reopen a small `atomic single-signal discovery(原子单信号发现)` batch with only six mechanism-orthogonal candidates.
4. Apply a hard composability gate before any future promotion:
   - `screen_avg_top10_overlap_next_day(筛查次日前10平均重叠)` must not be lower than reference by more than `0.10`.
   - If `reference - screen > 0.10`, promotion is blocked regardless of other partial improvements.
