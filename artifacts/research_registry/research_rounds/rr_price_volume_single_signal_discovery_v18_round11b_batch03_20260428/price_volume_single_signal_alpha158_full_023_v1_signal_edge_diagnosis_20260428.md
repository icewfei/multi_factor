# price_volume_single_signal_alpha158_full_023_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_full_023_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_batch03_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 769`
- `null_score_share = 0.00005`
- `scored_with_label_rows = 15021902`

## 2. IC Readout
- Full-sample correlation IC: `0.007567`
- Average daily IC: `0.009496`
- Median daily IC: `0.005410`
- Positive daily IC share: `0.52274`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003844`
- Decile 2: `0.004238`
- Decile 3: `0.004251`
- Decile 4: `0.004234`
- Decile 5: `0.004285`
- Decile 6: `0.004269`
- Decile 7: `0.004197`
- Decile 8: `0.003920`
- Decile 9: `0.003348`
- Decile 10: `0.001531`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.003590`
- Average label, rank 11-20: `0.003823`
- Average label, bottom 10: `-0.001848`
- `top10 - rank11_20 = -0.000234`
- `top10 - bottom10 = 0.005438`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6071`

