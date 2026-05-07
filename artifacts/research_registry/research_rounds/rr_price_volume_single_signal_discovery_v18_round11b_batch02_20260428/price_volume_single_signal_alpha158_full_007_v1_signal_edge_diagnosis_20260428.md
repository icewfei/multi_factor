# price_volume_single_signal_alpha158_full_007_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_full_007_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_batch02_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.003173`
- Average daily IC: `0.009256`
- Median daily IC: `0.008457`
- Positive daily IC share: `0.55924`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003738`
- Decile 2: `0.004104`
- Decile 3: `0.004122`
- Decile 4: `0.004018`
- Decile 5: `0.004071`
- Decile 6: `0.003789`
- Decile 7: `0.003812`
- Decile 8: `0.003843`
- Decile 9: `0.003671`
- Decile 10: `0.002952`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.003229`
- Average label, rank 11-20: `0.004080`
- Average label, bottom 10: `0.001725`
- `top10 - rank11_20 = -0.000850`
- `top10 - bottom10 = 0.001505`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

