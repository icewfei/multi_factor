#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Composability screen: test a new orthogonal 5-signal family against the frozen v18 reference.

Candidate family (v19-style):
  1. alpha158_corr20 —— 量价滚动相关性 (IC=0.0185, highest IC signal, correlation family)
  2. intraday_trend_bias_20d —— 日内趋势 (IC=0.0147, intraday bias, kept from v18)
  3. alpha158_vsumd60 —— 量能路径净差 (IC=0.0140, volume path, orthogonal)
  4. momentum_60_5 —— 中期动量 (IC=0.0098, momentum, kept from v18)
  5. lower_shadow_support_20d —— K线下跌支撑 (IC=0.0062, kline, most orthogonal)

Reference: v18 (beta_20d + intraday_trend_bias_20d + liquidity_trend_20_60 + momentum_60_5 + upside_range_share_20d)

Output: composability diagnosis JSON + MD
"""

from __future__ import annotations

import json, re, os, sys
from datetime import datetime
from pathlib import Path
import duckdb

ROOT = Path("/Users/wy/MiscProject/multi_factor")
SCRIPTS = ROOT / "scripts"
REGISTRY = ROOT / "artifacts" / "research_registry"
CONTRACTS = ROOT / "contracts"
RUN_STATE = ROOT / "artifacts" / "run_state"
ROUND_DIR = REGISTRY / "research_rounds"
FIXED_TEST_DIR = ROOT / "artifacts" / "fixed_test"

sys.path.insert(0, str(SCRIPTS))
from alpha158_canonical_common import build_feature_views, load_manifest, FEATURE_META, sql_quote

# ── Round config ──
ROUND_ID = "rr_composability_screen_orthogonal_family_v19_test_20260430"
AS_OF_DATE = "20260430"
CONTRACT_PATH = CONTRACTS / "run_input_contract.research_trainval_20211231.json"

REFERENCE_CANDIDATE_ID = "price_volume_v18_refresh_hysteresis"
REFERENCE_RUN_ID = "confirmatory_reference_v18_trainval_20260429"

SCREEN_CANDIDATE_ID = "composability_screen_orthogonal_family_v19_v1"
RUN_ID = "screendiag_orthogonal_family_v19_20260430"

# Candidate signals (5 orthogonal signals)
CANDIDATE_FEATURES = [
    {"qlib": "CORR20", "field": "alpha158_corr20_raw", "kind": "alpha158"},
    {"qlib": "VSUMD60", "field": "alpha158_vsumd60_raw", "kind": "alpha158"},
    {"qlib": None, "field": "intraday_trend_bias_20d", "kind": "project"},
    {"qlib": None, "field": "momentum_60_5", "kind": "project"},
    {"qlib": None, "field": "lower_shadow_support_20d", "kind": "project"},
]

# v18 reference signals (5 signals)
REFERENCE_FEATURES = [
    {"qlib": None, "field": "pv_beta_20d", "kind": "project"},
    {"qlib": None, "field": "intraday_trend_bias_20d", "kind": "project"},
    {"qlib": None, "field": "liq_trend_20_60", "kind": "project"},
    {"qlib": None, "field": "momentum_60_5", "kind": "project"},
    {"qlib": None, "field": "upside_range_share_20d", "kind": "project"},
]

OVERLAP_TOLERANCE = 0.2  # Max acceptable drop in day-over-day Top10 overlap


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sql_path(path: Path) -> str:
    return sql_quote(path.resolve().as_posix())


def fmt(v: float | None, d: int = 6) -> str:
    if v is None: return "null"
    return f"{v:.{d}f}"


def fmt_pct(v: float | None) -> str:
    if v is None: return "null"
    return f"{v*100:.4f}%"


def main() -> None:
    round_dir = ROUND_DIR / ROUND_ID
    round_dir.mkdir(parents=True, exist_ok=True)

    contract = load_json(CONTRACT_PATH)
    snapshot_id = contract["snapshot_id"]
    source_db = Path(contract["source_root"]["snapshot_path"]) / "duckdb" / "warehouse.duckdb"
    assert source_db.exists(), f"DB not found: {source_db}"

    # Use same sample panel as reference
    reference_dir = RUN_STATE / REFERENCE_RUN_ID
    sample_panel = reference_dir / "project_sample_panel.parquet"
    label_panel = reference_dir / "project_label_panel.parquet"
    reference_scores = reference_dir / "model_scores_D0.parquet"
    assert sample_panel.exists() and label_panel.exists() and reference_scores.exists()

    con = duckdb.connect()
    snq = sql_quote(snapshot_id)

    try:
        # ── Build candidate alpha158 features ──
        alpha158_names = [f["qlib"] for f in CANDIDATE_FEATURES if f["kind"] == "alpha158"]
        manifest = load_manifest()
        catalog = {f["qlib_feature_name"]: f for f in manifest["feature_catalog"]}
        enriched = [{**catalog[n], **FEATURE_META[n]} for n in alpha158_names]

        build_feature_views(
            con=con, sample_panel=sample_panel, source_db_path=source_db,
            snapshot_id=snapshot_id, feature_batch=enriched,
        )

        # ── Reference v18 scores ──
        con.execute(f"""
            CREATE OR REPLACE VIEW reference_scores_t AS
            SELECT * FROM read_parquet({sql_path(reference_scores)})
        """)

        con.execute(f"""
            CREATE OR REPLACE VIEW label_panel_t AS
            SELECT * FROM read_parquet({sql_path(label_panel)})
        """)

        # ── Build v18 family signals + candidate project signals in one pass ──
        print("Building reference + candidate features...")
        con.execute(f"""
            CREATE OR REPLACE VIEW all_features_t AS
            WITH bars AS (
                SELECT ts_code AS instrument, trade_date AS signal_date,
                    adj_open, adj_high, adj_low, adj_close, amount, pct_chg
                FROM warehouse_db.serving.vw_bars_daily
                WHERE snapshot_id = {snq}
            ),
            e1 AS (
                SELECT *, LN(GREATEST(amount,0)+1) AS log_amount, pct_chg/100.0 AS ret
                FROM bars
            ),
            rolling AS (
                SELECT *,
                    AVG(log_amount) OVER w20 AS avg_la20,
                    AVG(log_amount) OVER w60 AS avg_la60,
                    STDDEV_SAMP(ret) OVER w20 AS std_ret20,
                    LAG(adj_close,5) OVER w AS ac5b, LAG(adj_close,60) OVER w AS ac60b
                FROM e1
                WINDOW w AS (PARTITION BY instrument ORDER BY signal_date),
                    w20 AS (PARTITION BY instrument ORDER BY signal_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW),
                    w60 AS (PARTITION BY instrument ORDER BY signal_date ROWS BETWEEN 59 PRECEDING AND CURRENT ROW)
            ),
            e2 AS (
                SELECT *,
                    log_amount - LAG(log_amount,1) OVER w AS dlog_amount,
                    CASE WHEN pct_chg>0 AND adj_close>1e-12 THEN (adj_high-adj_low)/adj_close ELSE 0.0 END AS up_range
                FROM rolling WINDOW w AS (PARTITION BY instrument ORDER BY signal_date)
            ),
            daily AS (
                SELECT *,
                    CASE WHEN pct_chg<0 AND adj_high-adj_low+1e-12>0 THEN (adj_close-adj_low)/(adj_high-adj_low) ELSE NULL END AS ls_daily,
                    CASE WHEN adj_open>1e-12 THEN (adj_close-adj_open)/adj_open ELSE NULL END AS trend_daily,
                    CASE WHEN adj_close>1e-12 THEN (adj_high-adj_low)/adj_close ELSE 0.0 END AS range_pct
                FROM e2
            )
            SELECT instrument, signal_date,
                -- v18 signals
                CASE WHEN std_ret20>1e-12 AND STDDEV_SAMP(dlog_amount) OVER w20>1e-12
                    THEN COVAR_SAMP(ret,dlog_amount) OVER w20/NULLIF(VAR_SAMP(dlog_amount) OVER w20,0) ELSE NULL END AS pv_beta_20d,
                AVG(trend_daily) OVER w20 AS intraday_trend_bias_20d,
                avg_la20 - avg_la60 AS liq_trend_20_60,
                ac5b/NULLIF(ac60b,0)-1.0 AS momentum_60_5,
                CASE WHEN SUM(range_pct) OVER w20>1e-12
                    THEN SUM(up_range) OVER w20/SUM(range_pct) OVER w20 ELSE NULL END AS upside_range_share_20d,
                -- candidate project signals
                AVG(ls_daily) OVER w20 AS lower_shadow_support_20d
            FROM daily
            WINDOW w20 AS (PARTITION BY instrument ORDER BY signal_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW)
        """)

        # ── Build screen frame ──
        print("Building screen frame...")
        con.execute(f"""
            CREATE OR REPLACE VIEW screen_frame_t AS
            SELECT
                p.snapshot_id, p.instrument, p.signal_date, p.ranking_eligible_D0,
                l.label_5d_next_open_close, l.label_defined,
                r.model_score_D0 AS ref_score,
                r.momentum_rank, r.liquidity_trend_rank, r.liquidity_rank,
                -- candidate raw features
                f.alpha158_corr20_raw, f.alpha158_vsumd60_raw,
                a.intraday_trend_bias_20d, a.momentum_60_5, a.lower_shadow_support_20d,
                -- reference raw features
                a.pv_beta_20d, a.liq_trend_20_60, a.upside_range_share_20d
            FROM project_sample_panel p
            LEFT JOIN label_panel_t l ON p.snapshot_id=l.snapshot_id AND p.instrument=l.instrument AND p.signal_date=l.signal_date
            LEFT JOIN reference_scores_t r ON p.snapshot_id=r.snapshot_id AND p.instrument=r.instrument AND p.signal_date=r.signal_date
            LEFT JOIN feature_frame f ON p.snapshot_id=f.snapshot_id AND p.instrument=f.instrument AND p.signal_date=f.signal_date
            LEFT JOIN all_features_t a ON p.instrument=a.instrument AND p.signal_date=a.signal_date
        """)

        # ── Compute percentile ranks ──
        print("Computing percentile ranks...")
        SCREEN_FIELDS = ['alpha158_corr20_raw', 'alpha158_vsumd60_raw', 'intraday_trend_bias_20d', 'momentum_60_5', 'lower_shadow_support_20d']
        REF_FIELDS = ['pv_beta_20d', 'intraday_trend_bias_20d', 'liq_trend_20_60', 'momentum_60_5', 'upside_range_share_20d']

        rank_cols = []
        for field in SCREEN_FIELDS:
            rank_cols.append(f"PERCENT_RANK() OVER (PARTITION BY signal_date ORDER BY {field} DESC, instrument ASC) AS rank_{field}")
        for field in REF_FIELDS:
            rank_cols.append(f"PERCENT_RANK() OVER (PARTITION BY signal_date ORDER BY {field} DESC, instrument ASC) AS ref_rank_{field}")

        con.execute(f"""
            CREATE OR REPLACE VIEW ranked_frame_t AS
            SELECT signal_date, instrument,
                {', '.join(rank_cols)}
            FROM screen_frame_t WHERE ranking_eligible_D0
        """)

        # Compute composites: equal-weight of percentile ranks
        screen_rank_fields = [f"rank_{f}" for f in SCREEN_FIELDS]
        ref_rank_fields = [f"ref_rank_{f}" for f in REF_FIELDS]
        screen_composite_expr = " + ".join(f"COALESCE({f}, 0.0)" for f in screen_rank_fields) + \
            f" / NULLIF(CAST({' + '.join(f'CASE WHEN {f} IS NOT NULL THEN 1 ELSE 0 END' for f in screen_rank_fields)} AS DOUBLE), 0.0)"
        ref_composite_expr = " + ".join(f"COALESCE({f}, 0.0)" for f in ref_rank_fields) + \
            f" / NULLIF(CAST({' + '.join(f'CASE WHEN {f} IS NOT NULL THEN 1 ELSE 0 END' for f in ref_rank_fields)} AS DOUBLE), 0.0)"

        con.execute(f"""
            CREATE OR REPLACE VIEW score_frame_t AS
            SELECT
                r.signal_date, r.instrument,
                ({screen_composite_expr}) AS screen_model_score_D0,
                ({ref_composite_expr}) AS reference_model_score_D0,
                rank_alpha158_corr20_raw, rank_alpha158_vsumd60_raw,
                rank_intraday_trend_bias_20d, rank_momentum_60_5, rank_lower_shadow_support_20d,
                ref_rank_pv_beta_20d, ref_rank_intraday_trend_bias_20d,
                ref_rank_liq_trend_20_60, ref_rank_momentum_60_5, ref_rank_upside_range_share_20d
            FROM ranked_frame_t r
        """)

        con.execute(f"""
            CREATE OR REPLACE VIEW combined_score_t AS
            SELECT
                s.signal_date, s.instrument, s.snapshot_id,
                s.ranking_eligible_D0, l.label_5d_next_open_close, l.label_defined,
                s.liquidity_rank, s.ref_score,
                f.screen_model_score_D0, f.reference_model_score_D0,
                f.rank_alpha158_corr20_raw, f.rank_alpha158_vsumd60_raw,
                f.rank_intraday_trend_bias_20d, f.rank_momentum_60_5, f.rank_lower_shadow_support_20d,
                f.ref_rank_pv_beta_20d, f.ref_rank_intraday_trend_bias_20d,
                f.ref_rank_liq_trend_20_60, f.ref_rank_momentum_60_5, f.ref_rank_upside_range_share_20d
            FROM screen_frame_t s
            LEFT JOIN score_frame_t f ON s.signal_date=f.signal_date AND s.instrument=f.instrument
            LEFT JOIN label_panel_t l ON s.snapshot_id=l.snapshot_id AND s.instrument=l.instrument AND s.signal_date=l.signal_date
        """)

        # ── Compute diagnostic metrics ──
        print("Computing diagnostic metrics...")

        def score_readout(score_col: str) -> dict:
            row = con.execute(f"""
                WITH scored AS (
                    SELECT * FROM combined_score_t
                    WHERE {score_col} IS NOT NULL AND label_defined AND label_5d_next_open_close IS NOT NULL
                ),
                daily AS (
                    SELECT signal_date, CORR({score_col}, label_5d_next_open_close) AS daily_ic
                    FROM scored GROUP BY signal_date
                ),
                ranked AS (
                    SELECT signal_date, instrument, liquidity_rank, label_5d_next_open_close, {score_col} AS sv,
                        ROW_NUMBER() OVER (PARTITION BY signal_date ORDER BY {score_col} DESC, instrument ASC) AS rk,
                        LEAD({score_col}) OVER (PARTITION BY signal_date ORDER BY {score_col} DESC, instrument ASC) AS nx
                    FROM scored
                )
                SELECT
                    (SELECT CORR({score_col}, label_5d_next_open_close) FROM scored) AS full_ic,
                    (SELECT AVG(daily_ic) FROM daily) AS avg_daily_ic,
                    (SELECT MEDIAN(daily_ic) FROM daily) AS med_daily_ic,
                    (SELECT AVG(CASE WHEN daily_ic>0 THEN 1.0 ELSE 0.0 END) FROM daily) AS pos_daily_ic,
                    (SELECT AVG(label_5d_next_open_close) FROM ranked WHERE rk<=10) AS top10,
                    (SELECT AVG(label_5d_next_open_close) FROM ranked WHERE rk BETWEEN 11 AND 20) AS r11_20,
                    (SELECT AVG(label_5d_next_open_close) FROM (SELECT label_5d_next_open_close FROM ranked ORDER BY sv ASC, instrument ASC LIMIT 10)) AS bot10,
                    (SELECT AVG(sv-nx) FROM ranked WHERE rk=10 AND nx IS NOT NULL) AS gap10_11,
                    (SELECT AVG(liquidity_rank) FROM ranked WHERE rk<=10) AS liq_top10
            """).fetchone()
            return {
                "full_sample_corr_ic": row[0], "avg_daily_ic": row[1], "median_daily_ic": row[2],
                "positive_daily_ic_share": row[3], "avg_label_top10": row[4],
                "avg_label_rank11_20": row[5], "avg_label_bottom10": row[6],
                "top10_minus_rank11_20": (row[4]-row[5]) if row[4] is not None and row[5] is not None else None,
                "avg_rank10_11_score_gap": row[7], "avg_top10_liquidity_rank_mean": row[8],
            }

        def pair_corr(col_a: str, col_b: str) -> dict:
            row = con.execute(f"""
                WITH u AS (
                    SELECT signal_date, {col_a} AS a, {col_b} AS b
                    FROM combined_score_t WHERE {col_a} IS NOT NULL AND {col_b} IS NOT NULL
                ),
                d AS (SELECT signal_date, CORR(a,b) AS cv FROM u GROUP BY signal_date)
                SELECT (SELECT CORR(a,b) FROM u) AS full, (SELECT AVG(cv) FROM d) AS avg_daily,
                    (SELECT MEDIAN(cv) FROM d) AS med_daily,
                    (SELECT AVG(CASE WHEN cv>0 THEN 1.0 ELSE 0.0 END) FROM d) AS pos_share
            """).fetchone()
            return {"corr_full": row[0], "corr_avg_daily": row[1], "corr_median_daily": row[2], "corr_positive_daily_share": row[3]}

        def bucket_readout() -> dict:
            rows = con.execute("""
                WITH u AS (
                    SELECT signal_date, instrument, label_5d_next_open_close,
                        reference_model_score_D0, screen_model_score_D0
                    FROM combined_score_t
                    WHERE reference_model_score_D0 IS NOT NULL AND screen_model_score_D0 IS NOT NULL
                      AND label_defined AND label_5d_next_open_close IS NOT NULL
                ),
                b AS (
                    SELECT *, NTILE(3) OVER (PARTITION BY signal_date ORDER BY reference_model_score_D0 DESC, instrument ASC) AS ref_bucket,
                        NTILE(3) OVER (PARTITION BY signal_date ORDER BY screen_model_score_D0 DESC, instrument ASC) AS scr_bucket
                    FROM u
                )
                SELECT ref_bucket, scr_bucket, AVG(label_5d_next_open_close) AS avg_label
                FROM b GROUP BY ref_bucket, scr_bucket ORDER BY ref_bucket, scr_bucket
            """).fetchall()
            m, labels = {}, {1: "high", 2: "mid", 3: "low"}
            for rb, sb, al in rows:
                m[f"ref_{labels[rb]}_scr_{labels[sb]}"] = al
            return m

        def overlap_stats(score_col: str) -> tuple:
            row = con.execute(f"""
                WITH r AS (
                    SELECT signal_date, instrument,
                        ROW_NUMBER() OVER (PARTITION BY signal_date ORDER BY {score_col} DESC, instrument ASC) AS rk
                    FROM combined_score_t WHERE {score_col} IS NOT NULL
                ),
                t AS (SELECT signal_date, instrument FROM r WHERE rk<=10),
                p AS (
                    SELECT a.signal_date, COUNT(*) AS oc
                    FROM t a JOIN t b ON a.instrument=b.instrument
                        AND b.signal_date=STRFTIME(CAST(STRPTIME(a.signal_date,'%Y%m%d') AS DATE)+INTERVAL 1 DAY,'%Y%m%d')
                    GROUP BY 1
                )
                SELECT AVG(oc), MEDIAN(oc) FROM p
            """).fetchone()
            return row[0], row[1]

        def overlap_vs_reference() -> tuple:
            row = con.execute("""
                WITH ref AS (
                    SELECT signal_date, instrument,
                        ROW_NUMBER() OVER (PARTITION BY signal_date ORDER BY reference_model_score_D0 DESC, instrument ASC) AS rk
                    FROM combined_score_t WHERE reference_model_score_D0 IS NOT NULL
                ),
                scr AS (
                    SELECT signal_date, instrument,
                        ROW_NUMBER() OVER (PARTITION BY signal_date ORDER BY screen_model_score_D0 DESC, instrument ASC) AS rk
                    FROM combined_score_t WHERE screen_model_score_D0 IS NOT NULL
                ),
                rt AS (SELECT signal_date, instrument FROM ref WHERE rk<=10),
                st AS (SELECT signal_date, instrument FROM scr WHERE rk<=10),
                p AS (
                    SELECT r.signal_date, COUNT(*) AS oc
                    FROM rt r JOIN st s ON r.signal_date=s.signal_date AND r.instrument=s.instrument
                    GROUP BY 1
                )
                SELECT AVG(oc), MEDIAN(oc) FROM p
            """).fetchone()
            return row[0], row[1]

        # Run diagnostics
        ref_readout = score_readout("reference_model_score_D0")
        scr_readout = score_readout("screen_model_score_D0")

        # Pairwise correlations within candidate family
        comp_corrs = {}
        for i, f1 in enumerate(screen_rank_fields):
            for f2 in screen_rank_fields[i+1:]:
                comp_corrs[f"{f1}_vs_{f2}"] = pair_corr(f1, f2)

        # Pairwise within reference
        ref_corrs = {}
        for i, f1 in enumerate(ref_rank_fields):
            for f2 in ref_rank_fields[i+1:]:
                ref_corrs[f"{f1}_vs_{f2}"] = pair_corr(f1, f2)

        # Cross-family correlations
        cross_corrs = {}
        for sf in screen_rank_fields:
            for rf in ref_rank_fields:
                cross_corrs[f"{sf}_vs_{rf}"] = pair_corr(sf, rf)

        bucket_stats = bucket_readout()
        ref_overlap_avg, ref_overlap_med = overlap_stats("reference_model_score_D0")
        scr_overlap_avg, scr_overlap_med = overlap_stats("screen_model_score_D0")
        same_day_overlap_avg, same_day_overlap_med = overlap_vs_reference()

        # ── Judgement ──
        top_slice_improved = (
            scr_readout["top10_minus_rank11_20"] is not None
            and ref_readout["top10_minus_rank11_20"] is not None
            and scr_readout["top10_minus_rank11_20"] >= ref_readout["top10_minus_rank11_20"]
        )
        head_stability_not_worse = (
            scr_overlap_avg is not None and ref_overlap_avg is not None
            and scr_overlap_avg >= ref_overlap_avg - OVERLAP_TOLERANCE
        )
        liquidity_not_worse = (
            scr_readout["avg_top10_liquidity_rank_mean"] is not None
            and ref_readout["avg_top10_liquidity_rank_mean"] is not None
            and scr_readout["avg_top10_liquidity_rank_mean"] >= ref_readout["avg_top10_liquidity_rank_mean"] - 0.02
        )
        additive_high_bucket = (
            bucket_stats.get("ref_high_scr_high") is not None
            and bucket_stats.get("ref_high_scr_mid") is not None
            and bucket_stats["ref_high_scr_high"] >= bucket_stats["ref_high_scr_mid"]
        )

        if top_slice_improved and head_stability_not_worse and liquidity_not_worse and additive_high_bucket:
            classification = "composability_screen_promising"
            primary_conclusion = (
                "The orthogonal 5-signal family (corr20 + trend_bias + vsumd60 + momentum + lower_shadow) "
                "appears compositionally promising relative to v18: it improves or preserves static head quality "
                "without materially worsening head stability or liquidity proxies."
            )
            implication = (
                "Advance this orthogonal family into a confirmatory full-chain round with preregistered "
                "single-dimension change declaration."
            )
        else:
            classification = "composability_screen_mixed"
            primary_conclusion = (
                "The orthogonal 5-signal family shows mixed composability vs v18. "
                "It may improve some static ordering diagnostics, but at least one of additive monotonicity, "
                "head stability, or liquidity/head proxy behavior remains questionable."
            )
            implication = (
                "Keep the orthogonal family as a research candidate; do not promote into confirmatory yet. "
                "Consider subset reduction or alternative signal selection."
            )

        judgement = {
            "classification": classification,
            "primary_conclusion": primary_conclusion,
            "implication_for_next_step": implication,
            "top_slice_improved": top_slice_improved,
            "head_stability_not_worse": head_stability_not_worse,
            "liquidity_not_worse": liquidity_not_worse,
            "additive_high_bucket": additive_high_bucket,
            "hard_gate": {
                "screen_avg_top10_overlap_next_day_drop_tolerance": OVERLAP_TOLERANCE,
                "head_stability_not_worse": head_stability_not_worse,
            },
        }

        # Count rows
        total = con.execute("SELECT COUNT(*) FROM combined_score_t").fetchone()[0]
        eligible = con.execute("SELECT COUNT(*) FROM combined_score_t WHERE ranking_eligible_D0").fetchone()[0]
        scored_ref = con.execute("SELECT COUNT(*) FROM combined_score_t WHERE reference_model_score_D0 IS NOT NULL").fetchone()[0]
        scored_scr = con.execute("SELECT COUNT(*) FROM combined_score_t WHERE screen_model_score_D0 IS NOT NULL").fetchone()[0]

    finally:
        con.close()

    # ── Build report ──
    report = {
        "research_round_id": ROUND_ID,
        "generated_at": now_iso(),
        "candidate_scheme_id": SCREEN_CANDIDATE_ID,
        "reference_candidate_scheme_id": REFERENCE_CANDIDATE_ID,
        "candidate_signal_composition": [f["field"] for f in CANDIDATE_FEATURES],
        "reference_signal_composition": [f["field"] for f in REFERENCE_FEATURES],
        "coverage": {
            "total_rows": total, "ranking_eligible_rows": eligible,
            "reference_scored_rows": scored_ref, "screen_scored_rows": scored_scr,
        },
        "reference_readout": ref_readout,
        "screen_readout": scr_readout,
        "pairwise_component_correlation": {
            "candidate_family": {k: v for k, v in comp_corrs.items()},
            "reference_family": {k: v for k, v in ref_corrs.items()},
            "cross_family": {k: v for k, v in cross_corrs.items()},
        },
        "component_interaction": {"bucket_readout": bucket_stats},
        "head_stability": {
            "reference_avg_top10_overlap_next_day": ref_overlap_avg,
            "screen_avg_top10_overlap_next_day": scr_overlap_avg,
            "reference_median_top10_overlap_next_day": ref_overlap_med,
            "screen_median_top10_overlap_next_day": scr_overlap_med,
            "avg_top10_overlap_same_day_vs_reference": same_day_overlap_avg,
            "median_top10_overlap_same_day_vs_reference": same_day_overlap_med,
            "overlap_drop_tolerance": OVERLAP_TOLERANCE,
        },
        "judgement": judgement,
        "notes": [
            "This is a static composability screen (signal-edge only, no portfolio execution).",
            "The candidate family replaces 3 of v18's 5 signals with more orthogonal alternatives.",
            "Equal-weight percentile-rank blend used for both reference and candidate composites.",
        ],
    }

    json_path = round_dir / f"{SCREEN_CANDIDATE_ID}_diagnosis_{AS_OF_DATE}.json"
    write_json(json_path, report)

    # ── Markdown report ──
    def md_fmt(v, d=6): return fmt(v, d)
    def md_fmt_pct(v): return fmt_pct(v)

    md_lines = [
        f"# Orthogonal Family Composability Screen — v19 Candidate vs v18",
        "",
        f"- `research_round_id(研究轮次ID) = {ROUND_ID}`",
        f"- `candidate_scheme_id(候选方案ID) = {SCREEN_CANDIDATE_ID}`",
        f"- `reference_candidate_scheme_id(参考候选方案ID) = {REFERENCE_CANDIDATE_ID}`",
        "",
        "## Candidate Signal Composition",
        "",
    ]
    for f in CANDIDATE_FEATURES:
        md_lines.append(f"- `{f['field']}` ({f['kind']})")
    md_lines.extend(["", "## Reference Signal Composition (v18)", ""])
    for f in REFERENCE_FEATURES:
        md_lines.append(f"- `{f['field']}` (project)")
    md_lines.extend([
        "",
        "## Core Answer",
        "",
        f"**{classification}**",
        "",
        primary_conclusion,
        "",
        "## Reference vs Screen Static Readout",
        "",
        f"- `reference_full_sample_corr_ic(参考全样本IC) = {md_fmt(ref_readout['full_sample_corr_ic'])}`",
        f"- `screen_full_sample_corr_ic(筛查全样本IC) = {md_fmt(scr_readout['full_sample_corr_ic'])}`",
        f"- `reference_avg_daily_ic(参考平均日IC) = {md_fmt(ref_readout['avg_daily_ic'])}`",
        f"- `screen_avg_daily_ic(筛查平均日IC) = {md_fmt(scr_readout['avg_daily_ic'])}`",
        f"- `reference_top10_minus_rank11_20(参考前10减11-20) = {md_fmt(ref_readout['top10_minus_rank11_20'])}`",
        f"- `screen_top10_minus_rank11_20(筛查前10减11-20) = {md_fmt(scr_readout['top10_minus_rank11_20'])}`",
        f"- `reference_avg_rank10_11_score_gap(参考第10/11名平均间距) = {md_fmt(ref_readout['avg_rank10_11_score_gap'])}`",
        f"- `screen_avg_rank10_11_score_gap(筛查第10/11名平均间距) = {md_fmt(scr_readout['avg_rank10_11_score_gap'])}`",
        "",
        "## Component Interaction (Candidate Family)",
        "",
    ])
    for key, val in comp_corrs.items():
        parts = key.replace("rank_", "").replace("_raw", "").replace("_vs_", " ↔ ")
        md_lines.append(f"- `{parts}`: full_corr={md_fmt(val['corr_full'])}, avg_daily={md_fmt(val['corr_avg_daily'])}")
    md_lines.extend([
        "",
        "## Bucket Analysis",
        "",
    ])
    for key, val in sorted(bucket_stats.items()):
        md_lines.append(f"- `{key}`: avg_label={md_fmt(val)}")
    md_lines.extend([
        "",
        "## Head Stability",
        "",
        f"- `reference_avg_top10_overlap_next_day(参考次日前10平均重叠) = {md_fmt(ref_overlap_avg)}`",
        f"- `screen_avg_top10_overlap_next_day(筛查次日前10平均重叠) = {md_fmt(scr_overlap_avg)}`",
        f"- `overlap_drop_tolerance(重叠下降容忍阈值) = {OVERLAP_TOLERANCE}`",
        f"- `avg_top10_overlap_same_day_vs_reference(与参考同日前10平均重叠) = {md_fmt(same_day_overlap_avg)}`",
        f"- `reference_avg_top10_liquidity_rank_mean(参考前10平均流动性分位) = {md_fmt(ref_readout['avg_top10_liquidity_rank_mean'])}`",
        f"- `screen_avg_top10_liquidity_rank_mean(筛查前10平均流动性分位) = {md_fmt(scr_readout['avg_top10_liquidity_rank_mean'])}`",
        "",
        "## Judgement",
        "",
        f"- `classification(分类) = {classification}`",
        f"- `top_slice_improved(头部区分改善) = {top_slice_improved}`",
        f"- `head_stability_not_worse(头部稳定性未恶化) = {head_stability_not_worse}`",
        f"- `liquidity_not_worse(流动性未恶化) = {liquidity_not_worse}`",
        f"- `additive_high_bucket(单调加成) = {additive_high_bucket}`",
        f"- `implication_for_next_step(下一步含义) = {implication}`",
        "",
    ])
    md_path = round_dir / f"{SCREEN_CANDIDATE_ID}_diagnosis_{AS_OF_DATE}.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"\n{'='*70}")
    print(f"Composability screen complete: {classification}")
    print(f"{'='*70}")
    print(f"Reference IC: {md_fmt(ref_readout['full_sample_corr_ic'])}")
    print(f"Screen IC:    {md_fmt(scr_readout['full_sample_corr_ic'])}")
    print(f"Reference Top10-11_20: {md_fmt(ref_readout['top10_minus_rank11_20'])}")
    print(f"Screen Top10-11_20:    {md_fmt(scr_readout['top10_minus_rank11_20'])}")
    print(f"Reference overlap: {md_fmt(ref_overlap_avg)}")
    print(f"Screen overlap:    {md_fmt(scr_overlap_avg)}")
    print(f"Same-day overlap:  {md_fmt(same_day_overlap_avg)}")
    print(f"\nJSON: {json_path}")
    print(f"MD:   {md_path}")


if __name__ == "__main__":
    main()
