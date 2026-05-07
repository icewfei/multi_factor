# 54只正向因子的去重后 Canonical 清单 (20260430)

## 一句话结论

- 原始 `signal_edge_positive(正向信号)` 共 `54` 只。
- 物理去重收口后，压缩为 `25` 个 `canonical clusters(标准机制簇)`。
- 今后工作因子池应以这份 canonical 清单为准，不再直接把 54 只原始正向标签当作独立机制池。

## Summary

- `raw_positive_signal_count(原始正向信号数) = 54`
- `canonical_cluster_count(标准机制簇数) = 25`
- `current_reserve_keeper_cluster_count(当前reserve簇数) = 3`
- `historical_positive_canonical_cluster_count(历史正向但仍为标准簇数) = 19`
- `historical_positive_retired_cluster_count(历史正向但已退休簇数) = 2`
- `retired_noncanonical_pilot_cluster_count(非标准pilot簇数) = 1`

## Coverage Check

- `covered_unique_member_count(已覆盖唯一成员数) = 54`
- `duplicate_member_count(重复映射成员数) = 0`
- `missing_member_count(遗漏成员数) = 0`
- `extra_member_count(额外成员数) = 0`

## Canonical Clusters

### 1. `momentum_medium_term`

- `cluster_status(簇状态) = historical_positive_canonical`
- `mechanism_family(机制家族) = momentum`
- `relationship_type(关系类型) = single`
- `representative_candidate_scheme_id(代表候选) = price_volume_single_signal_momentum_60_5_v1`
- `member_count(成员数) = 1`
- `members(成员) = price_volume_single_signal_momentum_60_5_v1`
- reason: Baseline medium-term momentum anchor; no duplicate positive horizon retained in the current 54-signal pool.

### 2. `liquidity_trend`

- `cluster_status(簇状态) = historical_positive_canonical`
- `mechanism_family(机制家族) = liquidity_improvement`
- `relationship_type(关系类型) = horizon_variant_cluster`
- `representative_candidate_scheme_id(代表候选) = price_volume_single_signal_liquidity_trend_20_60_v1`
- `secondary_candidate_scheme_ids(次级变体) = price_volume_single_signal_liquidity_trend_60_120_v1`
- `member_count(成员数) = 2`
- `members(成员) = price_volume_single_signal_liquidity_trend_20_60_v1, price_volume_single_signal_liquidity_trend_60_120_v1`
- reason: Same liquidity-improvement mechanism across two horizons; retain 20/60 as the primary canonical label and 60/120 only as a slower variant inside the same cluster.

### 3. `turnover_acceleration`

- `cluster_status(簇状态) = historical_positive_canonical`
- `mechanism_family(机制家族) = turnover`
- `relationship_type(关系类型) = single`
- `representative_candidate_scheme_id(代表候选) = price_volume_single_signal_turnover_acceleration_5_20_v1`
- `member_count(成员数) = 1`
- `members(成员) = price_volume_single_signal_turnover_acceleration_5_20_v1`
- reason: Distinct turnover-rate acceleration mechanism, not an alias of amount-based shock.

### 4. `amount_shock`

- `cluster_status(簇状态) = historical_positive_canonical`
- `mechanism_family(机制家族) = liquidity_shock`
- `relationship_type(关系类型) = alias_cluster`
- `representative_candidate_scheme_id(代表候选) = price_volume_single_signal_amount_shock_5_20_v1`
- `member_count(成员数) = 2`
- `members(成员) = price_volume_single_signal_amount_shock_5_20_v1, price_volume_single_signal_volume_momentum_5_20_v1`
- reason: The two names describe the same 5/20 amount-expansion mechanism; canonical name is amount_shock_5_20.

### 5. `price_volume_synchronicity`

- `cluster_status(簇状态) = historical_positive_canonical`
- `mechanism_family(机制家族) = price_volume_confirmation`
- `relationship_type(关系类型) = alias_cluster`
- `representative_candidate_scheme_id(代表候选) = price_volume_single_signal_volume_price_synchronicity_20d_v1`
- `member_count(成员数) = 2`
- `members(成员) = price_volume_single_signal_volume_price_synchronicity_20d_v1, price_volume_single_signal_price_volume_corr_20d_v1`
- reason: The two labels are near-identical 20-day price-volume co-movement signals; canonical name is volume_price_synchronicity_20d.

### 6. `up_amount_persistence`

