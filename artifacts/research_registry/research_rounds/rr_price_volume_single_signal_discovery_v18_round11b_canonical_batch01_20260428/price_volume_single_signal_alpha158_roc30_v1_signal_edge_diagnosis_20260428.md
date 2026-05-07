# price_volume_single_signal_alpha158_roc30_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_roc30_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch01_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 27511`
- `null_score_share = 0.00181`
- `scored_with_label_rows = 14994825`

## 2. IC Readout
- Full-sample correlation IC: `0.020702`
- Average daily IC: `0.033435`
- Median daily IC: `0.029298`
- Positive daily IC share: `0.58498`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.005662`
- Decile 2: `0.005013`
- Decile 3: `0.004742`
- Decile 4: `0.004519`
- Decile 5: `0.004332`
- Decile 6: `0.004126`
- Decile 7: `0.003746`
- Decile 8: `0.003154`
- Decile 9: `0.002464`
- Decile 10: `-0.000093`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.004815`
- Average label, rank 11-20: `0.007374`
- Average label, bottom 10: `-0.001752`
- `top10 - rank11_20 = -0.002559`
- `top10 - bottom10 = 0.006567`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000534`
- Median score gap `rank10 - rank11`: `0.000444`
- Days with both ranks present: `6332`
- Days with `|gap| < 0.005`: `6332`
- Days with `|gap| < 0.001`: `6075`

