# price_volume_single_signal_alpha158_high0_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_high0_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch01_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.011540`
- Average daily IC: `0.017308`
- Median daily IC: `0.010326`
- Positive daily IC share: `0.54430`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003849`
- Decile 2: `0.004513`
- Decile 3: `0.004577`
- Decile 4: `0.004611`
- Decile 5: `0.004547`
- Decile 6: `0.004382`
- Decile 7: `0.004113`
- Decile 8: `0.003818`
- Decile 9: `0.003139`
- Decile 10: `0.000561`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.000204`
- Average label, rank 11-20: `0.002807`
- Average label, bottom 10: `-0.002209`
- `top10 - rank11_20 = -0.002603`
- `top10 - bottom10 = 0.002413`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