- `cluster_status(簇状态) = historical_positive_canonical`
- `mechanism_family(机制家族) = volume_persistence`
- `relationship_type(关系类型) = single`
- `representative_candidate_scheme_id(代表候选) = price_volume_single_signal_up_amount_persistence_20d_v1`
- `member_count(成员数) = 1`
- `members(成员) = price_volume_single_signal_up_amount_persistence_20d_v1`
- reason: Distinct persistence-of-up-volume mechanism.

### 7. `breakout_volume_confirmation`

- `cluster_status(簇状态) = historical_positive_retired`
- `mechanism_family(机制家族) = breakout_confirmation`
- `relationship_type(关系类型) = single`
- `representative_candidate_scheme_id(代表候选) = price_volume_single_signal_breakout_volume_confirmation_20d_v1`
- `member_count(成员数) = 1`
- `members(成员) = price_volume_single_signal_breakout_volume_confirmation_20d_v1`
- reason: Historically positive but family-level promotion failed badly; keep as retired historical evidence only.

### 8. `price_volume_beta`

- `cluster_status(簇状态) = historical_positive_canonical`
- `mechanism_family(机制家族) = price_volume_beta`
- `relationship_type(关系类型) = single`
- `representative_candidate_scheme_id(代表候选) = price_volume_single_signal_price_volume_beta_20d_v1`
- `member_count(成员数) = 1`
- `members(成员) = price_volume_single_signal_price_volume_beta_20d_v1`
- reason: Distinct return-to-volume-beta mechanism.

### 9. `price_volume_rank_corr`

- `cluster_status(簇状态) = historical_positive_canonical`
- `mechanism_family(机制家族) = price_volume_confirmation`
- `relationship_type(关系类型) = single`
- `representative_candidate_scheme_id(代表候选) = price_volume_single_signal_price_volume_rank_corr_20d_v1`
- `member_count(成员数) = 1`
- `members(成员) = price_volume_single_signal_price_volume_rank_corr_20d_v1`
- reason: Rank/sign-based robust variant, not identical to Pearson co-movement.

### 10. `intraday_trend_bias`

- `cluster_status(簇状态) = historical_positive_canonical`
- `mechanism_family(机制家族) = intraday_bias`
- `relationship_type(关系类型) = single`
- `representative_candidate_scheme_id(代表候选) = price_volume_single_signal_intraday_trend_bias_20d_v1`
- `member_count(成员数) = 1`
- `members(成员) = price_volume_single_signal_intraday_trend_bias_20d_v1`
- reason: Distinct intraday drift mechanism.

### 11. `intraday_reversal_asymmetry`

- `cluster_status(簇状态) = historical_positive_canonical`
- `mechanism_family(机制家族) = intraday_resilience`
- `relationship_type(关系类型) = single`
- `representative_candidate_scheme_id(代表候选) = price_volume_single_signal_intraday_reversal_asymmetry_20d_v1`
- `member_count(成员数) = 1`
- `members(成员) = price_volume_single_signal_intraday_reversal_asymmetry_20d_v1`
- reason: Distinct intraday recovery-vs-fade asymmetry mechanism.

### 12. `upside_range_share`

- `cluster_status(簇状态) = historical_positive_canonical`
- `mechanism_family(机制家族) = intraday_structure`
- `relationship_type(关系类型) = single`
- `representative_candidate_scheme_id(代表候选) = price_volume_single_signal_upside_range_share_20d_v1`
- `member_count(成员数) = 1`
- `members(成员) = price_volume_single_signal_upside_range_share_20d_v1`
- reason: Distinct up-day range participation mechanism.

### 13. `high_open_hold_ratio`

- `cluster_status(簇状态) = historical_positive_canonical`
- `mechanism_family(机制家族) = intraday_structure`
- `relationship_type(关系类型) = single`
- `representative_candidate_scheme_id(代表候选) = price_volume_single_signal_high_open_hold_ratio_20d_v1`
- `member_count(成员数) = 1`
- `members(成员) = price_volume_single_signal_high_open_hold_ratio_20d_v1`
- reason: Distinct high-open quality mechanism.

### 14. `lower_shadow_support`

- `cluster_status(簇状态) = historical_positive_canonical`
- `mechanism_family(机制家族) = kline_shadow_support`
- `relationship_type(关系类型) = single`
- `representative_candidate_scheme_id(代表候选) = price_volume_single_signal_lower_shadow_support_20d_v1`
- `member_count(成员数) = 1`
- `members(成员) = price_volume_single_signal_lower_shadow_support_20d_v1`
- reason: Distinct lower-shadow support mechanism.

