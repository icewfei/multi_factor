# price_volume_single_signal_alpha158_full_009_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_full_009_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_batch02_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.004693`
- Average daily IC: `0.001432`
- Median daily IC: `0.000205`
- Positive daily IC share: `0.50071`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003245`
- Decile 2: `0.003820`
- Decile 3: `0.004089`
- Decile 4: `0.004290`
- Decile 5: `0.004442`
- Decile 6: `0.004611`
- Decile 7: `0.004489`
- Decile 8: `0.004223`
- Decile 9: `0.003641`
- Decile 10: `0.001267`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.002437`
- Average label, rank 11-20: `0.002557`
- Average label, bottom 10: `-0.001942`
- `top10 - rank11_20 = -0.000120`
- `top10 - bottom10 = 0.004379`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

