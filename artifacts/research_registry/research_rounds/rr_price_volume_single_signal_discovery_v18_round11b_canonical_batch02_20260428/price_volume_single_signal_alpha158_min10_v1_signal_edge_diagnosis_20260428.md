# price_volume_single_signal_alpha158_min10_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_min10_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch02_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.008685`
- Average daily IC: `0.016847`
- Median daily IC: `0.015372`
- Positive daily IC share: `0.55374`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.002611`
- Decile 2: `0.003926`
- Decile 3: `0.004565`
- Decile 4: `0.004918`
- Decile 5: `0.005130`
- Decile 6: `0.005052`
- Decile 7: `0.004780`
- Decile 8: `0.004189`
- Decile 9: `0.003000`
- Decile 10: `-0.000055`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `-0.001662`
- Average label, rank 11-20: `0.001896`
- Average label, bottom 10: `-0.000947`
- `top10 - rank11_20 = -0.003558`
- `top10 - bottom10 = -0.000715`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

