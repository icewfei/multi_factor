# price_volume_single_signal_rolling_vwap_distance_20d_v1 (20260428)

Candidate: `price_volume_single_signal_rolling_vwap_distance_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_batch01_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.006054`
- Average daily IC: `0.012831`
- Median daily IC: `0.007636`
- Positive daily IC share: `0.52211`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004562`
- Decile 2: `0.004159`
- Decile 3: `0.004074`
- Decile 4: `0.003921`
- Decile 5: `0.003906`
- Decile 6: `0.003922`
- Decile 7: `0.003723`
- Decile 8: `0.003568`
- Decile 9: `0.003385`
- Decile 10: `0.002897`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.004965`
- Average label, rank 11-20: `0.006689`
- Average label, bottom 10: `0.002698`
- `top10 - rank11_20 = -0.001724`
- `top10 - bottom10 = 0.002268`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

