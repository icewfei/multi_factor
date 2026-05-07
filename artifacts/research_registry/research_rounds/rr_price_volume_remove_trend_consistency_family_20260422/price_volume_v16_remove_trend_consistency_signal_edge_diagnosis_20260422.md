# v16 Signal-Edge and Head-Slice Diagnosis (20260422)

Candidate: `price_volume_v16_remove_trend_consistency`
Research round: `rr_price_volume_remove_trend_consistency_family_20260422`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 135887`
- `null_score_share = 0.00892`
- `scored_with_label_rows = 14888004`

## 2. IC Readout
- Full-sample correlation IC: `0.013345`
- Average daily IC: `0.020658`
- Median daily IC: `0.017744`
- Positive daily IC share: `0.55822`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.005081`
- Decile 2: `0.004583`
- Decile 3: `0.004356`
- Decile 4: `0.004256`
- Decile 5: `0.004052`
- Decile 6: `0.003813`
- Decile 7: `0.003684`
- Decile 8: `0.003519`
- Decile 9: `0.002734`
- Decile 10: `0.001425`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.006814`
- Average label, rank 11-20: `0.006295`
- Average label, bottom 10: `0.000516`
- `top10 - rank11_20 = 0.000519`
- `top10 - bottom10 = 0.006298`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.002006`
- Median score gap `rank10 - rank11`: `0.001284`
- Days with both ranks present: `6302`
- Days with `|gap| < 0.005`: `5731`
- Days with `|gap| < 0.001`: `2613`

