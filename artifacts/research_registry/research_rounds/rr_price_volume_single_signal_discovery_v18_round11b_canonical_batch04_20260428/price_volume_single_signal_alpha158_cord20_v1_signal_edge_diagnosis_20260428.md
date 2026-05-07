# price_volume_single_signal_alpha158_cord20_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_cord20_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch04_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 1816`
- `null_score_share = 0.00012`
- `scored_with_label_rows = 15020216`

## 2. IC Readout
- Full-sample correlation IC: `0.016534`
- Average daily IC: `0.029667`
- Median daily IC: `0.025862`
- Positive daily IC share: `0.63923`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.005208`
- Decile 2: `0.004914`
- Decile 3: `0.004707`
- Decile 4: `0.004465`
- Decile 5: `0.004278`
- Decile 6: `0.004008`
- Decile 7: `0.003659`
- Decile 8: `0.003161`
- Decile 9: `0.002644`
- Decile 10: `0.001018`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.006332`
- Average label, rank 11-20: `0.006021`
- Average label, bottom 10: `-0.001941`
- `top10 - rank11_20 = 0.000311`
- `top10 - bottom10 = 0.008273`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6360`
- Days with `|gap| < 0.005`: `6360`
- Days with `|gap| < 0.001`: `6075`

