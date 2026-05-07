# price_volume_single_signal_alpha158_wvma30_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_wvma30_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch05_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 907`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021120`

## 2. IC Readout
- Full-sample correlation IC: `-0.011973`
- Average daily IC: `-0.019104`
- Median daily IC: `-0.018770`
- Positive daily IC share: `0.36874`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.001762`
- Decile 2: `0.002926`
- Decile 3: `0.003392`
- Decile 4: `0.003784`
- Decile 5: `0.003928`
- Decile 6: `0.004189`
- Decile 7: `0.004306`
- Decile 8: `0.004375`
- Decile 9: `0.004638`
- Decile 10: `0.004797`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `-0.001919`
- Average label, rank 11-20: `0.000642`
- Average label, bottom 10: `0.005210`
- `top10 - rank11_20 = -0.002561`
- `top10 - bottom10 = -0.007129`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

