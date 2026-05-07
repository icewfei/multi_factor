# price_volume_single_signal_alpha158_std60_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_std60_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch01_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 907`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021120`

## 2. IC Readout
- Full-sample correlation IC: `0.009547`
- Average daily IC: `0.018469`
- Median daily IC: `0.015340`
- Positive daily IC share: `0.53966`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.005504`
- Decile 2: `0.004487`
- Decile 3: `0.004152`
- Decile 4: `0.003916`
- Decile 5: `0.003695`
- Decile 6: `0.003294`
- Decile 7: `0.003445`
- Decile 8: `0.003328`
- Decile 9: `0.003151`
- Decile 10: `0.003110`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.005211`
- Average label, rank 11-20: `0.008313`
- Average label, bottom 10: `0.003473`
- `top10 - rank11_20 = -0.003102`
- `top10 - bottom10 = 0.001737`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

