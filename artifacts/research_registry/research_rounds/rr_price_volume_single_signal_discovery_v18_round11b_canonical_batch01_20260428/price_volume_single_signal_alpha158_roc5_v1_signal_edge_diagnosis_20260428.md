# price_volume_single_signal_alpha158_roc5_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_roc5_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch01_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 4538`
- `null_score_share = 0.00030`
- `scored_with_label_rows = 15017521`

## 2. IC Readout
- Full-sample correlation IC: `0.021762`
- Average daily IC: `0.041577`
- Median daily IC: `0.039505`
- Positive daily IC share: `0.62803`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004770`
- Decile 2: `0.005160`
- Decile 3: `0.005053`
- Decile 4: `0.005005`
- Decile 5: `0.004774`
- Decile 6: `0.004593`
- Decile 7: `0.004191`
- Decile 8: `0.003545`
- Decile 9: `0.002249`
- Decile 10: `-0.001175`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `-0.001406`
- Average label, rank 11-20: `0.004947`
- Average label, bottom 10: `-0.000977`
- `top10 - rank11_20 = -0.006352`
- `top10 - bottom10 = -0.000429`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6357`
- Days with `|gap| < 0.005`: `6357`
- Days with `|gap| < 0.001`: `6075`

