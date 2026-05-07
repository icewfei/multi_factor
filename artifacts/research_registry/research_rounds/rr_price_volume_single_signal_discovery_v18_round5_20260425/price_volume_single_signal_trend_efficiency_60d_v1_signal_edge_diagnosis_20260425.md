# price_volume_single_signal_trend_efficiency_60d_v1 (20260425)

Candidate: `price_volume_single_signal_trend_efficiency_60d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round5_20260425`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 18239`
- `null_score_share = 0.00120`
- `scored_with_label_rows = 15003964`

## 2. IC Readout
- Full-sample correlation IC: `0.008624`
- Average daily IC: `0.014350`
- Median daily IC: `0.013229`
- Positive daily IC share: `0.54412`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003661`
- Decile 2: `0.004258`
- Decile 3: `0.004339`
- Decile 4: `0.004443`
- Decile 5: `0.004522`
- Decile 6: `0.004349`
- Decile 7: `0.004080`
- Decile 8: `0.003690`
- Decile 9: `0.002877`
- Decile 10: `0.001514`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `-0.000591`
- Average label, rank 11-20: `0.003123`
- Average label, bottom 10: `0.000961`
- `top10 - rank11_20 = -0.003714`
- `top10 - bottom10 = -0.001551`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000535`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6342`
- Days with `|gap| < 0.005`: `6342`
- Days with `|gap| < 0.001`: `6075`

