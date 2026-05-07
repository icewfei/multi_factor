# Price-Volume Single-Signal Discovery Phase Summary (20260422)

Research round: `rr_price_volume_single_signal_discovery_20260422`

## Executive Conclusion

This discovery round has now evaluated the first four atomic price-volume signals under the frozen calibrated `v7` operational contract.

Current conclusion:

- `momentum_60_5_raw` is the **only signal worth keeping** in the candidate pool.
- `reversal_5d_raw`, `volatility_20d_raw`, and `liquidity_20d_raw` should be **rejected** from later family construction in their current standalone forms.

Therefore:

- **Do not build the next family by remixing all four price-volume signals.**
- The correct next step is to either:
  1. expand the atomic-signal pool further, or
  2. build the next family around `momentum_60_5_raw` plus one new atomic signal that first proves positive edge on its own.

## Candidate-by-Candidate Summary

### 1. `price_volume_single_signal_momentum_60_5_v1`

Status:

- `signal_edge_positive`

Key readout:

- full-sample IC: `0.009758`
- avg daily IC: `0.013398`
- positive daily IC share: `0.52359`
- broad decile ordering: positive
- top10 vs rank11_20: `0.004282` vs `0.005483`

Interpretation:

- This is a **weak but directionally coherent positive signal**.
- It is worth keeping in the downstream candidate pool.
- It is **not** itself a promotable strategy, because the head slice is fragile and `rank10-11` separation is very thin.

### 2. `price_volume_single_signal_reversal_5d_v1`

Status:

- `signal_edge_negative`

Key readout:

- full-sample IC: `-0.021762`
- avg daily IC: `-0.041578`
- positive daily IC share: `0.37197`
- decile ordering: effectively inverted

Interpretation:

- This signal should be rejected from later family construction in its current standalone form.
- It does not look like a "good signal with bad extraction"; it looks directionally wrong under the current contract.

### 3. `price_volume_single_signal_volatility_20d_v1`

Status:

- `signal_edge_negative`

Key readout:

- full-sample IC: `-0.005088`
- avg daily IC: `-0.005787`
- positive daily IC share: `0.48111`
- decile ordering: non-monotonic / weak

Interpretation:

- This is not a clean positive edge.
- It should not be moved into the next family-construction round unless a new, separately registered variant is justified.

### 4. `price_volume_single_signal_liquidity_20d_v1`

Status:

- `signal_edge_negative`

Key readout:

- full-sample IC: `-0.025580`
- avg daily IC: `-0.037555`
- positive daily IC share: `0.36428`
- decile ordering: inverted

Interpretation:

- This signal should be rejected from later family construction in its current standalone form.
- It is not just noisy; it is clearly pointing the wrong way under the current frozen contract.

## Round-Level Decision

### What we learned

The main value of this discovery round is that it separates one usable atomic price-volume signal from three signals that should not be mixed back in casually.

The current retained pool is:

- `momentum_60_5_raw`

The current rejected pool is:

- `reversal_5d_raw`
- `volatility_20d_raw`
- `liquidity_20d_raw`

### What we should not do next

- Do not build `v15` by simply re-mixing these four signals again.
- Do not rescue the rejected signals by immediately adding extraction, turnover, or cost tweaks.
- Do not interpret this round as proof that "price-volume doesn’t work"; it only shows that three tested atomic signals do not work in their current fixed forms.

## Recommended Next Step

Recommended next action:

- **Continue expanding the atomic signal pool before constructing the next mixed family.**

Priority logic:

1. Keep `momentum_60_5_raw` as the current retained atomic signal.
2. Add one or two new atomic price-volume signals that are directionally cleaner than reversal / raw liquidity / low-vol.
3. Only after another atomic signal shows positive edge should we open the next family-construction round.

In other words:

- **The correct next move is to continue single-signal discovery, not to open a new mixed family immediately.**
