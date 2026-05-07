# price_volume_single_signal_alpha158_rsv5_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_rsv5_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch03_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.015575`
- Average daily IC: `0.030092`
- Median daily IC: `0.025944`
- Positive daily IC share: `0.60079`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003760`
- Decile 2: `0.004705`
- Decile 3: `0.004857`
- Decile 4: `0.004898`
- Decile 5: `0.004878`
- Decile 6: `0.004715`
- Decile 7: `0.004366`
- Decile 8: `0.003712`
- Decile 9: `0.002706`
- Decile 10: `-0.000487`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.000161`
- Average label, rank 11-20: `0.003210`
- Average label, bottom 10: `-0.005422`
- `top10 - rank11_20 = -0.003049`
- `top10 - bottom10 = 0.005583`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

