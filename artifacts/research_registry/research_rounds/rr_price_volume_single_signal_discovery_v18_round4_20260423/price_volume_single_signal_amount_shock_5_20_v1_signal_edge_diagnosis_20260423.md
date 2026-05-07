# price_volume_single_signal_amount_shock_5_20_v1 (20260423)

Candidate: `price_volume_single_signal_amount_shock_5_20_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round4_20260423`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.007194`
- Average daily IC: `0.011316`
- Median daily IC: `0.012519`
- Positive daily IC share: `0.55783`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003048`
- Decile 2: `0.003911`
- Decile 3: `0.004331`
- Decile 4: `0.004620`
- Decile 5: `0.004767`
- Decile 6: `0.004760`
- Decile 7: `0.004578`
- Decile 8: `0.004252`
- Decile 9: `0.003504`
- Decile 10: `0.000345`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.003593`
- Average label, rank 11-20: `0.003129`
- Average label, bottom 10: `-0.005476`
- `top10 - rank11_20 = 0.000464`
- `top10 - bottom10 = 0.009069`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

