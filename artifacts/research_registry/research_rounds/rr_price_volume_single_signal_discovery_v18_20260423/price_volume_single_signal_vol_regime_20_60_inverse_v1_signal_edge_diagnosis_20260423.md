# price_volume_single_signal_vol_regime_20_60_inverse_v1 Signal Edge Diagnosis (20260423)

Candidate: `price_volume_single_signal_vol_regime_20_60_inverse_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_20260423`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 908`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021119`

## 2. IC Readout
- Full-sample correlation IC: `0.004308`
- Average daily IC: `0.003899`
- Median daily IC: `0.005561`
- Positive daily IC share: `0.52675`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003725`
- Decile 2: `0.003823`
- Decile 3: `0.003856`
- Decile 4: `0.004178`
- Decile 5: `0.004352`
- Decile 6: `0.004294`
- Decile 7: `0.004194`
- Decile 8: `0.004087`
- Decile 9: `0.003599`
- Decile 10: `0.001978`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.002926`
- Average label, rank 11-20: `0.003296`
- Average label, bottom 10: `0.001218`
- `top10 - rank11_20 = -0.000371`
- `top10 - bottom10 = 0.001707`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

