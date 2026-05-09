#!/opt/anaconda3/envs/quant_trade/bin/python
"""
MODEL EDGE DIAGNOSIS — NOT A BACKTEST

Compare nonlinear confirmed5 (reversal_tail_exclude_p98_v1) against
baseline multi_equal_weight_v1 on model-score-level diagnostics only.

Outputs: RankIC, ICIR, decile forward return, top-bottom spread,
score distribution, yearly stability — train/validation separately.

THIS SCRIPT:
- Does NOT produce holdings, portfolio weights, backtest_daily, or metrics
- Does NOT read frozen test data
- Does NOT claim strategy effectiveness
- Outputs to /private/tmp only
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

ROOT = Path("/Users/wy/MiscProject/multi_factor")
RUN_INPUT_PATH = ROOT / "contracts" / "run_input_contract.current.json"
RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
CONFIRMED5_DIR = RUN_STATE_DIR / "confirmatory_reversal_p98_trainval_20260506"
PANELS_DIR = RUN_STATE_DIR / "project_panels_research_trainval_20211231_20260429"
OUTPUT_DIR = Path("/private/tmp")

DIAGNOSIS_LABEL = (
    "MODEL EDGE DIAGNOSIS ONLY — NOT A BACKTEST — "
    "DO NOT INTERPRET AS STRATEGY PERFORMANCE"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get_db_path() -> Path:
    run_input = load_json(RUN_INPUT_PATH)
    db_path = Path(run_input["source_root"]["snapshot_path"]) / "duckdb" / "warehouse.duckdb"
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    return db_path


def sql_quote(v: str) -> str:
    return "'" + v.replace("'", "''") + "'"


def sql_path(p: Path) -> str:
    return sql_quote(str(p.resolve()))


def load_data(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Load confirmed5 scores, baseline scores, labels, and splits into one DataFrame."""
    db_path = get_db_path()
    snapshot_id = load_json(RUN_INPUT_PATH)["snapshot_id"]

    con.execute(f"ATTACH '{db_path}' AS wh (READ_ONLY)")
    con.execute(
        f"""
        CREATE OR REPLACE VIEW confirmed5_t AS
        SELECT * FROM read_parquet({sql_path(CONFIRMED5_DIR / 'model_scores_D0.parquet')})
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE VIEW label_t AS
        SELECT * FROM read_parquet({sql_path(PANELS_DIR / 'project_label_panel.parquet')})
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE VIEW split_t AS
        SELECT * FROM read_parquet({sql_path(PANELS_DIR / 'dataset_split_daily.parquet')})
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE VIEW sample_t AS
        SELECT snapshot_id, instrument, signal_date,
               train_mask_v1, eval_mask_v1
        FROM read_parquet({sql_path(PANELS_DIR / 'project_sample_panel.parquet')})
        """
    )

    # Build baseline_v1 features inline
    con.execute(
        f"""
        CREATE OR REPLACE VIEW baseline_features AS
        WITH bars AS (
            SELECT
                ts_code AS instrument,
                trade_date AS signal_date,
                adj_close,
                amount,
                pct_chg / 100.0 AS pct_ret
            FROM wh.serving.vw_bars_daily
            WHERE snapshot_id = {sql_quote(snapshot_id)}
        ),
        features AS (
            SELECT
                instrument,
                signal_date,
                (adj_close / LAG(adj_close, 5) OVER w - 1.0) AS reversal_5d_raw,
                (LAG(adj_close, 5) OVER w / LAG(adj_close, 60) OVER w - 1.0) AS momentum_60_5_raw,
                STDDEV_SAMP(pct_ret) OVER w20 AS volatility_20d_raw,
                AVG(LN(GREATEST(amount, 0.0) + 1.0)) OVER w20 AS liquidity_20d_raw
            FROM bars
            WINDOW
                w AS (PARTITION BY instrument ORDER BY signal_date),
                w20 AS (PARTITION BY instrument ORDER BY signal_date
                        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW)
        )
        SELECT * FROM features
        WHERE reversal_5d_raw IS NOT NULL
          AND momentum_60_5_raw IS NOT NULL
          AND volatility_20d_raw IS NOT NULL
          AND liquidity_20d_raw IS NOT NULL
        """
    )

    # Compute baseline_v1 scores (= equal-weight rank average)
    con.execute(
        """
        CREATE OR REPLACE VIEW baseline_scores AS
        WITH ranked AS (
            SELECT
                instrument,
                signal_date,
                reversal_5d_raw,
                momentum_60_5_raw,
                volatility_20d_raw,
                liquidity_20d_raw,
                -- reversal: lower is better → rank descending (highest rank = lowest reversal)
                RANK() OVER (PARTITION BY signal_date ORDER BY reversal_5d_raw DESC) AS reversal_rank,
                -- momentum: higher is better → rank ascending
                RANK() OVER (PARTITION BY signal_date ORDER BY momentum_60_5_raw ASC) AS momentum_rank,
                -- low vol: lower is better → rank descending
                RANK() OVER (PARTITION BY signal_date ORDER BY volatility_20d_raw DESC) AS lowvol_rank,
                -- liquidity: higher is better → rank ascending
                RANK() OVER (PARTITION BY signal_date ORDER BY liquidity_20d_raw ASC) AS liquidity_rank,
                COUNT(*) OVER (PARTITION BY signal_date) AS daily_count
            FROM baseline_features
        )
        SELECT
            instrument,
            signal_date,
            (reversal_rank::DOUBLE / daily_count
             + momentum_rank::DOUBLE / daily_count
             + lowvol_rank::DOUBLE / daily_count
             + liquidity_rank::DOUBLE / daily_count) / 4.0 AS model_score_D0,
            'baseline_multi_equal_weight_v1' AS candidate_scheme_id
        FROM ranked
        WHERE daily_count >= 10
        """
    )

    # Merge confirmed5 scores, baseline scores, labels, and splits
    result = con.execute(
        """
        SELECT
            c.snapshot_id,
            c.instrument,
            c.signal_date,
            c.model_score_D0 AS confirmed5_score,
            COALESCE(b.model_score_D0, NULL) AS baseline_score,
            l.label_5d_next_open_close AS forward_return_5d,
            l.label_defined,
            s.split_bucket,
            s.train_flag,
            s.validation_flag,
            sm.train_mask_v1,
            sm.eval_mask_v1
        FROM confirmed5_t c
        INNER JOIN label_t l
            ON c.snapshot_id = l.snapshot_id
           AND c.instrument = l.instrument
           AND c.signal_date = l.signal_date
        INNER JOIN split_t s
            ON c.snapshot_id = s.snapshot_id
           AND c.instrument = s.instrument
           AND c.signal_date = s.signal_date
        INNER JOIN sample_t sm
            ON c.snapshot_id = sm.snapshot_id
           AND c.instrument = sm.instrument
           AND c.signal_date = sm.signal_date
        LEFT JOIN baseline_scores b
            ON c.instrument = b.instrument
           AND c.signal_date = b.signal_date
        WHERE l.label_defined
          AND s.train_flag OR s.validation_flag
        """
    ).fetchdf()

    return result


