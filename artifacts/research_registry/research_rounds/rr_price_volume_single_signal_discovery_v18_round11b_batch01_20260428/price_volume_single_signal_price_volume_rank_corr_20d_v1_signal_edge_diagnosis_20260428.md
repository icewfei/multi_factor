# price_volume_single_signal_price_volume_rank_corr_20d_v1 (20260428)

Candidate: `price_volume_single_signal_price_volume_rank_corr_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_batch01_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 907`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021120`

## 2. IC Readout
- Full-sample correlation IC: `0.011394`
- Average daily IC: `0.020216`
- Median daily IC: `0.019702`
- Positive daily IC share: `0.62685`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004933`
- Decile 2: `0.004580`
- Decile 3: `0.004357`
- Decile 4: `0.004201`
- Decile 5: `0.004001`
- Decile 6: `0.003942`
- Decile 7: `0.003710`
- Decile 8: `0.003402`
- Decile 9: `0.003059`
- Decile 10: `0.001895`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.005890`
- Average label, rank 11-20: `0.005759`
- Average label, bottom 10: `0.000290`
- `top10 - rank11_20 = 0.000131`
- `top10 - bottom10 = 0.005601`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

