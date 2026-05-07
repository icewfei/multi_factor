# price_volume_single_signal_downside_gap_frequency_20d_v1 (20260425)

Candidate: `price_volume_single_signal_downside_gap_frequency_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round7_orthogonal_20260425`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `-0.002335`
- Average daily IC: `0.002236`
- Median daily IC: `0.001887`
- Positive daily IC share: `0.51094`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.002875`
- Decile 2: `0.003690`
- Decile 3: `0.003838`
- Decile 4: `0.003918`
- Decile 5: `0.004094`
- Decile 6: `0.004073`
- Decile 7: `0.004121`
- Decile 8: `0.004110`
- Decile 9: `0.003910`
- Decile 10: `0.003493`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.000704`
- Average label, rank 11-20: `0.003179`
- Average label, bottom 10: `0.002932`
- `top10 - rank11_20 = -0.002476`
- `top10 - bottom10 = -0.002228`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

