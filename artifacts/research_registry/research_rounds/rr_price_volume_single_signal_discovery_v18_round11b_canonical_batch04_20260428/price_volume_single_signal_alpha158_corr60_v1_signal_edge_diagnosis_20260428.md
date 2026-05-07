# price_volume_single_signal_alpha158_corr60_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_corr60_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch04_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 942`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021085`

## 2. IC Readout
- Full-sample correlation IC: `0.008210`
- Average daily IC: `0.015454`
- Median daily IC: `0.018043`
- Positive daily IC share: `0.58137`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004519`
- Decile 2: `0.004206`
- Decile 3: `0.004252`
- Decile 4: `0.003958`
- Decile 5: `0.004169`
- Decile 6: `0.004092`
- Decile 7: `0.003866`
- Decile 8: `0.003641`
- Decile 9: `0.003192`
- Decile 10: `0.002187`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.006780`
- Average label, rank 11-20: `0.005830`
- Average label, bottom 10: `0.001258`
- `top10 - rank11_20 = 0.000950`
- `top10 - bottom10 = 0.005522`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

