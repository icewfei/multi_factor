# price_volume_single_signal_path_efficiency_60d_v1 (20260425)

Candidate: `price_volume_single_signal_path_efficiency_60d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round6_alpha158_paper_20260425`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 135887`
- `null_score_share = 0.00892`
- `scored_with_label_rows = 14888004`

## 2. IC Readout
- Full-sample correlation IC: `-0.001670`
- Average daily IC: `-0.008432`
- Median daily IC: `-0.003644`
- Positive daily IC share: `0.48038`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003594`
- Decile 2: `0.003503`
- Decile 3: `0.003497`
- Decile 4: `0.003740`
- Decile 5: `0.003733`
- Decile 6: `0.003901`
- Decile 7: `0.003962`
- Decile 8: `0.004028`
- Decile 9: `0.004101`
- Decile 10: `0.003457`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.003042`
- Average label, rank 11-20: `0.003852`
- Average label, bottom 10: `0.001224`
- `top10 - rank11_20 = -0.000811`
- `top10 - bottom10 = 0.001818`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000535`
- Median score gap `rank10 - rank11`: `0.000446`
- Days with both ranks present: `6302`
- Days with `|gap| < 0.005`: `6302`
- Days with `|gap| < 0.001`: `6041`

