# Momentum 60-5 Single-Signal Edge Diagnosis (20260422)

Candidate: `price_volume_single_signal_momentum_60_5_v1`
Research round: `rr_price_volume_single_signal_discovery_20260422`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 135887`
- `null_score_share = 0.00892`
- `scored_with_label_rows = 14888004`

## 2. IC Readout
- Full-sample correlation IC: `0.009758`
- Average daily IC: `0.013398`
- Median daily IC: `0.007710`
- Positive daily IC share: `0.52359`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004724`
- Decile 2: `0.004351`
- Decile 3: `0.004218`
- Decile 4: `0.004079`
- Decile 5: `0.003997`
- Decile 6: `0.003953`
- Decile 7: `0.003711`
- Decile 8: `0.003497`
- Decile 9: `0.002884`
- Decile 10: `0.002092`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.004282`
- Average label, rank 11-20: `0.005483`
- Average label, bottom 10: `0.001820`
- `top10 - rank11_20 = -0.001201`
- `top10 - bottom10 = 0.002461`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000535`
- Median score gap `rank10 - rank11`: `0.000446`
- Days with both ranks present: `6302`
- Days with `|gap| < 0.005`: `6302`
- Days with `|gap| < 0.001`: `6041`

