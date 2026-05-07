# price_volume_single_signal_turnover_stability_20d_v1 (20260425)

Candidate: `price_volume_single_signal_turnover_stability_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round5_20260425`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 907`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021120`

## 2. IC Readout
- Full-sample correlation IC: `-0.015466`
- Average daily IC: `-0.027256`
- Median daily IC: `-0.027674`
- Positive daily IC share: `0.39786`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.000480`
- Decile 2: `0.002718`
- Decile 3: `0.003406`
- Decile 4: `0.003802`
- Decile 5: `0.004310`
- Decile 6: `0.004597`
- Decile 7: `0.004791`
- Decile 8: `0.004833`
- Decile 9: `0.004875`
- Decile 10: `0.004289`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `-0.005670`
- Average label, rank 11-20: `-0.002341`
- Average label, bottom 10: `0.003324`
- `top10 - rank11_20 = -0.003328`
- `top10 - bottom10 = -0.008994`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

