# price_volume_single_signal_upper_shadow_pressure_20d_v1 (20260425)

Candidate: `price_volume_single_signal_upper_shadow_pressure_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round6_alpha158_paper_20260425`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.002355`
- Average daily IC: `0.000354`
- Median daily IC: `0.000719`
- Positive daily IC share: `0.50543`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003704`
- Decile 2: `0.003949`
- Decile 3: `0.003943`
- Decile 4: `0.003995`
- Decile 5: `0.004022`
- Decile 6: `0.004060`
- Decile 7: `0.003951`
- Decile 8: `0.003847`
- Decile 9: `0.003752`
- Decile 10: `0.002896`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.003126`
- Average label, rank 11-20: `0.003463`
- Average label, bottom 10: `0.000607`
- `top10 - rank11_20 = -0.000337`
- `top10 - bottom10 = 0.002519`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

