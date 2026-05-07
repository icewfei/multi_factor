# v14 Trend-Quality Price/Volume Signal-Edge Diagnosis (2026-04-22)

Candidate: `trend_quality_price_volume_v14_core`
Research round: `rr_trend_quality_price_volume_family_20260419`

## Executive Readout
The trend-quality price/volume score does **not** show convincing positive signal quality in this fixed form, so the family may lack usable gross edge before portfolio extraction.

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 907`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021120`

Coverage interpretation:
- Market-data coverage is broad enough that missing scores are not the primary issue in this family.

## 2. IC Readout
- Full-sample correlation IC: `-0.009235`
- Average daily IC: `-0.013902`
- Median daily IC: `-0.028778`
- Positive daily IC share: `0.39707`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003188`
- Decile 2: `0.003060`
- Decile 3: `0.003112`
- Decile 4: `0.003247`
- Decile 5: `0.003373`
- Decile 6: `0.003595`
- Decile 7: `0.003998`
- Decile 8: `0.004334`
- Decile 9: `0.004836`
- Decile 10: `0.005354`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.002371`
- Average label, rank 11-20: `0.003205`
- Average label, bottom 10: `0.005982`
- `top10 - rank11_20 = -0.000835`
- `top10 - bottom10 = -0.003612`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.004079`
- Median score gap `rank10 - rank11`: `0.002694`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `4562`
- Days with `|gap| < 0.001`: `1411`

## Conclusion
1. The trend-quality price/volume score does not show convincing positive full-sample IC, so the family likely lacks usable gross edge in its current fixed form.
2. Ranks 11-20 outperform the top 10 on average, which suggests the current TopK=10 extraction is cutting too aggressively or too noisily at the head.
3. Decile ordering is weak or inverted, which suggests the family may not carry stable cross-sectional ordering information.
4. Use this diagnosis before deciding whether to continue the trend-quality price/volume family or switch to a different score family.

