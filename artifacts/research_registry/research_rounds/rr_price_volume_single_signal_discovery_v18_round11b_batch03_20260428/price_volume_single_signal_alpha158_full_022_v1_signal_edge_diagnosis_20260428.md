# price_volume_single_signal_alpha158_full_022_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_full_022_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_batch03_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 907`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021120`

## 2. IC Readout
- Full-sample correlation IC: `0.000500`
- Average daily IC: `0.003450`
- Median daily IC: `0.005640`
- Positive daily IC share: `0.54721`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003486`
- Decile 2: `0.003871`
- Decile 3: `0.003883`
- Decile 4: `0.003936`
- Decile 5: `0.003950`
- Decile 6: `0.003974`
- Decile 7: `0.003897`
- Decile 8: `0.003914`
- Decile 9: `0.003807`
- Decile 10: `0.003371`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.003236`
- Average label, rank 11-20: `0.003669`
- Average label, bottom 10: `0.001525`
- `top10 - rank11_20 = -0.000433`
- `top10 - bottom10 = 0.001711`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

