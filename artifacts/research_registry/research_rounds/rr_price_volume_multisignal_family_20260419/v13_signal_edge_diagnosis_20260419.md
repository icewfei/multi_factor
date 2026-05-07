# v13 Price/Volume Multisignal Signal-Edge Diagnosis (2026-04-19)

Candidate: `price_volume_multisignal_v13_core`
Research round: `rr_price_volume_multisignal_family_20260419`

## Executive Readout
The price/volume multisignal score does **not** show convincing positive signal quality in this fixed form, so the family may lack usable gross edge before portfolio extraction.

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 4538`
- `null_score_share = 0.00030`
- `scored_with_label_rows = 15017521`

Coverage interpretation:
- Market-data coverage is broad enough that missing scores are not the primary issue in this family.

## 2. IC Readout
- Full-sample correlation IC: `-0.021984`
- Average daily IC: `-0.038414`
- Median daily IC: `-0.042239`
- Positive daily IC share: `0.35575`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.000382`
- Decile 2: `0.001764`
- Decile 3: `0.003014`
- Decile 4: `0.003651`
- Decile 5: `0.004079`
- Decile 6: `0.004322`
- Decile 7: `0.004763`
- Decile 8: `0.005030`
- Decile 9: `0.005411`
- Decile 10: `0.005785`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `-0.002341`
- Average label, rank 11-20: `-0.001512`
- Average label, bottom 10: `0.007023`
- `top10 - rank11_20 = -0.000829`
- `top10 - bottom10 = -0.009365`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.004040`
- Median score gap `rank10 - rank11`: `0.002783`
- Days with both ranks present: `6357`
- Days with `|gap| < 0.005`: `4548`
- Days with `|gap| < 0.001`: `1399`

## Conclusion
1. The price/volume multisignal score does not show convincing positive full-sample IC, so the family likely lacks usable gross edge in its current fixed form.
2. Ranks 11-20 outperform the top 10 on average, which suggests the current TopK=10 extraction is cutting too aggressively or too noisily at the head.
3. Decile ordering is weak or inverted, which suggests the family may not carry stable cross-sectional ordering information.
4. Use this diagnosis before deciding whether to continue the price/volume multisignal family or switch to a different score family.

