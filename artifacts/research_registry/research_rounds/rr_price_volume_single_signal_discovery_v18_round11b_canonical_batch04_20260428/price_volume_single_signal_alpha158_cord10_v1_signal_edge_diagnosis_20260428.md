# price_volume_single_signal_alpha158_cord10_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_cord10_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch04_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 1822`
- `null_score_share = 0.00012`
- `scored_with_label_rows = 15020211`

## 2. IC Readout
- Full-sample correlation IC: `0.013113`
- Average daily IC: `0.024033`
- Median daily IC: `0.023891`
- Positive daily IC share: `0.62396`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004731`
- Decile 2: `0.004618`
- Decile 3: `0.004565`
- Decile 4: `0.004428`
- Decile 5: `0.004302`
- Decile 6: `0.004040`
- Decile 7: `0.003790`
- Decile 8: `0.003436`
- Decile 9: `0.002855`
- Decile 10: `0.001299`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.005906`
- Average label, rank 11-20: `0.005780`
- Average label, bottom 10: `-0.001628`
- `top10 - rank11_20 = 0.000126`
- `top10 - bottom10 = 0.007534`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6360`
- Days with `|gap| < 0.005`: `6360`
- Days with `|gap| < 0.001`: `6075`

