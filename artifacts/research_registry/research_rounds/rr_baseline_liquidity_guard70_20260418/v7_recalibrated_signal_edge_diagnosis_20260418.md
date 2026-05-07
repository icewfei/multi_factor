# v7 Recalibrated Signal-Edge Diagnosis (2026-04-18)

Candidate: `baseline_momentum_v7_liquidity_guard70`
Research round: `rr_baseline_liquidity_guard70_20260418`

## Executive Readout
The recalibrated momentum-only score is **not random**, but its edge is **weak and shallow**.
The key issue is not complete lack of signal. The key issue is that the current `TopK=10` extraction appears to pull a noisy extreme slice from a score whose best names are not clearly separated from the next bucket.

## 1. Coverage
- `ranking_eligible_rows = 15,233,701`
- `null_score_rows = 135,887`
- `null_score_share = 0.00892`

Coverage is good enough that missing scores are not the primary problem.

## 2. IC Readout
- Full-sample correlation IC: `0.009758`
- Average daily IC: `0.013398`
- Median daily IC: `0.007710`
- Positive daily IC share: `0.52359`

Interpretation:
- The score has a weak but real positive relationship with forward returns.
- This is consistent with a marginal signal, not a broken one.

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004724`
- Decile 2: `0.004351`
- Decile 3: `0.004218`
- Decile 4: `0.004079`
- Decile 5: `0.003997`
- Decile 6: `0.003953`
- Decile 7: `0.003711`
- Decile 8: `0.003497`
- Decile 9: `0.002884`
- Decile 10: `0.002092`

Interpretation:
- There is a broad monotonic decline from top to bottom decile.
- So the score does carry useful ordering information.
- But the slope is shallow rather than steep.

## 4. Why `TopK=10` Still Struggles
Bucket comparison:
- Average label, top 10 names: `0.004282`
- Average label, rank 11-20: `0.005483`
- Average label, bottom 10: `0.001820`
- `top10 - rank11_20 = -0.001201`
- `top10 - bottom10 = 0.002461`

Interpretation:
- The top 10 does beat the bottom tail.
- But the next 10 names outperform the top 10.
- That strongly suggests the score's edge is not concentrated cleanly in the most extreme head bucket.

This fits the earlier run-state evidence that the cutoff around ranks 10/11 is very thin.

## Conclusion
The recalibrated `v7` signal layer indicates:
1. The score still has **weak positive edge**.
2. The edge is **too shallow** to make the extreme top 10 a robust extraction.
3. The current `TopK=10` mapping likely amplifies noise at the head of the rank ordering.

## Recommended Direction
Do not keep tweaking liquidity guards.
The next one-dimensional research step should target **score-to-portfolio extraction**, because the problem now looks more like:
- weak edge concentration, and
- noisy top-slice selection,
rather than simple low-liquidity contamination.
