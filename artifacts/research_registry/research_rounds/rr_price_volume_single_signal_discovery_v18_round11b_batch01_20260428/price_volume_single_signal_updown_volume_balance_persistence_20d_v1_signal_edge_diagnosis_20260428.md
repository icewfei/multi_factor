# price_volume_single_signal_updown_volume_balance_persistence_20d_v1 (20260428)

Candidate: `price_volume_single_signal_updown_volume_balance_persistence_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_batch01_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 907`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021120`

## 2. IC Readout
- Full-sample correlation IC: `-0.005004`
- Average daily IC: `-0.007986`
- Median daily IC: `-0.007200`
- Positive daily IC share: `0.43311`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.002922`
- Decile 2: `0.003434`
- Decile 3: `0.003650`
- Decile 4: `0.003777`
- Decile 5: `0.003869`
- Decile 6: `0.003957`
- Decile 7: `0.004099`
- Decile 8: `0.004064`
- Decile 9: `0.004113`
- Decile 10: `0.004208`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.001599`
- Average label, rank 11-20: `0.002398`
- Average label, bottom 10: `0.004265`
- `top10 - rank11_20 = -0.000799`
- `top10 - bottom10 = -0.002666`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

