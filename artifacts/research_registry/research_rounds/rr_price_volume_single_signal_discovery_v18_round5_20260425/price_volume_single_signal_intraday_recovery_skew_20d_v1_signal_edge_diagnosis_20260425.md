# price_volume_single_signal_intraday_recovery_skew_20d_v1 (20260425)

Candidate: `price_volume_single_signal_intraday_recovery_skew_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round5_20260425`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.005507`
- Average daily IC: `0.007581`
- Median daily IC: `0.002328`
- Positive daily IC share: `0.50952`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003730`
- Decile 2: `0.004107`
- Decile 3: `0.004102`
- Decile 4: `0.004142`
- Decile 5: `0.004175`
- Decile 6: `0.004267`
- Decile 7: `0.004165`
- Decile 8: `0.003982`
- Decile 9: `0.003519`
- Decile 10: `0.001927`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.004645`
- Average label, rank 11-20: `0.004063`
- Average label, bottom 10: `-0.000056`
- `top10 - rank11_20 = 0.000582`
- `top10 - bottom10 = 0.004701`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

