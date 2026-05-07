# price_volume_single_signal_breakout_proximity_60d_v1 (20260423)

Candidate: `price_volume_single_signal_breakout_proximity_60d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round4_20260423`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 907`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021120`

## 2. IC Readout
- Full-sample correlation IC: `0.016031`
- Average daily IC: `0.028719`
- Median daily IC: `0.018644`
- Positive daily IC share: `0.55146`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.006177`
- Decile 2: `0.004825`
- Decile 3: `0.004293`
- Decile 4: `0.003921`
- Decile 5: `0.003689`
- Decile 6: `0.003613`
- Decile 7: `0.003560`
- Decile 8: `0.003523`
- Decile 9: `0.003358`
- Decile 10: `0.001117`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.005599`
- Average label, rank 11-20: `0.008413`
- Average label, bottom 10: `-0.003385`
- `top10 - rank11_20 = -0.002815`
- `top10 - bottom10 = 0.008984`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

