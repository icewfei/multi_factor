#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Build minimal portfolio-layer artifacts from run-state outputs.

Inputs:
- artifacts/run_state/<run_id>/attempts/<attempt_id>/ranking_state_daily.parquet
- artifacts/run_state/<run_id>/attempts/<attempt_id>/execution_state_daily.parquet
- artifacts/run_state/<run_id>/project_execution_panel.parquet

Outputs:
- attempts/<attempt_id>/holdings.csv
- attempts/<attempt_id>/portfolio_weights_daily.csv
- attempts/<attempt_id>/portfolio_daily_summary.csv
- attempts/<attempt_id>/turnover_daily.csv
- attempts/<attempt_id>/portfolio_artifacts_manifest.json

Notes:
- This is a minimum portfolio-layer skeleton, not a full fixed-test engine.
- To keep daily overlapping 5-day cohorts on a bounded capital base, actual portfolio
  weights use `cohort_capital_fraction = 1 / holding_cohort_count`, where the default
  holding cohort count is 5 for the v1 framework.
- `industry_active_weight_max` remains NULL until the style / industry exposure layer
  is implemented.
- `turnover_daily` is weight-notional turnover on normalized equity; it assumes
  `lag_total_equity = 1.0` until a full equity curve is implemented.
- All `*_weight` fields in this script are normalized portfolio weights on a `0-1`
  basis. They are not percentages and they are not currency notionals.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime
