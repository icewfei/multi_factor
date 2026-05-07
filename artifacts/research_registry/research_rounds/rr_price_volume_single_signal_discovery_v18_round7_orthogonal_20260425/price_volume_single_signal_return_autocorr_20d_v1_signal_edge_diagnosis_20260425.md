# price_volume_single_signal_return_autocorr_20d_v1 (20260425)

Candidate: `price_volume_single_signal_return_autocorr_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round7_orthogonal_20260425`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 907`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021120`

## 2. IC Readout
- Full-sample correlation IC: `-0.005212`
- Average daily IC: `-0.009544`
- Median daily IC: `-0.008423`
- Positive daily IC share: `0.44618`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.002311`
- Decile 2: `0.003292`
- Decile 3: `0.003791`
- Decile 4: `0.003990`
- Decile 5: `0.004134`
- Decile 6: `0.004369`
- Decile 7: `0.004259`
- Decile 8: `0.004314`
- Decile 9: `0.004182`
- Decile 10: `0.003450`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.000651`
- Average label, rank 11-20: `0.001485`
- Average label, bottom 10: `0.001358`
- `top10 - rank11_20 = -0.000833`
- `top10 - bottom10 = -0.000707`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

