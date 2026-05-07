# 哪些规则不能放松，哪些流程可以提速

日期：`2026-04-30`

---

## 一句话结论

当前项目推进偏慢，**主因不是治理规则太严格**，而是前期 `exploratory research(探索性研究)` 扩张过快，后期不得不补做治理收口。

因此，正确动作不是放松证据标准，而是：

- **不放松核心治理底线**
- **显著收缩研究排程与分叉数量**
- **把推进单位从“大池子扫描”改成“小批次确认”**

---

## 1. 不能放松的规则

这些规则一旦放松，项目会重新掉回“看起来有结果、但不能信”的状态。

### 1.1 `test-set isolation(测试集隔离)`

不能放松原因：

- 这是防止 `OOS(in-sample 外)` 结果失真的底线
- 前面项目已经因为全量 `snapshot(快照)` 可见性问题，付出过一次治理纠偏成本

当前执行含义：

- 研究默认继续使用 `trainval-only snapshot(仅训练+验证快照)`
- 新的主线结论，不能再建立在可见测试集的 exploratory 历史产物上

### 1.2 `confirmatory single_dimension_only(确认性单维改动)`

不能放松原因：

- 这是区分“真改进”与“多维一起动导致无法归因”的关键
- 如果一轮里同时改 `signal / extraction / weighting / guard`，结果再好也很难解释

当前执行含义：

- 每一轮确认性研究只允许一个 `changed_dimension(变更维度)`
- 失败后不能靠同轮追加多个补丁“救回来”

### 1.3 `fixed boolean success rule(固定布尔通过规则)`

不能放松原因：

- 没有固定布尔门槛，就会滑回“看完结果再改口径”
- 这正是 exploratory 和 confirmatory 的分水岭

当前执行含义：

- `annual_relative_return(年化超额收益)`、`relative_ir(相对信息比率)`、`max_drawdown(最大回撤)`、`avg_turnover_daily(平均日换手)` 等通过条件，必须在 prereg 里先写死

### 1.4 `walk-forward(滚动前推)` 仍是正式晋升门槛

不能放松原因：

- 单次 trainval 通过，不等于跨年份稳健
- `vsumd60` 已经说明：confirmatory 能过，不代表 `walk-forward` 就能达到主线晋级标准

当前执行含义：

- `walk-forward` 可以决定“是否继续投入”
- 但不能因为某张卡在 trainval 上不错，就跳过 `walk-forward` 直接晋升

### 1.5 `exploratory pool budget discipline(探索池预算约束)`

不能放松原因：

- 搜索空间一旦再次膨胀，多重比较风险会迅速吞掉结果可信度
- 前一阶段已经出现 `search-space explosion(搜索空间爆炸)`

当前执行含义：

- 不再恢复“大池子扫矿”
- 不再整包导入新的大因子池进入主线推进节奏

---

## 2. 可以提速的流程

这些地方可以更快，而且提速后**不会伤到治理有效性**。

### 2.1 从“大批量探索”改成“小批次 shortlist(短名单)”

建议：

- 每次只推进 `2-3` 只候选
- 先做 `confirmatory shortlist(确认性短名单)`，再决定是否进入下一层

这样提速的原因：

- 减少并行分叉
- 减少后续总结、归档、比对成本
- 更快形成“继续 / 停止”的硬结论

### 2.2 先做 atomic(原子信号) 判断，再做 family

建议：

- 新线优先验证 `standalone atomic keeper(单信号储备卡)` 是否具备 `head-extraction(头部提取)` 特征
- 不要一开始就跳到 family 微调

这样提速的原因：

- family 失败时，归因成本高
- atomic 层先收缩，可以显著减少无效 family 轮次

### 2.3 对失败路线尽早止损

建议：

- 一条线连续 `1-2` 轮确认性失败，就停止继续细磨
- 不再对同一对象无限追加 `guard / extraction / weighting` 小修小补

这样提速的原因：

- 防止时间被“几乎成功”的对象长期占用
- 让研究资源回到真正不同的问题定义上

### 2.4 把 `reserve atomic keeper(储备原子信号)` 和 `mainline candidate(主线候选)` 分层管理

建议：

- `reserve` 只保留证据，不自动进入下一轮
- 只有进 `confirmatory shortlist` 的对象，才算真正主线活跃候选

这样提速的原因：

- 降低活跃上下文负担
- 避免每次都把全部历史 keeper 重新带入决策

### 2.5 强化“先收口、再分叉”的节奏

建议：

- 每个小批次结束后，先出 `phase decision(阶段判断)`
- 明确：
  - 哪些进入下一轮
  - 哪些冻结为 `reserve`
  - 哪些正式关闭

这样提速的原因：

- 防止历史尾巴越拖越长
- 后续新轮次启动时，上下文更干净

---

## 3. 当前最适合的提速方式

结合项目现状，最优节奏应当是：

1. 保持 `trainval-only snapshot(仅训练+验证快照)` 作为研究默认口径
2. 保持确认性研究的 `single_dimension_only(单维改动)` 规则
3. 不再扩 exploratory 大池
4. 新主线一次只推进 `2-3` 个候选
5. 先做 confirmatory，再决定要不要进 family
6. `walk-forward` 作为“是否继续投入”的关键筛门，而不是最后才补

---

## 4. 结论

项目现在真正需要的，不是“放松治理”，而是**压缩问题规模、减少并行分叉、加快失败止损**。

因此：

- 不能放松的，是 `test-set isolation(测试集隔离)`、`single_dimension_only(单维改动)`、`fixed boolean gate(固定布尔门槛)`、`walk-forward(滚动前推)` 这些证据规则
- 可以提速的，是研究排程方式：少候选、少分叉、快收口、快止损

一句话收口：

**后续要做的是“更少、更硬、更快”，而不是“更松”。**
