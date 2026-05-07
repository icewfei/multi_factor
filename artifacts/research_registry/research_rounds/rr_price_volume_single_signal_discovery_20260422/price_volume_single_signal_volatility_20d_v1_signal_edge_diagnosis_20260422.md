# Volatility 20D Single-Signal Edge Diagnosis (20260422)

Candidate: `price_volume_single_signal_volatility_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_20260422`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 907`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021120`

## 2. IC Readout
- Full-sample correlation IC: `-0.005088`
- Average daily IC: `-0.005787`
- Median daily IC: `-0.007777`
- Positive daily IC share: `0.48111`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.001856`
- Decile 2: `0.003195`
- Decile 3: `0.003874`
- Decile 4: `0.004216`
- Decile 5: `0.004510`
- Decile 6: `0.004503`
- Decile 7: `0.004529`
- Decile 8: `0.004429`
- Decile 9: `0.003957`
- Decile 10: `0.003025`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.002486`
- Average label, rank 11-20: `0.001059`
- Average label, bottom 10: `0.002884`
- `top10 - rank11_20 = 0.001427`
- `top10 - bottom10 = -0.000398`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

