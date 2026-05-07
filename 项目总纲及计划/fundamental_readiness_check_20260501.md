# Fundamental Signal Family — Readiness Check

**Date:** 2026-05-01
**Snapshot:** `warehouse_20260429_trainval_20211231`
**Status:** Design only, no registration yet.

---

## 1. Data Availability

| 数据 | 状态 | 说明 |
|---|---|---|
| `fina_indicator_pit.parquet` | ✅ **READY** | 23.2 MB, 26 列, 包含 ROE / gross_margin / eps 等核心字段 |
| `financial_statement_raw_pit.parquet` | ✅ **READY** | 187.7 MB, 321 列, 完整三大报表行项目 |
| `industry_membership_interval.parquet` | ✅ **READY** | L1-L3 行业代码, 含 `in_date`/`out_date` 可用于 PIT 行业归属 |
| Serving views for fundamental data | ❌ **NOT READY** | 数据以 parquet 形式存在，但**没有 serving 视图**（如 `vw_fina_indicator_pit`）|

### 覆盖范围
- fina_indicator：5,528 只股票，覆盖 100% 的 ranking_eligible 宇宙
- ROE 非空率：297,648 / 303,199 = 98.2%
- 季度频率：2010-2021 年共 72 个季度（足够覆盖训练+验证集）

---

## 2. PIT 口径

| 检查项 | 结果 |
|---|---|
| `pit_available_date` 存在 | ✅ 是 |
| `ann_date` 存在 | ✅ 是 |
| PIT 对齐规则可执行 | ✅ `pit_available_date <= signal_date` |
| 未来函数风险 | ✅ **可控**——已有 `pit_available_date` 字段作为 PIT 可见性标记 |
| 多对多 join 问题 | ⚠️ **需要处理**——直接 LEFT JOIN 会产生 23× 膨胀（每 stock-day 匹配多个 end_date 的记录）。需要使用窗口函数取"`pit_available_date <= signal_date` 且 `pit_available_date` 最大"的那一条 |

---

## 3. 项目链路兼容性

| 链路环节 | 状态 |
|---|---|
| `build_baseline_model_scores.py` | ❌ 需要新建 builder（或大幅扩展现有 builder）——现有 builder 只读 `serving.vw_bars_daily`，不读 fundamental parquet |
| `build_run_state_skeleton.py` | ✅ 无改动——只读 model_scores_D0.parquet |
| `build_portfolio_artifacts.py` | ✅ 无改动——已有 `--holding-cohort-count 5` |
| `build_fixed_test_minimal.py` | ✅ 无改动 |
| `build_confirmatory_validation_readout.py` | ✅ 无改动 |

**主要实现工作：新建 `build_fundamental_model_scores.py`**（或扩展现有 builder）。

---

## 4. 特征范围与限制

### ✅ READY NOW — 可直接用于新 round

| 特征 | 来源 | 说明 |
|---|---|---|
| `roe`（ROE） | `fina_indicator_pit` | 核心质量指标，覆盖率 98% |
| `gross_margin`（毛利率） | `fina_indicator_pit` | 盈利能力指标 |
| `eps`（每股收益） | `fina_indicator_pit` | 盈利指标 |
| `net_profit_margin`（净利润率） | `fina_indicator_pit` | 盈利质量 |

### ⚠️ PARTIAL — 数据存在但需额外接线

| 特征 | 说明 |
|---|---|
| 财务 PIT 最近值查询 | 需实现 `ROW_NUMBER()` 窗口函数取最近值逻辑 |
| 行业中性化 | `industry_membership_interval.parquet` 数据存在，但需在 builder 中实现中性化逻辑 |
| 市值对齐 | `serving.vw_bars_daily` 不含市值；市值数据需从 `vw_bars_daily` 的 `total_mv` 或 `circ_mv` 获取 |

### ❌ NOT READY — 当前不建议直接研究

| 特征 | 说明 |
|---|---|
| `financial_statement_raw_pit` 全量表 | 321 列，体量大，需先完成 fina_indicator 层的基本验证后再考虑 |
| value 因子（EP/BP/CFP） | 需要整合 price 和 fundamental 数据，属于后续阶段 |
| investment 因子 | 需要资产增长/投资类指标，在 fina_indicator 中不可直接获得 |

---

## 5. 注册建议

### ❌ NOT READY TO REGISTER YET

### 最小阻塞项（按优先级排列）

| 优先级 | 阻塞项 | 预估工作量 |
|---|---|---|
| **P0** | 缺少 serving 视图：需创建 `serving.vw_fina_indicator_pit` 或让 builder 直接读 parquet | 1 天 |
| **P0** | 缺少 fundamental score builder：需新建 `build_fundamental_model_scores.py` 或扩展现有 builder | 1-2 天 |
| **P1** | PIT 最近值 join 逻辑：多对多关系需用 `ROW_NUMBER()` 窗口函数取最近值 | 0.5 天 |
| **P1** | PIT 会计年度到 signal_date 的对齐规则需验证（quarterly report available date + 1 day lag） | 0.5 天 |
| **P2** | 行业中性化的实现 | 0.5 天 |
| **P2** | ROE 极端值处理（min=-19098, max=1719）——需扩展预处理合同但已在框架范围内 | 0.5 天 |

**总预估：3-5 天工程工作后方可注册。** 在此之前，该方向应停留在设计阶段，不可注册或开跑实验。
