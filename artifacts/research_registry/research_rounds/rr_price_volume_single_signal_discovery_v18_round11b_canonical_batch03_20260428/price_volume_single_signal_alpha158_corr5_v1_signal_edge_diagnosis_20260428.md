# price_volume_single_signal_alpha158_corr5_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_corr5_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch03_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 1325`
- `null_score_share = 0.00009`
- `scored_with_label_rows = 15020717`

## 2. IC Readout
- Full-sample correlation IC: `0.016252`
- Average daily IC: `0.027261`
- Median daily IC: `0.026893`
- Positive daily IC share: `0.64715`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.005383`
- Decile 2: `0.004730`
- Decile 3: `0.004648`
- Decile 4: `0.004454`
- Decile 5: `0.004286`
- Decile 6: `0.004011`
- Decile 7: `0.003630`
- Decile 8: `0.003282`
- Decile 9: `0.002497`
- Decile 10: `0.001156`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.007483`
- Average label, rank 11-20: `0.007029`
- Average label, bottom 10: `-0.000894`
- `top10 - rank11_20 = 0.000454`
- `top10 - bottom10 = 0.008377`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

