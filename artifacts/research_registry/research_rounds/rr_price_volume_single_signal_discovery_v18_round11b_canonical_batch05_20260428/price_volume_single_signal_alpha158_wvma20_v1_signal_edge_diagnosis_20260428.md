# price_volume_single_signal_alpha158_wvma20_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_wvma20_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch05_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 907`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021120`

## 2. IC Readout
- Full-sample correlation IC: `-0.012350`
- Average daily IC: `-0.020271`
- Median daily IC: `-0.019484`
- Positive daily IC share: `0.36072`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.001711`
- Decile 2: `0.002934`
- Decile 3: `0.003359`
- Decile 4: `0.003693`
- Decile 5: `0.003986`
- Decile 6: `0.004108`
- Decile 7: `0.004342`
- Decile 8: `0.004420`
- Decile 9: `0.004719`
- Decile 10: `0.004828`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `-0.001898`
- Average label, rank 11-20: `0.000520`
- Average label, bottom 10: `0.004678`
- `top10 - rank11_20 = -0.002418`
- `top10 - bottom10 = -0.006576`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

