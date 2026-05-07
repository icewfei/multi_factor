# price_volume_single_signal_intraday_path_curvature_20d_v1 (20260428)

Candidate: `price_volume_single_signal_intraday_path_curvature_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_batch01_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `-0.005445`
- Average daily IC: `-0.009257`
- Median daily IC: `-0.009502`
- Positive daily IC share: `0.47191`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.001918`
- Decile 2: `0.003319`
- Decile 3: `0.003897`
- Decile 4: `0.004116`
- Decile 5: `0.004252`
- Decile 6: `0.004420`
- Decile 7: `0.004429`
- Decile 8: `0.004310`
- Decile 9: `0.004088`
- Decile 10: `0.003377`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.000129`
- Average label, rank 11-20: `0.001064`
- Average label, bottom 10: `0.003155`
- `top10 - rank11_20 = -0.000935`
- `top10 - bottom10 = -0.003026`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

