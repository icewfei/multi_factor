# price_volume_single_signal_up_amount_persistence_20d_v1 (20260425)

Candidate: `price_volume_single_signal_up_amount_persistence_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round5_20260425`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.009374`
- Average daily IC: `0.013587`
- Median daily IC: `0.012385`
- Positive daily IC share: `0.54917`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004708`
- Decile 2: `0.004198`
- Decile 3: `0.004277`
- Decile 4: `0.003995`
- Decile 5: `0.004179`
- Decile 6: `0.004005`
- Decile 7: `0.003878`
- Decile 8: `0.003853`
- Decile 9: `0.003413`
- Decile 10: `0.001609`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.006377`
- Average label, rank 11-20: `0.005613`
- Average label, bottom 10: `-0.000546`
- `top10 - rank11_20 = 0.000764`
- `top10 - bottom10 = 0.006922`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

