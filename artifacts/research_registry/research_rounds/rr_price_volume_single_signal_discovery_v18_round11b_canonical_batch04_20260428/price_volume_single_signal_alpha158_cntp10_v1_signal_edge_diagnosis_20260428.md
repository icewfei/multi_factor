# price_volume_single_signal_alpha158_cntp10_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_cntp10_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch04_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.002914`
- Average daily IC: `0.005352`
- Median daily IC: `0.002855`
- Positive daily IC share: `0.51345`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003112`
- Decile 2: `0.003959`
- Decile 3: `0.004166`
- Decile 4: `0.004218`
- Decile 5: `0.004453`
- Decile 6: `0.004051`
- Decile 7: `0.004192`
- Decile 8: `0.004101`
- Decile 9: `0.003537`
- Decile 10: `0.002330`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.000390`
- Average label, rank 11-20: `0.002514`
- Average label, bottom 10: `0.001286`
- `top10 - rank11_20 = -0.002125`
- `top10 - bottom10 = -0.000896`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

