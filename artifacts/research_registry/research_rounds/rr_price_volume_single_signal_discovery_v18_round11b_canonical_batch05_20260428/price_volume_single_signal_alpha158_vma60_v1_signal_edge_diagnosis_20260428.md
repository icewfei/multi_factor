# price_volume_single_signal_alpha158_vma60_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_vma60_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch05_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.012987`
- Average daily IC: `0.022111`
- Median daily IC: `0.021413`
- Positive daily IC share: `0.59229`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004030`
- Decile 2: `0.004129`
- Decile 3: `0.004510`
- Decile 4: `0.004676`
- Decile 5: `0.004778`
- Decile 6: `0.004694`
- Decile 7: `0.004517`
- Decile 8: `0.004153`
- Decile 9: `0.003139`
- Decile 10: `-0.000514`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.006174`
- Average label, rank 11-20: `0.005141`
- Average label, bottom 10: `-0.007636`
- `top10 - rank11_20 = 0.001034`
- `top10 - bottom10 = 0.013810`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

