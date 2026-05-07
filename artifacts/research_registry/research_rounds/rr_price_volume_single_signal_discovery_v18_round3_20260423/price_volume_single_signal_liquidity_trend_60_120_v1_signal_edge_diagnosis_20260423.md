# price_volume_single_signal_liquidity_trend_60_120_v1 Signal Edge Diagnosis (20260423)

Candidate: `price_volume_single_signal_liquidity_trend_60_120_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round3_20260423`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.008324`
- Average daily IC: `0.013666`
- Median daily IC: `0.013089`
- Positive daily IC share: `0.55515`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004601`
- Decile 2: `0.004258`
- Decile 3: `0.004230`
- Decile 4: `0.004179`
- Decile 5: `0.004047`
- Decile 6: `0.003889`
- Decile 7: `0.003705`
- Decile 8: `0.003659`
- Decile 9: `0.003352`
- Decile 10: `0.002195`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.006167`
- Average label, rank 11-20: `0.005726`
- Average label, bottom 10: `0.000994`
- `top10 - rank11_20 = 0.000441`
- `top10 - bottom10 = 0.005172`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

