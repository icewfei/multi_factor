# Round Note: Exploratory Intraday Microstructure Independent Baseline

## Round Context

This round was opened after the Alpha158 confirmatory fine-tuning line was formally paused (see `alpha158_cord30_turnover_control_seed_closeout_and_pause_decision_20260430.md`). The previous exploratory rounds (v15-v23, rounds 2-11b) all attempted to add individual price-volume signals on top of the v18 two-signal working reference (momentum_60_5 + liquidity_trend_20_60), and all composability screens returned `mixed` verdicts.

## Key Design Decisions

### 1. Not "add to v18" but "independent baseline"

All composability screens (rounds 4-8, 11b) tested "add signal X to v18's momentum + liquidity_trend" and all returned `composability_screen_mixed` — 0 clean passes out of 7+ attempts. This round pivots to: build a completely independent baseline from intraday microstructure signals, without any momentum or liquidity-trend component.

### 2. Intraday frequency as differentiation

The three selected mechanism families (intraday_bias, intraday_structure, intraday_resilience) operate at a fundamentally different frequency (intraday) than the daily-level statistics used by the paused Alpha158 fine-tuning line (corr, cord, vsumd — all daily-level price-volume aggregates).

### 3. Exploratory tier, not confirmatory

This round is exploratory family-construction (same tier as v15/v16/v21 et al.) because there is no existing winner to confirm. If successful, the round produces one or more `reasonable_candidate`s for future confirmatory scrutiny.

### 4. Parallel candidates, not cascading

Unlike the abandoned `rr_confirmatory_pv_microstructure_baseline_20260501` (which used cascading design), this round uses parallel candidates. Each candidate independently tests a different composition of intraday signals, and verdicts are independent.

## Success Rule Rationale

| Rule | Value | Rationale |
|---|---|---|
| `avg_invested_weight >= 0.15` | 0.15 | v18 actual = 0.1554. Prevents extreme 轻仓 without being impossible. |
| `max_drawdown_delta_vs_v18 >= -0.05` | -0.05 | Candidate drawdown no more than 5pp worse than v18's -0.3988. Direction verified: positive delta = better. |
| `avg_turnover_daily_delta_vs_v18 <= 0.04` | 0.04 | v18 actual = 0.0757. Wider than strict-recheck 0.02, appropriate for exploratory tier. |
| `annual_relative_return_delta_vs_v18 >= -0.005` | -0.005 | Candidate return no worse than 0.5pp below v18's -0.2748. |
| `pass_topk_perturbation` | 0.00 | Standard project gate. |
| `pass_cost_stress` | 0.00 | Standard project gate. |

## Supersedes

This round supersedes `rr_confirmatory_pv_microstructure_baseline_20260501`, which was abandoned due to reference mismatch (v18 was incorrectly assumed to be 5-signal rather than 2-signal, and the three proposed candidates had already been tested in exploratory rounds 5/7/11b against v18).
