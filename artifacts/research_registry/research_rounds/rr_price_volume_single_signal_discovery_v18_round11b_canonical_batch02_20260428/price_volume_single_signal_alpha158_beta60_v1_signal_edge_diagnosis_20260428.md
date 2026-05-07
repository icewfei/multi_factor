# price_volume_single_signal_alpha158_beta60_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_beta60_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch02_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.012754`
- Average daily IC: `0.018743`
- Median daily IC: `0.014665`
- Positive daily IC share: `0.54131`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.005617`
- Decile 2: `0.004685`
- Decile 3: `0.004316`
- Decile 4: `0.004055`
- Decile 5: `0.003920`
- Decile 6: `0.003768`
- Decile 7: `0.003511`
- Decile 8: `0.003142`
- Decile 9: `0.002739`
- Decile 10: `0.002356`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.005506`
- Average label, rank 11-20: `0.007210`
- Average label, bottom 10: `0.003810`
- `top10 - rank11_20 = -0.001704`
- `top10 - bottom10 = 0.001697`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

