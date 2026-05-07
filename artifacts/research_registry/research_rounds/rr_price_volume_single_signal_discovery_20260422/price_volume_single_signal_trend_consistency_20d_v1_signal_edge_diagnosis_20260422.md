# Trend Consistency 20D Single-Signal Edge Diagnosis (20260422)

Candidate: `price_volume_single_signal_trend_consistency_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_20260422`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.003251`
- Average daily IC: `0.005854`
- Median daily IC: `0.002756`
- Positive daily IC share: `0.51487`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003465`
- Decile 2: `0.003982`
- Decile 3: `0.004132`
- Decile 4: `0.004077`
- Decile 5: `0.004175`
- Decile 6: `0.004123`
- Decile 7: `0.004092`
- Decile 8: `0.003905`
- Decile 9: `0.003686`
- Decile 10: `0.002483`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.002143`
- Average label, rank 11-20: `0.003380`
- Average label, bottom 10: `0.001993`
- `top10 - rank11_20 = -0.001237`
- `top10 - bottom10 = 0.000149`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

