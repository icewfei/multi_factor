# Nonlinear Challenger v1 Design

本文档定义在当前冻结边界下可接受的 `Nonlinear Challenger v1` 方案设计。它是一个治理受限的 challenger 立项说明，不是训练实现，不是回测结果，也不是已验证成功的 ML 结论。

相关背景与边界请同时参照：

- [docs/current_stage.md](/Users/wy/MiscProject/multi_factor/docs/current_stage.md)
- [docs/research_freeze_policy.md](/Users/wy/MiscProject/multi_factor/docs/research_freeze_policy.md)
- [docs/audit_boundary.md](/Users/wy/MiscProject/multi_factor/docs/audit_boundary.md)
- [项目状态总结 2026-05-07](/Users/wy/MiscProject/multi_factor/项目总纲及计划/project_status_20260507.md)

## 1. 立项目的

当前第一阶段线性排序与规则型信号工程已经收口，`exploratory_winner = multi_equal_weight_v1`，但 `strict_confirmatory_winner = none`。这意味着现有线性/规则型组合虽然留下了可审计的探索性改善证据，但还没有出现可以晋升为严格确认性赢家的候选。

在这一背景下，`Nonlinear Challenger v1` 的目的不是重新打开同一数据模态上的自由探索，更不是把 ML 包装成新的默认主线。它的唯一目标是：在现有数据源不变、执行语义不变、TopK/成本/tradability 不变、样本切分制度不变的前提下，受控检验是否存在足以超越线性 baseline 的非线性交互 alpha。

由于当前没有新数据源，这个 challenger 必须被视为一次低自由度、有限候选、强治理约束下的验证动作，而不是第二轮无边界特征工程。若非线性模型没有在严格边界内稳定胜出，应接受“现有信息源下非线性增益不足”的结论，而不是继续扩张搜索空间。

## 2. 不变制度

`Nonlinear Challenger v1` 不得改写当前已冻结的研究与执行制度。以下内容必须保持不变：

- `D0` 收盘后出信号
- `D1 open` 买入
- `D5 close` 计划卖出
- `D5 close` 不可卖时按后续 `open` retry
- `raw price` 用于成交
- `adjusted` 或 `base-adjusted price` 用于标签与收益连续性
- `TopK` 默认制度不因 ML 改变
- `tradability` 过滤与可交易约束不因 ML 改变
- `train / validation / frozen test` 边界不因 ML 改变
- 不得读取或使用 `frozen test`
- 不得基于 `trainval` 结果继续无限调参

这意味着 ML challenger 只能替换“打分函数”本身，不能借机改变执行语义、样本制度、成交假设或组合制度来制造表面改善。任何脱离上述不变制度的结果，均不应纳入本方案的有效证据。

## 3. 基线与挑战者关系

当前线性模型与规则型组合必须保留为 baseline。`multi_equal_weight_v1` 目前只能作为 exploratory baseline 使用，不得被写成严格赢家，也不得因为引入 ML 而抹去其作为第一阶段最佳探索性候选的比较地位。

`Nonlinear Challenger v1` 的评估方式必须是与线性 baseline 并排比较，而不是单独展示一组对 ML 有利的指标。比较时不能只看年化收益，还必须同步观察：

- 成本 stress 后是否仍优于 baseline
- `TopK` 稳健性是否保留
- 平均现金权重是否异常抬升
- 换手是否显著上升
- 分年份表现是否稳定
- 回撤改善是否只是由低持仓带来
- `RankIC / RankICIR` 是否同步支持

若 ML 只在个别展示口径上看起来更好，但在持仓、成本、稳健性或年度分布上劣化，则不应被视为真实胜出。

## 4. 允许的模型

第一版仅允许以下模型族进入候选集合：

- `Ridge` / `ElasticNet`，作为线性正则化对照
- `LightGBM` 或 `XGBoost` 的小深度树模型，作为非线性 challenger

为控制自由度，建议采用以下限制：

- `max_depth <= 3`
- `num_leaves` 保持小规模
- `learning_rate` 预先固定
- `n_estimators` 预先固定，或只允许有限 early stopping
- `random_seed` 固定
- 调参预算有限且事先声明
- 不允许大规模参数搜索
- 不允许 `AutoML`
- 不允许神经网络在第一版直接进入主线比较

这里的设计原则不是寻找最强 ML，而是用最小额外自由度回答一个更窄的问题：在现有信息源和现有制度下，受控的非线性映射是否明显优于线性映射。

