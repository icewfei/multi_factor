# price_volume_single_signal_downside_semivol_ratio_20d_v1 (20260428)

Candidate: `price_volume_single_signal_downside_semivol_ratio_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round9_composability_first_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 5`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022014`

## 2. IC Readout
- Full-sample correlation IC: `0.015265`
- Average daily IC: `0.024182`
- Median daily IC: `0.022011`
- Positive daily IC share: `0.58159`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004456`
- Decile 2: `0.004673`
- Decile 3: `0.004813`
- Decile 4: `0.004843`
- Decile 5: `0.004513`
- Decile 6: `0.004256`
- Decile 7: `0.004019`
- Decile 8: `0.003425`
- Decile 9: `0.002416`
- Decile 10: `0.000696`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.001741`
- Average label, rank 11-20: `0.004150`
- Average label, bottom 10: `0.000274`
- `top10 - rank11_20 = -0.002409`
- `top10 - bottom10 = 0.001467`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

