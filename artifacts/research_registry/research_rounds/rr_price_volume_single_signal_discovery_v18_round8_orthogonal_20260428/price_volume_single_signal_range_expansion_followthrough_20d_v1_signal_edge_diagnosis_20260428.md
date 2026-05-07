# price_volume_single_signal_range_expansion_followthrough_20d_v1 (20260428)

Candidate: `price_volume_single_signal_range_expansion_followthrough_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round8_orthogonal_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.020858`
- Average daily IC: `0.028979`
- Median daily IC: `0.027090`
- Positive daily IC share: `0.63037`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.005238`
- Decile 2: `0.005432`
- Decile 3: `0.005033`
- Decile 4: `0.004767`
- Decile 5: `0.004346`
- Decile 6: `0.004166`
- Decile 7: `0.003593`
- Decile 8: `0.003133`
- Decile 9: `0.002421`
- Decile 10: `-0.000023`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.003877`
- Average label, rank 11-20: `0.005163`
- Average label, bottom 10: `-0.002899`
- `top10 - rank11_20 = -0.001286`
- `top10 - bottom10 = 0.006776`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

