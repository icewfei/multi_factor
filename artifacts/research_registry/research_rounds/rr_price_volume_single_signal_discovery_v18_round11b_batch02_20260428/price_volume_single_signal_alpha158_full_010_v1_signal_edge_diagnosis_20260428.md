# price_volume_single_signal_alpha158_full_010_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_full_010_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_batch02_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 907`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021120`

## 2. IC Readout
- Full-sample correlation IC: `-0.003156`
- Average daily IC: `-0.005082`
- Median daily IC: `-0.004497`
- Positive daily IC share: `0.45578`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.002869`
- Decile 2: `0.003496`
- Decile 3: `0.003760`
- Decile 4: `0.003936`
- Decile 5: `0.004020`
- Decile 6: `0.004146`
- Decile 7: `0.004144`
- Decile 8: `0.004180`
- Decile 9: `0.004075`
- Decile 10: `0.003467`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.000600`
- Average label, rank 11-20: `0.001926`
- Average label, bottom 10: `-0.000446`
- `top10 - rank11_20 = -0.001327`
- `top10 - bottom10 = 0.001046`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

