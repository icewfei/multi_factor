# price_volume_single_signal_overnight_gap_stability_20d_v1 (20260428)

Candidate: `price_volume_single_signal_overnight_gap_stability_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round8_orthogonal_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 1814`
- `null_score_share = 0.00012`
- `scored_with_label_rows = 15020218`

## 2. IC Readout
- Full-sample correlation IC: `-0.007107`
- Average daily IC: `-0.008187`
- Median daily IC: `-0.008668`
- Positive daily IC share: `0.46734`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.001750`
- Decile 2: `0.003378`
- Decile 3: `0.003788`
- Decile 4: `0.003915`
- Decile 5: `0.004198`
- Decile 6: `0.004387`
- Decile 7: `0.004419`
- Decile 8: `0.004375`
- Decile 9: `0.004284`
- Decile 10: `0.003587`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.000490`
- Average label, rank 11-20: `0.000428`
- Average label, bottom 10: `0.003055`
- `top10 - rank11_20 = 0.000062`
- `top10 - bottom10 = -0.002565`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6360`
- Days with `|gap| < 0.005`: `6360`
- Days with `|gap| < 0.001`: `6075`

