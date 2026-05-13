# Clean Composite TopK Improvement Decomposition Decision Record

This closes `clean_composite_topk_improvement_decomposition_round_v1`. It is train/validation diagnosis only: not OOS, not strategy approval, not a portfolio dry-run, not a backtest, not holdings generation, and not formal metrics/readout. Frozen test remains unread.

Artifacts:

- JSON: `/private/tmp/clean_composite_topk_improvement_decomposition.json`
- Markdown: `/private/tmp/clean_composite_topk_improvement_decomposition.md`

## Boundary

- The composite formula was not changed.
- No weights were tuned.
- No new candidate was created.
- No ML model was trained.
- No portfolio, backtest, holdings, or `backtest_daily` was generated.
- No frozen test was read.
- Blocked fields were not used: `listing_age_trading_days`, `newly_listed_flag`.
- `p98_conditional_reference` remains conditional reference only, not a clean component and not an unconditional gold standard.
- Trainval diagnosis is not OOS evidence.

## Main Finding

The validation TopK proxy improvement is real versus clean comparators, but the full TopK improvement is not stable enough because `TopK-minus-nextK` is not consistently positive. The RankIC damage is severe and persistent. Therefore this evidence does not justify opening a next clean candidate and does not justify portfolio dry-run.

Validation deltas:

| comparison | RankIC delta | ICIR delta | Top-bottom delta | TopK proxy delta | TopK-minus-nextK delta | coverage delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| composite vs `no_p98_reversal_baseline_v1` | -0.022099 | -0.179337 | -0.002972 | 0.009859 | 0.009641 | 0.000000 |
| composite vs `liquidity_quality` | -0.025167 | -0.196170 | -0.003919 | 0.004122 | 0.004433 | 0.173034 |
| composite vs `p98_conditional_reference` | -0.027659 | -0.227756 | -0.004158 | -0.000286 | 0.000988 | 0.019055 |

## Required Questions

1. Composite TopK improvement 是否真实存在？

Yes for validation TopK proxy versus clean comparators: composite beats no-p98 by `0.009859` and liquidity-quality by `0.004122`. It does not beat p98 conditional on validation TopK proxy. The stronger claim, stable positive TopK-minus-nextK, is not supported.

2. Composite RankIC damage 是否严重？

Yes. Validation RankIC delta is `-0.022099` versus no-p98, `-0.025167` versus liquidity-quality, and `-0.027659` versus p98 conditional. The damage appears in every validation year versus the clean comparators.

3. TopK improvement 是否稳定？

No. TopK proxy delta is directionally stable versus no-p98 and liquidity-quality in train and each validation year, but composite `TopK-minus-nextK` is negative in train (`-0.001019`) and negative in validation year 2021 (`-0.000266`). The validation aggregate positive spread is therefore not stable enough.

4. 是否只是少数日期 / 少数样本贡献？

No clear evidence of a small-date artifact. For composite validation, the top 5% positive daily-spread days contribute about `18.3%` of positive edge, and the worst 5% days contribute about `17.2%` of damage. That concentration is not the main failure mode.

5. 是否能解释为 D0 可见结构，而不是 validation artifact？

Only partially. The TopK set is strongly D0-visible and tradability/liquidity shaped: validation composite TopK is `100%` entry-buyable, has no no-trade/suspension/zero-amount/zero-volume rows, and is almost entirely top-20% amount bucket (`99.69%`). But the positive TopK-minus-nextK is not stable across train and validation years, so this cannot be treated as a clean stable D0 structure.

6. 是否建议开下一轮 candidate？

No. The pre-registered rule blocks a new candidate because TopK-minus-nextK stability fails and RankIC damage is severe.

7. 是否建议进入 portfolio dry-run？

No.

8. 是否继续禁止 portfolio？

Yes. Continue the portfolio ban for this line.

9. 是否需要补字段或新数据？

No blocked fields should be added. The current allowed exposure fields are sufficient to explain the broad tradability/liquidity shape, but they do not rescue the instability. If this line is revisited, it should be through pre-registered diagnostics of existing D0-visible components, not through validation-tuned fields.

10. 是否继续把 p98 只作为 conditional reference？

Yes. `p98_conditional_reference` remains conditional reference only. It was used only for comparison/overlap, not as a clean component or source-selection input.

## RankIC Damage Explanation

The damage is mostly full-cross-section compression and loss of tail separation, not a simple middle-decile inversion.

- Composite validation score dispersion is compressed: daily score-std mean is about `0.1487`, versus about `0.2887` for no-p98, liquidity-quality, and p98 conditional.
- Composite validation top-bottom decile spread is negative (`-0.000548`).
- Composite validation monotonicity score is only `0.556`, with four adjacent decile inversions.
- The bottom decile is not behaving like a bad tail: bottom-decile mean is `0.005273`, and it is above decile 9 by `0.000567`.
- Middle-decile inversion count is `0`, so the main problem is not a localized middle-rank flip.

## Overlap / Divergence

Validation TopK overlap is low, which means the composite improvement versus clean comparators comes from replacing many names:

- Composite vs no-p98: average overlap `9.20 / 30`, Jaccard `0.185`; composite-only mean return `0.005953` versus no-p98-only `-0.008095`.
- Composite vs liquidity-quality: average overlap `9.61 / 30`, Jaccard `0.194`; composite-only mean return `0.006147` versus liquidity-only `0.000133`.
- Composite vs p98 conditional: average overlap `3.93 / 30`, Jaccard `0.071`; composite-only mean return `0.004061` versus p98-only `0.004249`.

The structure is divergence from clean reversal/liquidity heads, not replication of p98 conditional.

## Exposure Decomposition

Composite validation TopK exposure:

- Board: `78.39%` main board, `21.61%` ChiNext.
- Exchange: `61.67%` SZ, `38.33%` SH.
- Tradability: `100%` entry-buyable; no no-trade, suspension, zero-volume, or zero-amount rows.
- Limit status: `4.64%` close-at-down-limit / limit-down; `0.49%` limit-up.
- Liquidity: `99.69%` in the top 20% same-day amount bucket.
- Listing age: `89.54%` at least 3 years; small but nonzero short-age exposure remains.

This explains why TopK proxy can improve, but it does not explain away the RankIC collapse or spread instability.

## Decision

Do not open a next pre-registered candidate from this evidence. Do not enter portfolio dry-run. Continue treating the composite as a diagnostic object only.
