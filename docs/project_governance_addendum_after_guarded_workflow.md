# Project Governance Addendum After Guarded Workflow

## Scope

This addendum updates the project-level governance interpretation after the `data_field_enrichment_v1` next-use guardrail and `guarded_clean_baseline_workflow_v1` were implemented. It is a governance record only. It does not train, backtest, run portfolio construction, read frozen test, generate metrics/readout, or approve any strategy.

## Constitution Continuity

The original constitution remains valid. The project objective remains a low-discretion, auditable, anti-overfitting multi-factor ranking research system, not a mandate to chase historical returns.

The original project governance rules continue to apply:

- frozen test access remains prohibited unless the original freeze governance explicitly allows it.
- trainval evidence must not be relabeled as OOS.
- execution semantics remain unchanged.
- strategy effectiveness must not be claimed from governance, diagnosis, or trainval-only artifacts.

## New Governance Conclusions

- `p98` / `multi_equal_weight_v1` is a conditional baseline / conditional reference only, not an unconditional gold standard.
- `data_field_enrichment_v1` is a conditional enrichment layer, not alpha, not strategy approval, and not OOS evidence.
- blocked enrichment fields are `listing_age_trading_days` and `newly_listed_flag`.
- guarded workflow required: downstream clean baseline and challenger research that consumes enrichment fields must use `guarded_clean_baseline_workflow_v1` or an equivalent guarded workflow.

## Historical Research Route

At the time of this addendum, the research route was constrained by two simultaneous findings:

- the strong baseline is not clean enough to become an unconditional gold standard.
- the clean baseline family is clean but not strong enough; its model-layer / TopK head quality is insufficient.

Therefore the next research direction at that stage was clean baseline redesign, not platform expansion. That route has since been superseded by `current_data_regime_research_stop_decision`, which stops clean baseline / TopK / mid-rank research under the current D0 OHLCV + state field regime.

## Non-Changes

This addendum does not change the frozen test rule. Frozen test remains prohibited and no frozen test evidence is introduced here.

This addendum does not change execution semantics. Existing terminal-event, tradability, ranking-entry, and execution-path semantics remain governed by their existing contracts and decision records.

This addendum does not permit trainval-as-OOS. Trainval diagnosis remains diagnostic evidence only and must not be treated as OOS, portfolio approval, or strategy validation.

## Final Position

Historical phase: `data_enrichment_and_guarded_research_workflow_phase`.

Superseded route: clean baseline redesign research round.

Current phase: `current_data_regime_research_stopped`.

Current restrictions: no portfolio, no frozen test, no v4, no training, no backtest, no formal metrics/readout, no concrete trading rules, no trainval-as-OOS.
