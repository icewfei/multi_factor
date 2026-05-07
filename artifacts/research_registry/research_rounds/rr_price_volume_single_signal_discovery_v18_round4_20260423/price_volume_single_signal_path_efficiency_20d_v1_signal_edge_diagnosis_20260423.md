# price_volume_single_signal_path_efficiency_20d_v1 (20260423)

Candidate: `price_volume_single_signal_path_efficiency_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round4_20260423`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 18239`
- `null_score_share = 0.00120`
- `scored_with_label_rows = 15003964`

## 2. IC Readout
- Full-sample correlation IC: `0.011511`
- Average daily IC: `0.020042`
- Median daily IC: `0.016917`
- Positive daily IC share: `0.55391`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003857`
- Decile 2: `0.004324`
- Decile 3: `0.004480`
- Decile 4: `0.004642`
- Decile 5: `0.004558`
- Decile 6: `0.004425`
- Decile 7: `0.004177`
- Decile 8: `0.003760`
- Decile 9: `0.002786`
- Decile 10: `0.000722`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.001921`
- Average label, rank 11-20: `0.003672`
- Average label, bottom 10: `-0.000852`
- `top10 - rank11_20 = -0.001750`
- `top10 - bottom10 = 0.002774`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000535`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6342`
- Days with `|gap| < 0.005`: `6342`
- Days with `|gap| < 0.001`: `6075`

