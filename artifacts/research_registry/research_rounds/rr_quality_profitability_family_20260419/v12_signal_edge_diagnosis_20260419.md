# v12 Quality/Profitability Signal-Edge Diagnosis (2026-04-19)

Candidate: `quality_profitability_v12_core`
Research round: `rr_quality_profitability_family_20260419`

## Executive Readout
The quality/profitability score has only a **very weak positive edge**. It is not clearly broken, but the signal is shallow enough that current `TopK=10` extraction may be too aggressive.

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 4114150`
- `null_score_share = 0.27007`
- `scored_with_label_rows = 11024607`

Coverage interpretation:
- Missing PIT coverage is material, but there are still enough scored observations to diagnose the family.

## 2. IC Readout
- Full-sample correlation IC: `0.002484`
- Average daily IC: `-0.008694`
- Median daily IC: `0.004418`
- Positive daily IC share: `0.51318`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004127`
- Decile 2: `0.004024`
- Decile 3: `0.003923`
- Decile 4: `0.004044`
- Decile 5: `0.004005`
- Decile 6: `0.003716`
- Decile 7: `0.003900`
- Decile 8: `0.003874`
- Decile 9: `0.003769`
- Decile 10: `0.003415`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.003872`
- Average label, rank 11-20: `0.003928`
- Average label, bottom 10: `0.004045`
- `top10 - rank11_20 = -0.000056`
- `top10 - bottom10 = -0.000173`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.011295`
- Median score gap `rank10 - rank11`: `0.000867`
- Days with both ranks present: `5684`
- Days with `|gap| < 0.005`: `3710`
- Days with `|gap| < 0.001`: `2988`

## Conclusion
1. The quality/profitability score has positive but weak full-sample IC, so it is not random, but the gross edge is thin.
2. Ranks 11-20 outperform the top 10 on average, which suggests the current TopK=10 extraction is cutting too aggressively or too noisily at the head.
3. Broad decile ordering remains positive from top to bottom, which implies some ordering information survives before costs and extraction.
4. Use this diagnosis before deciding whether to continue the quality/profitability family or switch to a different score family.