from pathlib import Path
from bisect import bisect_right

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
ARTIFACTS_RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
CONTRACTS_DIR = ROOT / "contracts"
RESEARCH_ROUNDS_DIR = ROOT / "artifacts" / "research_registry" / "research_rounds"
UNRESOLVED_EXIT_BLOCKED_MESSAGE = (
    "Found backtest_executable positions with actual_exit_date = NULL; "
    "unresolved exit would cause holdings/portfolio path mismatch."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build minimal portfolio-layer artifacts.")
    parser.add_argument("--run-id", required=True, help="Project-side run identifier.")
    parser.add_argument(
        "--input-dir",
        default=None,
        help="Optional run-state directory. Defaults to artifacts/run_state/<run_id>/",
    )
    parser.add_argument(
        "--attempt-id",
        default=None,
        help="Optional attempt identifier. Defaults to run_state_latest_attempt.json.",
    )
    parser.add_argument(
        "--holding-cohort-count",
        type=int,
        default=None,
        help=(
            "Optional capital tranche count for overlapping holding cohorts. "
            "If omitted, the script auto-detects the maximum concurrent signal-date cohorts."
        ),
    )
    parser.add_argument(
        "--run-input-contract",
        default=None,
        help="Optional explicit run input contract JSON path. Defaults to contracts/run_input_contract.current.json",
    )
    return parser.parse_args()


def resolve_run_dir(run_id: str, input_dir: str | None) -> Path:
    run_dir = Path(input_dir) if input_dir else (ARTIFACTS_RUN_STATE_DIR / run_id)
    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")
    return run_dir


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def atomic_json_write(path: Path, payload: dict) -> None:
    temp_path = path.with_suffix(path.suffix + ".inprogress")
    write_json(temp_path, payload)
    os.replace(temp_path, path)


def sql_quote(value: str | None) -> str:
    if value is None:
        return "NULL"
    return "'" + value.replace("'", "''") + "'"


def sql_path(path: Path) -> str:
    return sql_quote(path.resolve().as_posix())


def require_path(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Required input file not found: {path}")
    return path


def resolve_attempt_dir(run_dir: Path, attempt_id: str | None) -> tuple[str, Path]:
    if attempt_id:
        resolved_attempt_id = attempt_id
    else:
        latest_pointer = require_path(run_dir / "run_state_latest_attempt.json")
        latest_payload = load_json(latest_pointer)
        resolved_attempt_id = latest_payload["attempt_id"]

    attempt_dir = require_path(run_dir / "attempts" / resolved_attempt_id)
    return resolved_attempt_id, attempt_dir


def atomic_csv_copy(con: duckdb.DuckDBPyConnection, query: str, output_path: Path) -> None:
    temp_path = output_path.with_suffix(output_path.suffix + ".inprogress")
    if temp_path.exists():
        temp_path.unlink()
    con.execute(
        f"""
        COPY (
            {query}
        ) TO {sql_path(temp_path)}
        (HEADER, DELIMITER ',', FORCE_QUOTE *)
        """
    )
    os.replace(temp_path, output_path)


def ensure_no_unresolved_backtest_exits(con: duckdb.DuckDBPyConnection) -> None:
    unresolved_rows = con.execute(
        """
        SELECT COUNT(*)
        FROM pre_holdings_positions_t
        WHERE backtest_executable
          AND actual_exit_date IS NULL
        """
    ).fetchone()[0]
    unresolved_rows_int = int(unresolved_rows or 0)
    if unresolved_rows_int == 0:
        return

    sample_rows = con.execute(
        """
        SELECT signal_date, instrument
        FROM pre_holdings_positions_t
        WHERE backtest_executable
          AND actual_exit_date IS NULL
        ORDER BY signal_date, instrument
        LIMIT 5
        """
    ).fetchall()
    sample_positions = ", ".join(f"{signal_date}/{instrument}" for signal_date, instrument in sample_rows)
    raise ValueError(
        f"{UNRESOLVED_EXIT_BLOCKED_MESSAGE} "
        f"unresolved_rows={unresolved_rows_int}; sample_positions=[{sample_positions}]"
    )


def load_preregistration(research_round_id: str | None) -> dict | None:
    if not research_round_id:
        return None
    prereg_path = RESEARCH_ROUNDS_DIR / research_round_id / "preregistration.json"
    if not prereg_path.exists():
        return None
    return load_json(prereg_path)


def parse_weight_mapping_contract(preregistration: dict | None) -> dict | None:
    if not isinstance(preregistration, dict):
        return None
    if preregistration.get("changed_dimension") != "weight_mapping":
        return None
    contract = preregistration.get("weight_mapping_contract")
    if not isinstance(contract, dict):
        raise ValueError(
            "weight_mapping preregistration must include a weight_mapping_contract object."
        )

    mapping_name = contract.get("mapping_name")
    liquidity_rank_field = contract.get("liquidity_rank_field")
    intercept = contract.get("intercept")
    slope = contract.get("slope")
    null_rank_fallback = contract.get("null_rank_fallback")
    normalization = contract.get("normalization")
    if not isinstance(mapping_name, str) or not mapping_name.strip():
        raise ValueError("weight_mapping_contract.mapping_name must be a non-empty string.")
    if liquidity_rank_field != "liquidity_rank":
        raise ValueError(
            "Only weight_mapping_contract.liquidity_rank_field = 'liquidity_rank' is supported."
        )
    if not isinstance(intercept, (int, float)) or not isinstance(slope, (int, float)):
        raise ValueError("weight_mapping_contract intercept and slope must be numeric.")
    if not isinstance(null_rank_fallback, (int, float)):
        raise ValueError("weight_mapping_contract.null_rank_fallback must be numeric.")
    if normalization != "same_signal_date_topk_sum_to_1":
        raise ValueError(
            "Only weight_mapping_contract.normalization = 'same_signal_date_topk_sum_to_1' "
            "is supported."
        )

    return {
        "mapping_name": mapping_name.strip(),
        "liquidity_rank_field": "liquidity_rank",
        "intercept": float(intercept),
        "slope": float(slope),
        "null_rank_fallback": float(null_rank_fallback),
        "normalization": normalization,
    }


def parse_portfolio_extraction_contract(preregistration: dict | None) -> dict | None:
    if not isinstance(preregistration, dict):
        return None
    if preregistration.get("changed_dimension") == "portfolio_extraction":
        contract = preregistration.get("portfolio_extraction_contract")
    else:
        contract = preregistration.get("portfolio_extraction_contract_frozen")
        if contract is None:
            return None
    if not isinstance(contract, dict):
        raise ValueError(
            "portfolio_extraction preregistration must include a portfolio_extraction_contract object."
        )

    extraction_name = contract.get("extraction_name")
    rank_field = contract.get("rank_field")
    head_size = contract.get("head_size")
    weight_formula = contract.get("weight_formula")
    normalization = contract.get("normalization")
    bucket_weights = contract.get("bucket_weights")
    stability_cap_type = contract.get("stability_cap_type")
    max_daily_weight_change_per_instrument = contract.get("max_daily_weight_change_per_instrument")
    previous_weight_reference = contract.get("previous_weight_reference")
    if not isinstance(extraction_name, str) or not extraction_name.strip():
        raise ValueError("portfolio_extraction_contract.extraction_name must be a non-empty string.")
    if rank_field != "rank_position":
        raise ValueError(
            "Only portfolio_extraction_contract.rank_field = 'rank_position' is supported."
        )
    if not isinstance(head_size, int) or head_size <= 0:
        raise ValueError("portfolio_extraction_contract.head_size must be a positive integer.")
    if weight_formula not in {"linear_rank_decay", "piecewise_bucket"}:
        raise ValueError(
            "Only portfolio_extraction_contract.weight_formula in "
            "{'linear_rank_decay', 'piecewise_bucket'} is supported."
        )
    if normalization != "same_signal_date_selected_head_sum_to_1":
        raise ValueError(
            "Only portfolio_extraction_contract.normalization = "
            "'same_signal_date_selected_head_sum_to_1' is supported."
        )

    parsed_contract = {
        "extraction_name": extraction_name.strip(),
        "rank_field": "rank_position",
        "head_size": int(head_size),
        "weight_formula": weight_formula,
        "normalization": normalization,
        "bucket_weights": None,
        "stability_cap_type": None,
        "max_daily_weight_change_per_instrument": None,
        "previous_weight_reference": None,
    }
    if weight_formula == "piecewise_bucket":
        if not isinstance(bucket_weights, list) or not bucket_weights:
            raise ValueError(
                "portfolio_extraction_contract.bucket_weights must be a non-empty list "
                "when weight_formula = 'piecewise_bucket'."
            )
        parsed_buckets: list[dict] = []
        expected_rank = 1
        total_bucket_slots = 0
        for bucket in bucket_weights:
            if not isinstance(bucket, dict):
                raise ValueError("Each piecewise bucket must be an object.")
            rank_from = bucket.get("rank_from")
            rank_to = bucket.get("rank_to")
            per_name_weight = bucket.get("per_name_weight")
            if (
                not isinstance(rank_from, int)
                or not isinstance(rank_to, int)
                or rank_from <= 0
                or rank_to < rank_from
            ):
                raise ValueError("Each piecewise bucket must define valid rank_from/rank_to.")
            if rank_from != expected_rank:
                raise ValueError("piecewise_bucket definitions must be contiguous from rank 1.")
            if not isinstance(per_name_weight, (int, float)) or float(per_name_weight) <= 0.0:
                raise ValueError("Each piecewise bucket must define positive per_name_weight.")
            parsed_buckets.append(
                {
                    "rank_from": rank_from,
                    "rank_to": rank_to,
                    "per_name_weight": float(per_name_weight),
                }
            )
            expected_rank = rank_to + 1
            total_bucket_slots += rank_to - rank_from + 1
        if total_bucket_slots != int(head_size):
            raise ValueError(
                "piecewise_bucket weights must cover exactly head_size ranks without gaps or extras."
            )
        parsed_contract["bucket_weights"] = parsed_buckets
    if stability_cap_type is not None:
        if stability_cap_type != "absolute_daily_weight_change_cap":
            raise ValueError(
                "Only portfolio_extraction_contract.stability_cap_type = "
                "'absolute_daily_weight_change_cap' is supported."
            )
        if not isinstance(max_daily_weight_change_per_instrument, (int, float)):
            raise ValueError(
                "portfolio_extraction_contract.max_daily_weight_change_per_instrument must be numeric."
            )
        if previous_weight_reference != "previous_signal_date_mapped_target_weight":
            raise ValueError(
                "Only portfolio_extraction_contract.previous_weight_reference = "
                "'previous_signal_date_mapped_target_weight' is supported."
            )
        max_change = float(max_daily_weight_change_per_instrument)
        if max_change <= 0.0 or max_change > 1.0:
            raise ValueError(
                "portfolio_extraction_contract.max_daily_weight_change_per_instrument must be "
                "within (0, 1]."
            )
        parsed_contract["stability_cap_type"] = stability_cap_type
        parsed_contract["max_daily_weight_change_per_instrument"] = max_change
        parsed_contract["previous_weight_reference"] = previous_weight_reference

    return parsed_contract


def solve_box_constrained_simplex_projection(
    raw_weights: list[float],
    lower_bounds: list[float],
    upper_bounds: list[float],
) -> list[float]:
    if not raw_weights:
        return []
    lower_sum = sum(lower_bounds)
    upper_sum = sum(upper_bounds)
    if lower_sum > 1.0 + 1e-9 or upper_sum < 1.0 - 1e-9:
        raise ValueError("Infeasible stability-cap bounds for simplex projection.")

    def projected_sum(lam: float) -> float:
        total = 0.0
        for raw_weight, lower, upper in zip(raw_weights, lower_bounds, upper_bounds):
            total += min(max(raw_weight - lam, lower), upper)
        return total

    lo = min(raw_weights[i] - upper_bounds[i] for i in range(len(raw_weights))) - 1.0
    hi = max(raw_weights[i] - lower_bounds[i] for i in range(len(raw_weights))) + 1.0
    for _ in range(100):
        mid = (lo + hi) / 2.0
        if projected_sum(mid) > 1.0:
            lo = mid
        else:
            hi = mid
    lam = (lo + hi) / 2.0
    projected = [
        min(max(raw_weight - lam, lower), upper)
        for raw_weight, lower, upper in zip(raw_weights, lower_bounds, upper_bounds)
    ]
    total = sum(projected)
    if total <= 0.0:
        raise ValueError("Projected stability-capped weights summed to zero.")
    adjustment = 1.0 - total
    if abs(adjustment) > 1e-9:
        slack_indices: list[int] = []
        slack_values: list[float] = []
        for index, value in enumerate(projected):
            slack = (
                upper_bounds[index] - value
                if adjustment > 0.0
                else value - lower_bounds[index]
            )
            if slack > 1e-12:
                slack_indices.append(index)
                slack_values.append(slack)
        slack_total = sum(slack_values)
        if slack_total > 0.0:
            for index, slack in zip(slack_indices, slack_values):
                projected[index] += adjustment * (slack / slack_total)
    total = sum(projected)
    if total <= 0.0:
        raise ValueError("Stability-capped weights remain invalid after normalization.")
    return [value / total for value in projected]


def compute_extraction_weights_for_selected_count(
    selected_count: int,
    portfolio_extraction_contract: dict | None,
) -> list[float]:
    if selected_count <= 0:
        return []
    if portfolio_extraction_contract is None:
        return [1.0 / float(selected_count)] * selected_count

    head_size = int(portfolio_extraction_contract["head_size"])
    active_count = min(selected_count, head_size)
    weight_formula = portfolio_extraction_contract["weight_formula"]
    raw_weights: list[float] = []
    if weight_formula == "linear_rank_decay":
        decay_denominator = 1.0 if head_size == 1 else float(head_size - 1)
        for selected_rank in range(1, active_count + 1):
            raw_weights.append(1.0 - ((selected_rank - 1) * (0.9 / decay_denominator)))
    elif weight_formula == "piecewise_bucket":
        bucket_weights = portfolio_extraction_contract.get("bucket_weights") or []
        for selected_rank in range(1, active_count + 1):
            matched_weight = 0.0
            for bucket in bucket_weights:
                if bucket["rank_from"] <= selected_rank <= bucket["rank_to"]:
                    matched_weight = float(bucket["per_name_weight"])
                    break
            raw_weights.append(matched_weight)
    else:
        raise ValueError(f"Unsupported extraction weight formula: {weight_formula}")

    raw_sum = sum(raw_weights)
    if raw_sum <= 0.0:
        return [1.0 / float(selected_count)] * selected_count

    normalized = [value / raw_sum for value in raw_weights]
    if selected_count > active_count:
        normalized.extend([0.0] * (selected_count - active_count))
    return normalized


def _parse_portfolio_refresh_contract_object(contract: dict | None) -> dict | None:
    if contract is None:
        return None
    if not isinstance(contract, dict):
        raise ValueError(
            "portfolio refresh preregistration must include a portfolio_refresh_contract object."
        )

    refresh_rule_name = contract.get("refresh_rule_name")
    reference_rank_field = contract.get("reference_rank_field")
    retain_if_rank_leq = contract.get("retain_if_rank_leq")
    retain_if_guard_still_passes = contract.get("retain_if_guard_still_passes")
    retain_if_entry_tradeable = contract.get("retain_if_entry_tradeable")
    max_holdings = contract.get("max_holdings")
    target_weight_rule = contract.get("target_weight_rule")
    lock_duration = contract.get("lock_duration_signal_dates")

    if not isinstance(refresh_rule_name, str) or not refresh_rule_name.strip():
        raise ValueError(
            "portfolio_refresh_contract.refresh_rule_name must be a non-empty string."
        )

    if refresh_rule_name == "cohort_entry_locked":
        if not isinstance(lock_duration, int) or lock_duration <= 0:
            raise ValueError(
                "portfolio_refresh_contract.lock_duration_signal_dates must be a positive integer."
            )
        if retain_if_guard_still_passes is not True:
            raise ValueError(
                "Only portfolio_refresh_contract.retain_if_guard_still_passes = true is supported."
            )
        if retain_if_entry_tradeable is not True:
            raise ValueError(
                "Only portfolio_refresh_contract.retain_if_entry_tradeable = true is supported."
            )
        if not isinstance(max_holdings, int) or max_holdings <= 0:
            raise ValueError("portfolio_refresh_contract.max_holdings must be a positive integer.")
        if target_weight_rule != "Equal-weight across currently held names after refresh; unfilled slots remain cash.":
            raise ValueError(
                "Only the preregistered equal-weight refresh target_weight_rule is supported."
            )
        return {
            "refresh_rule_name": "cohort_entry_locked",
            "lock_duration_signal_dates": int(lock_duration),
            "retain_if_guard_still_passes": True,
            "retain_if_entry_tradeable": True,
            "max_holdings": int(max_holdings),
            "target_weight_rule": target_weight_rule,
        }

    if reference_rank_field != "rank_position":
        raise ValueError(
            "Only portfolio_refresh_contract.reference_rank_field = 'rank_position' is supported."
        )
    if not isinstance(retain_if_rank_leq, int) or retain_if_rank_leq <= 0:
        raise ValueError(
            "portfolio_refresh_contract.retain_if_rank_leq must be a positive integer."
        )
    if retain_if_guard_still_passes is not True:
        raise ValueError(
            "Only portfolio_refresh_contract.retain_if_guard_still_passes = true is supported."
        )
    if retain_if_entry_tradeable is not True:
        raise ValueError(
            "Only portfolio_refresh_contract.retain_if_entry_tradeable = true is supported."
        )
    if not isinstance(max_holdings, int) or max_holdings <= 0:
        raise ValueError("portfolio_refresh_contract.max_holdings must be a positive integer.")
    if target_weight_rule != "Equal-weight across currently held names after refresh; unfilled slots remain cash.":
        raise ValueError(
            "Only the preregistered equal-weight refresh target_weight_rule is supported."
        )

    return {
        "refresh_rule_name": refresh_rule_name.strip(),
        "reference_rank_field": "rank_position",
        "retain_if_rank_leq": int(retain_if_rank_leq),
        "retain_if_guard_still_passes": True,
        "retain_if_entry_tradeable": True,
        "max_holdings": int(max_holdings),
        "target_weight_rule": target_weight_rule,
    }


def parse_portfolio_refresh_contract(preregistration: dict | None) -> dict | None:
    if not isinstance(preregistration, dict):
        return None
    if preregistration.get("changed_dimension") == "portfolio_refresh_rule":
        return _parse_portfolio_refresh_contract_object(
            preregistration.get("portfolio_refresh_contract")
        )
    return _parse_portfolio_refresh_contract_object(
        preregistration.get("portfolio_refresh_contract_frozen")
    )


def main() -> None:
    args = parse_args()
    if args.holding_cohort_count is not None and args.holding_cohort_count <= 0:
        raise ValueError("--holding-cohort-count must be positive.")

    run_dir = resolve_run_dir(args.run_id, args.input_dir)
    attempt_id, attempt_dir = resolve_attempt_dir(run_dir, args.attempt_id)

    execution_state = require_path(attempt_dir / "execution_state_daily.parquet")
    ranking_state = require_path(attempt_dir / "ranking_state_daily.parquet")
    project_execution_panel = require_path(run_dir / "project_execution_panel.parquet")
    attempt_manifest_path = require_path(attempt_dir / "run_state_attempt_manifest.json")
    attempt_manifest = load_json(attempt_manifest_path)
    preregistration = load_preregistration(attempt_manifest.get("research_round_id"))
    weight_mapping_contract = parse_weight_mapping_contract(preregistration)
    portfolio_extraction_contract = parse_portfolio_extraction_contract(preregistration)
    portfolio_refresh_contract = parse_portfolio_refresh_contract(preregistration)
    model_scores_path = run_dir / "model_scores_D0.parquet"
    if weight_mapping_contract is not None:
        require_path(model_scores_path)

    run_input_contract_path = (
        Path(args.run_input_contract)
        if args.run_input_contract
        else (CONTRACTS_DIR / "run_input_contract.current.json")
    )
    run_input = load_json(run_input_contract_path)
    source_db_path = Path(run_input["source_root"]["snapshot_path"]) / "duckdb" / "warehouse.duckdb"
    require_path(source_db_path)

    holdings_path = attempt_dir / "holdings.csv"
    weights_path = attempt_dir / "portfolio_weights_daily.csv"
    summary_path = attempt_dir / "portfolio_daily_summary.csv"
    turnover_path = attempt_dir / "turnover_daily.csv"
    manifest_path = attempt_dir / "portfolio_artifacts_manifest.json"

    con = duckdb.connect()
    derived_holding_cohort_count: int | None = None
    cohort_fraction: float | None = None
    row_counts: tuple[int, int, int, int, float] | None = None
    weight_sanity: tuple[float | None, float | None, int | None, int | None] | None = None
    try:
        con.execute(f"ATTACH {sql_path(source_db_path)} AS warehouse_db (READ_ONLY)")
        con.execute(
            f"""
            CREATE OR REPLACE VIEW execution_state_t AS
            SELECT * FROM read_parquet({sql_path(execution_state)})
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW ranking_state_t AS
            SELECT * FROM read_parquet({sql_path(ranking_state)})
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW project_execution_panel_t AS
            SELECT * FROM read_parquet({sql_path(project_execution_panel)})
            """
        )
        if weight_mapping_contract is not None:
            con.execute(
                f"""
                CREATE OR REPLACE VIEW model_scores_t AS
                SELECT * FROM read_parquet({sql_path(model_scores_path)})
                """
            )
        con.execute(
            """
            CREATE OR REPLACE VIEW calendar_t AS
            SELECT
                trade_date,
                next_trade_date_1,
                next_trade_date_5
            FROM warehouse_db.serving.vw_calendar
            """
        )

        if (
            weight_mapping_contract is None
            and portfolio_extraction_contract is None
            and portfolio_refresh_contract is None
        ):
            con.execute(
                """
                CREATE OR REPLACE VIEW mapped_execution_targets_t AS
                SELECT
                    e.run_id,
                    e.attempt_id,
                    e.run_type,
                    e.snapshot_id,
                    e.instrument,
                    e.signal_date,
                    e.target_weight_D0 AS mapped_target_weight_D0,
                    1.0::DOUBLE AS weight_mapping_multiplier
                FROM execution_state_t e
                """
            )
        elif weight_mapping_contract is not None:
            intercept = weight_mapping_contract["intercept"]
            slope = weight_mapping_contract["slope"]
            null_rank_fallback = weight_mapping_contract["null_rank_fallback"]
            con.execute(
                f"""
                CREATE OR REPLACE VIEW mapped_execution_targets_t AS
                WITH scored_topk AS (
                    SELECT
                        e.run_id,
                        e.attempt_id,
                        e.run_type,
                        e.snapshot_id,
                        e.instrument,
                        e.signal_date,
                        e.target_weight_D0 AS base_target_weight_D0,
                        COALESCE(s.liquidity_rank, {null_rank_fallback}::DOUBLE) AS liquidity_rank_for_weighting,
                        ({intercept}::DOUBLE + {slope}::DOUBLE * COALESCE(s.liquidity_rank, {null_rank_fallback}::DOUBLE)) AS weight_mapping_multiplier
                    FROM execution_state_t e
                    INNER JOIN ranking_state_t r
                        ON e.run_id = r.run_id
                       AND e.attempt_id = r.attempt_id
                       AND e.snapshot_id = r.snapshot_id
                       AND e.instrument = r.instrument
                       AND e.signal_date = r.signal_date
                    INNER JOIN model_scores_t s
                        ON e.snapshot_id = s.snapshot_id
                       AND e.instrument = s.instrument
                       AND e.signal_date = s.signal_date
                    WHERE r.topk_frozen_D0
                ),
                normalized AS (
                    SELECT
                        run_id,
                        attempt_id,
                        run_type,
                        snapshot_id,
                        instrument,
                        signal_date,
                        weight_mapping_multiplier,
                        base_target_weight_D0 * weight_mapping_multiplier AS raw_weight,
                        SUM(base_target_weight_D0 * weight_mapping_multiplier) OVER (
                            PARTITION BY run_id, attempt_id, signal_date
                        ) AS raw_weight_sum
                    FROM scored_topk
                )
                SELECT
                    e.run_id,
                    e.attempt_id,
                    e.run_type,
                    e.snapshot_id,
                    e.instrument,
                    e.signal_date,
                    CASE
                        WHEN n.raw_weight_sum IS NULL OR n.raw_weight_sum <= 0.0 THEN e.target_weight_D0
                        ELSE n.raw_weight / n.raw_weight_sum
                    END AS mapped_target_weight_D0,
                    COALESCE(n.weight_mapping_multiplier, 1.0::DOUBLE) AS weight_mapping_multiplier
                FROM execution_state_t e
                LEFT JOIN normalized n
                    ON e.run_id = n.run_id
                   AND e.attempt_id = n.attempt_id
                   AND e.snapshot_id = n.snapshot_id
                   AND e.instrument = n.instrument
                   AND e.signal_date = n.signal_date
                """
            )
        elif portfolio_extraction_contract is not None:
            head_size = portfolio_extraction_contract["head_size"]
            if head_size == 1:
                decay_denominator = 1.0
            else:
                decay_denominator = float(head_size - 1)
            stability_cap_type = portfolio_extraction_contract.get("stability_cap_type")
            if stability_cap_type is None:
                con.execute(
                    f"""
                    CREATE OR REPLACE VIEW mapped_execution_targets_t AS
                    WITH selected_head AS (
                        SELECT
                            e.run_id,
                            e.attempt_id,
                            e.run_type,
                            e.snapshot_id,
                            e.instrument,
                            e.signal_date,
                            e.target_weight_D0 AS base_target_weight_D0,
                            r.rank_position,
                            CASE
                                WHEN r.rank_position IS NULL OR r.rank_position > {head_size} THEN 0.0
                                ELSE 1.0 - ((r.rank_position - 1) * (0.9 / {decay_denominator}))
                            END AS extraction_multiplier
                        FROM execution_state_t e
                        INNER JOIN ranking_state_t r
                            ON e.run_id = r.run_id
                           AND e.attempt_id = r.attempt_id
                           AND e.snapshot_id = r.snapshot_id
                           AND e.instrument = r.instrument
                           AND e.signal_date = r.signal_date
                        WHERE r.topk_frozen_D0
                    ),
                    normalized AS (
                        SELECT
                            run_id,
                            attempt_id,
                            run_type,
                            snapshot_id,
                            instrument,
                            signal_date,
                            rank_position,
                            extraction_multiplier AS weight_mapping_multiplier,
                            base_target_weight_D0 * extraction_multiplier AS raw_weight,
                            SUM(base_target_weight_D0 * extraction_multiplier) OVER (
                                PARTITION BY run_id, attempt_id, signal_date
                            ) AS raw_weight_sum
                        FROM selected_head
                    )
                    SELECT
                        e.run_id,
                        e.attempt_id,
                        e.run_type,
                        e.snapshot_id,
                        e.instrument,
                        e.signal_date,
                        CASE
                            WHEN n.raw_weight_sum IS NULL OR n.raw_weight_sum <= 0.0 THEN e.target_weight_D0
                            ELSE n.raw_weight / n.raw_weight_sum
                        END AS mapped_target_weight_D0,
                        COALESCE(n.weight_mapping_multiplier, 1.0::DOUBLE) AS weight_mapping_multiplier
                    FROM execution_state_t e
                    LEFT JOIN normalized n
                        ON e.run_id = n.run_id
                       AND e.attempt_id = n.attempt_id
                       AND e.snapshot_id = n.snapshot_id
                       AND e.instrument = n.instrument
                       AND e.signal_date = n.signal_date
                    """
                )
            else:
                max_daily_change = float(
                    portfolio_extraction_contract["max_daily_weight_change_per_instrument"]
                )
                extraction_rows = con.execute(
                    f"""
                    SELECT
                        e.run_id,
                        e.attempt_id,
                        e.run_type,
                        e.snapshot_id,
                        e.instrument,
                        e.signal_date,
                        e.target_weight_D0 AS base_target_weight_D0,
                        r.rank_position
                    FROM execution_state_t e
                    INNER JOIN ranking_state_t r
                        ON e.run_id = r.run_id
                       AND e.attempt_id = r.attempt_id
                       AND e.snapshot_id = r.snapshot_id
                       AND e.instrument = r.instrument
                       AND e.signal_date = r.signal_date
                    WHERE r.topk_frozen_D0
                    ORDER BY e.signal_date, r.rank_position, e.instrument
                    """
                ).fetchall()
                extraction_cols = [col[0] for col in con.description]
                extraction_by_signal_date: dict[str, list[dict]] = {}
                for row in extraction_rows:
                    record = dict(zip(extraction_cols, row))
                    extraction_by_signal_date.setdefault(str(record["signal_date"]), []).append(record)

                mapped_rows: list[dict] = []
                previous_weights: dict[str, float] = {}
                for signal_date in sorted(extraction_by_signal_date.keys()):
                    rows_for_day = extraction_by_signal_date[signal_date]
                    selected_rows = []
                    raw_weights = []
                    lower_bounds = []
                    upper_bounds = []
                    for row in rows_for_day:
                        rank_position = int(row["rank_position"])
                        extraction_multiplier = (
                            1.0 - ((rank_position - 1) * (0.9 / decay_denominator))
                            if rank_position <= head_size
                            else 0.0
                        )
                        raw_weight = float(row["base_target_weight_D0"]) * extraction_multiplier
                        selected_rows.append((row, extraction_multiplier))
                        raw_weights.append(raw_weight)
                        previous_weight = float(previous_weights.get(str(row["instrument"]), 0.0))
                        lower_bounds.append(max(0.0, previous_weight - max_daily_change))
                        upper_bounds.append(min(1.0, previous_weight + max_daily_change))
                    raw_weight_sum = sum(raw_weights)
                    if raw_weight_sum <= 0.0:
                        normalized_weights = [1.0 / float(len(raw_weights))] * len(raw_weights)
                    else:
                        normalized_raw = [value / raw_weight_sum for value in raw_weights]
                        normalized_weights = solve_box_constrained_simplex_projection(
                            normalized_raw,
                            lower_bounds,
                            upper_bounds,
                        )
                    previous_weights = {}
                    for (row, extraction_multiplier), mapped_target_weight in zip(
                        selected_rows, normalized_weights
                    ):
                        instrument = str(row["instrument"])
                        previous_weights[instrument] = float(mapped_target_weight)
                        mapped_rows.append(
                            {
                                "run_id": row["run_id"],
                                "attempt_id": row["attempt_id"],
                                "run_type": row["run_type"],
                                "snapshot_id": row["snapshot_id"],
                                "instrument": instrument,
                                "signal_date": row["signal_date"],
                                "mapped_target_weight_D0": float(mapped_target_weight),
                                "weight_mapping_multiplier": (
                                    float(mapped_target_weight) / float(row["base_target_weight_D0"])
                                    if float(row["base_target_weight_D0"]) > 0.0
                                    else extraction_multiplier
                                ),
                            }
                        )

                extraction_csv_path = attempt_dir / "portfolio_extraction_stability_targets.csv"
                with extraction_csv_path.open("w", encoding="utf-8", newline="") as handle:
                    fieldnames = [
                        "run_id",
                        "attempt_id",
                        "run_type",
                        "snapshot_id",
                        "instrument",
                        "signal_date",
                        "mapped_target_weight_D0",
                        "weight_mapping_multiplier",
                    ]
                    writer = csv.DictWriter(handle, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(mapped_rows)

                con.execute(
                    f"""
                    CREATE OR REPLACE VIEW mapped_execution_targets_t AS
                    SELECT
                        e.run_id,
                        e.attempt_id,
                        e.run_type,
                        e.snapshot_id,
                        e.instrument,
                        e.signal_date,
                        COALESCE(m.mapped_target_weight_D0, e.target_weight_D0) AS mapped_target_weight_D0,
                        COALESCE(m.weight_mapping_multiplier, 1.0::DOUBLE) AS weight_mapping_multiplier
                    FROM execution_state_t e
                    LEFT JOIN read_csv_auto({sql_path(extraction_csv_path)}, HEADER=TRUE) m
                        ON e.run_id = CAST(m.run_id AS VARCHAR)
                       AND e.attempt_id = CAST(m.attempt_id AS VARCHAR)
                       AND e.snapshot_id = CAST(m.snapshot_id AS VARCHAR)
                       AND e.instrument = CAST(m.instrument AS VARCHAR)
                       AND e.signal_date = CAST(m.signal_date AS VARCHAR)
                    """
                )
        else:
            con.execute(
                """
                CREATE OR REPLACE VIEW mapped_execution_targets_t AS
                SELECT
                    e.run_id,
                    e.attempt_id,
                    e.run_type,
                    e.snapshot_id,
                    e.instrument,
                    e.signal_date,
                    e.target_weight_D0 AS mapped_target_weight_D0,
                    1.0::DOUBLE AS weight_mapping_multiplier
                FROM execution_state_t e
                """
            )

        is_cohort_entry_locked = (
            portfolio_refresh_contract is not None
            and portfolio_refresh_contract.get("refresh_rule_name") == "cohort_entry_locked"
        )
        if portfolio_refresh_contract is None or is_cohort_entry_locked:
            con.execute(
                """
                CREATE OR REPLACE VIEW pre_holdings_positions_t AS
                SELECT
                    e.run_id,
                    e.attempt_id,
                    e.run_type,
                    e.snapshot_id,
                    e.instrument,
                    e.signal_date,
                    e.entry_date,
                    e.planned_exit_date,
                    p.actual_exit_date,
                    p.actual_exit_event_type,
                    p.actual_exit_price_field,
                    p.actual_sell_price,
                    p.exit_delay_days,
                    p.execution_delayed_realized_return,
                    p.execution_path_status,
                    p.terminal_event_flag,
                    p.terminal_event_type,
                    p.terminal_event_date,
                    p.terminal_exit_pricing_method,
                    p.terminal_exit_approximation_flag,
                    p.terminal_exit_conservative_flag,
                    t.mapped_target_weight_D0 AS target_weight_D0,
                    e.entry_filled_D1,
                    e.entry_filled_reason,
                    e.backtest_executable,
                    t.weight_mapping_multiplier,
                    CONCAT(e.run_id, '__', e.attempt_id, '__', e.instrument, '__', e.signal_date) AS position_id
                FROM execution_state_t e
                INNER JOIN mapped_execution_targets_t t
                    ON e.run_id = t.run_id
                   AND e.attempt_id = t.attempt_id
                   AND e.snapshot_id = t.snapshot_id
                   AND e.instrument = t.instrument
                   AND e.signal_date = t.signal_date
                INNER JOIN project_execution_panel_t p
                    ON e.snapshot_id = p.snapshot_id
                   AND e.instrument = p.instrument
                   AND e.signal_date = p.signal_date
                WHERE e.backtest_executable
                """
            )
        else:
            retain_if_rank_leq = portfolio_refresh_contract["retain_if_rank_leq"]
            max_holdings = portfolio_refresh_contract["max_holdings"]
            candidate_band = max(retain_if_rank_leq, max_holdings)
            refresh_candidates = con.execute(
                f"""
                SELECT
                    r.run_id,
                    r.attempt_id,
                    r.run_type,
                    r.snapshot_id,
                    r.instrument,
                    r.signal_date,
                    r.rank_position,
                    e.entry_date,
                    e.planned_exit_date,
                    p.actual_exit_date,
                    p.actual_exit_event_type,
                    p.actual_exit_price_field,
                    p.actual_sell_price,
                    p.exit_delay_days,
                    p.execution_delayed_realized_return,
                    p.execution_path_status,
                    p.terminal_event_flag,
                    p.terminal_event_type,
                    p.terminal_event_date,
                    p.terminal_exit_pricing_method,
                    p.terminal_exit_approximation_flag,
                    p.terminal_exit_conservative_flag
                FROM ranking_state_t r
                INNER JOIN execution_state_t e
                    ON r.run_id = e.run_id
                   AND r.attempt_id = e.attempt_id
                   AND r.snapshot_id = e.snapshot_id
                   AND r.instrument = e.instrument
                   AND r.signal_date = e.signal_date
                INNER JOIN project_execution_panel_t p
                    ON r.snapshot_id = p.snapshot_id
                   AND r.instrument = p.instrument
                   AND r.signal_date = p.signal_date
                WHERE r.rank_position IS NOT NULL
                  AND r.rank_position <= {candidate_band}
                  AND r.ranking_eligible_D0
                  AND COALESCE(r.liquidity_guard_pass_D0, TRUE)
                  AND COALESCE(e.entry_tradeable_shared_flag, FALSE)
                ORDER BY r.signal_date, r.rank_position, r.instrument
                """
            ).fetchall()
            candidate_cols = [col[0] for col in con.description]
            by_signal_date: dict[str, list[dict]] = {}
            for row in refresh_candidates:
                record = dict(zip(candidate_cols, row))
                by_signal_date.setdefault(str(record["signal_date"]), []).append(record)

            selected_rows: list[dict] = []
            previous_selected: list[str] = []
            for signal_date in sorted(by_signal_date.keys()):
                day_candidates = by_signal_date[signal_date]
                day_by_instrument = {str(row["instrument"]): row for row in day_candidates}
                retained: list[dict] = []
                for instrument in previous_selected:
                    row = day_by_instrument.get(instrument)
                    if row is None:
                        continue
                    if int(row["rank_position"]) <= retain_if_rank_leq:
                        retained.append(row)
                retained_instruments = {str(row["instrument"]) for row in retained}
                selected_for_day = list(retained)
                for row in day_candidates:
                    instrument = str(row["instrument"])
                    if instrument in retained_instruments:
                        continue
                    if len(selected_for_day) >= max_holdings:
                        break
                    selected_for_day.append(row)
                    retained_instruments.add(instrument)
                selected_count = len(selected_for_day)
                if selected_count == 0:
                    previous_selected = []
                    continue
                selected_for_day.sort(
                    key=lambda row: (int(row["rank_position"]), str(row["instrument"]))
                )
                extraction_weights = compute_extraction_weights_for_selected_count(
                    selected_count,
                    portfolio_extraction_contract,
                )
                for row, target_weight in zip(selected_for_day, extraction_weights):
                    selected_rows.append(
                        {
                            "run_id": row["run_id"],
                            "attempt_id": row["attempt_id"],
                            "run_type": row["run_type"],
                            "snapshot_id": row["snapshot_id"],
                            "instrument": row["instrument"],
                            "signal_date": row["signal_date"],
                            "entry_date": row["entry_date"],
                            "planned_exit_date": row["planned_exit_date"],
                            "actual_exit_date": row["actual_exit_date"],
                            "actual_exit_event_type": row["actual_exit_event_type"],
                            "actual_exit_price_field": row["actual_exit_price_field"],
                            "actual_sell_price": row["actual_sell_price"],
                            "exit_delay_days": row["exit_delay_days"],
                            "execution_delayed_realized_return": row["execution_delayed_realized_return"],
                            "execution_path_status": row["execution_path_status"],
                            "terminal_event_flag": row["terminal_event_flag"],
                            "terminal_event_type": row["terminal_event_type"],
                            "terminal_event_date": row["terminal_event_date"],
                            "terminal_exit_pricing_method": row["terminal_exit_pricing_method"],
                            "terminal_exit_approximation_flag": row["terminal_exit_approximation_flag"],
                            "terminal_exit_conservative_flag": row["terminal_exit_conservative_flag"],
                            "target_weight_D0": target_weight,
                            "entry_filled_D1": True,
                            "entry_filled_reason": "filled_via_portfolio_refresh_rule",
                            "backtest_executable": True,
                            "weight_mapping_multiplier": 1.0,
                        }
                    )
                previous_selected = [str(row["instrument"]) for row in selected_for_day]

            refresh_csv_path = attempt_dir / "portfolio_refresh_selected_positions.csv"
            with refresh_csv_path.open("w", encoding="utf-8", newline="") as handle:
                fieldnames = [
                    "run_id",
                    "attempt_id",
                    "run_type",
                    "snapshot_id",
                    "instrument",
                    "signal_date",
                    "entry_date",
                    "planned_exit_date",
                    "actual_exit_date",
                    "actual_exit_event_type",
                    "actual_exit_price_field",
                    "actual_sell_price",
                    "exit_delay_days",
                    "execution_delayed_realized_return",
                    "execution_path_status",
                    "terminal_event_flag",
                    "terminal_event_type",
                    "terminal_event_date",
                    "terminal_exit_pricing_method",
                    "terminal_exit_approximation_flag",
                    "terminal_exit_conservative_flag",
                    "target_weight_D0",
                    "entry_filled_D1",
                    "entry_filled_reason",
                    "backtest_executable",
                    "weight_mapping_multiplier",
                ]
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(selected_rows)

            con.execute(
                f"""
                CREATE OR REPLACE VIEW pre_holdings_positions_t AS
                SELECT
                    CAST(run_id AS VARCHAR) AS run_id,
                    CAST(attempt_id AS VARCHAR) AS attempt_id,
                    CAST(run_type AS VARCHAR) AS run_type,
                    CAST(snapshot_id AS VARCHAR) AS snapshot_id,
                    CAST(instrument AS VARCHAR) AS instrument,
                    CAST(signal_date AS VARCHAR) AS signal_date,
                    CAST(entry_date AS VARCHAR) AS entry_date,
                    CAST(planned_exit_date AS VARCHAR) AS planned_exit_date,
                    CAST(actual_exit_date AS VARCHAR) AS actual_exit_date,
                    CAST(actual_exit_event_type AS VARCHAR) AS actual_exit_event_type,
                    CAST(actual_exit_price_field AS VARCHAR) AS actual_exit_price_field,
                    CAST(actual_sell_price AS DOUBLE) AS actual_sell_price,
                    CAST(exit_delay_days AS BIGINT) AS exit_delay_days,
                    CAST(execution_delayed_realized_return AS DOUBLE) AS execution_delayed_realized_return,
                    CAST(execution_path_status AS VARCHAR) AS execution_path_status,
                    CAST(terminal_event_flag AS BOOLEAN) AS terminal_event_flag,
                    CAST(terminal_event_type AS VARCHAR) AS terminal_event_type,
                    CAST(terminal_event_date AS VARCHAR) AS terminal_event_date,
                    CAST(terminal_exit_pricing_method AS VARCHAR) AS terminal_exit_pricing_method,
                    CAST(terminal_exit_approximation_flag AS BOOLEAN) AS terminal_exit_approximation_flag,
                    CAST(terminal_exit_conservative_flag AS BOOLEAN) AS terminal_exit_conservative_flag,
                    CAST(target_weight_D0 AS DOUBLE) AS target_weight_D0,
                    CAST(entry_filled_D1 AS BOOLEAN) AS entry_filled_D1,
                    CAST(entry_filled_reason AS VARCHAR) AS entry_filled_reason,
                    CAST(backtest_executable AS BOOLEAN) AS backtest_executable,
                    CAST(weight_mapping_multiplier AS DOUBLE) AS weight_mapping_multiplier,
                    CONCAT(run_id, '__', attempt_id, '__', instrument, '__', signal_date) AS position_id
                FROM read_csv_auto({sql_path(refresh_csv_path)}, HEADER=TRUE)
                """
            )
        ensure_no_unresolved_backtest_exits(con)
        weight_sanity = con.execute(
            """
            SELECT
                MIN(target_weight_D0) AS min_target_weight,
                MAX(target_weight_D0) AS max_target_weight,
                SUM(CASE WHEN target_weight_D0 < 0 THEN 1 ELSE 0 END) AS negative_weight_rows,
                SUM(CASE WHEN target_weight_D0 > 1.0 THEN 1 ELSE 0 END) AS gt_one_weight_rows
            FROM pre_holdings_positions_t
            """
        ).fetchone()
        if int(weight_sanity[2] or 0) > 0:
            raise ValueError("Found negative target weights; expected normalized 0-1 weights.")
        if int(weight_sanity[3] or 0) > 0:
            raise ValueError("Found target weights above 1.0; expected normalized 0-1 weights.")
        if args.holding_cohort_count is None:
            derived_holding_cohort_count = con.execute(
                """
                WITH overlap AS (
                    SELECT
                        c.trade_date,
                        COUNT(DISTINCT h.signal_date) AS active_signal_cohort_count
                    FROM pre_holdings_positions_t h
                    INNER JOIN calendar_t c
                        ON c.trade_date >= h.entry_date
                       AND c.trade_date <= h.actual_exit_date
                    GROUP BY 1
                )
                SELECT COALESCE(MAX(active_signal_cohort_count), 1)
                FROM overlap
                """
            ).fetchone()[0]
        else:
            derived_holding_cohort_count = args.holding_cohort_count
        cohort_fraction = 1.0 / float(derived_holding_cohort_count)

        con.execute(
            f"""
            CREATE OR REPLACE VIEW holdings_positions_t AS
            SELECT
                h.run_id,
                h.attempt_id,
                h.run_type,
                h.snapshot_id,
                h.instrument,
                h.signal_date,
                h.entry_date,
                h.planned_exit_date,
                h.actual_exit_date,
                h.actual_exit_event_type,
                h.actual_exit_price_field,
                h.actual_sell_price,
                h.exit_delay_days,
                h.execution_delayed_realized_return,
                h.execution_path_status,
                h.terminal_event_flag,
                h.terminal_event_type,
                h.terminal_event_date,
                h.terminal_exit_pricing_method,
                h.terminal_exit_approximation_flag,
                h.terminal_exit_conservative_flag,
                h.target_weight_D0,
                h.entry_filled_D1,
                h.entry_filled_reason,
                h.backtest_executable,
                {cohort_fraction}::DOUBLE AS cohort_capital_fraction,
                h.position_id,
                CASE
                    WHEN h.backtest_executable THEN COALESCE(h.target_weight_D0, 0.0) * {cohort_fraction}::DOUBLE
                    ELSE 0.0
                END AS entry_fill_weight
            FROM pre_holdings_positions_t h
            """
        )

        atomic_csv_copy(
            con,
            """
            SELECT
                run_id,
                attempt_id,
                run_type,
                snapshot_id,
                position_id,
                instrument,
                signal_date,
                entry_date,
                planned_exit_date,
                actual_exit_date,
                actual_exit_event_type,
                actual_exit_price_field,
                actual_sell_price,
                exit_delay_days,
                execution_delayed_realized_return,
                execution_path_status,
                target_weight_D0,
                entry_fill_weight,
                cohort_capital_fraction,
                entry_filled_D1,
                entry_filled_reason,
                backtest_executable,
                terminal_event_flag,
                terminal_event_type,
                terminal_event_date,
                terminal_exit_pricing_method,
                terminal_exit_approximation_flag,
                terminal_exit_conservative_flag
            FROM holdings_positions_t
            ORDER BY signal_date, instrument, position_id
            """,
            holdings_path,
        )

        con.execute(
            """
            CREATE OR REPLACE VIEW position_weight_path_t AS
            SELECT
                h.run_id,
                h.attempt_id,
                h.run_type,
                h.snapshot_id,
                c.trade_date,
                h.instrument,
                h.position_id,
                h.target_weight_D0,
                h.entry_fill_weight,
                h.entry_date,
                h.planned_exit_date,
                h.actual_exit_date,
                CASE
                    WHEN c.trade_date = h.entry_date THEN 0.0
                    ELSE h.entry_fill_weight
                END AS opening_weight_position,
                CASE
                    WHEN c.trade_date = h.actual_exit_date THEN 0.0
                    ELSE h.entry_fill_weight
                END AS closing_weight_position,
                c.trade_date = h.entry_date AS entry_filled_flag_position,
                CASE
                    WHEN h.exit_delay_days > 0
                     AND c.trade_date > h.planned_exit_date
                     AND c.trade_date <= h.actual_exit_date THEN TRUE
                    ELSE FALSE
                END AS delayed_exit_flag_position
            FROM holdings_positions_t h
            INNER JOIN calendar_t c
                ON c.trade_date >= h.entry_date
               AND c.trade_date <= h.actual_exit_date
            """
        )

        con.execute(
            """
            CREATE OR REPLACE VIEW portfolio_weights_daily_t AS
            WITH raw AS (
                SELECT
                    run_id,
                    attempt_id,
                    run_type,
                    trade_date,
                    instrument,
                    SUM(target_weight_D0) AS target_weight_D0,
                    SUM(opening_weight_position) AS opening_weight_raw,
                    SUM(closing_weight_position) AS closing_weight_raw,
                    BOOL_OR(entry_filled_flag_position) AS entry_filled_flag,
                    BOOL_OR(delayed_exit_flag_position) AS delayed_exit_flag
                FROM position_weight_path_t
                GROUP BY 1, 2, 3, 4, 5
            ),
            daily_total AS (
                SELECT
                    trade_date,
                    SUM(closing_weight_raw) AS total_closing,
                    SUM(opening_weight_raw) AS total_opening
                FROM raw
                GROUP BY trade_date
            )
            SELECT
                r.run_id,
                r.attempt_id,
                r.run_type,
                r.trade_date,
                r.instrument,
                r.target_weight_D0,
                CASE WHEN d.total_opening > 1.0
                     THEN r.opening_weight_raw / d.total_opening
                     ELSE r.opening_weight_raw
                END AS opening_weight,
                CASE WHEN d.total_closing > 1.0
                     THEN r.closing_weight_raw / d.total_closing
                     ELSE r.closing_weight_raw
                END AS closing_weight,
                r.entry_filled_flag,
                r.delayed_exit_flag
            FROM raw r
            LEFT JOIN daily_total d
                ON r.trade_date = d.trade_date
            """
        )

        atomic_csv_copy(
            con,
            """
            SELECT
                run_id,
                attempt_id,
                run_type,
                trade_date,
                instrument,
                target_weight_D0,
                opening_weight,
                closing_weight,
                entry_filled_flag,
                delayed_exit_flag
            FROM portfolio_weights_daily_t
            ORDER BY trade_date, instrument
            """,
            weights_path,
        )

        con.execute(
            """
            CREATE OR REPLACE VIEW active_date_span_t AS
            SELECT
                MIN(entry_date) AS min_trade_date,
                MAX(actual_exit_date) AS max_trade_date
            FROM holdings_positions_t
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW active_calendar_t AS
            SELECT
                c.trade_date
            FROM calendar_t c
            CROSS JOIN active_date_span_t s
            WHERE c.trade_date >= s.min_trade_date
              AND c.trade_date <= s.max_trade_date
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW weight_summary_base_t AS
            SELECT
                run_id,
                attempt_id,
                run_type,
                trade_date,
                SUM(closing_weight) AS invested_weight,
                MAX(closing_weight) AS max_single_name_weight,
                SUM(POWER(closing_weight, 2)) AS portfolio_herfindahl_index
            FROM portfolio_weights_daily_t
            GROUP BY 1, 2, 3, 4
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW top3_weights_t AS
            WITH ranked AS (
                SELECT
                    run_id,
                    attempt_id,
                    run_type,
                    trade_date,
                    closing_weight,
                    ROW_NUMBER() OVER (
                        PARTITION BY run_id, attempt_id, trade_date
                        ORDER BY closing_weight DESC, instrument ASC
                    ) AS weight_rank
                FROM portfolio_weights_daily_t
            )
            SELECT
                run_id,
                attempt_id,
                run_type,
                trade_date,
                SUM(closing_weight) FILTER (WHERE weight_rank <= 3) AS top3_weight
            FROM ranked
            GROUP BY 1, 2, 3, 4
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW portfolio_daily_summary_t AS
            SELECT
                hp.run_id,
                hp.attempt_id,
                hp.run_type,
                c.trade_date,
                COALESCE(1.0 - b.invested_weight, 1.0) AS cash_weight,
                COALESCE(b.invested_weight, 0.0) AS invested_weight,
                COALESCE(b.max_single_name_weight, 0.0) AS max_single_name_weight,
                COALESCE(t.top3_weight, 0.0) AS top3_weight,
                COALESCE(b.portfolio_herfindahl_index, 0.0) AS portfolio_herfindahl_index,
                NULL::DOUBLE AS industry_active_weight_max
            FROM (SELECT DISTINCT run_id, attempt_id, run_type FROM holdings_positions_t) hp
            CROSS JOIN active_calendar_t c
            LEFT JOIN weight_summary_base_t b
                ON hp.run_id = b.run_id
               AND hp.attempt_id = b.attempt_id
               AND hp.run_type IS NOT DISTINCT FROM b.run_type
               AND c.trade_date = b.trade_date
            LEFT JOIN top3_weights_t t
                ON hp.run_id = t.run_id
               AND hp.attempt_id = t.attempt_id
               AND hp.run_type IS NOT DISTINCT FROM t.run_type
               AND c.trade_date = t.trade_date
            """
        )

        atomic_csv_copy(
            con,
            """
            SELECT
                run_id,
                attempt_id,
                run_type,
                trade_date,
                cash_weight,
                invested_weight,
                max_single_name_weight,
                top3_weight,
                portfolio_herfindahl_index,
                industry_active_weight_max
            FROM portfolio_daily_summary_t
            ORDER BY trade_date
            """,
            summary_path,
        )

        con.execute(
            """
            CREATE OR REPLACE VIEW turnover_events_t AS
            SELECT
                run_id,
                attempt_id,
                run_type,
                entry_date AS trade_date,
                SUM(entry_fill_weight) AS buy_notional_daily,
                0.0 AS sell_notional_daily
            FROM holdings_positions_t
            GROUP BY 1, 2, 3, 4

            UNION ALL

            SELECT
                run_id,
                attempt_id,
                run_type,
                actual_exit_date AS trade_date,
                0.0 AS buy_notional_daily,
                SUM(entry_fill_weight) AS sell_notional_daily
            FROM holdings_positions_t
            GROUP BY 1, 2, 3, 4
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW turnover_daily_t AS
            SELECT
                hp.run_id,
                hp.attempt_id,
                hp.run_type,
                c.trade_date,
                COALESCE(SUM(e.buy_notional_daily), 0.0) AS buy_notional_daily,
                COALESCE(SUM(e.sell_notional_daily), 0.0) AS sell_notional_daily,
                COALESCE(SUM(e.buy_notional_daily), 0.0) + COALESCE(SUM(e.sell_notional_daily), 0.0) AS turnover_daily,
                (
                    COALESCE(SUM(e.buy_notional_daily), 0.0) + COALESCE(SUM(e.sell_notional_daily), 0.0)
                ) > 0.0 AS rebalance_event_flag
            FROM (SELECT DISTINCT run_id, attempt_id, run_type FROM holdings_positions_t) hp
            CROSS JOIN active_calendar_t c
            LEFT JOIN turnover_events_t e
                ON hp.run_id = e.run_id
               AND hp.attempt_id = e.attempt_id
               AND hp.run_type IS NOT DISTINCT FROM e.run_type
               AND c.trade_date = e.trade_date
            GROUP BY 1, 2, 3, 4
            """
        )

        atomic_csv_copy(
            con,
            """
            SELECT
                run_id,
                attempt_id,
                run_type,
                trade_date,
                buy_notional_daily,
                sell_notional_daily,
                turnover_daily,
                rebalance_event_flag
            FROM turnover_daily_t
            ORDER BY trade_date
            """,
            turnover_path,
        )

        row_counts = con.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM holdings_positions_t) AS holdings_rows,
                (SELECT COUNT(*) FROM portfolio_weights_daily_t) AS portfolio_weights_daily_rows,
                (SELECT COUNT(*) FROM portfolio_daily_summary_t) AS portfolio_daily_summary_rows,
                (SELECT COUNT(*) FROM turnover_daily_t) AS turnover_daily_rows,
                (SELECT COALESCE(MAX(invested_weight), 0.0) FROM portfolio_daily_summary_t) AS max_invested_weight
            """
        ).fetchone()
    finally:
        con.close()

        manifest_payload = {
            "run_id": args.run_id,
            "attempt_id": attempt_id,
            "generated_at": datetime.now().astimezone().isoformat(),
            "source_attempt_manifest": str(attempt_manifest_path),
            "inputs": {
                "execution_state_daily": str(execution_state),
                "ranking_state_daily": str(ranking_state),
                "project_execution_panel": str(project_execution_panel),
            },
            "outputs": {
                "holdings_csv": str(holdings_path),
                "portfolio_weights_daily_csv": str(weights_path),
                "portfolio_daily_summary_csv": str(summary_path),
                "turnover_daily_csv": str(turnover_path),
            },
            "assumptions": {
                "holding_cohort_count": derived_holding_cohort_count,
                "cohort_capital_fraction": cohort_fraction,
                "weight_unit_basis": "normalized_0_to_1_portfolio_weight",
                "weight_mapping_contract": weight_mapping_contract,
                "portfolio_extraction_contract": portfolio_extraction_contract,
                "portfolio_refresh_contract": portfolio_refresh_contract,
                "turnover_notional_basis": "normalized_portfolio_weight_with_lag_total_equity_equal_1",
                "weight_path_rule": "entry_day_opening_weight_is_zero_and_actual_exit_day_closing_weight_is_zero",
                "industry_active_weight_max": "null_until_industry_exposure_layer_is_implemented",
            },
            "summary_counts": {
                "holdings_rows": row_counts[0] if row_counts is not None else None,
                "portfolio_weights_daily_rows": row_counts[1] if row_counts is not None else None,
                "portfolio_daily_summary_rows": row_counts[2] if row_counts is not None else None,
                "turnover_daily_rows": row_counts[3] if row_counts is not None else None,
                "max_invested_weight": row_counts[4] if row_counts is not None else None,
                "target_weight_min": (
                    float(weight_sanity[0]) if weight_sanity is not None and weight_sanity[0] is not None else None
                ),
                "target_weight_max": (
                    float(weight_sanity[1]) if weight_sanity is not None and weight_sanity[1] is not None else None
                ),
            },
            "upstream_attempt_parameters": attempt_manifest.get("parameters", {}),
        }
        atomic_json_write(manifest_path, manifest_payload)


if __name__ == "__main__":
    main()
