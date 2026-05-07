# price_volume_single_signal_range_compression_10_40_v1 (20260425)

Candidate: `price_volume_single_signal_range_compression_10_40_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round5_20260425`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 435`
- `null_score_share = 0.00003`
- `scored_with_label_rows = 15021977`

## 2. IC Readout
- Full-sample correlation IC: `-0.003399`
- Average daily IC: `-0.003309`
- Median daily IC: `-0.004109`
- Positive daily IC share: `0.48308`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.001778`
- Decile 2: `0.003771`
- Decile 3: `0.004164`
- Decile 4: `0.004285`
- Decile 5: `0.004490`
- Decile 6: `0.004342`
- Decile 7: `0.004271`
- Decile 8: `0.004011`
- Decile 9: `0.003784`
- Decile 10: `0.003226`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `-0.002053`
- Average label, rank 11-20: `-0.000413`
- Average label, bottom 10: `0.003911`
- `top10 - rank11_20 = -0.001640`
- `top10 - bottom10 = -0.005964`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6072`

