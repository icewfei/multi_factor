# Vol Regime 20-60 Single-Signal Edge Diagnosis (20260422)

Candidate: `price_volume_single_signal_vol_regime_20_60_v1`
Research round: `rr_price_volume_single_signal_discovery_20260422`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 908`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021119`

## 2. IC Readout
- Full-sample correlation IC: `-0.004406`
- Average daily IC: `-0.004130`
- Median daily IC: `-0.006177`
- Positive daily IC share: `0.47057`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.001976`
- Decile 2: `0.003597`
- Decile 3: `0.004077`
- Decile 4: `0.004181`
- Decile 5: `0.004307`
- Decile 6: `0.004342`
- Decile 7: `0.004198`
- Decile 8: `0.003861`
- Decile 9: `0.003825`
- Decile 10: `0.003729`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.001108`
- Average label, rank 11-20: `0.001459`
- Average label, bottom 10: `0.003036`
- `top10 - rank11_20 = -0.000351`
- `top10 - bottom10 = -0.001927`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

