# v15 signal-edge diagnosis (2026-04-22)

Candidate: `price_volume_v15_trend_liquidity_improvement_core`
Research round: `rr_price_volume_trend_liquidity_improvement_family_20260422`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.011769`
- Average daily IC: `0.018551`
- Median daily IC: `0.017687`
- Positive daily IC share: `0.55515`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004873`
- Decile 2: `0.004428`
- Decile 3: `0.004222`
- Decile 4: `0.004224`
- Decile 5: `0.004230`
- Decile 6: `0.004194`
- Decile 7: `0.003835`
- Decile 8: `0.003534`
- Decile 9: `0.003186`
- Decile 10: `0.001386`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.004986`
- Average label, rank 11-20: `0.005826`
- Average label, bottom 10: `-0.001423`
- `top10 - rank11_20 = -0.000839`
- `top10 - bottom10 = 0.006409`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.002928`
- Median score gap `rank10 - rank11`: `0.001939`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `5219`
- Days with `|gap| < 0.001`: `1891`

