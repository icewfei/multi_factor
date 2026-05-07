# price_volume_single_signal_gap_fill_rate_20d_v1 (20260428)

Candidate: `price_volume_single_signal_gap_fill_rate_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round9_composability_first_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 1276`
- `null_score_share = 0.00008`
- `scored_with_label_rows = 15020751`

## 2. IC Readout
- Full-sample correlation IC: `-0.007426`
- Average daily IC: `-0.009034`
- Median daily IC: `-0.011068`
- Positive daily IC share: `0.42823`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.002512`
- Decile 2: `0.003175`
- Decile 3: `0.003558`
- Decile 4: `0.003834`
- Decile 5: `0.003942`
- Decile 6: `0.003957`
- Decile 7: `0.004277`
- Decile 8: `0.004177`
- Decile 9: `0.004392`
- Decile 10: `0.004269`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.001071`
- Average label, rank 11-20: `0.002216`
- Average label, bottom 10: `0.003958`
- `top10 - rank11_20 = -0.001145`
- `top10 - bottom10 = -0.002887`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

