# Price-Volume Single-Signal Discovery Phase Summary (20260423)

Research round: `rr_price_volume_single_signal_discovery_v18_20260423`

## Executive Conclusion

This second discovery batch completed all four preregistered atomic signal tests under the frozen `price_volume_v18_refresh_hysteresis` operational contract.

Current conclusion:

- `price_volume_single_signal_reversal_5d_followthrough_v1` is `signal_edge_mixed(混合信号边际优势)`.
- `price_volume_single_signal_liquidity_60d_v1` is `signal_edge_negative(负向信号边际优势)`.
- `price_volume_single_signal_vol_regime_20_60_inverse_v1` is `signal_edge_mixed(混合信号边际优势)`.
- `price_volume_single_signal_volatility_60d_v1` is `signal_edge_negative(负向信号边际优势)`.

Therefore:

- **This batch produced no new clean positive keeper(正向可保留信号).**
- **We should not open a new mixed family from this batch.**
- **The next step should be to continue expanding the atomic signal pool, not to return immediately to family construction.**

## Candidate-by-Candidate Summary

### 1. `price_volume_single_signal_reversal_5d_followthrough_v1`

Status:

- `signal_edge_mixed(混合信号边际优势)`

Key readout:

- `full_sample_corr_ic(全样本IC) = 0.021762`
- `avg_daily_ic(平均日IC) = 0.041577`
- `positive_daily_ic_share(正IC日占比) = 0.628031`
- `avg_label_top10(前10平均标签) = -0.001409`
- `avg_label_rank11_20(11-20名平均标签) = 0.004951`

Interpretation:

- `broad ordering(整体排序)` is strongly positive.
- But `head_slice(头部切片)` is clearly bad.
- This is not a clean keeper for later family construction unless a future round explicitly tests a non-Top10 extraction hypothesis around it.

### 2. `price_volume_single_signal_liquidity_60d_v1`

Status:

- `signal_edge_negative(负向信号边际优势)`

Key readout:

- `full_sample_corr_ic(全样本IC) = -0.021565`
- `avg_daily_ic(平均日IC) = -0.031297`
- `positive_daily_ic_share(正IC日占比) = 0.376082`
- `avg_label_top10(前10平均标签) = 0.001830`
- `avg_label_bottom10(后10平均标签) = 0.008406`

Interpretation:

- The smoother structural liquidity-level hypothesis remains directionally wrong.
- This signal should be rejected from the next family-construction pool.

### 3. `price_volume_single_signal_vol_regime_20_60_inverse_v1`

Status:

- `signal_edge_mixed(混合信号边际优势)`

Key readout:

- `full_sample_corr_ic(全样本IC) = 0.004308`
- `avg_daily_ic(平均日IC) = 0.003899`
- `positive_daily_ic_share(正IC日占比) = 0.526755`
- `avg_label_top10(前10平均标签) = 0.002926`
- `avg_label_rank11_20(11-20名平均标签) = 0.003296`

Interpretation:

- The inverse volatility-regime hypothesis is not negative.
- But the edge is weak, upper-decile ordering bends down, and the head still underperforms ranks `11-20`.
- This is not a clean keeper.

### 4. `price_volume_single_signal_volatility_60d_v1`

Status:

- `signal_edge_negative(负向信号边际优势)`

Key readout:

- `full_sample_corr_ic(全样本IC) = -0.004017`
- `avg_daily_ic(平均日IC) = -0.004902`
- `positive_daily_ic_share(正IC日占比) = 0.486780`
- `avg_label_top10(前10平均标签) = 0.002522`
- `avg_label_rank11_20(11-20名平均标签) = 0.002898`

Interpretation:

- The slower low-volatility hypothesis still does not produce a usable positive edge.
- This signal should also be rejected from later family construction in its current standalone form.

## Round-Level Decision

### What we learned

Relative to the first discovery round, this second batch added:

- no new `signal_edge_positive(正向信号边际优势)` atomic signal,
- two `signal_edge_mixed(混合信号边际优势)` candidates that may be diagnostically interesting,
- and two clearly negative signals that should be removed from future construction candidates.

This means the currently active retained atomic pool still rests on the earlier retained signals rather than on anything new discovered here.

### What we should not do next

- Do not build a new price-volume family from these four batch-2 signals.
- Do not mix `reversal_5d_followthrough_raw` or `vol_regime_20_60_inverse_raw` into the next family just because they have weak positive IC.
- Do not rescue the two negative signals with extraction or refresh tweaks.

## Recommended Next Step

Recommended next action:

- **Continue expanding the atomic signal pool before constructing the next mixed family.**

Reason:

- This batch produced zero new clean keepers.
- The current best family line (`v18`) already uses the strongest retained signals discovered so far.
- Reconstructing another family now would mostly remix already-known retained signals plus weaker mixed candidates, which is unlikely to add much information and would increase overfitting risk.

In other words:

- **The correct next move is to continue single-signal discovery, not to open the next family immediately.**
