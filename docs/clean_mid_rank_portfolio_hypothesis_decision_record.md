# Clean Mid-Rank Portfolio Hypothesis Decision Record

This record closes `clean_mid_rank_portfolio_hypothesis_round_v1`. It is train/validation diagnosis only: not OOS, not strategy approval, not a portfolio dry-run, not a backtest, not holdings generation, and not formal metrics/readout. Frozen test remains unread.

Artifacts:

- JSON: `/private/tmp/clean_mid_rank_edge_diagnosis.json`
- Markdown: `/private/tmp/clean_mid_rank_edge_diagnosis.md`

## Boundary

- No rank bands were tuned based on validation.
- No new candidate was created.
- No ML model was trained.
- No portfolio, backtest, holdings, or `backtest_daily` was generated.
- No frozen test was read.
- Blocked fields were not used: `listing_age_trading_days`, `newly_listed_flag`.
- `p98` and `multi_equal_weight_v1` remain conditional reference only.
- Trainval diagnosis is not OOS evidence.
- This is not a strategy effectiveness conclusion.

## Required Questions

1. 是否存在稳定 mid-rank edge？

No. The diagnosis across seven clean scores shows that rank-band edge is not stable enough across train, validation, and validation-year dimensions. While rank31-100 consistently beats TopK in certain models, the cross-model, cross-split, and cross-year consistency required by pre-registered decision rules is not met.

2. 是否 rank31-100 / rank31-200 系统性优于 TopK？

Not systematically in the sense required for a pre-registered hypothesis. The edge is observed in multiple clean models in validation, but the fixed-band, no-tuning, cross-model, cross-split, and cross-year stability check does not clear the bar for a deployment recommendation.

3. 是否可解释为 TopK extreme reversal failure？

Partially. The TopK failure documented in prior rounds (extreme reversal, high-liquidity concentration, limit-down contamination) provides an explanation for why TopK underperforms nearby buckets. The mid-rank bands benefit from avoiding these TopK-specific failure patterns. However, this explanation does not rescue the stability requirement.

4. 是否建议下一阶段做 pre-registered same-contract diagnostic portfolio dry-run？

No. The pre-registered decision rules require: (a) fixed bands show mid-rank > TopK consistently in train, validation, and every validation year; (b) the edge does not depend on p98; (c) bands are not tuned. This round does not clear all conditions simultaneously.

5. 如果建议，必须强调仍不是 formal portfolio approval。

Not applicable since recommendation is not made. However, reiterating: any future diagnostic portfolio dry-run would still not constitute strategy approval, portfolio approval, or OOS evidence.

6. 如果不建议，则项目在现有数据条件下应暂停策略推进。

The clean baseline research program was already closed. This round adds the finding that mid-rank deployment also lacks the required stability for portfolio dry-run consideration under the existing D0 OHLCV + state field system. Do not continue pursuing portfolio-adjacent steps without new information sources or a reframed research question.

7. 是否读取 frozen test：否

Frozen test was not read. Frozen test access remains prohibited.

8. 是否训练/回测/portfolio：否

None of these were performed. No model was trained. No backtest was run. No portfolio or holdings were generated.

## Decision

Do not recommend a diagnostic portfolio dry-run from this evidence. The mid-rank edge hypothesis does not produce a stable, cross-model, pre-registered, no-tuning deployment candidate. Continue all existing prohibitions: no portfolio, no frozen test, no v4, p98 as conditional reference only, trainval not OOS.

The project should not continue pursuing portfolio-adjacent deployment under the existing D0 OHLCV + state field paradigm. Any successor phase requires new information sources, new data modalities, or a reframed research question, as previously concluded in the clean baseline research closure.
