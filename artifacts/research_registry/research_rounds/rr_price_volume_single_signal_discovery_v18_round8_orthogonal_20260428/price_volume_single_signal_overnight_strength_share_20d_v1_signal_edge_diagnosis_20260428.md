# price_volume_single_signal_overnight_strength_share_20d_v1 (20260428)

Candidate: `price_volume_single_signal_overnight_strength_share_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round8_orthogonal_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 1276`
- `null_score_share = 0.00008`
- `scored_with_label_rows = 15020751`

## 2. IC Readout
- Full-sample correlation IC: `0.003101`
- Average daily IC: `0.011005`
- Median daily IC: `0.010420`
- Positive daily IC share: `0.56846`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003281`
- Decile 2: `0.004127`
- Decile 3: `0.004259`
- Decile 4: `0.004207`
- Decile 5: `0.004108`
- Decile 6: `0.004093`
- Decile 7: `0.003962`
- Decile 8: `0.003824`
- Decile 9: `0.003492`
- Decile 10: `0.002731`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.000633`
- Average label, rank 11-20: `0.003510`
- Average label, bottom 10: `0.003391`
- `top10 - rank11_20 = -0.002877`
- `top10 - bottom10 = -0.002758`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

