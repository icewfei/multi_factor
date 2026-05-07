# price_volume_single_signal_downside_gap_fill_ratio_20d_v1 (20260428)

Candidate: `price_volume_single_signal_downside_gap_fill_ratio_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round8_orthogonal_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 6670`
- `null_score_share = 0.00044`
- `scored_with_label_rows = 15015428`

## 2. IC Readout
- Full-sample correlation IC: `0.005232`
- Average daily IC: `0.006654`
- Median daily IC: `0.004457`
- Positive daily IC share: `0.53462`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003959`
- Decile 2: `0.004105`
- Decile 3: `0.004169`
- Decile 4: `0.004056`
- Decile 5: `0.004158`
- Decile 6: `0.004092`
- Decile 7: `0.003983`
- Decile 8: `0.003625`
- Decile 9: `0.003128`
- Decile 10: `0.002825`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.003200`
- Average label, rank 11-20: `0.003966`
- Average label, bottom 10: `0.002355`
- `top10 - rank11_20 = -0.000766`
- `top10 - bottom10 = 0.000845`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6067`

