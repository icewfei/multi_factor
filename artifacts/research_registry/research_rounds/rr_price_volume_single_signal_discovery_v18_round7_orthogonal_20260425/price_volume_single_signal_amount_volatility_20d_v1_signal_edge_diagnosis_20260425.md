# price_volume_single_signal_amount_volatility_20d_v1 (20260425)

Candidate: `price_volume_single_signal_amount_volatility_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round7_orthogonal_20260425`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 907`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021120`

## 2. IC Readout
- Full-sample correlation IC: `-0.017632`
- Average daily IC: `-0.028194`
- Median daily IC: `-0.028166`
- Positive daily IC share: `0.34419`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.000738`
- Decile 2: `0.002625`
- Decile 3: `0.003382`
- Decile 4: `0.003613`
- Decile 5: `0.003903`
- Decile 6: `0.004205`
- Decile 7: `0.004503`
- Decile 8: `0.004795`
- Decile 9: `0.004950`
- Decile 10: `0.005388`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `-0.004945`
- Average label, rank 11-20: `-0.001260`
- Average label, bottom 10: `0.005832`
- `top10 - rank11_20 = -0.003686`
- `top10 - bottom10 = -0.010777`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

