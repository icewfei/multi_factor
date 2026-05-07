# price_volume_single_signal_low_break_recovery_rate_20d_v1 (20260428)

Candidate: `price_volume_single_signal_low_break_recovery_rate_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round8_orthogonal_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 6144939`
- `null_score_share = 0.40338`
- `scored_with_label_rows = 8962797`

## 2. IC Readout
- Full-sample correlation IC: `0.007531`
- Average daily IC: `0.010822`
- Median daily IC: `0.007904`
- Positive daily IC share: `0.55102`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004575`
- Decile 2: `0.004932`
- Decile 3: `0.004881`
- Decile 4: `0.004910`
- Decile 5: `0.004915`
- Decile 6: `0.004698`
- Decile 7: `0.004579`
- Decile 8: `0.004265`
- Decile 9: `0.003706`
- Decile 10: `0.002856`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.003136`
- Average label, rank 11-20: `0.004004`
- Average label, bottom 10: `0.002691`
- `top10 - rank11_20 = -0.000867`
- `top10 - bottom10 = 0.000446`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.002219`
- Median score gap `rank10 - rank11`: `0.000884`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `5802`
- Days with `|gap| < 0.001`: `3701`

