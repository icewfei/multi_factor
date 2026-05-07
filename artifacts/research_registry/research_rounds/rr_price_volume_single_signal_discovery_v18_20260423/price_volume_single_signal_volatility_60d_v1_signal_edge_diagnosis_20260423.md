# price_volume_single_signal_volatility_60d_v1 Signal Edge Diagnosis (20260423)

Candidate: `price_volume_single_signal_volatility_60d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_20260423`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 907`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021120`

## 2. IC Readout
- Full-sample correlation IC: `-0.004017`
- Average daily IC: `-0.004902`
- Median daily IC: `-0.005060`
- Positive daily IC share: `0.48678`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.002462`
- Decile 2: `0.003418`
- Decile 3: `0.003839`
- Decile 4: `0.003881`
- Decile 5: `0.004183`
- Decile 6: `0.004339`
- Decile 7: `0.004333`
- Decile 8: `0.004231`
- Decile 9: `0.004047`
- Decile 10: `0.003358`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.002522`
- Average label, rank 11-20: `0.002898`
- Average label, bottom 10: `0.002896`
- `top10 - rank11_20 = -0.000376`
- `top10 - bottom10 = -0.000375`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

