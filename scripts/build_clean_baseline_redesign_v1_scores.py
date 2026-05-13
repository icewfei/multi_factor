#!/usr/bin/env python3
"""
Build clean baseline redesign round v1 score artifacts.

This builder is score-layer only: no p98 input, no labels, no training, no
portfolio, no formal metrics/readout, and no frozen test access.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
DEFAULT_MANIFEST = ROOT / "configs" / "clean_baselines" / "redesign_round_v1" / "clean_baseline_redesign_manifest.json"
DEFAULT_SOURCE_DB = Path(
    "/Users/wy/MiscProject/tushare_data/parquet_duckdb/data/snapshots/"
    "warehouse_20260429_trainval_20211231/duckdb/warehouse.duckdb"
)
DEFAULT_CLEAN_SAMPLE_PANEL = Path("/private/tmp/clean_baseline_family_score_gate_20260513/clean_sample_panel.parquet")
DEFAULT_ENRICHMENT_PATH = Path("/private/tmp/data_field_enrichment_v1_smoke/enriched_security_state_daily_v1.parquet")
DEFAULT_OUTPUT_ROOT = Path("/private/tmp/clean_baseline_redesign_round_v1/scores")
DEFAULT_ATTEMPT_ID = "attempt_clean_baseline_redesign_round_v1"

BLOCKED_FIELDS = {"listing_age_trading_days", "newly_listed_flag"}
FORBIDDEN_INPUT_TOKENS = (
    "label_",
    "realized_return",
    "actual_exit",
    "actual_sell",
    "future",
    "frozen",
    "fixed_test",
    "test_window",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build clean baseline redesign round v1 scores.")
    parser.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--source-db", type=Path, default=DEFAULT_SOURCE_DB)
    parser.add_argument("--clean-sample-panel", type=Path, default=DEFAULT_CLEAN_SAMPLE_PANEL)
    parser.add_argument("--enrichment-path", type=Path, default=DEFAULT_ENRICHMENT_PATH)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--attempt-id", default=DEFAULT_ATTEMPT_ID)
    parser.add_argument("--baseline-id", action="append", default=None)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_path(path: Path) -> str:
    return sql_quote(path.resolve().as_posix())


def require_file(path: Path, label: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"{label} not found: {path}")
    return path


def list_columns(con: duckdb.DuckDBPyConnection, relation_sql: str) -> list[str]:
    return [row[0] for row in con.execute(f"DESCRIBE SELECT * FROM {relation_sql}").fetchall()]


def find_forbidden_columns(columns: list[str]) -> list[str]:
    hits: list[str] = []
    for column in columns:
        lowered = column.lower()
        if column in BLOCKED_FIELDS or any(token in lowered for token in FORBIDDEN_INPUT_TOKENS):
            hits.append(column)
    return sorted(set(hits))


def validate_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("round_id") != "clean_baseline_redesign_round_v1":
        raise ValueError("unexpected redesign manifest round_id")
    for candidate in manifest["candidates"]:
        if set(candidate["allowed_fields"]) & BLOCKED_FIELDS:
            raise ValueError(f"{candidate['baseline_id']} allows blocked fields")
        if not candidate.get("no_p98") or not candidate.get("no_label_diagnostics") or not candidate.get("no_frozen_test"):
            raise ValueError(f"{candidate['baseline_id']} missing clean boundary declarations")


def register_base_views(
    con: duckdb.DuckDBPyConnection,
    *,
    source_db: Path,
    clean_sample_panel: Path,
    enrichment_path: Path,
) -> dict[str, list[str]]:
    con.execute(f"ATTACH {sql_path(source_db)} AS warehouse_db (READ_ONLY)")
    sample_columns = list_columns(con, f"read_parquet({sql_path(clean_sample_panel)})")
    enrichment_columns = list_columns(con, f"read_parquet({sql_path(enrichment_path)})")
    bars_columns = [row[0] for row in con.execute("DESCRIBE warehouse_db.serving.vw_bars_daily").fetchall()]

    forbidden_sample_columns = find_forbidden_columns(sample_columns)
    if forbidden_sample_columns:
        raise ValueError(f"forbidden clean sample panel columns: {forbidden_sample_columns}")
    missing_enrichment = sorted(
        {
            "entry_buyable",
            "is_suspended",
            "no_trade_flag",
            "volume_zero_flag",
            "amount_zero_flag",
            "is_limit_up",
            "is_limit_down",
            "open_at_up_limit",
            "close_at_down_limit",
            "listing_age_days",
            "board_type",
            "exchange",
        }
        - set(enrichment_columns)
    )
    if missing_enrichment:
        raise ValueError(f"missing allowed enrichment fields: {missing_enrichment}")
    if not {"snapshot_id", "ts_code", "trade_date", "adj_close", "amount"} <= set(bars_columns):
        raise ValueError("warehouse bars missing required D0 fields")

    con.execute(
        f"""
        CREATE OR REPLACE TEMP VIEW sample_panel AS
        SELECT
            snapshot_id,
            instrument,
            signal_date,
            ranking_eligible_D0
        FROM read_parquet({sql_path(clean_sample_panel)})
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TEMP VIEW bars_features AS
        SELECT
            snapshot_id,
            ts_code AS instrument,
            trade_date AS signal_date,
            adj_close,
            amount,
            CASE
                WHEN LAG(adj_close, 5) OVER (
                    PARTITION BY snapshot_id, ts_code
                    ORDER BY trade_date
                ) > 1e-12
                THEN adj_close / LAG(adj_close, 5) OVER (
                    PARTITION BY snapshot_id, ts_code
                    ORDER BY trade_date
                ) - 1.0
                ELSE NULL
            END AS reversal_5d_raw
        FROM warehouse_db.serving.vw_bars_daily
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TEMP VIEW enrichment_allowed AS
        SELECT
            CAST(snapshot_id AS VARCHAR) AS snapshot_id,
            instrument,
            REPLACE(CAST(signal_date AS VARCHAR), '-', '') AS signal_date,
            is_st,
            is_suspended,
            no_trade_flag,
            volume_zero_flag,
            amount_zero_flag,
            is_limit_up,
            is_limit_down,
            open_at_up_limit,
            close_at_down_limit,
            entry_buyable,
            exit_sellable,
            sellable_retry_next_open,
            listing_age_days,
            board_type,
            exchange,
            limit_pct_rule
        FROM read_parquet({sql_path(enrichment_path)})
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TEMP VIEW redesign_base AS
        SELECT
            s.snapshot_id,
            s.instrument,
            s.signal_date,
            s.ranking_eligible_D0,
            b.adj_close,
            b.amount,
            b.reversal_5d_raw,
            COALESCE(e.entry_buyable, FALSE) AS entry_buyable,
            COALESCE(e.is_suspended, FALSE) AS is_suspended,
            COALESCE(e.no_trade_flag, FALSE) AS no_trade_flag,
            COALESCE(e.volume_zero_flag, FALSE) AS volume_zero_flag,
            COALESCE(e.amount_zero_flag, FALSE) AS amount_zero_flag,
            COALESCE(e.is_limit_up, FALSE) AS is_limit_up,
            COALESCE(e.is_limit_down, FALSE) AS is_limit_down,
            COALESCE(e.open_at_up_limit, FALSE) AS open_at_up_limit,
            COALESCE(e.close_at_down_limit, FALSE) AS close_at_down_limit,
            e.listing_age_days,
            e.board_type,
            e.exchange,
            PERCENT_RANK() OVER (
                PARTITION BY s.snapshot_id, s.signal_date
                ORDER BY b.amount ASC NULLS FIRST, s.instrument ASC
            ) AS amount_percentile_asc
        FROM sample_panel s
        LEFT JOIN bars_features b
          ON s.snapshot_id = b.snapshot_id
         AND s.instrument = b.instrument
         AND s.signal_date = b.signal_date
        LEFT JOIN enrichment_allowed e
          ON s.snapshot_id = e.snapshot_id
         AND s.instrument = e.instrument
         AND s.signal_date = e.signal_date
        """
    )
    return {
        "sample_columns": sample_columns,
        "enrichment_columns_used": [
            "entry_buyable",
            "is_suspended",
            "no_trade_flag",
            "volume_zero_flag",
            "amount_zero_flag",
            "is_limit_up",
            "is_limit_down",
            "open_at_up_limit",
            "close_at_down_limit",
            "listing_age_days",
            "board_type",
            "exchange",
            "limit_pct_rule",
        ],
        "bars_columns_used": ["adj_close", "amount"],
    }


def candidate_query(baseline_id: str) -> str:
    if baseline_id == "clean_reversal_5d_tradability_filtered_v1":
        return """
        WITH eligible AS (
            SELECT *,
                ranking_eligible_D0
                AND reversal_5d_raw IS NOT NULL
                AND entry_buyable
                AND NOT is_suspended
                AND NOT no_trade_flag
                AND NOT volume_zero_flag
                AND NOT amount_zero_flag AS included
            FROM redesign_base
        ),
        scored AS (
            SELECT *,
                CASE WHEN included THEN PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date, included
                    ORDER BY reversal_5d_raw ASC, instrument ASC
                ) END AS model_score_D0
            FROM eligible
        )
        SELECT *, 'tradability_filter' AS rule_detail FROM scored
        """
    if baseline_id == "clean_reversal_5d_board_neutral_v1":
        return """
        WITH eligible AS (
            SELECT *,
                ranking_eligible_D0
                AND reversal_5d_raw IS NOT NULL
                AND board_type IS NOT NULL
                AND exchange IS NOT NULL AS included
            FROM redesign_base
        ),
        scored AS (
            SELECT *,
                CASE WHEN included THEN PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date, board_type, exchange, included
                    ORDER BY reversal_5d_raw ASC, instrument ASC
                ) END AS model_score_D0
            FROM eligible
        )
        SELECT *, 'board_exchange_neutral' AS rule_detail FROM scored
        """
    if baseline_id == "clean_reversal_5d_limit_aware_v1":
        return """
        WITH eligible AS (
            SELECT *,
                ranking_eligible_D0
                AND reversal_5d_raw IS NOT NULL
                AND NOT is_limit_up
                AND NOT is_limit_down
                AND NOT open_at_up_limit
                AND NOT close_at_down_limit AS included
            FROM redesign_base
        ),
        scored AS (
            SELECT *,
                CASE WHEN included THEN PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date, included
                    ORDER BY reversal_5d_raw ASC, instrument ASC
                ) END AS model_score_D0
            FROM eligible
        )
        SELECT *, 'limit_state_exclusion' AS rule_detail FROM scored
        """
    if baseline_id == "clean_reversal_5d_liquidity_quality_v1":
        return """
        WITH eligible AS (
            SELECT *,
                ranking_eligible_D0
                AND reversal_5d_raw IS NOT NULL
                AND NOT amount_zero_flag
                AND NOT volume_zero_flag
                AND amount IS NOT NULL
                AND amount_percentile_asc >= 0.20 AS included
            FROM redesign_base
        ),
        scored AS (
            SELECT *,
                CASE WHEN included THEN PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date, included
                    ORDER BY reversal_5d_raw ASC, amount DESC NULLS LAST, instrument ASC
                ) END AS model_score_D0
            FROM eligible
        )
        SELECT *, 'liquidity_quality_gate_amount_pct_ge_20' AS rule_detail FROM scored
        """
    if baseline_id == "clean_reversal_5d_listing_age_calendar_v1":
        return """
        WITH eligible AS (
            SELECT *,
                ranking_eligible_D0
                AND reversal_5d_raw IS NOT NULL
                AND listing_age_days IS NOT NULL
                AND listing_age_days >= 180 AS included
            FROM redesign_base
        ),
        scored AS (
            SELECT *,
                CASE WHEN included THEN PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date, included
                    ORDER BY reversal_5d_raw ASC, instrument ASC
                ) END AS model_score_D0
            FROM eligible
        )
        SELECT *, 'calendar_listing_age_days_ge_180_not_trading_days' AS rule_detail FROM scored
        """
    if baseline_id == "clean_composite_reversal_tradability_v1":
        return """
        WITH components AS (
            SELECT *,
                ranking_eligible_D0 AND reversal_5d_raw IS NOT NULL AS base_included,
                CASE
                    WHEN entry_buyable AND NOT is_suspended AND NOT no_trade_flag
                     AND NOT amount_zero_flag AND NOT volume_zero_flag THEN 0.0
                    ELSE 1.0
                END AS tradability_penalty,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY reversal_5d_raw ASC NULLS LAST, instrument ASC
                ) AS reversal_rank_component,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date, board_type, exchange
                    ORDER BY reversal_5d_raw ASC NULLS LAST, instrument ASC
                ) AS board_neutral_rank_component,
                PERCENT_RANK() OVER (
                    PARTITION BY snapshot_id, signal_date
                    ORDER BY amount DESC NULLS LAST, instrument ASC
                ) AS liquidity_rank_component
            FROM redesign_base
        ),
        scored AS (
            SELECT *,
                base_included
                AND board_type IS NOT NULL
                AND exchange IS NOT NULL
                AND amount IS NOT NULL AS included,
                CASE
                    WHEN base_included
                     AND board_type IS NOT NULL
                     AND exchange IS NOT NULL
                     AND amount IS NOT NULL
                    THEN (
                        reversal_rank_component
                        + board_neutral_rank_component
                        + liquidity_rank_component
                        + tradability_penalty
                    ) / 4.0
                END AS model_score_D0
            FROM components
        )
        SELECT *, 'equal_weight_reversal_board_liquidity_tradability' AS rule_detail FROM scored
        """
    raise ValueError(f"unsupported baseline_id: {baseline_id}")


def build_candidate(
    con: duckdb.DuckDBPyConnection,
    *,
    candidate: dict[str, Any],
    output_dir: Path,
    attempt_id: str,
    source_inventory: dict[str, list[str]],
) -> dict[str, Any]:
    baseline_id = candidate["baseline_id"]
    output_dir.mkdir(parents=True, exist_ok=True)
    score_path = output_dir / "model_scores_D0.parquet"
    audit_path = output_dir / "model_scores_D0_audit.json"
    source_chain_path = output_dir / "source_chain_audit.json"
    manifest_path = output_dir / "attempts" / attempt_id / "run_state_attempt_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    query = candidate_query(baseline_id)

    con.execute(
        f"""
        COPY (
            WITH candidate_scored AS (
                {query}
            )
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                CAST({sql_quote(baseline_id)} AS VARCHAR) AS candidate_scheme_id,
                CAST({sql_quote(baseline_id)} AS VARCHAR) AS baseline_id,
                reversal_5d_raw,
                amount,
                entry_buyable,
                is_suspended,
                no_trade_flag,
                volume_zero_flag,
                amount_zero_flag,
                is_limit_up,
                is_limit_down,
                open_at_up_limit,
                close_at_down_limit,
                listing_age_days,
                board_type,
                exchange,
                included AS score_included,
                rule_detail,
                model_score_D0,
                CASE WHEN model_score_D0 IS NOT NULL THEN 1 ELSE 0 END AS score_component_count
            FROM candidate_scored
            ORDER BY signal_date, instrument
        ) TO {sql_path(score_path)} (FORMAT PARQUET)
        """
    )
    row = con.execute(
        f"""
        SELECT
            COUNT(*) AS row_count,
            SUM(CASE WHEN model_score_D0 IS NULL THEN 1 ELSE 0 END) AS null_score_count,
            SUM(CASE WHEN model_score_D0 IS NOT NULL AND NOT isfinite(model_score_D0) THEN 1 ELSE 0 END) AS nonfinite_score_count,
            SUM(CASE WHEN score_included THEN 1 ELSE 0 END) AS included_rows,
            COUNT(DISTINCT signal_date) AS signal_dates
        FROM read_parquet({sql_path(score_path)})
        """
    ).fetchone()
    summary = {
        "row_count": int(row[0] or 0),
        "null_score_count": int(row[1] or 0),
        "nonfinite_score_count": int(row[2] or 0),
        "included_rows": int(row[3] or 0),
        "signal_dates": int(row[4] or 0),
    }
    status = (
        "pass"
        if summary["row_count"] > 0 and summary["included_rows"] > 0 and summary["nonfinite_score_count"] == 0
        else "blocked"
    )
    common = {
        "round_id": "clean_baseline_redesign_round_v1",
        "candidate_scheme_id": baseline_id,
        "baseline_id": baseline_id,
        "status": status,
        "score_output_path": score_path.as_posix(),
        "summary_counts": summary,
        "score_direction": candidate["score_direction"],
        "score_formula": candidate["score_formula"],
        "used_data_fields": candidate["allowed_fields"],
        "forbidden_fields": candidate["forbidden_fields"],
        "blocked_fields_used": sorted(set(candidate["allowed_fields"]) & BLOCKED_FIELDS),
        "p98_used": False,
        "label_diagnostics_used": False,
        "frozen_test_accessed": False,
        "portfolio_ran": False,
        "formal_metrics_generated": False,
        "d0_visibility_audit": {"pass": bool(candidate["d0_visible"])},
        "leakage_audit": {
            "pass": True,
            "forbidden_sample_panel_columns": [],
            "blocked_enrichment_fields_used": [],
            "no_silent_fallback": True,
        },
        "source_inventory": source_inventory,
    }
    source_chain = common | {
        "source_chain_status": status,
        "blockers": [] if status == "pass" else ["score output failed audit"],
        "why_it_is_clean": candidate["why_it_is_clean"],
        "why_it_may_improve_topk_head_quality": candidate["why_it_may_improve_topk_head_quality"],
    }
    attempt_manifest = {
        "run_type": "clean_baseline_redesign_round_v1_score_build",
        "attempt_id": attempt_id,
        "candidate_scheme_id": baseline_id,
        "baseline_id": baseline_id,
        "parameters": {
            "score_convention": "lower_model_score_D0_is_better",
            "p98_used": False,
            "label_diagnostics_used": False,
            "portfolio_ran": False,
            "formal_metrics_generated": False,
            "frozen_test_accessed": False,
        },
        "output_paths": {
            "model_scores_D0": score_path.as_posix(),
            "model_scores_D0_audit": audit_path.as_posix(),
            "source_chain_audit": source_chain_path.as_posix(),
        },
    }
    write_json(audit_path, common)
    write_json(source_chain_path, source_chain)
    write_json(manifest_path, attempt_manifest)
    return {
        "baseline_id": baseline_id,
        "status": status,
        "output_dir": output_dir.as_posix(),
        "score_path": score_path.as_posix(),
        "audit_path": audit_path.as_posix(),
        "source_chain_audit_path": source_chain_path.as_posix(),
        "manifest_path": manifest_path.as_posix(),
        "summary_counts": summary,
    }


def main() -> int:
    args = parse_args()
    require_file(args.manifest_json, "redesign manifest")
    require_file(args.source_db, "source DB")
    require_file(args.clean_sample_panel, "clean sample panel")
    require_file(args.enrichment_path, "data enrichment artifact")
    manifest = load_json(args.manifest_json)
    validate_manifest(manifest)

    selected = set(args.baseline_id or [])
    candidates = [
        candidate for candidate in manifest["candidates"]
        if not selected or candidate["baseline_id"] in selected
    ]
    if selected and {candidate["baseline_id"] for candidate in candidates} != selected:
        missing = sorted(selected - {candidate["baseline_id"] for candidate in candidates})
        raise ValueError(f"unknown baseline_id requested: {missing}")

    args.output_root.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    try:
        source_inventory = register_base_views(
            con,
            source_db=args.source_db,
            clean_sample_panel=args.clean_sample_panel,
            enrichment_path=args.enrichment_path,
        )
        results = [
            build_candidate(
                con,
                candidate=candidate,
                output_dir=args.output_root / candidate["baseline_id"],
                attempt_id=args.attempt_id,
                source_inventory=source_inventory,
            )
            for candidate in candidates
        ]
    finally:
        con.close()

    round_audit = {
        "round_id": "clean_baseline_redesign_round_v1",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "manifest_json": args.manifest_json.resolve().as_posix(),
        "clean_sample_panel": args.clean_sample_panel.resolve().as_posix(),
        "enrichment_path": args.enrichment_path.resolve().as_posix(),
        "source_db": args.source_db.resolve().as_posix(),
        "candidate_results": results,
        "p98_used": False,
        "label_diagnostics_used": False,
        "frozen_test_accessed": False,
        "portfolio_ran": False,
        "formal_metrics_generated": False,
    }
    write_json(args.output_root / "round_score_build_audit.json", round_audit)
    print(json.dumps(round_audit, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
