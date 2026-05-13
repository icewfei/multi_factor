# Next Research Roadmap After Nonlinear Rounds

## Scope

本文档用于在 `confirmed5`、`v2`、`v3` 全部收口后，明确下一阶段应如何开展 `portfolio construction / capital deployment` 研究。本文档只总结已有结论与后续研究边界，不做新实验，不训练，不跑回测，不读取 frozen test，不生成新的 metrics/readout，不设计具体 `v4` 参数，不修改 `confirmed5 / v2 / v3`，也不把 trainval dry-run 当 OOS。

## Current Research Conclusions

当前 nonlinear rounds 的阶段结论已经固定：

- `confirmed5` 已封口，不晋级
- `v2` 已封口，不晋级
- `v3` 已封口，不进入 portfolio dry-run
- `confirmed5 / v2 / v3` 均不晋级
- nonlinear challenger failure analysis 已完成
- portfolio construction gap summary 已完成
- baseline portfolio edge decomposition 已完成

当前必须接受的核心结论是：

1. `model-layer edge 不等于 TopK portfolio edge`
2. nonlinear `model-layer edge 未能稳定转化为 portfolio-layer edge`
3. baseline 的优势主要来自 `selected-head realized return` 更强
4. `confirmed5` 高 churn 且 head quality 不够强
5. `v2` 降低风险但牺牲收益捕获
6. `v3` 在 model-layer 已明显劣化
7. `baseline` 仍是当前必须正面超过的最低门槛
8. 下一阶段不应继续堆模型复杂度

## Next-Stage Research Focus

下一阶段研究重心必须从“继续造 nonlinear model”转向“约束明确的组合构造与资金部署诊断”：

- `portfolio construction`
- `capital deployment`
- `TopK head quality`
- `turnover-aware deployment`
- `cash / invested capital 口径`
- `selected-head realized return decomposition`

这里的含义不是宣称已经找到有效策略，而是把研究问题收缩到更低自由度、可审计、D0 可见的诊断方向。

## Directions Not Recommended

下一阶段明确不建议继续做以下方向：

- 不继续堆 `LightGBM / nonlinear` 模型复杂度
- 不继续围绕 `confirmed5 / v2 / v3` 微调
- 不用 validation 结果反复筛公式
- 不直接开 `v4` 训练
- 不围绕 validation 调参
- 不把 trainval dry-run 当 OOS
- 不宣称策略有效

## Low-Degree Research Directions

以下只列低自由度研究方向，不实现，不训练，不回测，不生成新 metrics/readout。

### A. TopK Head Quality Gate

- 研究假设：某些 `signal_date` 的头部质量不足时，机械满额部署 `TopK` 会放大弱头部暴露，因此应先研究是否存在“降低部署而非继续满额部署”的可审计触发条件。
- 可用数据：已有 `trainval dry-run` 产物、已有 holdings 摘要、已有 turnover 摘要、已有 `cash / invested capital` 路径、已有 `selected-head realized return decomposition`、已有 baseline vs nonlinear overlap 诊断。
- 禁止使用的数据：frozen test、任何新训练结果、任何新回测结果、任何新 metrics/readout、任何把 trainval dry-run 包装成 OOS 的材料。
- 可能的 fail-fast 条件：如果头部质量弱日无法在 D0 可见字段上形成稳定、低自由度、可复述的区分条件，则停止该方向，不进入 challenger 设计。
- 是否需要新 challenger：不需要。该方向应先做 diagnostic-only research。
- 是否可能引入过拟合风险：会。若事后从大量日期切片中反复筛条件，极易把 validation 噪声伪装成 gate 规则。

### B. Turnover-Aware Admission Rule

- 研究假设：`confirmed5` 的主要问题之一是高 churn，因此新入选股票可能需要稳定性或质量确认，避免头部集合过快替换。
- 可用数据：已有 TopK 替换率摘要、已有 candidate entry/exit 审计、已有持仓变更摘要、已有 baseline 与 nonlinear 的 cohort overlap 诊断、已有头部 realized return 统计。
- 禁止使用的数据：frozen test、任何新训练分数、任何新 dry-run、任何新回测、任何从 validation 反复筛出的 admission 公式。
- 可能的 fail-fast 条件：如果高 churn 并不能与弱头部 realized return 或较差部署结果形成稳定关联，则停止该方向。
- 是否需要新 challenger：不需要。先做规则层诊断，不立刻开新 challenger。
- 是否可能引入过拟合风险：会。admission rule 很容易演变成隐性调参，尤其当规则是根据 validation 结果反推时。

