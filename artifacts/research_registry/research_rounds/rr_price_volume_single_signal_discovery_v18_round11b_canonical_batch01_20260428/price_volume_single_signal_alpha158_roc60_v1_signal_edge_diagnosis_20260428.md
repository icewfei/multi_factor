# price_volume_single_signal_alpha158_roc60_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_roc60_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch01_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 135887`
- `null_score_share = 0.00892`
- `scored_with_label_rows = 14888004`

## 2. IC Readout
- Full-sample correlation IC: `0.017695`
- Average daily IC: `0.027200`
- Median daily IC: `0.022861`
- Positive daily IC share: `0.56283`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.005663`
- Decile 2: `0.004897`
- Decile 3: `0.004548`
- Decile 4: `0.004228`
- Decile 5: `0.004085`
- Decile 6: `0.003825`
- Decile 7: `0.003718`
- Decile 8: `0.003262`
- Decile 9: `0.002523`
- Decile 10: `0.000750`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.005284`
- Average label, rank 11-20: `0.007427`
- Average label, bottom 10: `-0.000104`
- `top10 - rank11_20 = -0.002143`
- `top10 - bottom10 = 0.005388`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000535`
- Median score gap `rank10 - rank11`: `0.000446`
- Days with both ranks present: `6302`
- Days with `|gap| < 0.005`: `6302`
- Days with `|gap| < 0.001`: `6041`

