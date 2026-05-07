# Dual-Probe Design: Tradeable-Constrained vs Execution-Override Oracle

**Status:** Design only, not registered. Framework-level diagnostic.

---

## 1. Background

Single oracle probe (v1) found: perfect future 5d return ranking + standard execution = total loss (-1.0). Root cause: oracle-selected stocks (highest future returns) are systematically the ones that hit limit-up on D1 → cannot be bought. The strategy fills only the "leftover" positions that are easy to buy but have poor returns.

This finding is more fundamental than the cost_stress question: **even with perfect information, the gap between ranking and tradable portfolio is large enough to destroy all alpha.**

---

## 2. Two Probes

### Probe A: Tradeable-Constrained Oracle

**Purpose:** Answer "under realistic execution constraints (limit-up, suspension), what is the maximum achievable gross alpha?"

**Method:**
```
Signal: label_5d_next_open_close (future 5d return)
Ranking universe: ONLY stocks that pass ranking_eligible_D0 AND entry_tradeable_D1
Execution: standard (same as all previous rounds)
Contract: 10-cohort full refresh
```

Key difference from v1 oracle: the ranking is restricted to stocks that CAN actually be bought on D1. This avoids the "pick winners → they're all limit-up → can't buy" problem.

### Probe B: Execution-Override Oracle

**Purpose:** Answer "if trading were costless and execution were frictionless, can cost_stress ≥ 0 be achieved?"

**Method:**
```
Signal: label_5d_next_open_close (future 5d return)
Ranking universe: all ranking_eligible_D0 (ignore entry_tradeable)
Execution override: force entry_filled_D1 = true for ALL topk_frozen_D0 positions
  (overrides the tradability check — diagnostic only, not realistic)
Contract: 10-cohort full refresh
```

**Constraint:** This requires modifying `build_run_state_skeleton.py` or the execution panel to bypass the tradability check. This is acceptable ONLY because it's a diagnostic probe, not a real strategy.

---

## 3. Result Interpretation Rules

```
                    ┌─────────────────────────────────────────────┐
                    │  Probe B (Override) cost_stress             │
                    │  ≥ 0?                                       │
                    ├──────────┬──────────────────────────────────┤
                    │   YES    │  Framework cost model is OK.     │
                    │          │  Main bottleneck is execution    │
                    │          │  feasibility gap (limit-up etc). │
    Probe A         │          │                                  │
    (Constrained)   ├──────────┼──────────────────────────────────┤
    cost_stress     │   NO     │  BOTH problems exist:            │
    ≥ 0?            │          │  1. Cost model or threshold      │
                    │          │     may be structurally too high │
                    │          │  2. Execution feasibility gap    │
                    │          │     amplifies the problem        │
                    └──────────┴──────────────────────────────────┘
```

| Probe A | Probe B | Interpretation |
|---|---|---|
| FAIL | PASS | Main bottleneck is execution feasibility gap. Cost model is OK. Next: fix entry limit-up handling or widen TopK to account for unfillable slots. |
| FAIL | FAIL | Both execution feasibility AND cost model are structural constraints. Framework needs changes at both levels. |
| PASS | PASS | Framework is OK. Main bottleneck is signal quality. Return to signal research. |
| PASS | FAIL | (Unlikely — override should always be ≥ constrained) |

### Additional diagnostics

| Metric | Probe A tells us | Probe B tells us |
|---|---|---|
| annual_relative_return | Realistic max alpha under execution constraints | Theoretical max alpha without execution friction |
| cost_stress | Whether cost model is feasible under real execution | Whether cost model is feasible in principle |
| topk_perturbation | Whether rank stability is achievable | Whether rank stability is an execution or a signal problem |
| invested_weight | How much capital can be deployed under real constraints | Theoretical max invested weight |

---

## 4. Implementation Requirements

### Probe A: Run as standard pipeline
- Same as v1 oracle but with `ranking_eligible_D0 AND entry_tradeable` in the score
- **New column needed:** add `entry_tradeable_D1` to the oracle parquet by joining with the sample panel's `entry_tradeable` field

### Probe B: Requires execution panel override
- Need to modify one of:
  - `build_run_state_skeleton.py`: force `entry_filled_D1 = true` for all TopK selections
  - **OR** override the `project_execution_panel.parquet` entry_tradeable fields to always be true
- This changes execution semantics — acceptable ONLY as diagnostic

---

## 5. Prereg (draft, not to register as normal round)

```yaml
round_id: diag_dual_oracle_probe_20260501
research_tier: framework_diagnostic
not_a_research_candidate: true

probes:
  - probe_id: diag_oracle_tradeable_constrained
    signal: label_5d_next_open_close
    universe: ranking_eligible_D0 AND entry_tradeable
    execution: standard
    contract: 10-cohort full refresh

  - probe_id: diag_oracle_execution_override
    signal: label_5d_next_open_close
    universe: all ranking_eligible_D0
    execution: override — force entry_filled_D1 = true
    contract: 10-cohort full refresh

purpose: >
  Separate the two constraints: (1) execution feasibility gap
  (can't buy winners) vs (2) cost model structural feasibility.
  Not a research candidate; not a tradable strategy.
```

---

## 6. Resource Estimate

| Probe | New code needed | Run time |
|---|---|---|
| A: Tradeable-constrained | Minor — add entry_tradeable to oracle score query | ~30 min |
| B: Execution-override | Modify run_state (force fill) | ~30 min |
| **Total** | **~1 file modification** | **~1 hour** |
