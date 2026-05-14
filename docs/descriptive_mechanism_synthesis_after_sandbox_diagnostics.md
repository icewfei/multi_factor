# Descriptive Mechanism Synthesis After Sandbox Diagnostics

This document synthesizes the current sandbox diagnostics under the exploratory descriptive boundary.

It is descriptive-only and paper-only. It is not alpha, not OOS, not a candidate, not a new baseline, not portfolio, not portfolio dry-run, not training, not backtest, and does not read frozen test. `p98` and `multi_equal_weight_v1` remain conditional reference only.

Current governance status remains unchanged:

- `strategy_research: paused`
- no candidate
- no portfolio
- no frozen test
- trainval diagnosis is not OOS
- no strategy restart

## Strongest Mechanism Explanation

The strongest current mechanism explanation is not that the clean D0 OHLCV + state regime has no descriptive signal at all. The stronger explanation is that the regime repeatedly fails at exact head placement.

The combined evidence suggests the following mechanism map:

1. clean scores often preserve some cross-section ordering, but the rank-band profile is non-monotonic rather than head-dominant;
2. the strongest descriptive structure often survives in `nextK` / `rank_31_100` / nearby middle-head bands rather than in exact TopK;
3. TopK weakness is repeatedly associated with stress-like head contamination, including extreme reversal placement, limit-like placement, and state-anomaly exposure;
4. cross-model agreement does not rescue the head; common TopK consensus can still be weak, while stronger shared structure often appears one band below the head;
5. therefore the main failure mode is head conversion failure, not generic absence of middle-rank descriptive structure.

In short: the current D0 OHLCV + state regime looks more like a near-head / middle-head descriptive ordering system with unstable head placement than a stable TopK selection system.

## Evidence With Stronger Support

The following mechanism evidence is currently the strongest within the sandbox:

1. rank-band non-monotonic profile
   - Full rank-band diagnosis repeatedly shows clean scores do not produce a monotonic head-first profile.
   - `TopK < nextK` and `TopK < rank_31_100` appear broadly enough to treat this as a recurring descriptive shape rather than a one-model artifact.

2. TopK failure is a head-placement problem, not a broad score-layer collapse
   - Several clean scores retain broader cross-section structure or middle-rank strength while still failing at exact TopK conversion.
   - This is consistent with the prior finding that full-cross-section improvement does not automatically convert into head quality.

3. market-state conditional findings point to stress-sensitive head weakness
   - TopK failure and mid-rank strength become more visible under bottom-amount, `is_limit_down`, and `close_at_down_limit` style states.
   - The conditional profile therefore supports a TopK stress / extreme / limit-like hypothesis at the descriptive level.

4. cross-model agreement findings strengthen the head-failure interpretation
   - Common TopK is weaker than model-specific TopK in both train and validation in the implemented cross-model diagnosis.
   - Common `nextK` and common `rank_31_100` are stronger than common TopK, with validation yearly direction consistency in the current descriptive outputs.

5. near-head consensus appears more informative than exact TopK consensus
   - The current cross-model outputs support a near-head consensus hypothesis: shared structure appears more stable in `nextK` / `rank_31_100` than in exact TopK.
   - This does not authorize any rank-band rule. It only sharpens the descriptive mechanism map.

## Evidence That Is Meaningful But Still Limited

The following findings matter, but their mechanism interpretation is narrower than the stronger evidence above:

1. liquidity exposure
   - Liquidity state clearly interacts with TopK failure, but the evidence does not justify a general low-liquidity or high-liquidity explanation by itself.
   - In some slices, high-liquidity dilution matters; in others, the worst damage is concentrated in stress-like bottom-amount / limit-like pockets.

2. board / exchange exposure
   - Board / exchange differences are visible in the descriptive outputs.
   - They do not currently look like the dominant mechanism axis relative to stress, reversal, liquidity, and limit-like state.

3. listing-age calendar buckets
   - Listing-age calendar fields remain descriptively usable.
   - They may interact with middle-head structure, but they do not currently displace the stronger head-failure explanation.

## Evidence That Is Still Insufficient

The following mechanism claims remain insufficient:

1. insufficient evidence for a single deployable D0-visible exclusion condition
   - No single stress, liquidity, limit, board, or listing-age state is stable enough to justify a candidate.
   - The sandbox evidence is explanatory, not promotable.

2. insufficient evidence that model disagreement is always better than model consensus
   - The cross-model diagnosis supports stronger near-head structure than common TopK.
   - It does not support the stronger statement that disagreement itself is the dominant source of strength in all cases.

3. insufficient evidence that one fixed state rule rescues TopK
   - Extreme reversal, limit-like state, and stress pockets help explain failure.
   - They do not jointly validate any actionable filter, threshold, or gating rule.

4. insufficient evidence that rank-band strength can be upgraded into a candidate
   - Mid-rank and near-head strength exist descriptively.
   - That still does not permit a candidate, portfolio, or strategy restart.

## Future Paper-Only Hypotheses

The following are only future paper-only hypotheses:

1. near-head consensus hypothesis
   - clean shared information may survive more stably in `nextK` / `rank_31_100` than in exact TopK.

2. TopK stress / extreme / limit-like hypothesis
   - exact TopK may be where stress-sensitive names, extreme reversal placement, and limit-like state contamination become concentrated.

3. state-conditional conversion failure hypothesis
   - broader score-layer ordering may remain present, while exact head conversion fails specifically under certain D0-visible stress states.

4. conditional-reference alignment hypothesis
   - `p98` conditional reference only may align more with clean near-head structure than with clean common TopK structure.

None of these hypotheses allows candidate creation, validation tuning, portfolio recommendation, or strategy restart.

## Direct Answers

1. Current strongest mechanism explanation:
   - the regime mainly fails at exact TopK head placement; stronger descriptive structure often survives in near-head / `rank_31_100` bands, while TopK is more exposed to stress / extreme / limit-like contamination.

2. Mechanisms with stronger evidence:
   - rank-band non-monotonic profile;
   - market-state conditional head weakness under stress-like states;
   - cross-model finding that common TopK is weak while common near-head bands are stronger;
   - repeated separation between broader score-layer structure and exact TopK conversion.

3. Mechanisms with insufficient evidence:
   - any single deployable exclusion condition;
   - any claim that disagreement universally dominates consensus;
   - any claim that a fixed rank-band mapping is promotable;
   - any claim that this is OOS-valid.

4. Future paper-only hypotheses:
   - near-head consensus hypothesis;
   - TopK stress / extreme / limit-like hypothesis;
   - state-conditional conversion failure hypothesis;
   - `p98` conditional-reference alignment hypothesis.

5. Candidate allowed?
   - no candidate.

6. Portfolio allowed?
   - no portfolio.

7. Does this change `strategy_research: paused`?
   - no.

## Final Statement

This is sandbox understanding only, no strategy restart.
