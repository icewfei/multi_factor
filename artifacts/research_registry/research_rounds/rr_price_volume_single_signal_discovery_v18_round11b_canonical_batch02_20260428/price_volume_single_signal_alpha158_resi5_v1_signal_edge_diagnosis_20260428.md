# price_volume_single_signal_alpha158_resi5_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_resi5_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch02_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.005821`
- Average daily IC: `0.010060`
- Median daily IC: `0.011039`
- Positive daily IC share: `0.54241`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.002202`
- Decile 2: `0.004077`
- Decile 3: `0.004548`
- Decile 4: `0.004877`
- Decile 5: `0.004944`
- Decile 6: `0.004853`
- Decile 7: `0.004632`
- Decile 8: `0.004098`
- Decile 9: `0.003149`
- Decile 10: `0.000737`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `-0.003384`
- Average label, rank 11-20: `-0.000133`
- Average label, bottom 10: `-0.001891`
- `top10 - rank11_20 = -0.003251`
- `top10 - bottom10 = -0.001493`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

