# price_volume_single_signal_close_to_vwap_bias_20d_v1 (20260428)

Candidate: `price_volume_single_signal_close_to_vwap_bias_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round10_alpha158_paper_whitelist_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 769`
- `null_score_share = 0.00005`
- `scored_with_label_rows = 15021902`

## 2. IC Readout
- Full-sample correlation IC: `0.016715`
- Average daily IC: `0.021815`
- Median daily IC: `0.017190`
- Positive daily IC share: `0.56066`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004753`
- Decile 2: `0.004526`
- Decile 3: `0.004592`
- Decile 4: `0.004597`
- Decile 5: `0.004506`
- Decile 6: `0.004543`
- Decile 7: `0.004373`
- Decile 8: `0.003985`
- Decile 9: `0.002954`
- Decile 10: `-0.000719`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.005720`
- Average label, rank 11-20: `0.006220`
- Average label, bottom 10: `-0.005454`
- `top10 - rank11_20 = -0.000500`
- `top10 - bottom10 = 0.011174`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6071`