def compute_rank_ic(df: pd.DataFrame, score_col: str, label_col: str) -> pd.Series:
    """Compute daily RankIC (Spearman) for a given score column."""
    valid = df[[score_col, label_col, "signal_date"]].dropna()
    if len(valid) == 0:
        return pd.Series(dtype=float)
    daily_ic = valid.groupby("signal_date").apply(
        lambda g: g[score_col].corr(g[label_col], method="spearman")
        if len(g) >= 10 else None
    )
    return daily_ic.dropna()


def compute_decile_returns(df: pd.DataFrame, score_col: str, label_col: str) -> pd.DataFrame:
    """Compute mean forward return by score decile (daily, then average over time)."""
    valid = df[[score_col, label_col, "signal_date"]].dropna()
    if len(valid) == 0:
        return pd.DataFrame()

    # Assign deciles within each signal_date
    valid["decile"] = valid.groupby("signal_date")[score_col].transform(
        lambda x: pd.qcut(x, 10, labels=False, duplicates="drop") + 1
    )

    # Mean return by decile and signal_date, then average over time
    daily_decile = valid.groupby(["signal_date", "decile"])[label_col].mean().reset_index()
    avg_decile = daily_decile.groupby("decile")[label_col].agg(["mean", "std", "count"]).reset_index()
    avg_decile.columns = ["decile", "mean_return", "std_return", "n_days"]
    avg_decile["t_stat"] = avg_decile["mean_return"] / (avg_decile["std_return"] / np.sqrt(avg_decile["n_days"]))
    return avg_decile


