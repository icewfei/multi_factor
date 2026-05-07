# Liquidity Trend 20-60 Single-Signal Edge Diagnosis (20260422)

Candidate: `price_volume_single_signal_liquidity_trend_20_60_v1`
Research round: `rr_price_volume_single_signal_discovery_20260422`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.012159`
- Average daily IC: `0.018665`
- Median daily IC: `0.020868`
- Positive daily IC share: `0.57923`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004605`
- Decile 2: `0.004562`
- Decile 3: `0.004406`
- Decile 4: `0.004367`
- Decile 5: `0.004334`
- Decile 6: `0.004159`
- Decile 7: `0.003929`
- Decile 8: `0.003466`
- Decile 9: `0.003090`
- Decile 10: `0.001194`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.005774`
- Average label, rank 11-20: `0.005599`
- Average label, bottom 10: `-0.001394`
- `top10 - rank11_20 = 0.000174`
- `top10 - bottom10 = 0.007168`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