## 5. 允许的特征范围

第一版不得新增新数据源，也不得把已有字段无边界组合成特征爆炸空间。建议把 `Nonlinear Challenger v1` 的特征集上限控制在最多 `20` 个特征，并优先从第一阶段已经出现边际迹象的家族中挑选少量代表项：

- `p98 / reversal` 类
- `cord30 / corr30` 类
- `vsumd60 / volume-strength` 类
- `overnight / intraday` 中最稳定的少数特征
- `volatility / turnover / liquidity / amount` 状态特征
- `simple momentum / reversal` 多窗口
- 指数近 `N` 日收益或波动这类 `market regime proxy`

所有特征都必须满足以下条件：

- 必须在 `D0` 可见
- 必须通过 `PIT` 审计
- 不得引入未来信息
- 不得通过事后筛选把弱特征无限替换重试
- 不得借由大量衍生组合制造隐性调参

第一版特征集的目标是覆盖“可能存在非线性交互”的最小必要信息，而不是重建一个新的全量研究宇宙。

## 6. 训练与验证协议

`Nonlinear Challenger v1` 只允许使用 `train / validation`，不得读取 `frozen test`，不得把任何未来正式隔离评估层提前消耗掉。`validation` 的角色是有限候选比较，而不是允许研究者无限循环地修改特征和参数直到出现满意结果。

为保证治理可追踪，每个模型候选都必须具备明确留痕，至少包括：

- `candidate_scheme_id`
- `snapshot_id`
- `config_hash`
- `feature_set_id`
- `model_config_id`

同时应遵守以下协议：

- 候选数目事先限制
- 候选特征集与模型配置应先冻结再运行
- `validation` 只用于有限候选比较
- 失败结果必须保留
- 不允许只展示最好的一次运行
- 不允许根据中间 readout 继续无限扩表或无限调参

换言之，本方案接受“受控比较中的失败”，不接受“靠反复重试换出一个偶然胜利”。

## 7. 晋升标准

`ML challenger` 若要被认定为值得进入下一阶段，至少需要同时满足以下条件：

- `validation` 相对年化收益优于线性 baseline
- 成本 stress 后仍优于 baseline
- `TopK = 8 / 10 / 12` 不崩
- 分年份表现不是主要由 `1-2` 个年份贡献
- 平均现金权重不能靠大幅空仓美化
- `turnover` 不显著失控
- `RankIC / RankICIR` 不明显恶化
- 最大回撤不能主要靠降低持仓获得
- 结果不能主要来自单一行业、微盘或低流动性暴露
- 不得牺牲执行可行性换取收益

这些标准共同表达的是：ML 若胜出，必须是“在同一制度下更强”，而不是“换一种更脆弱的暴露方式看起来更亮眼”。

## 8. 失败条件

出现以下任一情况，应判定 `Nonlinear Challenger v1` 失败或暂不晋升：

- 只在 `train` 表现更好，`validation` 没有改善
- `validation` 改善主要来自高换手，且成本 stress 后失败
- 改善主要来自高现金、低持仓或规避交易
- `TopK` 轻微扰动即崩溃
- 结果集中在少数年份
- 结果依赖低流动性股票
- 需要反复改特征或参数才能维持效果
- 与现有治理制度冲突

失败在本方案中是允许且有信息价值的结果。若失败发生，正确结论应是“当前受控非线性 challenger 未证明值得进入下一阶段”，而不是继续追加更大自由度的修补动作。

## 9. 第一版工程边界

第一版当前只做方案，不写代码，不跑训练，不产出新回测。若后续确认进入实现，应按分阶段方式推进，并保持每一阶段都可单独审阅：

1. `feature_set_manifest`
2. `model_config_manifest`
3. 训练脚本
4. `validation readout`
5. `audit summary`
6. 与 linear baseline 的对照报告

在方案冻结之前，`Codex` 不应直接跳到训练脚本或模型实验实现，更不应越过 manifest 与治理留痕层去做一次性试跑。

## 10. 当前结论

当前阶段可以设计 `Nonlinear Challenger v1`，因为这属于冻结后的边界治理与下一阶段候选立项，不等于重新开启自由探索。

但在方案尚未冻结前，不允许 `Codex` 直接编写模型训练脚本，也不允许把 ML challenger 写成已验证成功的主线结论。这个阶段的目标不是保证赚钱，而是用尽可能低的新增自由度回答一个更基础的问题：非线性是否值得在下一阶段获得有限实现预算。
