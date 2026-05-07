# price_volume_single_signal_alpha158_rsqr60_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_rsqr60_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch02_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 942`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021085`

## 2. IC Readout
- Full-sample correlation IC: `-0.006325`
- Average daily IC: `-0.011167`
- Median daily IC: `-0.006709`
- Positive daily IC share: `0.46522`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003253`
- Decile 2: `0.003309`
- Decile 3: `0.003509`
- Decile 4: `0.003582`
- Decile 5: `0.003514`
- Decile 6: `0.003829`
- Decile 7: `0.003990`
- Decile 8: `0.004160`
- Decile 9: `0.004329`
- Decile 10: `0.004618`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.003770`
- Average label, rank 11-20: `0.003349`
- Average label, bottom 10: `0.005508`
- `top10 - rank11_20 = 0.000421`
- `top10 - bottom10 = -0.001737`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

