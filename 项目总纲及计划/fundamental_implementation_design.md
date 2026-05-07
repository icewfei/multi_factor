# Fundamental Signal Family — Implementation Design

**Status:** Design only, no code changes yet.

---

## 1. Current State Assessment

### 已有先例

`build_quality_profitability_model_scores.py` 已存在，且具备以下 ready 能力：
- 直接读取 `fina_indicator_pit.parquet`（**不依赖 serving view**）
- 使用 **DuckDB `ASOF LEFT JOIN`** 做 PIT join（`signal_date >= pit_available_date`，**无多对多膨胀**）
- 生成与 `build_baseline_model_scores.py` 相同格式的 `model_scores_D0.parquet`（**下游链路兼容**）
- 已有的 feature set：`roe_dt`, `roa_yearly`, `q_roe`, `q_dt_roe`

### 为什么不能直接用于当前主线

| 问题 | 说明 |
|---|---|
| 合同不匹配 | 硬编码 `run_input_contract.current.json`，不支持 `--run-input-contract` 参数 |
| 缺少 `--feature-preset` | 不支持多候选，需要硬编码 feature_set |
| 缺少 `ensure_registered_candidate` 与运行时 round 一致性检查 | 不拦截未注册的候选 |
| 未接入本轮 contract-matched baseline 比较 | 无 `baseline_reference` 字段输出 |

---

## 2. PIT Join 设计（单一方案：维持 ASOF LEFT JOIN）

### 当前已有实现（已在 builder 中）

```sql
CREATE OR REPLACE VIEW feature_frame AS
SELECT p.*, f.*
FROM project_sample_panel p
ASOF LEFT JOIN pit_source f
  ON p.instrument = f.instrument
 AND p.signal_date >= f.pit_available_date
```

### 为什么这是最稳方案

DuckDB 的 `ASOF LEFT JOIN` 语义：对于每个 `(instrument, signal_date)`，取 `pit_available_date <= signal_date` 且 `pit_available_date` 最大的那一条 PIT 记录。

- **无多对多膨胀** ← 这是直接 `LEFT JOIN` 不能替代的
- **无未来函数风险** ← `pit_available_date <= signal_date` 确保只使用当时可见数据
- **与总纲 5.4 一致** ← `pit_available_date` 已在 ETL 层计算好
- **已在先例 builder 中验证过** ← 非新设计

### Audit 字段保留

feature_frame 输出中包含以下字段，可直接传入 model_scores_D0.parquet：
- `ann_date`：公告日
- `end_date`：财报截止日
- `pit_available_date`：PIT 可见日（≥ ann_date 的下一个交易日）

---

## 3. Builder 架构方案

### 方案对比

| 维度 | A：扩展现有 quality/profitability builder | B：新建当前主线兼容的 builder |
|---|---|---|
| 改动面 | 扩展 ~50 行（加参数 + round 校验 + preset） | 新建 ~250 行 |
| 复用性 | 直接沿用已验证的 ASOF JOIN + feature 定义 | 可以更现代化但重复已有逻辑 |
| 旧 round 影响 | **无**——不修改现有 feature_set | 无——新文件 |
| 推荐 | ✅ **推荐** | ❌ |
| 理由 | 已有逻辑已验证（ASOF JOIN、feature 定义、输出格式），最小改动即可接入当前主线 |

### 推荐方案 A 的具体改动

**只改 1 个文件：`build_quality_profitability_model_scores.py`**

| 改动 | 说明 |
|---|---|
| 添加 `--run-input-contract` 参数 | 与 build_baseline_model_scores.py 一致 |
| 添加 `--feature-preset` 参数 | 支持多候选（单信号 / 组合）|
| 添加 `--research-round-id` 参数 | 支持 round 校验 |
| 添加 `ensure_registered_candidate()` | 防止未注册即运行 |
| 添加 `FEATURE_PRESETS` dict | 与 build_baseline_model_scores.py 一致 |
| 添加 audit_counts 输出 | 与 build_baseline_model_scores.py 一致 |
| 将 `run_input_contract.current.json` 替换为参数 | 读取指定 contract |

**不改的文件：**
- `build_run_state_skeleton.py` — 兼容（读 model_scores_D0.parquet）
- `build_portfolio_artifacts.py` — 兼容（已有 --holding-cohort-count 5）
- `build_fixed_test_minimal.py` — 兼容
- `build_confirmatory_validation_readout.py` — 兼容
- `build_baseline_model_scores.py` — 不碰（这是独立的 fundamental builder）

**不对旧 round 造成影响：** 旧 quality/profitability round 使用该 builder 硬编码的 v12 feature_set，改动不触及现有逻辑。

---

## 4. 接入边界

### 直接 snapshot-parquet builder 更稳

**推荐：不改 serving view，直接从 snapshot parquet 做只读 builder。**

理由：
1. **已有成功先例**——现有 `build_quality_profitability_model_scores.py` 就是直接读 `fina_indicator_pit.parquet`，已在上轮质量/盈利因子探索中验证过
2. **不污染共享基础层**——serving view 属于共享仓库（parquet_duckdb），`multi_factor` 项目的 builder 只读共享仓库而不写，符合总纲 5.1A
3. **减少一层依赖**——不依赖于 serving view 的创建/维护/版本管理

### 必须改的文件

| 文件 | 说明 |
|---|---|
| `build_quality_profitability_model_scores.py` | 见方案 A 改动列表 |

### 不该改的文件

| 文件 | 理由 |
|---|---|
| `run_input_contract.research_trainval_20211231.json` | 已有正确的 source_root，builder 直接读 |
| `build_run_state_skeleton.py` | 无改动需要 |
| `build_portfolio_artifacts.py` | 无改动需要 |
| `build_fixed_test_minimal.py` | 无改动需要 |
| `build_confirmatory_validation_readout.py` | 无改动需要 |
| `build_baseline_model_scores.py` | 无改动需要（这是 price-volume builder） |

---

## 5. 注册前最小完成条件

### Checklist

| # | 条件 | 预计改动量 |
|---|---|---|
| 1 | `build_quality_profitability_model_scores.py` 添加 `--run-input-contract` 参数 | ~10 行 |
| 2 | 添加 `--feature-preset` 参数 + `FEATURE_PRESETS`（至少 2 个：single_quality, quality_combo） | ~20 行 |
| 3 | 添加 `--research-round-id` + `ensure_registered_candidate()` | ~10 行 |
| 4 | 替换硬编码 `run_input_contract.current.json` 为参数读取 | ~5 行 |
| 5 | 添加 audit_counts 输出（feature coverage） | ~15 行 |
| **合计** | | **~60 行，1 个文件** |
| **完成后** | = ready to register | |

### 不需要做（推迟到后续 round）

- 行业中性化（P1，可以等 c1 有正向结果后再加）
- 市值对齐（P1，同左）
- serving view 创建（不需要，直接用 snapshot-parquet）
- `financial_statement_raw_pit` 全量表接入（P2，后续阶段）
- multiple-end_date PIT 对齐审计（P2，ASOF JOIN 已保证正确，审计字段已保留）
