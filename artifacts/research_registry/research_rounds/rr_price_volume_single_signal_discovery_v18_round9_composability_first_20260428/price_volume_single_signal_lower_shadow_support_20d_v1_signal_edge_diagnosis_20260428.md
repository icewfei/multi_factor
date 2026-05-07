# price_volume_single_signal_lower_shadow_support_20d_v1 (20260428)

Candidate: `price_volume_single_signal_lower_shadow_support_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round9_composability_first_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 769`
- `null_score_share = 0.00005`
- `scored_with_label_rows = 15021902`

## 2. IC Readout
- Full-sample correlation IC: `0.006151`
- Average daily IC: `0.010726`
- Median daily IC: `0.008010`
- Positive daily IC share: `0.54555`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004268`
- Decile 2: `0.004297`
- Decile 3: `0.004170`
- Decile 4: `0.004006`
- Decile 5: `0.003929`
- Decile 6: `0.003927`
- Decile 7: `0.003862`
- Decile 8: `0.003700`
- Decile 9: `0.003371`
- Decile 10: `0.002591`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.005563`
- Average label, rank 11-20: `0.005020`
- Average label, bottom 10: `0.001136`
- `top10 - rank11_20 = 0.000543`
- `top10 - bottom10 = 0.004427`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6071`

