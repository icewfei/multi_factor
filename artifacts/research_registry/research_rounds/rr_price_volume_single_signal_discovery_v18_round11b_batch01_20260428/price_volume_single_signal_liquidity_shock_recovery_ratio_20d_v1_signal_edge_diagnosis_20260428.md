# price_volume_single_signal_liquidity_shock_recovery_ratio_20d_v1 (20260428)

Candidate: `price_volume_single_signal_liquidity_shock_recovery_ratio_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_batch01_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 1814`
- `null_score_share = 0.00012`
- `scored_with_label_rows = 15020218`

## 2. IC Readout
- Full-sample correlation IC: `-0.000388`
- Average daily IC: `-0.000947`
- Median daily IC: `0.000054`
- Positive daily IC share: `0.50087`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003750`
- Decile 2: `0.003798`
- Decile 3: `0.003747`
- Decile 4: `0.003738`
- Decile 5: `0.003874`
- Decile 6: `0.003958`
- Decile 7: `0.003798`
- Decile 8: `0.003724`
- Decile 9: `0.003687`
- Decile 10: `0.004001`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.004084`
- Average label, rank 11-20: `0.004648`
- Average label, bottom 10: `0.004030`
- `top10 - rank11_20 = -0.000564`
- `top10 - bottom10 = 0.000055`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6360`
- Days with `|gap| < 0.005`: `6360`
- Days with `|gap| < 0.001`: `6075`

