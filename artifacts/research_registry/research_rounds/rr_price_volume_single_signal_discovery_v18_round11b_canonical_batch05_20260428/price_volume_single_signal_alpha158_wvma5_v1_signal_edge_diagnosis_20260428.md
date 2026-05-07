# price_volume_single_signal_alpha158_wvma5_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_wvma5_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch05_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 907`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021120`

## 2. IC Readout
- Full-sample correlation IC: `-0.007836`
- Average daily IC: `-0.015262`
- Median daily IC: `-0.014361`
- Positive daily IC share: `0.38055`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.002207`
- Decile 2: `0.003176`
- Decile 3: `0.003618`
- Decile 4: `0.003893`
- Decile 5: `0.003983`
- Decile 6: `0.004157`
- Decile 7: `0.004282`
- Decile 8: `0.004264`
- Decile 9: `0.004257`
- Decile 10: `0.004258`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `-0.001060`
- Average label, rank 11-20: `0.000938`
- Average label, bottom 10: `0.004421`
- `top10 - rank11_20 = -0.001998`
- `top10 - bottom10 = -0.005481`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

