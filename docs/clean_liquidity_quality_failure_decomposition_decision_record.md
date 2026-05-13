# Clean Liquidity Quality Failure Decomposition Decision Record

This closes `clean_liquidity_quality_failure_decomposition_round_v1`. It is train/validation diagnosis only: not OOS, not strategy approval, not a portfolio dry-run, not a backtest, not holdings generation, and not formal metrics/readout. Frozen test remains unread.

Artifacts:

- JSON: `/private/tmp/clean_liquidity_quality_failure_decomposition.json`
- Markdown: `/private/tmp/clean_liquidity_quality_failure_decomposition.md`

## Boundary

- The `clean_reversal_5d_liquidity_quality_v1` formula was not changed.
- No liquidity threshold was tuned.
- No new candidate was created.
- No ML model was trained.
- No portfolio, backtest, holdings, or `backtest_daily` was generated.
- No frozen test was read.
- Blocked fields were not used: `listing_age_trading_days`, `newly_listed_flag`.
- `p98_conditional_reference` and `multi_equal_weight_v1` remain conditional reference only.
- `clean_composite_reversal_tradability_v1` is used only as a rejected comparator.
- Trainval diagnosis is not OOS evidence.

## Main Finding

`clean_reversal_5d_liquidity_quality_v1` has a real full-cross-section RankIC improvement versus no-p98, but that improvement is not a TopK head improvement. The edge is mainly middle/tail shaped: the top decile is not the best-returning bucket, the nextK bucket beats TopK, and rank 31-100 beats TopK. This line therefore cannot enter portfolio dry-run.

Validation deltas:

| comparison | RankIC delta | ICIR delta | top-bottom delta | TopK proxy delta | TopK-minus-nextK delta | coverage delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| liquidity_quality vs `no_p98_reversal_baseline_v1` | 0.003068 | 0.016833 | 0.000947 | 0.005738 | 0.005208 | -0.173034 |
| liquidity_quality vs `p98_conditional_reference` | -0.002492 | -0.031586 | -0.000239 | -0.004408 | -0.003445 | -0.153979 |
| liquidity_quality vs rejected `clean_composite_reversal_tradability_v1` | 0.025167 | 0.196170 | 0.003919 | -0.004122 | -0.004433 | -0.173034 |
| liquidity_quality vs `multi_equal_weight_v1` conditional | -0.024612 | -0.272699 | -0.001419 | -0.005713 | -0.002390 | -0.153979 |

## Required Questions

1. liquidity_quality 的 RankIC 改善是否真实存在？

Yes versus no-p98. Validation RankIC improves by `0.003068`, and the improvement exists in each validation year: 2019 `0.005523`, 2020 `0.002054`, 2021 `0.001587`. It remains below p98 conditional by `-0.002492`.

2. RankIC 改善主要来自头部、中段、还是尾部？

Mainly middle/tail structure, not the top head. The top decile mean is `0.004413`, below the middle deciles 4-7 mean `0.005809`. The bottom decile mean is much weaker at `0.001042`, giving useful tail separation. Segment RankIC is negative inside the top decile (`-0.0366`), mildly positive in the middle (`0.0123`), and strongest in the bottom decile (`0.0648`).

3. TopK-minus-nextK 为负的主因是什么？

The immediate next bucket is stronger than the TopK bucket. Validation TopK mean is `0.000312`; nextK mean is `0.003547`; rank 31-100 mean is `0.004507`. TopK-minus-nextK is `-0.003235`.

4. 是否是 nextK 比 TopK 更强？

Yes. TopK beats nextK on only `43.6%` of validation days. TopK-minus-nextK remains negative in every validation year: 2019 `-0.002865`, 2020 `-0.004171`, 2021 `-0.002660`.

5. 是否是 liquidity filter 把 alpha 从 top head 推到中高分位？

Yes, partially. The decile and ventile curves peak after the very top: validation decile 1 is `0.004413`, while deciles 2-6 are all higher. Ventile 1 is only `0.003610`, while ventiles 3-8 are around `0.0059-0.0063`. The filter improves full-cross-section ordering mostly by avoiding weak low-liquidity tail names, not by making the first 30 names strongest.

6. 是否是高流动性/低风险结构稀释了 reversal edge？

Likely yes. Validation TopK is overrepresented in high-liquidity names: `44.04%` top-20% amount bucket and `41.13%` 50-80% bucket. Top-liquidity names return `0.002408`, while mid-liquidity names return `0.003845`, so top liquidity underperforms mid liquidity by `-0.001437`.

7. 该现象是否 train / validation / yearly 稳定？

Yes for the failure pattern. RankIC improvement versus no-p98 is positive in train and validation and in each validation year. TopK-minus-nextK is negative in train (`-0.003184`), validation (`-0.003235`), and every validation year.

8. 是否建议开下一轮 preregistered candidate？

No from this round. The diagnosis may motivate a separate pre-registered research question about head placement versus liquidity filtering, but this round cannot tune thresholds or open a new candidate.

9. 是否建议进入 portfolio dry-run？

No. The rule blocks portfolio because TopK-minus-nextK remains negative and RankIC improvement is not head-driven.

10. 是否继续把 p98 只作为 conditional reference？

Yes. p98 remains conditional reference only and was used only for comparison/overlap, not as a clean component or source-selection input.

## Decile / Ventile Interpretation

The curve is not head-monotone:

- Decile monotonicity score is `0.556`; ventile monotonicity score is `0.526`.
- Decile 1 is weaker than deciles 2-8.
- Ventile 1 is weaker than most middle/upper-middle ventiles.
- The strongest RankIC contribution is not from the very top head; it comes from middle ordering plus cleaner bottom-tail separation.

This explains why RankIC can approach p98 conditional while TopK head quality remains insufficient.

## Overlap / Divergence

Validation TopK overlap:

- Liquidity-quality vs no-p98: average overlap `28.43 / 30`, Jaccard `0.905`. Liquidity-only return is `-0.001388`, no-p98-only return is `-0.110839`; the filter mostly removes very bad low-liquidity names, not enough to create a strong positive head.
- Liquidity-quality vs p98 conditional: average overlap `0.00 / 30`, Jaccard `0.000`. Liquidity-only return is `0.000312`, p98-only return is `0.004720`.

The no-p98 divergence is small but useful because excluded names are very weak on average. The p98 divergence is structural and explains the TopK gap to the conditional reference.

## Liquidity Exposure

Validation exposure:

- TopK amount bucket: `44.04%` top-20%, `41.13%` 50-80%, `14.83%` 20-50%.
- NextK amount bucket: `36.23%` top-20%, `43.19%` 50-80%, `20.57%` 20-50%.
- TopK mean return is lower than nextK despite higher top-liquidity concentration.
- Excluded no-p98 TopK names are almost all bottom-20% amount names and are very weak on average (`-0.1073`), but some positive winners are also excluded (`304` positive excluded names, mean `0.0742`).

The filter is doing useful risk cleanup, but it also concentrates the head in high-liquidity names where reversal edge is diluted.

## Decision

Do not open a new candidate in this round. Do not enter portfolio dry-run. Continue treating `clean_reversal_5d_liquidity_quality_v1` as a diagnostic object and require any next step to be separately pre-registered.
