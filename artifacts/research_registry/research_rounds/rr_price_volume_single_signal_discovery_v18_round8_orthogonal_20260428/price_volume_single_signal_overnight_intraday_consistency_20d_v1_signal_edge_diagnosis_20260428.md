# price_volume_single_signal_overnight_intraday_consistency_20d_v1 (20260428)

Candidate: `price_volume_single_signal_overnight_intraday_consistency_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round8_orthogonal_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 907`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021120`

## 2. IC Readout
- Full-sample correlation IC: `-0.006006`
- Average daily IC: `-0.003886`
- Median daily IC: `-0.002667`
- Positive daily IC share: `0.48001`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.001741`
- Decile 2: `0.003434`
- Decile 3: `0.004031`
- Decile 4: `0.004082`
- Decile 5: `0.004330`
- Decile 6: `0.004183`
- Decile 7: `0.004300`
- Decile 8: `0.004219`
- Decile 9: `0.004255`
- Decile 10: `0.003518`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `-0.001981`
- Average label, rank 11-20: `0.000046`
- Average label, bottom 10: `0.002713`
- `top10 - rank11_20 = -0.002027`
- `top10 - bottom10 = -0.004694`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

