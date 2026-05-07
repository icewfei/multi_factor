# Atomic Keepers Dedup / Standardization (20260425)

## Scope

This note consolidates the current retained `atomic keepers(原子保留信号)` on the price-volume line after:

- the frozen `working_reference(工作基准)` decision on `v18 = price_volume_v18_refresh_hysteresis`,
- rounds 1-6 of `single-signal discovery(单信号发现)`,
- the later `composability screening(组合相容性筛查)` rounds,
- and the phase decision that paused further price-volume family micro-tuning.

This note does **not** reopen any family round. Its purpose is only:

- to deduplicate equivalent or near-equivalent atomic signals,
- to define canonical names,
- to separate active keepers from historical-but-retired positives,
- and to reduce future research-space inflation.

## Current high-level judgement

The current `working_reference(工作基准)` remains:

- `price_volume_v18_refresh_hysteresis`

The current price-volume family tuning line remains paused.

The strongest retained `watchlist keeper(观察名单保留信号)` is still:

- `price_volume_single_signal_volume_price_synchronicity_20d_v1`

but it is **not promotable yet** because its `composability screening(组合相容性筛查)` stayed `mixed(混合)`.

## Canonical active atomic keeper pool

These are the atomic mechanisms that are still worth preserving as distinct ideas.

### 1. `momentum_60_5_raw`

- Canonical candidate: `price_volume_single_signal_momentum_60_5_v1`
- Status: `signal_edge_positive(正向信号边际优势)`
- Role: baseline trend-strength anchor
- Judgement: keep as a core canonical signal

### 2. `liquidity_trend_20_60_raw`

- Canonical candidate: `price_volume_single_signal_liquidity_trend_20_60_v1`
- Status: `signal_edge_positive(正向信号边际优势)`
- Role: short-to-medium liquidity improvement
- Judgement: keep as a core canonical signal

### 3. `liquidity_trend_60_120_raw`

- Canonical candidate: `price_volume_single_signal_liquidity_trend_60_120_v1`
- Status: `signal_edge_positive(正向信号边际优势)`
- Role: slower liquidity improvement
- Judgement: keep as a distinct secondary keeper
- Note: direct family substitution in `v21` failed, so this remains a retained atomic signal, not an active promotion candidate

### 4. `turnover_acceleration_5_20_raw`

- Canonical candidate: `price_volume_single_signal_turnover_acceleration_5_20_v1`
- Status: `signal_edge_positive(正向信号边际优势)`
- Role: participation shock / trading-activity acceleration
- Judgement: keep as a distinct atomic keeper

### 5. `amount_shock_5_20_raw`

- Canonical candidate: `price_volume_single_signal_amount_shock_5_20_v1`
- Status: `signal_edge_positive(正向信号边际优势)`
- Role: short-horizon amount surge
- Judgement: keep as a distinct atomic keeper
- Note: later `composability screening(组合相容性筛查)` returned `mixed(混合)`, so this is retained as an atomic signal, not promotable as a clean third family component

### 6. `volume_price_synchronicity_20d_raw`

- Canonical candidate: `price_volume_single_signal_volume_price_synchronicity_20d_v1`
- Status: `signal_edge_positive(正向信号边际优势)`
- Role: price-volume confirmation
- Judgement: keep as the primary `watchlist keeper(观察名单保留信号)`
- Note: strongest new standardized keeper, but still `composability_screen_mixed(组合相容性筛查混合)`

### 7. `up_amount_persistence_20d_raw`

- Canonical candidate: `price_volume_single_signal_up_amount_persistence_20d_v1`
- Status: `signal_edge_positive(正向信号边际优势)`
- Role: persistence of amount support on up days
- Judgement: keep as a secondary watchlist keeper
- Note: later `composability screening(组合相容性筛查)` also returned `mixed(混合)`

### 8. `breakout_volume_confirmation_20d_raw`

- Canonical candidate: `price_volume_single_signal_breakout_volume_confirmation_20d_v1`
- Status: `signal_edge_positive(正向信号边际优势)`
- Role: breakout position plus volume confirmation
- Judgement: keep only as a historical positive atomic signal
- Note: direct family substitution in `v22` failed badly, so this signal should not be reopened casually

## Retired from active keeper pool

These signals were once positive at the atomic level, but should not remain in the current active keeper pool.

### `trend_consistency_20d_raw`

- Historical candidate: `price_volume_single_signal_trend_consistency_20d_v1`
- Historical status: `signal_edge_positive(正向信号边际优势)`
- Why retire:
  - later component ablation showed it was the easiest component to remove from the `v15` line,
  - removing it improved the family-level signal layer,
  - later `v16` confirmed that dropping it moved the strategy in a healthier direction.
- Judgement: retire from active keeper pool; preserve only as historical evidence

## Exact or near-exact dedup / merge decisions

These pairs should be treated as the same or nearly the same mechanism.

### A. `price_volume_corr_20d_raw` -> merge into `volume_price_synchronicity_20d_raw`

- Canonical name: `volume_price_synchronicity_20d_raw`
- Alias to retire: `price_volume_corr_20d_raw`
- Reason:
  - both are 20-day price-volume co-movement / confirmation signals,
  - round-6 readout is numerically identical in spirit to the round-5 keeper,
  - keeping both as separate future candidates would inflate the search space without adding real mechanism diversity

### B. `volume_momentum_5_20_raw` -> merge into `amount_shock_5_20_raw`

