# VSUMD60 confirmatory round1-2 closeout

## Bottom line

- `candidate_scheme_id(候选方案ID) = price_volume_single_signal_alpha158_vsumd60_v1`
- `round1_decision(第1轮结论) = KEEP`
- `round2_decision(第2轮结论) = KEEP`
- `family_seed_permission(是否允许进入下一条家族种子线) = yes_with_restraint`

Decision sentence:

`price_volume_single_signal_alpha158_vsumd60_v1` is allowed to enter the next `family seed(家族种子线)`, but only as the **single promoted atomic winner(唯一晋级原子信号)** from this confirmatory branch, and only under a restrained new-family design rather than a reopened `v18 overlay(覆盖层)` line.

## Why it passed

Round 1 versus `price_volume_v18_refresh_hysteresis`:

- `annual_relative_return_delta(年化超额收益变化) = +0.151895`
- `relative_ir_delta(相对信息比率变化) = +0.993775`
- `max_drawdown_delta(最大回撤变化) = +0.348097`
- `avg_turnover_daily_delta(平均日换手变化) = +0.019115`

Round 2 stricter recheck:

- `validation_h1_annual_relative_return_delta(前半段年化超额收益变化) = +0.161858`
- `validation_h1_relative_ir_delta(前半段相对信息比率变化) = +0.801780`
- `validation_h2_annual_relative_return_delta(后半段年化超额收益变化) = +0.211317`
- `validation_h2_relative_ir_delta(后半段相对信息比率变化) = +1.199143`
- `cost_stress_annual_relative_return_delta(成本压力年化超额收益变化) = +0.013052`
- `low_liquidity_weight_share_delta(低流动性权重占比变化) = -0.040169`
- `topk8_annual_relative_return_delta(TopK=8年化超额收益变化) = +0.026527`
- `topk12_annual_relative_return_delta(TopK=12年化超额收益变化) = +0.015647`

Interpretation:

- It did not win by one noisy window only.
- It stayed better than `v18` in both validation subperiods.
- It stayed better under `TopK perturbation(TopK扰动)` and on `low_liquidity exposure(低流动性暴露)`.
- Its turnover increase stayed inside the preregistered tolerance.

## Why this is not a free pass

Two cautions remain true:

- `cost_stress_pass(成本压力通过) = false` in absolute terms for both the candidate and `v18`.
- `annual_relative_return(年化超额收益)` versus the benchmark is still negative in absolute terms; this is a relative win over `v18`, not proof of full production readiness.

So the correct interpretation is:

`vsumd60` is **promotable as a research seed(研究种子)**, not yet promotable as a production-ready terminal family.

## Family-seed decision

Allow entry into the next `family seed(家族种子线)` with these rules:

- Use `price_volume_single_signal_alpha158_vsumd60_v1` as the only carried-forward Alpha158 atomic winner.
- Do not reopen the failed `Alpha158 -> v18 overlay(覆盖层)` path.
- Do not add a second new atomic signal in the same seed round.
- Do not change more than one family dimension in the next prereg.
- Compare every new family seed directly against the standalone `vsumd60` reference, not only against `v18`.

Recommended seed framing:

- `seed_type(种子类型) = standalone-to-family transition`
- `seed_question(种子问题) = can a restrained family construction around VSUMD60 improve execution stability or benchmark-relative quality without giving back the confirmed single-signal edge?`

## Next action

Recommended next move:

Open exactly one new confirmatory-family seed round centered on `vsumd60`, with a single changed dimension such as:

- `portfolio_extraction_rule(组合提取规则)` only, or
- `weight_mapping(权重映射)` only, or
- `eligibility_guard(可选资格护栏)` only

Do not start from multi-signal expansion. Start from the narrowest family question first.