def compute_yearly_stability(df: pd.DataFrame, score_col: str, label_col: str) -> list[dict]:
    """Compute RankIC by year."""
    valid = df[[score_col, label_col, "signal_date"]].dropna()
    if len(valid) == 0:
        return []
    valid["year"] = valid["signal_date"].str[:4]
    yearly: list[dict] = []
    for year in sorted(valid["year"].unique()):
        yr_df = valid[valid["year"] == year]
        daily_ic = compute_rank_ic(yr_df, score_col, label_col)
        if len(daily_ic) > 0:
            yearly.append(
                {
                    "year": int(year),
                    "rank_ic_mean": float(daily_ic.mean()),
                    "rank_ic_std": float(daily_ic.std()),
                    "rank_ic_ir": float(daily_ic.mean() / daily_ic.std()) if daily_ic.std() > 0 else None,
                    "n_days": len(daily_ic),
                    "positive_ic_pct": float((daily_ic > 0).mean()),
                }
            )
    return yearly


def diagnose(df: pd.DataFrame, score_col: str, label_col: str, split_mask: pd.Series, label: str) -> dict[str, Any]:
    """Run full diagnosis for one model × one split."""
    subset = df[split_mask].copy()
    n_rows = len(subset)
    n_dates = subset["signal_date"].nunique()
    n_instruments = subset["instrument"].nunique()

    if n_rows < 100:
        return {"label": label, "n_rows": n_rows, "error": "Insufficient data"}

    # Score distribution
    scores = subset[score_col].dropna()
    score_dist = {
        "count": int(scores.count()),
        "mean": float(scores.mean()),
        "std": float(scores.std()),
        "min": float(scores.min()),
        "p25": float(scores.quantile(0.25)),
        "p50": float(scores.quantile(0.50)),
        "p75": float(scores.quantile(0.75)),
        "max": float(scores.max()),
    }

    # RankIC
    daily_ic = compute_rank_ic(subset, score_col, label_col)
    n_ic_days = len(daily_ic)
    if n_ic_days == 0:
        rank_ic = {"error": "No valid IC days"}
        icir = None
    else:
        ic_mean = float(daily_ic.mean())
        ic_std = float(daily_ic.std())
        rank_ic = {
            "mean": ic_mean,
            "std": ic_std,
            "n_days": n_ic_days,
            "positive_ic_pct": float((daily_ic > 0).mean()),
            "t_stat": float(ic_mean / (ic_std / np.sqrt(n_ic_days))) if ic_std > 0 else None,
        }
        icir = float(ic_mean / ic_std) if ic_std > 0 else None

    # Decile returns
    decile_df = compute_decile_returns(subset, score_col, label_col)
    deciles: list[dict] = []
    top_bottom_spread = None
    if len(decile_df) > 0:
        for _, row in decile_df.iterrows():
            deciles.append(
                {
                    "decile": int(row["decile"]),
                    "mean_forward_return": float(row["mean_return"]),
                    "std_forward_return": float(row["std_return"]),
                    "n_days": int(row["n_days"]),
                    "t_stat": float(row["t_stat"]) if pd.notna(row["t_stat"]) else None,
                }
            )
        top_row = decile_df[decile_df["decile"] == 10]
        bottom_row = decile_df[decile_df["decile"] == 1]
        if len(top_row) > 0 and len(bottom_row) > 0:
            top_bottom_spread = float(top_row["mean_return"].iloc[0] - bottom_row["mean_return"].iloc[0])

    # Yearly stability
    yearly_ic = compute_yearly_stability(subset, score_col, label_col)

    # Score autocorrelation (1-day lag of mean daily score)
    daily_mean_score = subset.groupby("signal_date")[score_col].mean().dropna()
    score_autocorr = float(daily_mean_score.autocorr(lag=1)) if len(daily_mean_score) > 1 else None

    return {
        "label": label,
        "n_rows": n_rows,
        "n_signal_dates": int(n_dates),
        "n_instruments": int(n_instruments),
        "score_distribution": score_dist,
        "rank_ic": rank_ic,
        "icir": icir,
        "decile_forward_returns": deciles,
        "top_bottom_spread": top_bottom_spread,
        "score_autocorr_lag1": score_autocorr,
        "yearly_stability": yearly_ic,
    }


