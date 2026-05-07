# price_volume_single_signal_high_open_hold_ratio_20d_v1 (20260428)

Candidate: `price_volume_single_signal_high_open_hold_ratio_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round8_orthogonal_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 26570`
- `null_score_share = 0.00174`
- `scored_with_label_rows = 14995985`

## 2. IC Readout
- Full-sample correlation IC: `0.005027`
- Average daily IC: `0.007099`
- Median daily IC: `0.005646`
- Positive daily IC share: `0.54627`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003949`
- Decile 2: `0.004188`
- Decile 3: `0.004216`
- Decile 4: `0.004118`
- Decile 5: `0.003910`
- Decile 6: `0.003920`
- Decile 7: `0.003878`
- Decile 8: `0.003794`
- Decile 9: `0.003448`
- Decile 10: `0.002696`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.004374`
- Average label, rank 11-20: `0.004370`
- Average label, bottom 10: `0.002458`
- `top10 - rank11_20 = 0.000004`
- `top10 - bottom10 = 0.001916`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000538`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6071`

