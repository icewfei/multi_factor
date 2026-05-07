# price_volume_single_signal_alpha158_full_013_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_full_013_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_batch03_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 1814`
- `null_score_share = 0.00012`
- `scored_with_label_rows = 15020218`

## 2. IC Readout
- Full-sample correlation IC: `0.009823`
- Average daily IC: `0.014189`
- Median daily IC: `0.013649`
- Positive daily IC share: `0.58775`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004128`
- Decile 2: `0.004464`
- Decile 3: `0.004519`
- Decile 4: `0.004450`
- Decile 5: `0.004296`
- Decile 6: `0.004154`
- Decile 7: `0.003786`
- Decile 8: `0.003452`
- Decile 9: `0.002939`
- Decile 10: `0.001877`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.002092`
- Average label, rank 11-20: `0.003045`
- Average label, bottom 10: `0.000435`
- `top10 - rank11_20 = -0.000953`
- `top10 - bottom10 = 0.001657`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6360`
- Days with `|gap| < 0.005`: `6360`
- Days with `|gap| < 0.001`: `6075`

