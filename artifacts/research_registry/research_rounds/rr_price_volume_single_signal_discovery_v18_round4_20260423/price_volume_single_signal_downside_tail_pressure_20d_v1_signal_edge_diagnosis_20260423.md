# price_volume_single_signal_downside_tail_pressure_20d_v1 (20260423)

Candidate: `price_volume_single_signal_downside_tail_pressure_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round4_20260423`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.005615`
- Average daily IC: `0.010972`
- Median daily IC: `0.006285`
- Positive daily IC share: `0.51865`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003796`
- Decile 2: `0.004187`
- Decile 3: `0.004229`
- Decile 4: `0.004356`
- Decile 5: `0.004184`
- Decile 6: `0.004067`
- Decile 7: `0.003850`
- Decile 8: `0.003623`
- Decile 9: `0.003197`
- Decile 10: `0.002628`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.001900`
- Average label, rank 11-20: `0.003842`
- Average label, bottom 10: `0.003974`
- `top10 - rank11_20 = -0.001942`
- `top10 - bottom10 = -0.002074`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

