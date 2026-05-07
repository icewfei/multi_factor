# price_volume_single_signal_downside_absorption_ratio_20d_v1 (20260425)

Candidate: `price_volume_single_signal_downside_absorption_ratio_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round7_orthogonal_20260425`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 2787`
- `null_score_share = 0.00018`
- `scored_with_label_rows = 15019256`

## 2. IC Readout
- Full-sample correlation IC: `0.005857`
- Average daily IC: `0.008072`
- Median daily IC: `0.006482`
- Positive daily IC share: `0.54382`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003982`
- Decile 2: `0.004249`
- Decile 3: `0.004351`
- Decile 4: `0.004161`
- Decile 5: `0.004069`
- Decile 6: `0.003876`
- Decile 7: `0.003855`
- Decile 8: `0.003630`
- Decile 9: `0.003253`
- Decile 10: `0.002690`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.002743`
- Average label, rank 11-20: `0.004441`
- Average label, bottom 10: `0.001531`
- `top10 - rank11_20 = -0.001698`
- `top10 - bottom10 = 0.001212`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000541`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

