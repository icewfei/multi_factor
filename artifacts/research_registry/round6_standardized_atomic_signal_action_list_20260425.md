# round6 standardized atomic signal action list

## Decision

- `working_reference(工作基准)` 继续冻结为 `price_volume_v18_refresh_hysteresis`
- `new_family_construction(新family构造)`：`hold(暂缓)`
- `new_composability_screening(新的组合相容性筛查)`：`hold(暂缓)`
- `main_value_of_round6(round6 主价值)`：`standardization_and_dedup(标准化与去重)`，不是 `new_alpha_expansion(新增阿尔法扩容)`

## Keep

- `volume_price_synchronicity_20d_raw`
  - canonical candidate: `price_volume_single_signal_volume_price_synchronicity_20d_v1`
  - status: `watchlist_keeper_composability_mixed(观察名单保留，组合相容性混合)`
  - action: keep on watchlist, do not promote now

- `amount_shock_5_20_raw`
  - canonical candidate: `price_volume_single_signal_amount_shock_5_20_v1`
  - status: `active_keeper_composability_mixed(活跃保留，组合相容性混合)`
  - action: keep as canonical amount/volume shock mechanism, do not reopen overlay/family promotion now

## Merge

- `price_volume_corr_20d_raw -> volume_price_synchronicity_20d_raw`
  - action: treat as naming alias only, no separate future budget

- `volume_momentum_5_20_raw -> amount_shock_5_20_raw`
  - action: treat as naming alias only, no separate future budget

- `close_to_high_ratio_20d_raw -> close_location_value_20d_raw`
  - action: treat as naming alias only

- `upper_shadow_pressure_20d_raw -> upper_shadow_ratio_20d_raw`
  - action: treat as naming alias only

- `breakout_distance_20d_raw -> breakout_proximity_20d_raw`
  - action: treat as naming alias only

- `turnover_mean_reversion_gap_5_20_raw -> turnover_acceleration_5_20_raw`
  - action: treat as inverse-direction duplicate, not a new mechanism

## Drop

- `path_efficiency_60d_raw`
  - reason: `signal_edge_negative(负向信号边际优势)`
  - action: reject from active pipeline

- `range_compression_5_20_raw`
  - reason: `signal_edge_negative(负向信号边际优势)`
  - action: reject from active pipeline

## Mixed But Not Promotable

- `breakdown_distance_20d_raw`
  - status: `signal_edge_mixed(混合信号边际优势)`
  - action: archive as mixed, no immediate follow-up

- `downside_recovery_strength_10d_raw`
  - status: `signal_edge_mixed(混合信号边际优势)`
  - action: archive as mixed, no immediate follow-up

## Intake Rule For Next Round

- Any future candidate that is only a `naming_alias(命名别名)`, `inverse_direction_duplicate(反向重复)`, or obvious `horizon-near variant(近邻时窗变体)` of the merged set above should fail intake unless it includes an explicit `override_reason(覆盖理由)`.
- If a future candidate maps to `volume_price_synchronicity_20d_raw` or `amount_shock_5_20_raw`, it should be recorded under the canonical mechanism instead of opening a new discovery budget line.

## Bottom Line

- `round6(第6轮)` should be treated as a `standardization cleanup(标准化清理轮次)`.
- The practical next state is:
  - keep `v18` frozen
  - keep `volume_price_synchronicity_20d_raw` on watchlist
  - keep `amount_shock_5_20_raw` as canonical amount-shock mechanism
  - do not open a new family or overlay round from round6 alone
