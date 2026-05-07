# price_volume_single_signal_downside_range_convexity_20d_v1 (20260428)

Candidate: `price_volume_single_signal_downside_range_convexity_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_batch01_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 3704`
- `null_score_share = 0.00024`
- `scored_with_label_rows = 15019007`

## 2. IC Readout
- Full-sample correlation IC: `0.002081`
- Average daily IC: `0.004594`
- Median daily IC: `0.003206`
- Positive daily IC share: `0.52510`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003781`
- Decile 2: `0.003898`
- Decile 3: `0.003968`
- Decile 4: `0.003965`
- Decile 5: `0.004014`
- Decile 6: `0.003913`
- Decile 7: `0.003967`
- Decile 8: `0.003824`
- Decile 9: `0.003631`
- Decile 10: `0.003168`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.003632`
- Average label, rank 11-20: `0.003491`
- Average label, bottom 10: `0.002003`
- `top10 - rank11_20 = 0.000141`
- `top10 - bottom10 = 0.001629`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000541`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6071`