### 15. `downside_range_convexity`

- `cluster_status(簇状态) = historical_positive_canonical`
- `mechanism_family(机制家族) = downside_tail_shape`
- `relationship_type(关系类型) = single`
- `representative_candidate_scheme_id(代表候选) = price_volume_single_signal_downside_range_convexity_20d_v1`
- `member_count(成员数) = 1`
- `members(成员) = price_volume_single_signal_downside_range_convexity_20d_v1`
- reason: Distinct downside-tail convexity mechanism.

### 16. `trend_consistency`

- `cluster_status(簇状态) = historical_positive_retired`
- `mechanism_family(机制家族) = trend_consistency`
- `relationship_type(关系类型) = single`
- `representative_candidate_scheme_id(代表候选) = price_volume_single_signal_trend_consistency_20d_v1`
- `member_count(成员数) = 1`
- `members(成员) = price_volume_single_signal_trend_consistency_20d_v1`
- reason: Historically positive, but explicitly retired from active keeper pool after later family evidence.

### 17. `alpha158_low0`

- `cluster_status(簇状态) = historical_positive_canonical`
- `mechanism_family(机制家族) = alpha158_close_location_support`
- `relationship_type(关系类型) = single`
- `representative_candidate_scheme_id(代表候选) = price_volume_single_signal_alpha158_low0_v1`
- `member_count(成员数) = 1`
- `members(成员) = price_volume_single_signal_alpha158_low0_v1`
- reason: Distinct Alpha158 close-location support mechanism.

### 18. `alpha158_rsqr10`

- `cluster_status(簇状态) = historical_positive_canonical`
- `mechanism_family(机制家族) = alpha158_trend_fit_quality`
- `relationship_type(关系类型) = single`
- `representative_candidate_scheme_id(代表候选) = price_volume_single_signal_alpha158_rsqr10_v1`
- `member_count(成员数) = 1`
- `members(成员) = price_volume_single_signal_alpha158_rsqr10_v1`
- reason: Distinct Alpha158 short-trend fit-quality mechanism.

### 19. `alpha158_path_ordering_breakout`

- `cluster_status(簇状态) = historical_positive_canonical`
- `mechanism_family(机制家族) = alpha158_path_ordering_breakout`
- `relationship_type(关系类型) = near_variant_cluster`
- `representative_candidate_scheme_id(代表候选) = price_volume_single_signal_alpha158_imxd5_v1`
- `secondary_candidate_scheme_ids(次级变体) = price_volume_single_signal_alpha158_imax20_v1`
- `member_count(成员数) = 2`
- `members(成员) = price_volume_single_signal_alpha158_imxd5_v1, price_volume_single_signal_alpha158_imax20_v1`
- reason: Both describe breakout path ordering / freshness; retain imxd5 as the canonical representative and imax20 only as a nearby variant.

### 20. `alpha158_price_volume_level_corr`

- `cluster_status(簇状态) = reserve_atomic_keeper`
- `mechanism_family(机制家族) = alpha158_price_volume_level_corr`
- `relationship_type(关系类型) = horizon_cluster`
- `representative_candidate_scheme_id(代表候选) = price_volume_single_signal_alpha158_corr30_v1`
- `secondary_candidate_scheme_ids(次级变体) = price_volume_single_signal_alpha158_corr20_v1, price_volume_single_signal_alpha158_corr10_v1`
- `member_count(成员数) = 5`
- `members(成员) = price_volume_single_signal_alpha158_corr5_v1, price_volume_single_signal_alpha158_corr10_v1, price_volume_single_signal_alpha158_corr20_v1, price_volume_single_signal_alpha158_corr30_v1, price_volume_single_signal_alpha158_corr60_v1`
- reason: All five are the same level-correlation mechanism across windows. corr30 is chosen as canonical because it survived furthest in confirmatory governance; corr20 and corr10 remain documented strong variants but not separate canonical entries.

### 21. `alpha158_price_volume_change_corr`

