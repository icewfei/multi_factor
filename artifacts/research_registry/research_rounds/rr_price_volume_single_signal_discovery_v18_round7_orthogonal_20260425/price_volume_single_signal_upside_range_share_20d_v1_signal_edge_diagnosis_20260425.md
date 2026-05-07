# price_volume_single_signal_upside_range_share_20d_v1 (20260425)

Candidate: `price_volume_single_signal_upside_range_share_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round7_orthogonal_20260425`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 769`
- `null_score_share = 0.00005`
- `scored_with_label_rows = 15021902`

## 2. IC Readout
- Full-sample correlation IC: `0.010329`
- Average daily IC: `0.015721`
- Median daily IC: `0.013551`
- Positive daily IC share: `0.55153`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004082`
- Decile 2: `0.004423`
- Decile 3: `0.004437`
- Decile 4: `0.004383`
- Decile 5: `0.004338`
- Decile 6: `0.004244`
- Decile 7: `0.004127`
- Decile 8: `0.003778`
- Decile 9: `0.003166`
- Decile 10: `0.001137`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.004096`
- Average label, rank 11-20: `0.003965`
- Average label, bottom 10: `-0.001307`
- `top10 - rank11_20 = 0.000131`
- `top10 - bottom10 = 0.005403`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6071`

