#!/opt/anaconda3/envs/quant_trade/bin/python
from __future__ import annotations

import json
from pathlib import Path

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
CONTRACTS_DIR = ROOT / "contracts"
RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
RESEARCH_DIR = ROOT / "artifacts" / "research_registry"

ROUND_ID = "rr_price_volume_lower_shadow_support_composability_screen_20260428"
CANDIDATE_ID = "price_volume_screen_lower_shadow_support_20d_composability_v1"
REFERENCE_CANDIDATE_ID = "price_volume_v18_refresh_hysteresis"
REFERENCE_RUN_ID = "fullchain_price_volume_refresh_hysteresis_20260422_143317"
RUN_ID = "screendiag_price_volume_lower_shadow_support_composability_20260428"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_path(path: Path) -> str:
    return sql_quote(path.resolve().as_posix())


def format_num(value: float | None, digits: int = 6) -> str:
    if value is None:
        return "null"
    return f"{value:.{digits}f}"


def main() -> None:
    reference_dir = RUN_STATE_DIR / REFERENCE_RUN_ID
    run_dir = RUN_STATE_DIR / RUN_ID
    run_dir.mkdir(parents=True, exist_ok=True)

    sample_panel = reference_dir / "project_sample_panel.parquet"
    label_panel = reference_dir / "project_label_panel.parquet"
    reference_scores = reference_dir / "model_scores_D0.parquet"
    if not sample_panel.exists() or not label_panel.exists() or not reference_scores.exists():
        raise FileNotFoundError("Missing required v18 reference artifacts for composability screening.")

    run_input = load_json(CONTRACTS_DIR / "run_input_contract.current.json")
    snapshot_id = run_input["snapshot_id"]
    source_db_path = Path(run_input["source_root"]["snapshot_path"]) / "duckdb" / "warehouse.duckdb"
    if not source_db_path.exists():
        raise FileNotFoundError(f"Shared warehouse DB not found: {source_db_path}")

    single_signal_report = load_json(
        RESEARCH_DIR
        / "research_rounds"
        / "rr_price_volume_single_signal_discovery_v18_round9_composability_first_20260428"
        / "price_volume_single_signal_lower_shadow_support_20d_v1_signal_edge_diagnosis_20260428.json"
    )

    round_dir = RESEARCH_DIR / "research_rounds" / ROUND_ID
    json_report_path = round_dir / "price_volume_screen_lower_shadow_support_20d_composability_v1_diagnosis_20260428.json"
    md_report_path = round_dir / "price_volume_screen_lower_shadow_support_20d_composability_v1_diagnosis_20260428.md"
    score_output_path = run_dir / "screen_scores_D0.parquet"
    audit_output_path = run_dir / "screen_scores_D0_audit.json"

    con = duckdb.connect()
    try:
        con.execute(f"ATTACH {sql_path(source_db_path)} AS warehouse_db (READ_ONLY)")
        con.execute(
            f"CREATE OR REPLACE VIEW project_sample_panel AS SELECT * FROM read_parquet({sql_path(sample_panel)})"
        )
        con.execute(
            f"CREATE OR REPLACE VIEW project_label_panel AS SELECT * FROM read_parquet({sql_path(label_panel)})"
        )
        con.execute(
            f"CREATE OR REPLACE VIEW reference_scores AS SELECT * FROM read_parquet({sql_path(reference_scores)})"
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW lower_shadow_support_features AS
            WITH bars AS (
                SELECT
                    ts_code AS instrument,
                    trade_date AS signal_date,
                    adj_open,
                    adj_high,
                    adj_low,
                    adj_close
                FROM warehouse_db.serving.vw_bars_daily
                WHERE snapshot_id = {sql_quote(snapshot_id)}
            ),
            daily AS (
                SELECT
                    instrument,
                    signal_date,
                    CASE
                        WHEN adj_high > adj_low
                        THEN (LEAST(adj_open, adj_close) - adj_low) / GREATEST(adj_high - adj_low, 1e-12)
                        ELSE NULL
                    END AS lower_shadow_support_part
                FROM bars
            )
            SELECT
                instrument,
                signal_date,
                AVG(lower_shadow_support_part) OVER w20 AS lower_shadow_support_20d_raw
            FROM daily
            WINDOW
                w20 AS (
                    PARTITION BY instrument
                    ORDER BY signal_date
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                )
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW base_frame AS
            SELECT
                p.snapshot_id,
                p.instrument,
                p.signal_date,
                p.ranking_eligible_D0,
                p.label_defined,
                l.label_5d_next_open_close,
                r.model_score_D0 AS reference_model_score_D0,
                r.momentum_rank,
                r.liquidity_trend_rank,
                r.liquidity_rank,
                s.lower_shadow_support_20d_raw
            FROM project_sample_panel p
            LEFT JOIN project_label_panel l
              ON p.snapshot_id = l.snapshot_id
             AND p.instrument = l.instrument
             AND p.signal_date = l.signal_date
            LEFT JOIN reference_scores r
              ON p.snapshot_id = r.snapshot_id
             AND p.instrument = r.instrument
             AND p.signal_date = r.signal_date
            LEFT JOIN lower_shadow_support_features s
              ON p.instrument = s.instrument
             AND p.signal_date = s.signal_date
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW signal_ranks AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY lower_shadow_support_20d_raw DESC, instrument ASC
                ) AS lower_shadow_support_rank
            FROM base_frame
            WHERE ranking_eligible_D0
              AND lower_shadow_support_20d_raw IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW screen_frame AS
            SELECT
                b.snapshot_id,
                b.instrument,
                b.signal_date,
                b.ranking_eligible_D0,
                b.label_defined,
                b.label_5d_next_open_close,
                b.reference_model_score_D0,
                b.momentum_rank,
                b.liquidity_trend_rank,
                b.liquidity_rank,
                s.lower_shadow_support_rank,
                CASE
                    WHEN b.momentum_rank IS NOT NULL AND b.liquidity_trend_rank IS NOT NULL
                    THEN (b.momentum_rank + b.liquidity_trend_rank) / 2.0
                    ELSE NULL
                END AS core_score_v18,
                CASE
                    WHEN b.momentum_rank IS NOT NULL
                     AND b.liquidity_trend_rank IS NOT NULL
                     AND s.lower_shadow_support_rank IS NOT NULL
                    THEN (b.momentum_rank + b.liquidity_trend_rank + s.lower_shadow_support_rank) / 3.0
                    ELSE NULL
                END AS screen_model_score_D0
            FROM base_frame b
            LEFT JOIN signal_ranks s
              ON b.snapshot_id = s.snapshot_id
             AND b.instrument = s.instrument
             AND b.signal_date = s.signal_date
            """
        )
        con.execute(
            f"""
            COPY (
                SELECT
                    snapshot_id,
                    instrument,
                    signal_date,
                    CAST({sql_quote(CANDIDATE_ID)} AS VARCHAR) AS candidate_scheme_id,
                    screen_model_score_D0,
                    CASE
                        WHEN momentum_rank IS NOT NULL
                         AND liquidity_trend_rank IS NOT NULL
                         AND lower_shadow_support_rank IS NOT NULL
                        THEN 3
                        ELSE (CASE WHEN momentum_rank IS NOT NULL THEN 1 ELSE 0 END)
                           + (CASE WHEN liquidity_trend_rank IS NOT NULL THEN 1 ELSE 0 END)
                           + (CASE WHEN lower_shadow_support_rank IS NOT NULL THEN 1 ELSE 0 END)
                    END AS score_component_count,
                    momentum_rank,
                    liquidity_trend_rank,
                    liquidity_rank,
                    lower_shadow_support_rank,
                    core_score_v18
                FROM screen_frame
            ) TO {sql_path(score_output_path)} (FORMAT PARQUET)
            """
        )

        counts = con.execute(
            """
            SELECT
                COUNT(*) AS total_rows,
                SUM(CASE WHEN ranking_eligible_D0 THEN 1 ELSE 0 END) AS ranking_eligible_rows,
                SUM(CASE WHEN reference_model_score_D0 IS NOT NULL THEN 1 ELSE 0 END) AS reference_scored_rows,
                SUM(CASE WHEN screen_model_score_D0 IS NOT NULL THEN 1 ELSE 0 END) AS screen_scored_rows
            FROM screen_frame
            """
        ).fetchone()

        def score_readout(score_col: str) -> dict:
            row = con.execute(
                f"""
                WITH scored AS (
                    SELECT *
                    FROM screen_frame
                    WHERE {score_col} IS NOT NULL
                      AND label_defined
                      AND label_5d_next_open_close IS NOT NULL
                ),
                daily AS (
                    SELECT
                        signal_date,
                        corr({score_col}, label_5d_next_open_close) AS daily_ic
                    FROM scored
                    GROUP BY signal_date
                ),
                ranked AS (
                    SELECT
                        signal_date,
                        instrument,
                        liquidity_rank,
                        label_5d_next_open_close,
                        {score_col} AS score_value,
                        ROW_NUMBER() OVER (
                            PARTITION BY signal_date
                            ORDER BY {score_col} DESC, instrument ASC
                        ) AS score_rank,
                        LEAD({score_col}) OVER (
                            PARTITION BY signal_date
                            ORDER BY {score_col} DESC, instrument ASC
                        ) AS next_score_value
                    FROM scored
                )
                SELECT
                    (SELECT corr({score_col}, label_5d_next_open_close) FROM scored) AS full_sample_corr_ic,
                    (SELECT avg(daily_ic) FROM daily) AS avg_daily_ic,
                    (SELECT median(daily_ic) FROM daily) AS median_daily_ic,
                    (SELECT avg(CASE WHEN daily_ic > 0 THEN 1.0 ELSE 0.0 END) FROM daily) AS positive_daily_ic_share,
                    (SELECT avg(label_5d_next_open_close) FROM ranked WHERE score_rank <= 10) AS avg_label_top10,
                    (SELECT avg(label_5d_next_open_close) FROM ranked WHERE score_rank BETWEEN 11 AND 20) AS avg_label_rank11_20,
                    (
                        SELECT avg(label_5d_next_open_close)
                        FROM (
                            SELECT label_5d_next_open_close
                            FROM ranked
                            ORDER BY score_value ASC, instrument ASC
                            LIMIT 10
                        )
                    ) AS avg_label_bottom10,
                    (SELECT avg(score_value - next_score_value) FROM ranked WHERE score_rank = 10 AND next_score_value IS NOT NULL) AS avg_rank10_11_score_gap,
                    (SELECT median(score_value - next_score_value) FROM ranked WHERE score_rank = 10 AND next_score_value IS NOT NULL) AS median_rank10_11_score_gap,
                    (SELECT count(*) FROM ranked WHERE score_rank = 10 AND next_score_value IS NOT NULL) AS days_with_both_ranks,
                    (SELECT avg(liquidity_rank) FROM ranked WHERE score_rank <= 10) AS avg_top10_liquidity_rank_mean
                """
            ).fetchone()
            return {
                "full_sample_corr_ic": row[0],
                "avg_daily_ic": row[1],
                "median_daily_ic": row[2],
                "positive_daily_ic_share": row[3],
                "avg_label_top10": row[4],
                "avg_label_rank11_20": row[5],
                "avg_label_bottom10": row[6],
                "top10_minus_rank11_20": (row[4] - row[5]) if row[4] is not None and row[5] is not None else None,
                "avg_rank10_11_score_gap": row[7],
                "median_rank10_11_score_gap": row[8],
                "days_with_both_ranks": row[9],
                "avg_top10_liquidity_rank_mean": row[10],
            }

        def pair_corr(col_a: str, col_b: str) -> dict:
            row = con.execute(
                f"""
                WITH usable AS (
                    SELECT signal_date, {col_a} AS a, {col_b} AS b
                    FROM screen_frame
                    WHERE {col_a} IS NOT NULL
                      AND {col_b} IS NOT NULL
                ),
                daily AS (
                    SELECT signal_date, corr(a, b) AS corr_value
                    FROM usable
                    GROUP BY signal_date
                )
                SELECT
                    (SELECT corr(a, b) FROM usable) AS corr_full,
                    (SELECT avg(corr_value) FROM daily) AS corr_avg_daily,
                    (SELECT median(corr_value) FROM daily) AS corr_median_daily,
                    (SELECT avg(CASE WHEN corr_value > 0 THEN 1.0 ELSE 0.0 END) FROM daily) AS corr_positive_daily_share
                """
            ).fetchone()
            return {
                "corr_full": row[0],
                "corr_avg_daily": row[1],
                "corr_median_daily": row[2],
                "corr_positive_daily_share": row[3],
            }

        def bucket_readout() -> dict:
            rows = con.execute(
                """
                WITH usable AS (
                    SELECT
                        signal_date,
                        instrument,
                        label_5d_next_open_close,
                        core_score_v18,
                        lower_shadow_support_rank
                    FROM screen_frame
                    WHERE core_score_v18 IS NOT NULL
                      AND lower_shadow_support_rank IS NOT NULL
                      AND label_defined
                      AND label_5d_next_open_close IS NOT NULL
                ),
                bucketed AS (
                    SELECT
                        signal_date,
                        instrument,
                        label_5d_next_open_close,
                        NTILE(3) OVER (
                            PARTITION BY signal_date
                            ORDER BY core_score_v18 DESC, instrument ASC
                        ) AS core_bucket,
                        NTILE(3) OVER (
                            PARTITION BY signal_date
                            ORDER BY lower_shadow_support_rank DESC, instrument ASC
                        ) AS signal_bucket
                    FROM usable
                )
                SELECT
                    core_bucket,
                    signal_bucket,
                    avg(label_5d_next_open_close) AS avg_label
                FROM bucketed
                GROUP BY core_bucket, signal_bucket
                ORDER BY core_bucket, signal_bucket
                """
            ).fetchall()
            mapping = {}
            labels = {1: "high", 2: "mid", 3: "low"}
            for core_bucket, signal_bucket, avg_label in rows:
                mapping[f"core_{labels[core_bucket]}_signal_{labels[signal_bucket]}"] = avg_label
            return mapping

        def overlap_stats(score_col: str) -> tuple[float | None, float | None]:
            row = con.execute(
                f"""
                WITH ranked AS (
                    SELECT
                        signal_date,
                        instrument,
                        ROW_NUMBER() OVER (
                            PARTITION BY signal_date
                            ORDER BY {score_col} DESC, instrument ASC
                        ) AS score_rank
                    FROM screen_frame
                    WHERE {score_col} IS NOT NULL
                ),
                top10 AS (
                    SELECT signal_date, instrument
                    FROM ranked
                    WHERE score_rank <= 10
                ),
                paired AS (
                    SELECT
                        a.signal_date AS signal_date,
                        count(*) AS overlap_count
                    FROM top10 a
                    JOIN top10 b
                      ON a.instrument = b.instrument
                     AND b.signal_date = strftime(
                            CAST(strptime(a.signal_date, '%Y%m%d') AS DATE) + INTERVAL 1 DAY,
                            '%Y%m%d'
                        )
                    GROUP BY 1
                )
                SELECT avg(overlap_count), median(overlap_count) FROM paired
                """
            ).fetchone()
            return row[0], row[1]

        def overlap_vs_reference() -> tuple[float | None, float | None]:
            row = con.execute(
                """
                WITH reference_ranked AS (
                    SELECT
                        signal_date,
                        instrument,
                        ROW_NUMBER() OVER (
                            PARTITION BY signal_date
                            ORDER BY reference_model_score_D0 DESC, instrument ASC
                        ) AS ref_rank
                    FROM screen_frame
                    WHERE reference_model_score_D0 IS NOT NULL
                ),
                screen_ranked AS (
                    SELECT
                        signal_date,
                        instrument,
                        ROW_NUMBER() OVER (
                            PARTITION BY signal_date
                            ORDER BY screen_model_score_D0 DESC, instrument ASC
                        ) AS screen_rank
                    FROM screen_frame
                    WHERE screen_model_score_D0 IS NOT NULL
                ),
                ref_top10 AS (
                    SELECT signal_date, instrument
                    FROM reference_ranked
                    WHERE ref_rank <= 10
                ),
                screen_top10 AS (
                    SELECT signal_date, instrument
                    FROM screen_ranked
                    WHERE screen_rank <= 10
                ),
                paired AS (
                    SELECT
                        r.signal_date,
                        count(*) AS overlap_count
                    FROM ref_top10 r
                    JOIN screen_top10 s
                      ON r.signal_date = s.signal_date
                     AND r.instrument = s.instrument
                    GROUP BY 1
                )
                SELECT avg(overlap_count), median(overlap_count) FROM paired
                """
            ).fetchone()
            return row[0], row[1]

        reference_readout = score_readout("reference_model_score_D0")
        screen_readout = score_readout("screen_model_score_D0")
        momentum_signal_corr = pair_corr("momentum_rank", "lower_shadow_support_rank")
        liquidity_signal_corr = pair_corr("liquidity_trend_rank", "lower_shadow_support_rank")
        core_signal_corr = pair_corr("core_score_v18", "lower_shadow_support_rank")
        bucket_stats = bucket_readout()
        ref_overlap_avg, ref_overlap_median = overlap_stats("reference_model_score_D0")
        screen_overlap_avg, screen_overlap_median = overlap_stats("screen_model_score_D0")
        same_day_overlap_avg, same_day_overlap_median = overlap_vs_reference()
    finally:
        con.close()

    audit = {
        "run_id": RUN_ID,
        "candidate_scheme_id": CANDIDATE_ID,
        "research_round_id": ROUND_ID,
        "reference_candidate_scheme_id": REFERENCE_CANDIDATE_ID,
        "snapshot_id": snapshot_id,
        "summary_counts": {
            "total_rows": counts[0],
            "ranking_eligible_rows": counts[1],
            "reference_scored_rows": counts[2],
            "screen_scored_rows": counts[3],
        },
        "notes": [
            "This is a composability-screening artifact, not a full-chain strategy run.",
            "The screen score is a tentative static three-component average over momentum_60_5_raw, liquidity_trend_20_60_raw, and lower_shadow_support_20d_raw.",
            "No live portfolio, execution, benchmark, or cost rule was changed inside this round."
        ]
    }
    write_json(audit_output_path, audit)

    judgement = {
        "primary_conclusion": "",
        "mechanism": [],
        "implication_for_next_step": "",
        "classification": ""
    }

    top_slice_improved = (
        screen_readout["top10_minus_rank11_20"] is not None
        and reference_readout["top10_minus_rank11_20"] is not None
        and screen_readout["top10_minus_rank11_20"] >= reference_readout["top10_minus_rank11_20"]
    )
    head_stability_not_worse = (
        screen_overlap_avg is not None and ref_overlap_avg is not None and screen_overlap_avg >= ref_overlap_avg - 0.2
    )
    liquidity_not_worse = (
        screen_readout["avg_top10_liquidity_rank_mean"] is not None
        and reference_readout["avg_top10_liquidity_rank_mean"] is not None
        and screen_readout["avg_top10_liquidity_rank_mean"] >= reference_readout["avg_top10_liquidity_rank_mean"] - 0.02
    )
    additive_high_bucket = (
        bucket_stats.get("core_high_signal_high") is not None
        and bucket_stats.get("core_high_signal_mid") is not None
        and bucket_stats["core_high_signal_high"] >= bucket_stats["core_high_signal_mid"]
    )

    if top_slice_improved and head_stability_not_worse and liquidity_not_worse and additive_high_bucket:
        judgement["classification"] = "composability_screen_promising"
        judgement["primary_conclusion"] = (
            "lower_shadow_support_20d_raw appears compositionally promising relative to the frozen v18 core family: "
            "the tentative tri-signal screen improves or preserves static head quality without materially worsening "
            "head stability or liquidity proxies."
        )
        judgement["implication_for_next_step"] = (
            "A future family round may test lower_shadow_support_20d_raw as a constrained third signal under a single-dimension preregistration."
        )
    else:
        judgement["classification"] = "composability_screen_mixed"
        judgement["primary_conclusion"] = (
            "lower_shadow_support_20d_raw is a real standalone keeper, but its additive fit with the frozen v18 core family is mixed rather than clean. "
            "It improves some static ordering diagnostics, but at least one of additive monotonicity, head stability, or liquidity/head proxy behavior remains questionable."
        )
        judgement["implication_for_next_step"] = (
            "Do not promote lower_shadow_support_20d_raw into a direct equal-weight family replacement yet. If used later, prefer a constrained third-signal test or gated modifier design."
        )

    if momentum_signal_corr["corr_avg_daily"] is not None:
        judgement["mechanism"].append(
            "Pairwise momentum-vs-lower-shadow-support rank correlation is "
            + format_num(momentum_signal_corr["corr_avg_daily"])
            + " on average by day, which indicates the new signal is not simply duplicating momentum."
        )
    if core_signal_corr["corr_avg_daily"] is not None:
        judgement["mechanism"].append(
            "Core-family-vs-lower-shadow-support rank correlation is "
            + format_num(core_signal_corr["corr_avg_daily"])
            + " on average by day, so the candidate contributes partially orthogonal ordering information."
        )
    if bucket_stats.get("core_high_signal_high") is not None and bucket_stats.get("core_high_signal_mid") is not None:
        judgement["mechanism"].append(
            "In the high-core region, core_high+signal_high average label is "
            + format_num(bucket_stats["core_high_signal_high"])
            + " versus core_high+signal_mid "
            + format_num(bucket_stats["core_high_signal_mid"])
            + ", which is the key additive-monotonicity check."
        )
    if screen_overlap_avg is not None and ref_overlap_avg is not None:
        judgement["mechanism"].append(
            "Head stability proxy changes from reference avg next-day top10 overlap "
            + format_num(ref_overlap_avg)
            + " to screen "
            + format_num(screen_overlap_avg)
            + "."
        )

    report = {
        "candidate_scheme_id": CANDIDATE_ID,
        "research_round_id": ROUND_ID,
        "as_of_date": "20260428",
        "diagnosis_question": "Relative to the frozen v18 core two-signal family, does lower_shadow_support_20d_raw look compositionally compatible enough to justify a later family-level promotion?",
        "single_signal_readout": {
            "full_sample_corr_ic": single_signal_report["ic_readout"]["full_sample_corr_ic"],
            "avg_daily_ic": single_signal_report["ic_readout"]["avg_daily_ic"],
            "median_daily_ic": single_signal_report["ic_readout"]["median_daily_ic"],
            "positive_daily_ic_share": single_signal_report["ic_readout"]["positive_daily_ic_share"],
            "avg_label_top10": single_signal_report["top_slice_readout"]["avg_label_top10"],
            "avg_label_rank11_20": single_signal_report["top_slice_readout"]["avg_label_rank11_20"],
            "avg_label_bottom10": single_signal_report["top_slice_readout"]["avg_label_bottom10"],
            "top10_minus_rank11_20": single_signal_report["top_slice_readout"]["top10_minus_rank11_20"]
        },
        "reference_family_signal_edge_readout": reference_readout,
        "screen_family_signal_edge_readout": screen_readout,
        "pairwise_component_correlation": {
            "momentum_vs_lower_shadow_support": momentum_signal_corr,
            "liquidity_trend_vs_lower_shadow_support": liquidity_signal_corr,
            "core_v18_vs_lower_shadow_support": core_signal_corr
        },
        "component_interaction": {
            "bucket_readout": bucket_stats
        },
        "head_stability": {
            "reference_avg_top10_overlap_next_day": ref_overlap_avg,
            "screen_avg_top10_overlap_next_day": screen_overlap_avg,
            "reference_median_top10_overlap_next_day": ref_overlap_median,
            "screen_median_top10_overlap_next_day": screen_overlap_median,
            "avg_top10_overlap_same_day_vs_reference": same_day_overlap_avg,
            "median_top10_overlap_same_day_vs_reference": same_day_overlap_median
        },
        "coverage": audit["summary_counts"],
        "judgement": judgement
    }
    write_json(json_report_path, report)

    md_lines = [
        "# lower_shadow_support_20d composability screening diagnosis",
        "",
        f"- `candidate_scheme_id(候选方案ID) = {CANDIDATE_ID}`",
        f"- `research_round_id(研究轮次ID) = {ROUND_ID}`",
        f"- `reference_candidate_scheme_id(参考候选方案ID) = {REFERENCE_CANDIDATE_ID}`",
        "",
        "## Core answer",
        "",
        judgement["primary_conclusion"],
        "",
        "## Single-signal baseline",
        "",
        f"- `full_sample_corr_ic(全样本IC) = {format_num(report['single_signal_readout']['full_sample_corr_ic'])}`",
        f"- `avg_daily_ic(平均日IC) = {format_num(report['single_signal_readout']['avg_daily_ic'])}`",
        f"- `positive_daily_ic_share(正IC日占比) = {format_num(report['single_signal_readout']['positive_daily_ic_share'])}`",
        f"- `avg_label_top10(前10平均标签) = {format_num(report['single_signal_readout']['avg_label_top10'])}`",
        f"- `avg_label_rank11_20(11-20名平均标签) = {format_num(report['single_signal_readout']['avg_label_rank11_20'])}`",
        "",
        "## Reference vs screen static family readout",
        "",
        f"- `reference_full_sample_corr_ic(参考全样本IC) = {format_num(reference_readout['full_sample_corr_ic'])}`",
        f"- `screen_full_sample_corr_ic(筛查全样本IC) = {format_num(screen_readout['full_sample_corr_ic'])}`",
        f"- `reference_avg_label_top10(参考前10平均标签) = {format_num(reference_readout['avg_label_top10'])}`",
        f"- `screen_avg_label_top10(筛查前10平均标签) = {format_num(screen_readout['avg_label_top10'])}`",
        f"- `reference_top10_minus_rank11_20(参考前10减11-20) = {format_num(reference_readout['top10_minus_rank11_20'])}`",
        f"- `screen_top10_minus_rank11_20(筛查前10减11-20) = {format_num(screen_readout['top10_minus_rank11_20'])}`",
        f"- `reference_avg_rank10_11_score_gap(参考第10/11名平均间距) = {format_num(reference_readout['avg_rank10_11_score_gap'])}`",
        f"- `screen_avg_rank10_11_score_gap(筛查第10/11名平均间距) = {format_num(screen_readout['avg_rank10_11_score_gap'])}`",
        "",
        "## Component interaction",
        "",
        f"- `momentum_vs_lower_shadow_support_corr_avg_daily(动量与下影线支撑日均相关) = {format_num(momentum_signal_corr['corr_avg_daily'])}`",
        f"- `liquidity_trend_vs_lower_shadow_support_corr_avg_daily(流动性趋势与下影线支撑日均相关) = {format_num(liquidity_signal_corr['corr_avg_daily'])}`",
        f"- `core_v18_vs_lower_shadow_support_corr_avg_daily(v18核心分数与下影线支撑日均相关) = {format_num(core_signal_corr['corr_avg_daily'])}`",
        f"- `core_high_signal_high_avg_label(核心高+信号高平均标签) = {format_num(bucket_stats.get('core_high_signal_high'))}`",
        f"- `core_high_signal_mid_avg_label(核心高+信号中平均标签) = {format_num(bucket_stats.get('core_high_signal_mid'))}`",
        f"- `core_high_signal_low_avg_label(核心高+信号低平均标签) = {format_num(bucket_stats.get('core_high_signal_low'))}`",
        "",
        "## Head stability proxy",
        "",
        f"- `reference_avg_top10_overlap_next_day(参考次日前10平均重叠) = {format_num(ref_overlap_avg)}`",
        f"- `screen_avg_top10_overlap_next_day(筛查次日前10平均重叠) = {format_num(screen_overlap_avg)}`",
        f"- `avg_top10_overlap_same_day_vs_reference(与参考同日前10平均重叠) = {format_num(same_day_overlap_avg)}`",
        f"- `reference_avg_top10_liquidity_rank_mean(参考前10平均流动性分位) = {format_num(reference_readout['avg_top10_liquidity_rank_mean'])}`",
        f"- `screen_avg_top10_liquidity_rank_mean(筛查前10平均流动性分位) = {format_num(screen_readout['avg_top10_liquidity_rank_mean'])}`",
        "",
        "## Judgement",
        "",
        f"- `classification(分类) = {judgement['classification']}`",
        f"- `implication_for_next_step(下一步含义) = {judgement['implication_for_next_step']}`",
    ]
    md_report_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
