# Reversal 5D Single-Signal Edge Diagnosis (20260422)

Candidate: `price_volume_single_signal_reversal_5d_v1`
Research round: `rr_price_volume_single_signal_discovery_20260422`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 4538`
- `null_score_share = 0.00030`
- `scored_with_label_rows = 15017521`

## 2. IC Readout
- Full-sample correlation IC: `-0.021762`
- Average daily IC: `-0.041578`
- Median daily IC: `-0.039576`
- Positive daily IC share: `0.37197`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `-0.001167`
- Decile 2: `0.002253`
- Decile 3: `0.003565`
- Decile 4: `0.004193`
- Decile 5: `0.004599`
- Decile 6: `0.004786`
- Decile 7: `0.004992`
- Decile 8: `0.005050`
- Decile 9: `0.005165`
- Decile 10: `0.004765`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `-0.000981`
- Average label, rank 11-20: `-0.004952`
- Average label, bottom 10: `-0.001407`
- `top10 - rank11_20 = 0.003970`
- `top10 - bottom10 = 0.000425`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6357`
- Days with `|gap| < 0.005`: `6357`
- Days with `|gap| < 0.001`: `6075`

