# price_volume_single_signal_signed_turnover_imbalance_20d_v1 (20260428)

Candidate: `price_volume_single_signal_signed_turnover_imbalance_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round8_orthogonal_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.005114`
- Average daily IC: `0.008009`
- Median daily IC: `0.006167`
- Positive daily IC share: `0.52998`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003404`
- Decile 2: `0.004041`
- Decile 3: `0.004189`
- Decile 4: `0.004294`
- Decile 5: `0.004279`
- Decile 6: `0.004307`
- Decile 7: `0.004236`
- Decile 8: `0.004006`
- Decile 9: `0.003660`
- Decile 10: `0.001702`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.002845`
- Average label, rank 11-20: `0.003037`
- Average label, bottom 10: `-0.001665`
- `top10 - rank11_20 = -0.000192`
- `top10 - bottom10 = 0.004510`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

