# Reversal + Cord30 Deployment-Loss Diagnosis

- generated_at: 2026-05-06T12:03:04+08:00

## High-level deltas (composite - p98 baseline)

- validation annual relative return delta = -0.020932
- validation relative IR delta = -0.100452
- validation max drawdown delta = 0.020746
- validation avg turnover delta = -0.013927
- validation avg invested weight delta = -0.028826
- cost_stress annual relative return delta = 0.015021
- low_liquidity weight share delta = 0.013048

## Attribution decomposition

- selection_alpha_total delta = 0.166715
- cash_drag_total delta = -0.049003
- low_liquidity_contribution_total delta = 0.082262

## Top10 overlap

- avg overlap count = 1.301 / 10
- avg overlap share = 0.130
- min overlap count = 0
- max overlap count = 7

## Unique-name liquidity profile

- composite-only avg liquidity_rank = 0.558125
- composite-only median liquidity_rank = 0.583987
- baseline-only avg liquidity_rank = 0.629901
- baseline-only median liquidity_rank = 0.682510

## Top10 deployment profile

- baseline fill rate = 0.980834
- composite fill rate = 0.980665
- baseline Top10 avg liquidity_rank = 0.622879
- composite Top10 avg liquidity_rank = 0.560441
- baseline avg filled names/day = 9.808343
- composite avg filled names/day = 9.806652

## Verdict

- Composite improves gross selection alpha, drawdown, turnover, and cost stress, but loses validation annual relative return because it deploys less capital and takes on more low-liquidity exposure than the standalone p98 baseline.