- Canonical name: `amount_shock_5_20_raw`
- Alias to retire: `volume_momentum_5_20_raw`
- Reason:
  - both represent short-vs-medium amount expansion,
  - the standardized name is useful, but mechanism-wise this is not a genuinely new keeper,
  - future work should pick exactly one canonical label and avoid running both

### C. `turnover_mean_reversion_gap_5_20_raw` -> inverse duplicate of `turnover_acceleration_5_20_raw`

- Canonical name: `turnover_acceleration_5_20_raw`
- Alias to retire: `turnover_mean_reversion_gap_5_20_raw`
- Reason:
  - same raw construction class, only reframed with opposite direction
  - round-6 confirms the inverse framing is not useful

### D. `breakout_distance_20d_raw` -> merge into `breakout_proximity_20d_raw`

- Canonical name: `breakout_proximity_20d_raw`
- Alias to retire: `breakout_distance_20d_raw`
- Reason:
  - same structural idea: distance to recent breakout boundary
  - round-6 only standardizes naming; it does not create a new mechanism

### E. `close_to_high_ratio_20d_raw` -> merge into `close_location_value_20d_raw`

- Canonical name: `close_location_value_20d_raw`
- Alias to retire: `close_to_high_ratio_20d_raw`
- Reason:
  - both encode persistent close location within recent trading range
  - keep one canonical naming style only

### F. `upper_shadow_pressure_20d_raw` -> merge into `upper_shadow_ratio_20d_raw`

- Canonical name: `upper_shadow_ratio_20d_raw`
- Alias to retire: `upper_shadow_pressure_20d_raw`
- Reason:
  - same overhead-supply / upper-shadow mechanism
  - round-6 adds standardization, not a truly new keeper

## Near-family clusters that should not be treated as independent alpha expansion

### Momentum cluster

- `momentum_60_5_raw`
- `momentum_20_5_raw`
- `momentum_120_20_raw`
- `momentum_250_20_raw`

Judgement:
- Keep only `momentum_60_5_raw` as the canonical active keeper.
- The others did not justify separate active-keeper status.

### Liquidity-improvement cluster

- `liquidity_trend_20_60_raw`
- `liquidity_trend_60_120_raw`

Judgement:
- Keep both as distinct horizons.
- But do not count them as two fully independent mechanism families; they are horizon variants inside one liquidity-improvement family.

### Price-volume confirmation cluster

- `volume_price_synchronicity_20d_raw`
- `price_volume_corr_20d_raw`
- `up_amount_persistence_20d_raw`
- `amount_shock_5_20_raw`
- `volume_momentum_5_20_raw`
- `breakout_volume_confirmation_20d_raw`

Judgement:
- This is the main cluster that needs the most governance.
- Do not count every member as new independent alpha.
- Recommended canonical anchors:
  - `volume_price_synchronicity_20d_raw`
  - `amount_shock_5_20_raw`
  - `up_amount_persistence_20d_raw`
- Treat `price_volume_corr_20d_raw` and `volume_momentum_5_20_raw` as aliases / standardization variants, not new keepers.
- Treat `breakout_volume_confirmation_20d_raw` as a historically interesting but promotion-failed composite atomic signal.

## Standard naming recommendations

Recommended canonical standardized names for future work:

- `momentum_60_5_raw`
- `liquidity_trend_20_60_raw`
- `liquidity_trend_60_120_raw`
- `turnover_acceleration_5_20_raw`
- `amount_shock_5_20_raw`
- `volume_price_synchronicity_20d_raw`
- `up_amount_persistence_20d_raw`
- `breakout_proximity_20d_raw`
- `close_location_value_20d_raw`
- `upper_shadow_ratio_20d_raw`

Preferred retirement / alias names:

- `price_volume_corr_20d_raw`
- `volume_momentum_5_20_raw`
- `turnover_mean_reversion_gap_5_20_raw`
- `breakout_distance_20d_raw`
- `close_to_high_ratio_20d_raw`
- `upper_shadow_pressure_20d_raw`

## Practical next-step rule

Before any future `single-signal discovery(单信号发现)` or `composability screening(组合相容性筛查)`:

- first check whether a proposed signal is merely a renamed or reoriented variant of an existing canonical mechanism,
- if yes, treat it as a standardization update instead of a new keeper,
- only genuinely orthogonal mechanisms should consume new exploration budget.

## Final decision

The current price-volume atomic library should be treated as:

- **core canonical keepers**
  - `momentum_60_5_raw`
  - `liquidity_trend_20_60_raw`
  - `liquidity_trend_60_120_raw`
  - `turnover_acceleration_5_20_raw`
  - `amount_shock_5_20_raw`
  - `volume_price_synchronicity_20d_raw`
  - `up_amount_persistence_20d_raw`

- **watchlist only**
  - `volume_price_synchronicity_20d_raw`

- **historical positive but not actively promotable**
  - `breakout_volume_confirmation_20d_raw`
  - `trend_consistency_20d_raw`

- **retired aliases / standardization duplicates**
  - `price_volume_corr_20d_raw`
  - `volume_momentum_5_20_raw`
  - `turnover_mean_reversion_gap_5_20_raw`
  - `breakout_distance_20d_raw`
  - `close_to_high_ratio_20d_raw`
  - `upper_shadow_pressure_20d_raw`

The purpose of this final split is to stop counting naming variants as fresh alpha discoveries.
