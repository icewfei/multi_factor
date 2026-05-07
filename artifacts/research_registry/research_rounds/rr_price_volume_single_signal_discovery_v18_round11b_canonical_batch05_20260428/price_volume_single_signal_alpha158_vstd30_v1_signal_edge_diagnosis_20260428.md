# price_volume_single_signal_alpha158_vstd30_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_vstd30_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch05_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 907`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021120`

## 2. IC Readout
- Full-sample correlation IC: `0.002992`
- Average daily IC: `0.004840`
- Median daily IC: `0.004294`
- Positive daily IC share: `0.52439`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003631`
- Decile 2: `0.003511`
- Decile 3: `0.003772`
- Decile 4: `0.004128`
- Decile 5: `0.004343`
- Decile 6: `0.004502`
- Decile 7: `0.004427`
- Decile 8: `0.004183`
- Decile 9: `0.003676`
- Decile 10: `0.001914`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.005973`
- Average label, rank 11-20: `0.004743`
- Average label, bottom 10: `0.000188`
- `top10 - rank11_20 = 0.001231`
- `top10 - bottom10 = 0.005786`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

