# price_volume_single_signal_alpha158_corr20_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_corr20_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch04_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 942`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021085`

## 2. IC Readout
- Full-sample correlation IC: `0.018514`
- Average daily IC: `0.030448`
- Median daily IC: `0.030692`
- Positive daily IC share: `0.64227`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.005504`
- Decile 2: `0.004971`
- Decile 3: `0.004758`
- Decile 4: `0.004479`
- Decile 5: `0.004322`
- Decile 6: `0.004022`
- Decile 7: `0.003681`
- Decile 8: `0.003182`
- Decile 9: `0.002449`
- Decile 10: `0.000708`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.010246`
- Average label, rank 11-20: `0.007490`
- Average label, bottom 10: `-0.002654`
- `top10 - rank11_20 = 0.002756`
- `top10 - bottom10 = 0.012900`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

