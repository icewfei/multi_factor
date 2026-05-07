# price_volume_single_signal_alpha158_max60_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_max60_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch02_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.014105`
- Average daily IC: `0.025580`
- Median daily IC: `0.016193`
- Positive daily IC share: `0.54367`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.006099`
- Decile 2: `0.004747`
- Decile 3: `0.004208`
- Decile 4: `0.003785`
- Decile 5: `0.003628`
- Decile 6: `0.003520`
- Decile 7: `0.003490`
- Decile 8: `0.003514`
- Decile 9: `0.003424`
- Decile 10: `0.001696`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.005463`
- Average label, rank 11-20: `0.008156`
- Average label, bottom 10: `-0.003696`
- `top10 - rank11_20 = -0.002693`
- `top10 - bottom10 = 0.009159`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

