# price_volume_single_signal_alpha158_qtld5_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_qtld5_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch02_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.019063`
- Average daily IC: `0.036983`
- Median daily IC: `0.036100`
- Positive daily IC share: `0.62612`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004408`
- Decile 2: `0.004852`
- Decile 3: `0.004856`
- Decile 4: `0.004930`
- Decile 5: `0.004933`
- Decile 6: `0.004674`
- Decile 7: `0.004351`
- Decile 8: `0.003653`
- Decile 9: `0.002370`
- Decile 10: `-0.000921`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `-0.001124`
- Average label, rank 11-20: `0.004465`
- Average label, bottom 10: `-0.000257`
- `top10 - rank11_20 = -0.005590`
- `top10 - bottom10 = -0.000868`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

