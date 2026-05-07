# Alpha158 CORR30 + CORD30 Dual-Signal Family — Closeout

日期: 2026-04-30

## 结论

**`round_decision = REJECT`**

## 解释

这轮只测试一个结构性问题：双信号融合本身能否在不引入 refresh / extraction / weight-tilt 干预的情况下，缓解单信号 `TopK + 等权 + 全刷新` 的结构性换手。

- 相对 `cord30` 的 `avg_turnover_daily(平均日换手)` 变化 = -0.025668
- 相对 `v18` 的 `avg_turnover_daily(平均日换手)` 变化 = 0.003411
- `topk_perturbation_pass(TopK扰动通过) = false`
- `cost_stress_pass(成本压力通过) = false`
