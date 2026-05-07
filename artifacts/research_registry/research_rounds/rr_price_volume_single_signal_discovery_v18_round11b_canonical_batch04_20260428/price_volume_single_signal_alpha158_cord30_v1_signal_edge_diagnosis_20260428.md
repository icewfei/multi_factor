# price_volume_single_signal_alpha158_cord30_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_cord30_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch04_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 1816`
- `null_score_share = 0.00012`
- `scored_with_label_rows = 15020216`

## 2. IC Readout
- Full-sample correlation IC: `0.016812`
- Average daily IC: `0.031407`
- Median daily IC: `0.027896`
- Positive daily IC share: `0.64017`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.005218`
- Decile 2: `0.004985`
- Decile 3: `0.004777`
- Decile 4: `0.004503`
- Decile 5: `0.004211`
- Decile 6: `0.003980`
- Decile 7: `0.003622`
- Decile 8: `0.003148`
- Decile 9: `0.002547`
- Decile 10: `0.001070`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.006834`
- Average label, rank 11-20: `0.006026`
- Average label, bottom 10: `-0.002200`
- `top10 - rank11_20 = 0.000807`
- `top10 - bottom10 = 0.009034`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6360`
- Days with `|gap| < 0.005`: `6360`
- Days with `|gap| < 0.001`: `6075`

