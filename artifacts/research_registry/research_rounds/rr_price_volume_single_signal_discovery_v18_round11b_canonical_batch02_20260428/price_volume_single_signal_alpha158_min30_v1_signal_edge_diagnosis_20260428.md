# price_volume_single_signal_alpha158_min30_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_min30_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch02_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.004651`
- Average daily IC: `0.009259`
- Median daily IC: `0.008121`
- Positive daily IC share: `0.52604`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.001798`
- Decile 2: `0.003661`
- Decile 3: `0.004524`
- Decile 4: `0.004984`
- Decile 5: `0.005241`
- Decile 6: `0.005131`
- Decile 7: `0.004860`
- Decile 8: `0.004381`
- Decile 9: `0.003185`
- Decile 10: `0.000354`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `-0.003497`
- Average label, rank 11-20: `0.000266`
- Average label, bottom 10: `-0.000443`
- `top10 - rank11_20 = -0.003762`
- `top10 - bottom10 = -0.003054`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

