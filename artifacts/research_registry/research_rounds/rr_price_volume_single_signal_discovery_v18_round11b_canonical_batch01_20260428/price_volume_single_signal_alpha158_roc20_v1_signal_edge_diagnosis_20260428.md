# price_volume_single_signal_alpha158_roc20_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_roc20_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch01_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 18239`
- `null_score_share = 0.00120`
- `scored_with_label_rows = 15003964`

## 2. IC Readout
- Full-sample correlation IC: `0.017578`
- Average daily IC: `0.028606`
- Median daily IC: `0.021723`
- Positive daily IC share: `0.56433`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004978`
- Decile 2: `0.004557`
- Decile 3: `0.004619`
- Decile 4: `0.004593`
- Decile 5: `0.004525`
- Decile 6: `0.004369`
- Decile 7: `0.004123`
- Decile 8: `0.003672`
- Decile 9: `0.002539`
- Decile 10: `-0.000249`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.003212`
- Average label, rank 11-20: `0.006610`
- Average label, bottom 10: `-0.002036`
- `top10 - rank11_20 = -0.003398`
- `top10 - bottom10 = 0.005248`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000535`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6342`
- Days with `|gap| < 0.005`: `6342`
- Days with `|gap| < 0.001`: `6075`

