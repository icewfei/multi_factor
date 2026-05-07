# price_volume_single_signal_alpha158_ma60_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_ma60_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch01_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.021836`
- Average daily IC: `0.035324`
- Median daily IC: `0.030370`
- Positive daily IC share: `0.58285`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.005801`
- Decile 2: `0.005241`
- Decile 3: `0.004815`
- Decile 4: `0.004656`
- Decile 5: `0.004376`
- Decile 6: `0.004023`
- Decile 7: `0.003737`
- Decile 8: `0.003242`
- Decile 9: `0.002368`
- Decile 10: `-0.000155`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.004280`
- Average label, rank 11-20: `0.007727`
- Average label, bottom 10: `-0.001748`
- `top10 - rank11_20 = -0.003447`
- `top10 - bottom10 = 0.006028`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