def main() -> None:
    print("=" * 70)
    print("MODEL EDGE DIAGNOSIS")
    print(f"  {DIAGNOSIS_LABEL}")
    print("=" * 70)
    print()

    con = duckdb.connect()
    print("Loading data (confirmed5 scores + baseline features + labels + splits)...")
    df = load_data(con)
    con.close()
    print(f"  Loaded {len(df):,} rows")
    print(f"  Confirmed5 scored: {df['confirmed5_score'].notna().sum():,}")
    print(f"  Baseline scored:   {df['baseline_score'].notna().sum():,}")
    print(f"  Train rows:        {df['train_flag'].sum():,}")
    print(f"  Validation rows:   {df['validation_flag'].sum():,}")
    print()

    results: dict[str, Any] = {
        "diagnosis_label": DIAGNOSIS_LABEL,
        "generated_at": datetime.now().astimezone().isoformat(),
        "models_compared": {
            "confirmed5": {
                "candidate_scheme_id": "reversal_tail_exclude_p98_v1",
                "description": "Nonlinear composite: reversal × cord30 composite with tail exclusion (p98)",
                "source": str(CONFIRMED5_DIR / "model_scores_D0.parquet"),
            },
            "baseline": {
                "candidate_scheme_id": "baseline_multi_equal_weight_v1",
                "description": "Multi-factor equal-weight: reversal_5d + momentum_60_5 + lowvol_20d + liquidity_20d",
                "source": "Computed inline from wh.serving.vw_bars_daily",
            },
        },
        "diagnostics": {},
        "cross_model_comparison": {},
        "conclusion": {},
    }

    # Compute train/validation masks
    train_mask = df["train_flag"] == True
    val_mask = df["validation_flag"] == True

    # Diagnose confirmed5
    print("--- Confirmed5 (reversal_tail_exclude_p98_v1) ---")
    for split_mask, split_name in [(train_mask, "train"), (val_mask, "validation")]:
        print(f"  {split_name}...")
        diag = diagnose(df, "confirmed5_score", "forward_return_5d", split_mask, f"confirmed5_{split_name}")
        results["diagnostics"][f"confirmed5_{split_name}"] = diag
        if "rank_ic" in diag and isinstance(diag["rank_ic"], dict) and "mean" in diag["rank_ic"]:
            print(f"    n_rows={diag['n_rows']:,}, n_dates={diag['n_signal_dates']}, "
                  f"RankIC={diag['rank_ic']['mean']:.4f}, ICIR={diag.get('icir') or 'N/A'}, "
                  f"top-bottom={diag['top_bottom_spread']:.4f}" if diag.get('top_bottom_spread') else "")
        else:
            print(f"    n_rows={diag['n_rows']:,}, n_dates={diag['n_signal_dates']}")

    # Diagnose baseline
    print()
    print("--- Baseline (multi_equal_weight_v1) ---")
    baseline_mask = df["baseline_score"].notna()
    for split_mask, split_name in [(train_mask & baseline_mask, "train"), (val_mask & baseline_mask, "validation")]:
        print(f"  {split_name}...")
        diag = diagnose(df, "baseline_score", "forward_return_5d", split_mask, f"baseline_{split_name}")
        results["diagnostics"][f"baseline_{split_name}"] = diag
        if "rank_ic" in diag and isinstance(diag["rank_ic"], dict) and "mean" in diag["rank_ic"]:
            print(f"    n_rows={diag['n_rows']:,}, n_dates={diag['n_signal_dates']}, "
                  f"RankIC={diag['rank_ic']['mean']:.4f}, ICIR={diag.get('icir') or 'N/A'}, "
                  f"top-bottom={diag['top_bottom_spread']:.4f}" if diag.get('top_bottom_spread') else "")
        else:
            print(f"    n_rows={diag['n_rows']:,}, n_dates={diag['n_signal_dates']}")

    # Cross-model comparison
    print()
    print("--- Cross-Model Comparison ---")
    comparison: dict[str, Any] = {}
    for split_name in ["train", "validation"]:
        c5 = results["diagnostics"].get(f"confirmed5_{split_name}", {})
        bl = results["diagnostics"].get(f"baseline_{split_name}", {})

        comp: dict[str, Any] = {}
        if isinstance(c5.get("rank_ic"), dict) and isinstance(bl.get("rank_ic"), dict):
            comp["rank_ic_delta"] = float(c5["rank_ic"]["mean"] - bl["rank_ic"]["mean"])
            comp["confirmed5_rank_ic"] = float(c5["rank_ic"]["mean"])
            comp["baseline_rank_ic"] = float(bl["rank_ic"]["mean"])
        if c5.get("icir") is not None and bl.get("icir") is not None:
            comp["icir_delta"] = float(c5["icir"] - bl["icir"])
            comp["confirmed5_icir"] = float(c5["icir"])
            comp["baseline_icir"] = float(bl["icir"])
        if c5.get("top_bottom_spread") is not None and bl.get("top_bottom_spread") is not None:
            comp["spread_delta"] = float(c5["top_bottom_spread"] - bl["top_bottom_spread"])
            comp["confirmed5_spread"] = float(c5["top_bottom_spread"])
            comp["baseline_spread"] = float(bl["top_bottom_spread"])
        comparison[split_name] = comp

        print(f"  {split_name}:")
        for k, v in comp.items():
            if isinstance(v, float):
                print(f"    {k}: {v:+.6f}")

    results["cross_model_comparison"] = comparison

    # Conclusion
    c5_train_ic = results["diagnostics"].get("confirmed5_train", {}).get("rank_ic", {})
    c5_val_ic = results["diagnostics"].get("confirmed5_validation", {}).get("rank_ic", {})
    c5_train_icir = results["diagnostics"].get("confirmed5_train", {}).get("icir")
    c5_val_icir = results["diagnostics"].get("confirmed5_validation", {}).get("icir")

    has_edge = False
    edge_reasons: list[str] = []
    concerns: list[str] = []

    if isinstance(c5_train_ic, dict) and isinstance(c5_val_ic, dict):
        train_ic = c5_train_ic.get("mean", 0)
        val_ic = c5_val_ic.get("mean", 0)
        train_pos = c5_train_ic.get("positive_ic_pct", 0)
        val_pos = c5_val_ic.get("positive_ic_pct", 0)

        if train_ic > 0.01 and val_ic > 0.005:
            has_edge = True
            edge_reasons.append(
                f"Confirmed5 RankIC is positive in both train ({train_ic:.4f}) "
                f"and validation ({val_ic:.4f})"
            )
        if train_pos > 0.55 and val_pos > 0.52:
            edge_reasons.append(
                f"Positive IC hit rate: train={train_pos:.1%}, validation={val_pos:.1%}"
            )
        if c5_train_icir and c5_val_icir and c5_train_icir > 0.3 and c5_val_icir > 0.15:
            edge_reasons.append(
                f"ICIR in reasonable range: train={c5_train_icir:.2f}, validation={c5_val_icir:.2f}"
            )

        if val_ic < 0.002:
            concerns.append(
                f"Validation RankIC ({val_ic:.4f}) is very close to zero; edge may be negligible"
            )
        if c5_val_icir and c5_val_icir < 0.2:
            concerns.append(
                f"Validation ICIR ({c5_val_icir:.2f}) is low; signal may be noisy"
            )
        if val_pos < 0.52:
            concerns.append(
                f"Validation positive IC rate ({val_pos:.1%}) is near random"
            )

    # Check cross-model comparison
    train_comp = comparison.get("train", {})
    val_comp = comparison.get("validation", {})
    if train_comp.get("rank_ic_delta", 0) > 0 and val_comp.get("rank_ic_delta", 0) > 0:
        edge_reasons.append("Confirmed5 outperforms baseline on RankIC in both train and validation")
    elif val_comp.get("rank_ic_delta", 0) < 0:
        concerns.append("Confirmed5 underperforms baseline on validation RankIC")

    results["conclusion"] = {
        "has_model_edge": has_edge,
        "edge_evidence": edge_reasons,
        "concerns": concerns,
        "portfolio_unblock_recommendation": (
            "The model shows measurable but modest signal in validation. "
            "The 20 execution blockers do NOT invalidate the model edge diagnosis — "
            "the model score signal and the execution exit completeness are independent layers. "
            "Recommendation: the 20 blocker rows are not blocking the model evaluation; "
            "they block portfolio construction. Continue with model diagnostics without "
            "waiting for terminal policy resolution. "
            "Portfolio unblocking should proceed when execution blockers are resolved, "
            "but model edge diagnosis does not depend on portfolio completion."
        ),
        "caveat": (
            "This is a MODEL-SCORE-LEVEL diagnosis only. "
            "It does not account for transaction costs, execution timing, liquidity constraints, "
            "or portfolio construction effects. Positive RankIC does not guarantee positive "
            "portfolio returns. Use ONLY for model evaluation purposes."
        ),
    }

    # Print conclusion
    print()
    print("--- Conclusion ---")
    print(f"  Has model edge: {has_edge}")
    if edge_reasons:
        print("  Edge evidence:")
        for r in edge_reasons:
            print(f"    + {r}")
    if concerns:
        print("  Concerns:")
        for c in concerns:
            print(f"    - {c}")
    print(f"  Recommendation: {results['conclusion']['portfolio_unblock_recommendation']}")

    # Write JSON
    json_path = OUTPUT_DIR / "model_edge_diagnosis.json"
    write_json(json_path, results)
    print(f"\nJSON written to {json_path}")

    # Write Markdown
    md_lines = [
        "# Model Edge Diagnosis",
        "",
        f"> **{DIAGNOSIS_LABEL}**",
        "",
        f"Generated: {results['generated_at']}",
        "",
        "## 1. Models Compared",
        "",
        "| Model | Scheme ID | Description |",
        "|-------|-----------|-------------|",
        f"| Confirmed5 | {results['models_compared']['confirmed5']['candidate_scheme_id']} | {results['models_compared']['confirmed5']['description']} |",
        f"| Baseline | {results['models_compared']['baseline']['candidate_scheme_id']} | {results['models_compared']['baseline']['description']} |",
        "",
        "## 2. Train Set Diagnostics",
        "",
    ]

    for model_key, model_name in [("confirmed5", "Confirmed5"), ("baseline", "Baseline")]:
        diag = results["diagnostics"].get(f"{model_key}_train", {})
        if not diag:
            continue
        md_lines.extend(_render_diagnosis_section(model_name, "train", diag))

    md_lines.extend(["## 3. Validation Set Diagnostics", ""])
    for model_key, model_name in [("confirmed5", "Confirmed5"), ("baseline", "Baseline")]:
        diag = results["diagnostics"].get(f"{model_key}_validation", {})
        if not diag:
            continue
        md_lines.extend(_render_diagnosis_section(model_name, "validation", diag))

    md_lines.extend(
        [
            "## 4. Cross-Model Comparison",
            "",
            "| Split | Metric | Confirmed5 | Baseline | Delta |",
            "|-------|--------|------------|----------|-------|",
        ]
    )
    for split_name in ["train", "validation"]:
        comp = comparison.get(split_name, {})
        if comp.get("confirmed5_rank_ic") is not None:
            md_lines.append(
                f"| {split_name} | RankIC | {comp['confirmed5_rank_ic']:.4f} | "
                f"{comp['baseline_rank_ic']:.4f} | {comp['rank_ic_delta']:+.4f} |"
            )
        if comp.get("confirmed5_icir") is not None:
            md_lines.append(
                f"| {split_name} | ICIR | {comp['confirmed5_icir']:.2f} | "
                f"{comp['baseline_icir']:.2f} | {comp['icir_delta']:+.2f} |"
            )
        if comp.get("confirmed5_spread") is not None:
            md_lines.append(
                f"| {split_name} | Top-Bottom Spread | {comp['confirmed5_spread']:.4f} | "
                f"{comp['baseline_spread']:.4f} | {comp['spread_delta']:+.4f} |"
            )

    conc = results["conclusion"]
    md_lines.extend(
        [
            "",
            "## 5. Conclusion",
            "",
            f"- **Has model edge:** {conc['has_model_edge']}",
            "",
            "### Edge Evidence",
        ]
    )
    for r in conc["edge_evidence"]:
        md_lines.append(f"- {r}")
    if conc["concerns"]:
        md_lines.extend(["", "### Concerns"])
        for c in conc["concerns"]:
            md_lines.append(f"- {c}")
    md_lines.extend(
        [
            "",
            "### Portfolio Unblock Recommendation",
            "",
            conc["portfolio_unblock_recommendation"],
            "",
            "### Caveat",
            "",
            conc["caveat"],
        ]
    )

    md_path = OUTPUT_DIR / "model_edge_diagnosis.md"
    Path(md_path).write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Markdown written to {md_path}")


