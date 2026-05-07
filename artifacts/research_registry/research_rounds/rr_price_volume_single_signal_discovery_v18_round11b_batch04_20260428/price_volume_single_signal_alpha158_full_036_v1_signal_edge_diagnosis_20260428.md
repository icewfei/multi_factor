# price_volume_single_signal_alpha158_full_036_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_full_036_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_batch04_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.011240`
- Average daily IC: `0.019715`
- Median daily IC: `0.019215`
- Positive daily IC share: `0.59308`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004640`
- Decile 2: `0.004678`
- Decile 3: `0.004530`
- Decile 4: `0.004351`
- Decile 5: `0.004144`
- Decile 6: `0.003867`
- Decile 7: `0.003555`
- Decile 8: `0.003242`
- Decile 9: `0.002914`
- Decile 10: `0.002191`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.007208`
- Average label, rank 11-20: `0.006184`
- Average label, bottom 10: `-0.001607`
- `top10 - rank11_20 = 0.001024`
- `top10 - bottom10 = 0.008815`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

