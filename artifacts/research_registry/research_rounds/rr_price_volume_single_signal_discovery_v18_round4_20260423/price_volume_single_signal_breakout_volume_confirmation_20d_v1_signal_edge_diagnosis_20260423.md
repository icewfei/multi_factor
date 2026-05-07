# price_volume_single_signal_breakout_volume_confirmation_20d_v1 (20260423)

Candidate: `price_volume_single_signal_breakout_volume_confirmation_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round4_20260423`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 907`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021120`

## 2. IC Readout
- Full-sample correlation IC: `0.007258`
- Average daily IC: `0.011053`
- Median daily IC: `0.012117`
- Positive daily IC share: `0.55461`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.002844`
- Decile 2: `0.003909`
- Decile 3: `0.004352`
- Decile 4: `0.004687`
- Decile 5: `0.004872`
- Decile 6: `0.004840`
- Decile 7: `0.004684`
- Decile 8: `0.004310`
- Decile 9: `0.003513`
- Decile 10: `0.000072`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.004263`
- Average label, rank 11-20: `0.001971`
- Average label, bottom 10: `-0.006743`
- `top10 - rank11_20 = 0.002292`
- `top10 - bottom10 = 0.011006`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

