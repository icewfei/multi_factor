# price_volume_single_signal_alpha158_sump30_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_sump30_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch04_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 907`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021120`

## 2. IC Readout
- Full-sample correlation IC: `0.015072`
- Average daily IC: `0.025458`
- Median daily IC: `0.021943`
- Positive daily IC share: `0.57082`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004849`
- Decile 2: `0.004768`
- Decile 3: `0.004617`
- Decile 4: `0.004501`
- Decile 5: `0.004360`
- Decile 6: `0.004094`
- Decile 7: `0.003908`
- Decile 8: `0.003442`
- Decile 9: `0.002708`
- Decile 10: `0.000829`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.003402`
- Average label, rank 11-20: `0.005452`
- Average label, bottom 10: `0.000611`
- `top10 - rank11_20 = -0.002050`
- `top10 - bottom10 = 0.002791`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

