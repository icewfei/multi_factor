# price_volume_single_signal_alpha158_rsqr5_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_rsqr5_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch02_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 1325`
- `null_score_share = 0.00009`
- `scored_with_label_rows = 15020717`

## 2. IC Readout
- Full-sample correlation IC: `0.007369`
- Average daily IC: `0.011751`
- Median daily IC: `0.010922`
- Positive daily IC share: `0.56311`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004107`
- Decile 2: `0.004227`
- Decile 3: `0.004297`
- Decile 4: `0.004298`
- Decile 5: `0.004227`
- Decile 6: `0.004025`
- Decile 7: `0.003858`
- Decile 8: `0.003563`
- Decile 9: `0.003188`
- Decile 10: `0.002294`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.004358`
- Average label, rank 11-20: `0.004790`
- Average label, bottom 10: `0.000391`
- `top10 - rank11_20 = -0.000432`
- `top10 - bottom10 = 0.003966`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

