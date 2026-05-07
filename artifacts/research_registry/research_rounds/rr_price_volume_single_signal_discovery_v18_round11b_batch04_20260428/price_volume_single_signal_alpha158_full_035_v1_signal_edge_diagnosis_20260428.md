# price_volume_single_signal_alpha158_full_035_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_full_035_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_batch04_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 769`
- `null_score_share = 0.00005`
- `scored_with_label_rows = 15021902`

## 2. IC Readout
- Full-sample correlation IC: `-0.003647`
- Average daily IC: `-0.004849`
- Median daily IC: `-0.003478`
- Positive daily IC share: `0.46955`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003046`
- Decile 2: `0.003651`
- Decile 3: `0.003713`
- Decile 4: `0.003843`
- Decile 5: `0.003805`
- Decile 6: `0.003917`
- Decile 7: `0.003979`
- Decile 8: `0.004086`
- Decile 9: `0.004105`
- Decile 10: `0.003981`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.001828`
- Average label, rank 11-20: `0.002821`
- Average label, bottom 10: `0.004319`
- `top10 - rank11_20 = -0.000993`
- `top10 - bottom10 = -0.002491`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6071`

