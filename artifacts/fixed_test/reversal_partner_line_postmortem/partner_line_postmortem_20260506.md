# Reversal Partner-Line Postmortem

- generated_at: 2026-05-06T12:33:49+08:00
- baseline_run_id: `confirmatory_reversal_p98_trainval_20260506`

## cord30_ew

- validation annual relative return delta = -0.020932
- validation relative IR delta = -0.100452
- validation max drawdown delta = 0.020746
- validation avg turnover delta = -0.013927
- validation avg invested weight delta = -0.028826
- cost_stress annual relative return delta = 0.015021
- low_liquidity weight share delta = 0.013048
- TopK8 annual relative return delta = 0.003449
- TopK12 annual relative return delta = 0.010007
- selection_alpha_total delta = 0.166715
- cash_drag_total delta = -0.049003
- low_liquidity_contribution_total delta = 0.082262
- avg Top10 overlap = 1.301 / 10
- challenger-only avg liquidity_rank = 0.558125

## corr30_ew

- validation annual relative return delta = -0.007501
- validation relative IR delta = 0.056592
- validation max drawdown delta = 0.030686
- validation avg turnover delta = -0.034085
- validation avg invested weight delta = -0.068887
- cost_stress annual relative return delta = 0.007369
- low_liquidity weight share delta = -0.002589
- TopK8 annual relative return delta = -0.007431
- TopK12 annual relative return delta = -0.007459
- selection_alpha_total delta = -0.091732
- cash_drag_total delta = -0.106459
- low_liquidity_contribution_total delta = 0.070285
- avg Top10 overlap = 1.547 / 10
- challenger-only avg liquidity_rank = 0.592976

## Common Failure Flags

- all_fail_validation_annual_relative_return = true
- all_fail_topk8 = false
- all_fail_topk12 = false
- all_improve_drawdown = true
- all_improve_turnover = true
- all_improve_cost_stress = true

## Verdict

- Composite partner line remains ambiguous; at least one challenger broke the common-failure pattern and may justify another targeted follow-up.
