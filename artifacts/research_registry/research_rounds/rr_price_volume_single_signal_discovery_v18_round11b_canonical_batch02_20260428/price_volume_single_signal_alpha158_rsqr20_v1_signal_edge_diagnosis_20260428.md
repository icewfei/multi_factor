# price_volume_single_signal_alpha158_rsqr20_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_rsqr20_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch02_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 942`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021085`

## 2. IC Readout
- Full-sample correlation IC: `-0.001308`
- Average daily IC: `-0.002598`
- Median daily IC: `0.002299`
- Positive daily IC share: `0.51086`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003513`
- Decile 2: `0.003657`
- Decile 3: `0.003744`
- Decile 4: `0.003830`
- Decile 5: `0.003781`
- Decile 6: `0.003964`
- Decile 7: `0.004034`
- Decile 8: `0.003951`
- Decile 9: `0.003874`
- Decile 10: `0.003741`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.003641`
- Average label, rank 11-20: `0.003818`
- Average label, bottom 10: `0.003382`
- `top10 - rank11_20 = -0.000177`
- `top10 - bottom10 = 0.000259`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

