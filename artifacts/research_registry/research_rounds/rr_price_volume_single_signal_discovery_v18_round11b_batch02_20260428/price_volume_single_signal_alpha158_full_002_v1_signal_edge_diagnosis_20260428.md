# price_volume_single_signal_alpha158_full_002_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_full_002_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_batch02_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 908`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021119`

## 2. IC Readout
- Full-sample correlation IC: `0.001983`
- Average daily IC: `0.004220`
- Median daily IC: `0.002513`
- Positive daily IC share: `0.51353`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.002275`
- Decile 2: `0.004023`
- Decile 3: `0.004375`
- Decile 4: `0.004627`
- Decile 5: `0.004590`
- Decile 6: `0.004436`
- Decile 7: `0.004288`
- Decile 8: `0.003846`
- Decile 9: `0.003424`
- Decile 10: `0.002204`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `-0.001190`
- Average label, rank 11-20: `0.001124`
- Average label, bottom 10: `0.000545`
- `top10 - rank11_20 = -0.002314`
- `top10 - bottom10 = -0.001735`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

