# price_volume_single_signal_price_volume_beta_20d_v1 (20260428)

Candidate: `price_volume_single_signal_price_volume_beta_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_batch01_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 1814`
- `null_score_share = 0.00012`
- `scored_with_label_rows = 15020218`

## 2. IC Readout
- Full-sample correlation IC: `0.017161`
- Average daily IC: `0.028287`
- Median daily IC: `0.028194`
- Positive daily IC share: `0.60806`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.005629`
- Decile 2: `0.004857`
- Decile 3: `0.004550`
- Decile 4: `0.004327`
- Decile 5: `0.004239`
- Decile 6: `0.004075`
- Decile 7: `0.003635`
- Decile 8: `0.003143`
- Decile 9: `0.002504`
- Decile 10: `0.001103`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.008462`
- Average label, rank 11-20: `0.007726`
- Average label, bottom 10: `0.000683`
- `top10 - rank11_20 = 0.000737`
- `top10 - bottom10 = 0.007779`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6360`
- Days with `|gap| < 0.005`: `6360`
- Days with `|gap| < 0.001`: `6075`