### C. Baseline Overlap / Divergence Analysis

- 研究假设：baseline 与 nonlinear 分歧最大的那些日期和名字，可能正是 nonlinear 更容易输给 baseline 的来源，因此应研究“分歧在哪里、为何输、是否存在低自由度共性”。
- 可用数据：已有 baseline / nonlinear 同日 TopK overlap、已有 divergence 名单、已有 `selected-head realized return decomposition`、已有 `cash / invested_weight` 路径、已有 cohort 层摘要。
- 禁止使用的数据：frozen test、任何新增 readout、任何新 manifest、任何借由 divergence 直接反推出新模型参数的材料。
- 可能的 fail-fast 条件：如果 baseline / nonlinear 的分歧无法沉淀为少量、可审计、D0 可见的共性，而只能形成事后叙述，则停止该方向。
- 是否需要新 challenger：不需要。先做 diagnostic-only research。
- 是否可能引入过拟合风险：会。若把每类分歧都单独解释并分别建规则，容易快速失去低自由度约束。

### D. Capital Deployment Schedule

- 研究假设：`cash / invested_weight` 不应被机械看作固定副产品，而应研究是否需要随头部质量变化而调整部署强度。
- 可用数据：已有 `avg_cash_weight`、已有 `avg_invested_weight`、已有日级 invested capital 路径、已有头部质量诊断、已有 baseline 部署对照摘要。
- 禁止使用的数据：frozen test、任何新部署回测、任何新增风险收益 readout、任何把 capital deployment schedule 直接包装成已验证有效策略的材料。
- 可能的 fail-fast 条件：如果部署强度变化无法用少量 D0 可见字段解释，或者只能依赖事后 realized return 才能定义，则停止该方向。
- 是否需要新 challenger：不需要。先研究部署口径，不直接开新 challenger。
- 是否可能引入过拟合风险：会。capital deployment schedule 若自由度过高，会变成 disguised timing rule。

### E. Tail-Loss Containment

- 研究假设：nonlinear TopK 中的大亏损样本，可能存在可审计、D0 可见的共同特征；若这些共同特征真实存在，组合层损失控制也许比继续改模型更关键。
- 可用数据：已有大亏损样本审计、已有 D0 可见暴露字段、已有 turnover 与替换摘要、已有 baseline / nonlinear 的尾部 realized return 对比。
- 禁止使用的数据：frozen test、任何未来信息、任何依赖 D1 以后才知道的标签式过滤条件、任何新增回测 readout。
- 可能的 fail-fast 条件：如果尾部大亏损无法沉淀为可审计、D0 可见、低自由度的共同特征，则停止该方向，不再延展成防尾损规则。
- 是否需要新 challenger：不需要。先做尾部诊断，再决定是否值得进入新 round。
- 是否可能引入过拟合风险：会。tail case 数量有限，最容易被个案叙事和 hindsight bias 污染。

## Operating Boundaries

下一阶段研究必须继续遵守以下硬边界：

- 不训练模型
- 不跑回测
- 不读取 frozen test
- 不生成 metrics/readout
- 不设计具体 `v4` 参数
- 不修改 `confirmed5 / v2 / v3`
- 不继续调 `confirmed5 / v2 / v3`
- 不围绕 validation 调参
- 不用 validation 结果反复筛公式
- 不把 trainval dry-run 当 OOS
- 不宣称策略有效

## Next-Step Recommendation

下一步建议固定为：

1. 先做 `diagnostic-only research`
2. 不立刻开新 challenger
3. 不直接进入新的 `research_round` 或新的 `manifest`
4. 只有当某个方向出现稳定、低自由度、D0 可见证据时，才允许进入 `new research_round / new manifest`

换句话说，下一阶段的目标不是尽快开 `nonlinear_challenger_v4`，而是先确认：

- 是否真的存在 `portfolio construction` 层的低自由度改进抓手
- 是否真的存在 `capital deployment` 层的低自由度改进抓手
- 这些抓手是否能在不依赖 frozen test、不依赖新训练、不依赖 validation 反复筛优的前提下成立

## Final Status

- `confirmed5 / v2 / v3` 当前全部收口，不晋级
- baseline 仍是必须正面超过的最低门槛
- 下一阶段不应继续盲目开 `nonlinear_challenger_v4`
- 下一阶段应围绕 `portfolio construction / capital deployment` 开展低自由度研究
- 在形成稳定、低自由度、D0 可见证据之前，不进入新 challenger 立项
