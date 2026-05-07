# price_volume_single_signal_alpha158_cord60_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_cord60_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch04_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 1816`
- `null_score_share = 0.00012`
- `scored_with_label_rows = 15020216`

## 2. IC Readout
- Full-sample correlation IC: `0.013683`
- Average daily IC: `0.026120`
- Median daily IC: `0.023950`
- Positive daily IC share: `0.62522`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004971`
- Decile 2: `0.004763`
- Decile 3: `0.004559`
- Decile 4: `0.004412`
- Decile 5: `0.004162`
- Decile 6: `0.003916`
- Decile 7: `0.003700`
- Decile 8: `0.003243`
- Decile 9: `0.002557`
- Decile 10: `0.001781`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.006040`
- Average label, rank 11-20: `0.005837`
- Average label, bottom 10: `-0.000395`
- `top10 - rank11_20 = 0.000203`
- `top10 - bottom10 = 0.006436`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6360`
- Days with `|gap| < 0.005`: `6360`
- Days with `|gap| < 0.001`: `6075`

