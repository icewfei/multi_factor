# price_volume_single_signal_alpha158_full_016_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_full_016_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_batch03_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 1697`
- `null_score_share = 0.00011`
- `scored_with_label_rows = 15020981`

## 2. IC Readout
- Full-sample correlation IC: `0.002166`
- Average daily IC: `0.005122`
- Median daily IC: `0.003724`
- Positive daily IC share: `0.52424`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.002399`
- Decile 2: `0.003967`
- Decile 3: `0.004419`
- Decile 4: `0.004561`
- Decile 5: `0.004598`
- Decile 6: `0.004382`
- Decile 7: `0.004229`
- Decile 8: `0.003881`
- Decile 9: `0.003371`
- Decile 10: `0.002283`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `-0.000213`
- Average label, rank 11-20: `0.000770`
- Average label, bottom 10: `0.002213`
- `top10 - rank11_20 = -0.000983`
- `top10 - bottom10 = -0.002426`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6071`

