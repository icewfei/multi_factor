# price_volume_single_signal_alpha158_qtlu60_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_qtlu60_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch02_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.021528`
- Average daily IC: `0.035618`
- Median daily IC: `0.028412`
- Positive daily IC share: `0.58206`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.006199`
- Decile 2: `0.005236`
- Decile 3: `0.004653`
- Decile 4: `0.004398`
- Decile 5: `0.004144`
- Decile 6: `0.003884`
- Decile 7: `0.003652`
- Decile 8: `0.003236`
- Decile 9: `0.002586`
- Decile 10: `0.000116`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.005407`
- Average label, rank 11-20: `0.008080`
- Average label, bottom 10: `-0.002456`
- `top10 - rank11_20 = -0.002673`
- `top10 - bottom10 = 0.007863`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

