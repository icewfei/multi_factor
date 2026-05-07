# price_volume_single_signal_alpha158_rsv30_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_rsv30_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch03_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.007508`
- Average daily IC: `0.014805`
- Median daily IC: `0.012100`
- Positive daily IC share: `0.53989`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.002996`
- Decile 2: `0.004056`
- Decile 3: `0.004358`
- Decile 4: `0.004598`
- Decile 5: `0.004704`
- Decile 6: `0.004680`
- Decile 7: `0.004559`
- Decile 8: `0.004265`
- Decile 9: `0.003508`
- Decile 10: `0.000391`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `-0.001586`
- Average label, rank 11-20: `0.002153`
- Average label, bottom 10: `-0.006195`
- `top10 - rank11_20 = -0.003738`
- `top10 - bottom10 = 0.004609`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

