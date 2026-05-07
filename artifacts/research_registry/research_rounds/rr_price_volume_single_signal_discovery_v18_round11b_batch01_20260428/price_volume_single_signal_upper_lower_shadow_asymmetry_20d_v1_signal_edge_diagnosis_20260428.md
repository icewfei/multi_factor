# price_volume_single_signal_upper_lower_shadow_asymmetry_20d_v1 (20260428)

Candidate: `price_volume_single_signal_upper_lower_shadow_asymmetry_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_batch01_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 769`
- `null_score_share = 0.00005`
- `scored_with_label_rows = 15021902`

## 2. IC Readout
- Full-sample correlation IC: `0.005203`
- Average daily IC: `0.006725`
- Median daily IC: `0.005196`
- Positive daily IC share: `0.53360`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004092`
- Decile 2: `0.004160`
- Decile 3: `0.004228`
- Decile 4: `0.004007`
- Decile 5: `0.003978`
- Decile 6: `0.003925`
- Decile 7: `0.003822`
- Decile 8: `0.003729`
- Decile 9: `0.003540`
- Decile 10: `0.002639`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.004636`
- Average label, rank 11-20: `0.004962`
- Average label, bottom 10: `0.000699`
- `top10 - rank11_20 = -0.000326`
- `top10 - bottom10 = 0.003937`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6071`

