# price_volume_single_signal_candle_body_efficiency_20d_v1 (20260428)

Candidate: `price_volume_single_signal_candle_body_efficiency_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_batch01_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 769`
- `null_score_share = 0.00005`
- `scored_with_label_rows = 15021902`

## 2. IC Readout
- Full-sample correlation IC: `-0.003758`
- Average daily IC: `-0.009714`
- Median daily IC: `-0.007521`
- Positive daily IC share: `0.44988`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.002842`
- Decile 2: `0.003484`
- Decile 3: `0.003707`
- Decile 4: `0.003849`
- Decile 5: `0.003976`
- Decile 6: `0.004205`
- Decile 7: `0.004153`
- Decile 8: `0.004123`
- Decile 9: `0.004093`
- Decile 10: `0.003695`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.001261`
- Average label, rank 11-20: `0.001475`
- Average label, bottom 10: `0.003390`
- `top10 - rank11_20 = -0.000214`
- `top10 - bottom10 = -0.002128`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6071`

