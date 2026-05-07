# price_volume_single_signal_amount_entropy_20d_v1 (20260428)

Candidate: `price_volume_single_signal_amount_entropy_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round8_orthogonal_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `-0.019016`
- Average daily IC: `-0.030858`
- Median daily IC: `-0.030352`
- Positive daily IC share: `0.32463`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.000628`
- Decile 2: `0.002574`
- Decile 3: `0.003100`
- Decile 4: `0.003563`
- Decile 5: `0.003956`
- Decile 6: `0.004292`
- Decile 7: `0.004492`
- Decile 8: `0.005004`
- Decile 9: `0.005079`
- Decile 10: `0.005448`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `-0.005702`
- Average label, rank 11-20: `-0.003185`
- Average label, bottom 10: `0.005732`
- `top10 - rank11_20 = -0.002517`
- `top10 - bottom10 = -0.011434`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