- `cluster_status(簇状态) = high_quality_reserve_atomic_keeper`
- `mechanism_family(机制家族) = alpha158_price_volume_change_corr`
- `relationship_type(关系类型) = horizon_cluster`
- `representative_candidate_scheme_id(代表候选) = price_volume_single_signal_alpha158_cord30_v1`
- `secondary_candidate_scheme_ids(次级变体) = price_volume_single_signal_alpha158_cord20_v1, price_volume_single_signal_alpha158_cord10_v1`
- `member_count(成员数) = 5`
- `members(成员) = price_volume_single_signal_alpha158_cord5_v1, price_volume_single_signal_alpha158_cord10_v1, price_volume_single_signal_alpha158_cord20_v1, price_volume_single_signal_alpha158_cord30_v1, price_volume_single_signal_alpha158_cord60_v1`
- reason: All five are the same change-correlation mechanism across windows. cord30 is the canonical representative because it became the strongest and furthest-advanced reserve card.

### 22. `alpha158_relative_volume_level`

- `cluster_status(簇状态) = historical_positive_canonical`
- `mechanism_family(机制家族) = alpha158_relative_volume_level`
- `relationship_type(关系类型) = horizon_cluster`
- `representative_candidate_scheme_id(代表候选) = price_volume_single_signal_alpha158_vma60_v1`
- `secondary_candidate_scheme_ids(次级变体) = price_volume_single_signal_alpha158_vma30_v1`
- `member_count(成员数) = 5`
- `members(成员) = price_volume_single_signal_alpha158_vma5_v1, price_volume_single_signal_alpha158_vma10_v1, price_volume_single_signal_alpha158_vma20_v1, price_volume_single_signal_alpha158_vma30_v1, price_volume_single_signal_alpha158_vma60_v1`
- reason: Same relative-volume-level mechanism across windows; retain vma60 as the slow canonical representative.

### 23. `alpha158_volume_stability`

- `cluster_status(簇状态) = historical_positive_canonical`
- `mechanism_family(机制家族) = alpha158_volume_stability`
- `relationship_type(关系类型) = horizon_cluster`
- `representative_candidate_scheme_id(代表候选) = price_volume_single_signal_alpha158_vstd60_v1`
- `secondary_candidate_scheme_ids(次级变体) = price_volume_single_signal_alpha158_vstd30_v1`
- `member_count(成员数) = 2`
- `members(成员) = price_volume_single_signal_alpha158_vstd30_v1, price_volume_single_signal_alpha158_vstd60_v1`
- reason: Same volume-stability mechanism across windows; retain vstd60 as the canonical representative.

### 24. `alpha158_volume_expansion_balance`

- `cluster_status(簇状态) = reserve_atomic_keeper`
- `mechanism_family(机制家族) = alpha158_volume_expansion_balance`
- `relationship_type(关系类型) = same_mechanism_cluster`
- `representative_candidate_scheme_id(代表候选) = price_volume_single_signal_alpha158_vsumd60_v1`
- `secondary_candidate_scheme_ids(次级变体) = price_volume_single_signal_alpha158_vsump60_v1, price_volume_single_signal_alpha158_vsumn60_v1`
- `member_count(成员数) = 9`
- `members(成员) = price_volume_single_signal_alpha158_vsump20_v1, price_volume_single_signal_alpha158_vsump30_v1, price_volume_single_signal_alpha158_vsump60_v1, price_volume_single_signal_alpha158_vsumn20_v1, price_volume_single_signal_alpha158_vsumn30_v1, price_volume_single_signal_alpha158_vsumn60_v1, price_volume_single_signal_alpha158_vsumd20_v1, price_volume_single_signal_alpha158_vsumd30_v1, price_volume_single_signal_alpha158_vsumd60_v1`
- reason: The VSUMP / VSUMN / VSUMD set is a highly homologous volume-expansion-balance family. vsumd60 is retained as the single canonical entry because it advanced furthest in confirmatory work and best fits later family use.

### 25. `alpha158_full_pilot_labels`

- `cluster_status(簇状态) = retired_noncanonical_pilot_cluster`
- `mechanism_family(机制家族) = alpha158_historical_pilot_slots`
- `relationship_type(关系类型) = historical_pilot_cluster`
- `representative_candidate_scheme_id(代表候选) = None`
- `member_count(成员数) = 5`
- `members(成员) = price_volume_single_signal_alpha158_full_003_v1, price_volume_single_signal_alpha158_full_004_v1, price_volume_single_signal_alpha158_full_019_v1, price_volume_single_signal_alpha158_full_027_v1, price_volume_single_signal_alpha158_full_036_v1`
- reason: These were pre-reconciliation slot labels from exploratory Alpha158 pilots. Keep them as historical evidence only; do not treat them as canonical signals after exact-definition reconciliation.

