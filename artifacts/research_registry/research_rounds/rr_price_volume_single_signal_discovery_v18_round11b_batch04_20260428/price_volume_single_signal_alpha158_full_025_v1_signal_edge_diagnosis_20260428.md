# price_volume_single_signal_alpha158_full_025_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_full_025_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_batch04_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 907`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021120`

## 2. IC Readout
- Full-sample correlation IC: `-0.007471`
- Average daily IC: `-0.007951`
- Median daily IC: `-0.008068`
- Positive daily IC share: `0.46947`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.001729`
- Decile 2: `0.003301`
- Decile 3: `0.003702`
- Decile 4: `0.003967`
- Decile 5: `0.004221`
- Decile 6: `0.004413`
- Decile 7: `0.004485`
- Decile 8: `0.004450`
- Decile 9: `0.004205`
- Decile 10: `0.003622`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `-0.000895`
- Average label, rank 11-20: `0.000862`
- Average label, bottom 10: `0.002979`
- `top10 - rank11_20 = -0.001757`
- `top10 - bottom10 = -0.003874`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

