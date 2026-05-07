# price_volume_single_signal_amihud_illiquidity_20d_v1 (20260428)

Candidate: `price_volume_single_signal_amihud_illiquidity_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round10_alpha158_paper_whitelist_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.024665`
- Average daily IC: `0.036689`
- Median daily IC: `0.044015`
- Positive daily IC share: `0.64406`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.006606`
- Decile 2: `0.006058`
- Decile 3: `0.005268`
- Decile 4: `0.004589`
- Decile 5: `0.003938`
- Decile 6: `0.003350`
- Decile 7: `0.002829`
- Decile 8: `0.002249`
- Decile 9: `0.001855`
- Decile 10: `0.001359`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.006116`
- Average label, rank 11-20: `0.007397`
- Average label, bottom 10: `0.001696`
- `top10 - rank11_20 = -0.001281`
- `top10 - bottom10 = 0.004421`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

