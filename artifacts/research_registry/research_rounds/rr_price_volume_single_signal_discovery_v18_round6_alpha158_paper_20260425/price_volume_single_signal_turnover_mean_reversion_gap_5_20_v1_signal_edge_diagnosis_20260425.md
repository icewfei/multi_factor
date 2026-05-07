# price_volume_single_signal_turnover_mean_reversion_gap_5_20_v1 (20260425)

Candidate: `price_volume_single_signal_turnover_mean_reversion_gap_5_20_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round6_alpha158_paper_20260425`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `-0.006322`
- Average daily IC: `-0.011098`
- Median daily IC: `-0.013940`
- Positive daily IC share: `0.43839`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.000355`
- Decile 2: `0.003626`
- Decile 3: `0.004492`
- Decile 4: `0.004701`
- Decile 5: `0.004741`
- Decile 6: `0.004671`
- Decile 7: `0.004417`
- Decile 8: `0.004144`
- Decile 9: `0.003792`
- Decile 10: `0.003188`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `-0.006493`
- Average label, rank 11-20: `-0.003635`
- Average label, bottom 10: `0.002852`
- `top10 - rank11_20 = -0.002858`
- `top10 - bottom10 = -0.009344`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

