# clean baseline family design

## Scope

本设计用于建立一组 clean baseline candidates，替代单一 `p98 conditional baseline` 作为比较锚。本文档只定义设计边界、候选 baseline 配置草案与 source-chain audit 要求，不训练，不跑 portfolio，不读取 `frozen test`，不生成 metrics/readout，不宣称任何策略有效。

## Family Objective

- 建立 `clean baseline family`
- 用多个低自由度、可复现、可审计的 baseline candidates 替代单一条件式锚
- 保持 `D0 visible only`
- 保持 `no p98`
- 保持 `no label diagnostics`
- 保持 `no trainval source-selection feedback`
- 保持 `no frozen test access`

## Hard Boundaries

以下边界对所有 baseline candidate 一致成立：

- `no p98`
- `no label diagnostics`
- `no trainval source-selection feedback`
- `D0 visible only`
- `no frozen test access`
- 不准训练 ML 模型
- 不准跑 portfolio
- 不准生成 metrics/readout
- 不准围绕 validation 调参
- 不准宣称策略有效

## Family Rules

- baseline 只允许使用当日可见字段与向后历史窗口，不允许未来收益、执行结果、标签诊断或任何 validation/frozen-test 反馈进入 source chain
- score rule 必须是低自由度、固定写法、单次可重建
- 每个 baseline 都必须能产出一致的 source-chain audit 记录
- 所有 baseline 的 intended role 都是 `clean comparison anchor candidate`，不是 winner claim

## Common Expected Artifacts

如果未来有人按本设计实现任一 baseline，只允许期待以下治理型 artifacts：

- `model_scores_D0.parquet`
- `model_scores_D0_audit.json`
- `source_chain_audit.json`
- `run_state_attempt_manifest.json`

这些 artifacts 只用于 source-chain audit 和复验，不等价于 portfolio、metrics 或 formal readout。

## Candidate Summary

### 1. no_p98_reversal_baseline_v1

- baseline_id: `no_p98_reversal_baseline_v1`
- score source: `c1 ASC / reversal_rank`
- allowed inputs: `D0 visible only` 的 `adj_close` 历史窗口、`ranking_eligible_D0`、`snapshot_id`
- forbidden inputs: `no p98`、`no label diagnostics`、`no trainval source-selection feedback`、`no frozen test access`、任何 `label_*`、任何 validation retuning
- score direction: `ascending 1d return / stronger short-horizon reversal first`
- expected artifacts: `model_scores_D0.parquet`、`model_scores_D0_audit.json`、`source_chain_audit.json`、`run_state_attempt_manifest.json`
- fail-fast conditions: 出现 `p98`，出现 label diagnostics，出现 frozen test access，`D0 visible only` 不成立，`c1 ASC` 方向声明不清
- intended role: `clean comparison anchor candidate`；作为 clean family 中的 reversal leg
- why it is clean: 只依赖可见价格历史和 eligibility，不借助 `p98`，不借助标签反馈，也不借助 validation 结果做 source selection

### 2. clean_momentum_20d_baseline_v1

- baseline_id: `clean_momentum_20d_baseline_v1`
- score source: `20d cumulative return DESC / momentum_rank`
- allowed inputs: `D0 visible only` 的 `adj_close` 历史窗口、`ranking_eligible_D0`、`snapshot_id`
- forbidden inputs: `no p98`、`no label diagnostics`、`no trainval source-selection feedback`、`no frozen test access`、任何 `label_*`、任何 validation retuning
- score direction: `descending 20d cumulative return / stronger momentum first`
- expected artifacts: `model_scores_D0.parquet`、`model_scores_D0_audit.json`、`source_chain_audit.json`、`run_state_attempt_manifest.json`
- fail-fast conditions: 出现 `p98`，出现 label diagnostics，出现 frozen test access，`D0 visible only` 不成立，20 日窗口定义不固定
- intended role: `clean comparison anchor candidate`；作为 clean family 中的 momentum leg
- why it is clean: 公式固定、只用可见价格历史、没有标签诊断和 source-selection feedback，也没有围绕 validation 调参

### 3. clean_liquidity_adjusted_reversal_baseline_v1

- baseline_id: `clean_liquidity_adjusted_reversal_baseline_v1`
- score source: `1d reversal primary, 20d median amount DESC tiebreak`
- allowed inputs: `D0 visible only` 的 `adj_close` 历史窗口、warehouse `vol` 历史窗口、warehouse `amount` 历史窗口、`ranking_eligible_D0`、`snapshot_id`
- forbidden inputs: `no p98`、`no label diagnostics`、`no trainval source-selection feedback`、`no frozen test access`、任何 `label_*`、任何 execution outcome、任何 validation retuning
- score direction: `ascending 1d return first, descending liquidity tiebreak`
- expected artifacts: `model_scores_D0.parquet`、`model_scores_D0_audit.json`、`source_chain_audit.json`、`run_state_attempt_manifest.json`
- fail-fast conditions: 出现 `p98`，出现 label diagnostics，出现 frozen test access，`D0 visible only` 不成立，liquidity tiebreak 不是固定 20d median amount，或 warehouse `vol/amount` 任一缺失
- intended role: `clean comparison anchor candidate`；作为 clean family 中的 liquidity-aware reversal leg
- why it is clean: 只增加一个固定、可见、非标签的流动性 tie-break；在真实 warehouse 契约下显式使用 `amount` 作为 liquidity proxy，并记录 `vol` / `amount` 字段来源，避免用 trainval 反馈去挑 source，同时保留可复现 source-chain audit

### 4. clean_equal_weight_random_eligible_baseline_v1

- baseline_id: `clean_equal_weight_random_eligible_baseline_v1`
- score source: `stable hash(snapshot_id, instrument_id, baseline_id) ASC`
- allowed inputs: `D0 visible only` 的 `ranking_eligible_D0`、`instrument_id`、`snapshot_id`
- forbidden inputs: `no p98`、`no label diagnostics`、`no trainval source-selection feedback`、`no frozen test access`、任何 `label_*`、任何 future return、任何 validation retuning
- score direction: `ascending deterministic hash / pseudo-random but reproducible order`
- expected artifacts: `model_scores_D0.parquet`、`model_scores_D0_audit.json`、`source_chain_audit.json`、`run_state_attempt_manifest.json`
- fail-fast conditions: 出现 `p98`，出现 label diagnostics，出现 frozen test access，`D0 visible only` 不成立，hash seed 不固定或排序不可复现
- intended role: `clean comparison anchor candidate`；作为 family 内部的 neutral control
- why it is clean: 它不依赖经济标签或 trainval 表现，只使用 eligibility 与固定 hash 种子，低自由度且最容易审计 reproducibility

## Source-Chain Audit Requirements

每个 baseline candidate 都必须满足以下 source-chain audit 要求：

- source formula 是固定文本，可直接写入 manifest
- allowed inputs 和 forbidden inputs 可逐项比对
- `D0 visible only` 要能在 audit 中显式声明
- baseline 构建不允许触碰 `frozen test`
- random baseline 必须固定 hash seed 规则，确保复现实验时分数顺序一致

## Governance Interpretation

- 这组 baseline 是 `clean baseline family`
- 它们是比较锚候选，不是 portfolio 入场凭证
- 它们不是 metrics/readout 替代物
- 它们不是策略有效性声明
- `multi_equal_weight_v1 / p98` 仍然只是 `stronger but not clean` 的 conditional baseline 参考，不进入本 family 的 clean 定义
