# price_volume_single_signal_alpha158_full_014_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_full_014_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_batch03_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 2721`
- `null_score_share = 0.00018`
- `scored_with_label_rows = 15019317`

## 2. IC Readout
- Full-sample correlation IC: `-0.003909`
- Average daily IC: `-0.007132`
- Median daily IC: `-0.008402`
- Positive daily IC share: `0.43530`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.002768`
- Decile 2: `0.003480`
- Decile 3: `0.003796`
- Decile 4: `0.004047`
- Decile 5: `0.003993`
- Decile 6: `0.003962`
- Decile 7: `0.004102`
- Decile 8: `0.004099`
- Decile 9: `0.004072`
- Decile 10: `0.003778`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.000435`
- Average label, rank 11-20: `0.001232`
- Average label, bottom 10: `0.003768`
- `top10 - rank11_20 = -0.000796`
- `top10 - bottom10 = -0.003332`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6359`
- Days with `|gap| < 0.005`: `6359`
- Days with `|gap| < 0.001`: `6075`

