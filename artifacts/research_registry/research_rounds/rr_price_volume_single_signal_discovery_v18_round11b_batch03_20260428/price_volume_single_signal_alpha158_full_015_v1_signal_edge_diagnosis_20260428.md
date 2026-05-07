# price_volume_single_signal_alpha158_full_015_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_full_015_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_batch03_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 1971`
- `null_score_share = 0.00013`
- `scored_with_label_rows = 15020061`

## 2. IC Readout
- Full-sample correlation IC: `-0.001850`
- Average daily IC: `-0.004546`
- Median daily IC: `-0.005262`
- Positive daily IC share: `0.45427`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.002350`
- Decile 2: `0.003897`
- Decile 3: `0.004028`
- Decile 4: `0.004238`
- Decile 5: `0.004323`
- Decile 6: `0.004245`
- Decile 7: `0.004018`
- Decile 8: `0.003881`
- Decile 9: `0.003729`
- Decile 10: `0.003368`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `-0.001578`
- Average label, rank 11-20: `0.000196`
- Average label, bottom 10: `0.004492`
- `top10 - rank11_20 = -0.001773`
- `top10 - bottom10 = -0.006070`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6360`
- Days with `|gap| < 0.005`: `6360`
- Days with `|gap| < 0.001`: `6075`

