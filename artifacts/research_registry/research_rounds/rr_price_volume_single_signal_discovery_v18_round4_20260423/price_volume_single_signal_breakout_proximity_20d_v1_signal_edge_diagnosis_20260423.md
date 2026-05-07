# price_volume_single_signal_breakout_proximity_20d_v1 (20260423)

Candidate: `price_volume_single_signal_breakout_proximity_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round4_20260423`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 907`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021120`

## 2. IC Readout
- Full-sample correlation IC: `0.014219`
- Average daily IC: `0.026396`
- Median daily IC: `0.018205`
- Positive daily IC share: `0.55713`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004591`
- Decile 2: `0.004392`
- Decile 3: `0.004344`
- Decile 4: `0.004443`
- Decile 5: `0.004527`
- Decile 6: `0.004421`
- Decile 7: `0.004384`
- Decile 8: `0.003984`
- Decile 9: `0.003238`
- Decile 10: `-0.000247`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.002664`
- Average label, rank 11-20: `0.005822`
- Average label, bottom 10: `-0.005262`
- `top10 - rank11_20 = -0.003158`
- `top10 - bottom10 = 0.007926`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

