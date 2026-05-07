# price_volume_v22_breakout_volume_confirmation_substitution (20260424)

Candidate: `price_volume_v22_breakout_volume_confirmation_substitution`
Research round: `rr_price_volume_breakout_volume_confirmation_substitution_family_20260424`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 135887`
- `null_score_share = 0.00892`
- `scored_with_label_rows = 14888004`

## 2. IC Readout
- Full-sample correlation IC: `0.012080`
- Average daily IC: `0.017646`
- Median daily IC: `0.018428`
- Positive daily IC share: `0.56172`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004371`
- Decile 2: `0.004590`
- Decile 3: `0.004562`
- Decile 4: `0.004381`
- Decile 5: `0.004038`
- Decile 6: `0.003738`
- Decile 7: `0.003684`
- Decile 8: `0.003620`
- Decile 9: `0.003199`
- Decile 10: `0.001320`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.004993`
- Average label, rank 11-20: `0.004327`
- Average label, bottom 10: `-0.002348`
- `top10 - rank11_20 = 0.000667`
- `top10 - bottom10 = 0.007341`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.002843`
- Median score gap `rank10 - rank11`: `0.001941`
- Days with both ranks present: `6302`
- Days with `|gap| < 0.005`: `5223`
- Days with `|gap| < 0.001`: `1913`

