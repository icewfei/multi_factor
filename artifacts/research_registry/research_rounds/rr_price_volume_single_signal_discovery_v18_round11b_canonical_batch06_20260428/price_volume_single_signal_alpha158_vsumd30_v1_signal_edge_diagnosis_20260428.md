# price_volume_single_signal_alpha158_vsumd30_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_vsumd30_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch06_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 907`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021120`

## 2. IC Readout
- Full-sample correlation IC: `0.013641`
- Average daily IC: `0.022346`
- Median daily IC: `0.021519`
- Positive daily IC share: `0.61032`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004774`
- Decile 2: `0.004292`
- Decile 3: `0.004282`
- Decile 4: `0.004328`
- Decile 5: `0.004393`
- Decile 6: `0.004403`
- Decile 7: `0.004371`
- Decile 8: `0.004117`
- Decile 9: `0.003298`
- Decile 10: `-0.000180`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.006593`
- Average label, rank 11-20: `0.005548`
- Average label, bottom 10: `-0.007320`
- `top10 - rank11_20 = 0.001045`
- `top10 - bottom10 = 0.013912`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

