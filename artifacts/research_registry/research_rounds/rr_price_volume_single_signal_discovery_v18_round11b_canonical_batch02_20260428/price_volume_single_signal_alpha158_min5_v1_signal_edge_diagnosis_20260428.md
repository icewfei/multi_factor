# price_volume_single_signal_alpha158_min5_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_min5_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch02_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.014297`
- Average daily IC: `0.027000`
- Median daily IC: `0.026273`
- Positive daily IC share: `0.59166`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003349`
- Decile 2: `0.004349`
- Decile 3: `0.004849`
- Decile 4: `0.005002`
- Decile 5: `0.005087`
- Decile 6: `0.005002`
- Decile 7: `0.004643`
- Decile 8: `0.003983`
- Decile 9: `0.002641`
- Decile 10: `-0.000795`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.000189`
- Average label, rank 11-20: `0.002922`
- Average label, bottom 10: `-0.001530`
- `top10 - rank11_20 = -0.002733`
- `top10 - bottom10 = 0.001719`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