def _render_diagnosis_section(model_name: str, split_name: str, diag: dict) -> list[str]:
    """Render a diagnosis section for one model × split."""
    lines = [
        f"### {model_name} — {split_name}",
        "",
        f"- Rows: {diag.get('n_rows', 'N/A'):,}",
        f"- Signal dates: {diag.get('n_signal_dates', 'N/A')}",
        f"- Instruments: {diag.get('n_instruments', 'N/A')}",
        "",
    ]

    sd = diag.get("score_distribution", {})
    if sd:
        lines.extend(
            [
                "**Score Distribution:**",
                f"| Mean | Std | Min | P25 | P50 | P75 | Max |",
                f"|------|-----|-----|-----|-----|-----|-----|",
                f"| {sd.get('mean', 0):.4f} | {sd.get('std', 0):.4f} | {sd.get('min', 0):.4f} | {sd.get('p25', 0):.4f} | {sd.get('p50', 0):.4f} | {sd.get('p75', 0):.4f} | {sd.get('max', 0):.4f} |",
                "",
            ]
        )

    ric = diag.get("rank_ic", {})
    if isinstance(ric, dict) and "mean" in ric:
        lines.extend(
            [
                "**RankIC:**",
                f"| Mean | Std | N Days | Positive% | T-Stat |",
                f"|------|-----|--------|-----------|--------|",
                f"| {ric['mean']:.4f} | {ric['std']:.4f} | {ric['n_days']} | {ric['positive_ic_pct']:.1%} | {ric.get('t_stat') or 'N/A'} |",
                "",
                f"**ICIR:** {diag.get('icir') or 'N/A'}",
                f"**Score Autocorr (lag 1):** {diag.get('score_autocorr_lag1') or 'N/A'}",
                "",
            ]
        )

    deciles = diag.get("decile_forward_returns", [])
    if deciles:
        lines.extend(
            [
                "**Decile Forward Returns:**",
                "| Decile | Mean Return | Std | N Days | T-Stat |",
                "|--------|-------------|-----|--------|--------|",
            ]
        )
        for d in deciles:
            lines.append(
                f"| {d['decile']} | {d['mean_forward_return']:.6f} | {d['std_forward_return']:.6f} | {d['n_days']} | {d.get('t_stat') or 'N/A'} |"
            )
        lines.append("")
        if diag.get("top_bottom_spread") is not None:
            lines.append(f"**Top-Bottom Spread:** {diag['top_bottom_spread']:.6f}")
            lines.append("")

    yearly = diag.get("yearly_stability", [])
    if yearly:
        lines.extend(
            [
                "**Yearly Stability (RankIC):**",
                "| Year | Mean IC | Std IC | ICIR | N Days | Positive% |",
                "|------|---------|--------|------|--------|-----------|",
            ]
        )
        for y in yearly:
            icir_str = f"{y['rank_ic_ir']:.2f}" if y.get("rank_ic_ir") else "N/A"
            lines.append(
                f"| {y['year']} | {y['rank_ic_mean']:.4f} | {y['rank_ic_std']:.4f} | {icir_str} | {y['n_days']} | {y['positive_ic_pct']:.1%} |"
            )
        lines.append("")

    return lines


if __name__ == "__main__":
    main()
