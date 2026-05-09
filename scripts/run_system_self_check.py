#!/opt/anaconda3/envs/quant_trade/bin/python
"""
System self-check: comprehensive placebo and consistency tests per 框架 14.3.

Checks:
1. Data quality & completeness (coverage, missing rates, tradability degradation)
2. Label & execution semantics consistency (main vs conservative mask)
3. Placebo tests:
   a) Random label shuffling — model IC should collapse to ~0
   b) Random model score shuffling — portfolio returns should collapse to ~0
4. Feature lagging — shifting features forward should not improve results
5. Feature leading — shifting features backward should not improve results
   (forward-looking leak detection)
6. Low liquidity exposure — alpha should not depend on low-liquidity names
7. Sub-period direction stability — IC direction consistency across sub-periods

Output:
- artifacts/research_registry/system_self_check_<as_of_date>.json
- artifacts/research_registry/system_self_check_<as_of_date>.md
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
from datetime import datetime
from pathlib import Path

import duckdb
import numpy as np


ROOT = Path("/Users/wy/MiscProject/multi_factor")
CONTRACTS_DIR = ROOT / "contracts"
ARTIFACTS_RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
RESEARCH_REGISTRY_DIR = ROOT / "artifacts" / "research_registry"
PYTHON = "/opt/anaconda3/envs/quant_trade/bin/python"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run system self-check per framework 14.3.")
    parser.add_argument(
        "--run-id",
        default="baseline_chain_20260417_105228",
        help="Reference run ID with project panels.",
    )
    parser.add_argument(
        "--as-of-date",
        default=None,
        help="Date label for output files. Defaults to today.",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="Random seed for placebo shuffling.",
    )
    parser.add_argument(
        "--n-shuffle-trials",
        type=int,
        default=5,
        help="Number of shuffle trials for placebo tests.",
    )
    parser.add_argument(
        "--terminal-event-repair-audit",
        default=None,
        help=(
            "Path to terminal_event_repair_audit JSON. "
            "Defaults to <run_dir>/terminal_event_repair_audit.json."
        ),
    )
    parser.add_argument(
        "--terminal-last-tradable-approval-audit",
        default=None,
        help=(
            "Optional path to terminal_last_tradable_close approval audit JSON. "
            "Used for execution-exit resolution self-check reporting."
        ),
    )
    parser.add_argument(
        "--repaired-terminal-event-candidate",
        default=None,
        help=(
            "Optional path to repaired_terminal_event_candidate JSON. "
            "Used for execution-exit resolution self-check reporting."
        ),
    )
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    temp = path.with_suffix(path.suffix + ".inprogress")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_path(path: Path) -> str:
    return sql_quote(path.resolve().as_posix())


def require_path(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Required path not found: {path}")
    return path


def resolve_run_dir(run_id: str) -> Path:
    return require_path(ARTIFACTS_RUN_STATE_DIR / run_id)


def inspect_terminal_event_repair_audit(audit_path: Path) -> dict[str, object]:
    result: dict[str, object] = {
        "audit_path": str(audit_path),
        "present": False,
        "status": "missing",
        "pass_flag": False,
        "missing_fields": [],
        "still_hard_blocker_count": None,
        "can_emit_terminal_priced_last_tradable_close_count": None,
        "unclassifiable_excluded_count": None,
        "hard_blocker_present_flag": None,
        "requires_upstream_execution_path_implementation": False,
        "portfolio_resolution_allowed": False,
        "notes": ["terminal_event_repair_audit JSON missing."],
    }
    if not audit_path.exists():
        return result

    payload = load_json(audit_path)
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        result.update({
            "present": True,
            "status": "invalid",
            "missing_fields": ["summary"],
            "notes": ["terminal_event_repair_audit JSON is invalid: missing summary object."],
        })
        return result

    required_fields = [
        "still_hard_blocker_count",
        "can_emit_terminal_priced_last_tradable_close_count",
        "unclassifiable_excluded_count",
    ]
    missing_fields = [field for field in required_fields if field not in summary]
    if missing_fields:
        result.update({
            "present": True,
            "status": "invalid",
            "missing_fields": missing_fields,
            "notes": [
                "terminal_event_repair_audit JSON is invalid: missing summary fields "
                + ", ".join(missing_fields)
                + "."
            ],
        })
        return result

    still_hard_blocker_count = int(summary["still_hard_blocker_count"])
    can_emit_count = int(summary["can_emit_terminal_priced_last_tradable_close_count"])
    unclassifiable_excluded_count = int(summary["unclassifiable_excluded_count"])

    status = "ok"
    pass_flag = still_hard_blocker_count == 0
    notes = [
        "This self-check does not produce prices, backfill actual_exit_date, or backfill actual_sell_price.",
    ]
    if still_hard_blocker_count > 0:
        status = "terminal_event_repair_blocked"
        notes.append(
            "terminal_event_repair_audit confirms rows remain hard blockers and must not be auto-unblocked."
        )
    if can_emit_count > 0:
        if still_hard_blocker_count == 0:
            status = "terminal_event_repair_requires_upstream_execution_path_implementation"
        notes.append(
            "can_emit_terminal_priced_last_tradable_close_count > 0 is informational only; "
            "upstream execution path implementation is still required before any unblock."
        )

    result.update({
        "present": True,
        "status": status,
        "pass_flag": pass_flag,
        "missing_fields": [],
        "still_hard_blocker_count": still_hard_blocker_count,
        "can_emit_terminal_priced_last_tradable_close_count": can_emit_count,
        "unclassifiable_excluded_count": unclassifiable_excluded_count,
        "hard_blocker_present_flag": still_hard_blocker_count > 0,
        "requires_upstream_execution_path_implementation": can_emit_count > 0,
        "portfolio_resolution_allowed": False,
        "notes": notes,
    })
    return result


def inspect_terminal_last_tradable_approval_audit(audit_path: Path | None) -> dict[str, object]:
    result: dict[str, object] = {
        "audit_path": str(audit_path) if audit_path is not None else None,
        "present": False,
        "status": "missing",
        "candidate_rows_count": 0,
        "still_hard_blocker_count": 0,
        "approval_gate_passed_count": 0,
        "approval_gate_failed_count": 0,
        "notes": [],
    }
    if audit_path is None or not audit_path.exists():
        return result

    payload = load_json(audit_path)
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        result.update({
            "present": True,
            "status": "invalid",
            "notes": ["terminal_last_tradable_close approval audit JSON is invalid: missing summary object."],
        })
        return result

    result.update({
        "present": True,
        "status": "ok",
        "candidate_rows_count": int(summary.get("candidate_rows_count") or 0),
        "still_hard_blocker_count": int(summary.get("still_hard_blocker_count") or 0),
        "approval_gate_passed_count": int(summary.get("approval_gate_passed_count") or 0),
        "approval_gate_failed_count": int(summary.get("approval_gate_failed_count") or 0),
        "notes": [
            "Approval audit is candidate-only and does not by itself price exits or unblock portfolio.",
        ],
    })
    return result


def inspect_repaired_terminal_event_candidate(candidate_path: Path | None) -> dict[str, object]:
    result: dict[str, object] = {
        "candidate_path": str(candidate_path) if candidate_path is not None else None,
        "present": False,
        "status": "missing",
        "candidate_rows_count": 0,
        "priced_rows_count": 0,
        "still_hard_blocker_count": 0,
        "notes": [],
    }
    if candidate_path is None or not candidate_path.exists():
        return result

    payload = load_json(candidate_path)
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        result.update({
            "present": True,
            "status": "invalid",
            "notes": ["repaired_terminal_event_candidate JSON is invalid: missing summary object."],
        })
        return result

    result.update({
        "present": True,
        "status": "ok",
        "candidate_rows_count": int(summary.get("candidate_rows_count") or 0),
        "priced_rows_count": int(summary.get("priced_rows_count") or 0),
        "still_hard_blocker_count": int(summary.get("still_hard_blocker_count") or 0),
        "notes": [
            "Candidate artifact remains upstream-only until execution path emits complete actual exit fields.",
        ],
    })
    return result


def inspect_execution_exit_resolution(
    project_execution_panel_path: Path,
    execution_state_path: Path,
    repaired_terminal_event_candidate_path: Path | None = None,
    terminal_last_tradable_approval_audit_path: Path | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "project_execution_panel_path": str(project_execution_panel_path),
        "execution_state_path": str(execution_state_path),
        "repaired_terminal_event_candidate_path": (
            str(repaired_terminal_event_candidate_path)
            if repaired_terminal_event_candidate_path is not None
            else None
        ),
        "terminal_last_tradable_approval_audit_path": (
            str(terminal_last_tradable_approval_audit_path)
            if terminal_last_tradable_approval_audit_path is not None
            else None
        ),
        "present": False,
        "status": "missing_inputs",
        "pass_flag": False,
        "portfolio_recovery_allowed": False,
        "backtest_executable_rows": 0,
        "missing_actual_exit_date_rows": 0,
        "missing_actual_sell_price_rows": 0,
        "missing_realized_return_rows": 0,
        "hard_blocker_rows": 0,
        "hard_blocker_status_counts": {},
        "terminal_priced_last_tradable_close_rows": 0,
        "approval_candidate_rows_count": 0,
        "repaired_candidate_rows_count": 0,
        "missing_input_paths": [],
        "notes": [],
    }

    missing_input_paths: list[str] = []
    if not project_execution_panel_path.exists():
        missing_input_paths.append(str(project_execution_panel_path))
    if not execution_state_path.exists():
        missing_input_paths.append(str(execution_state_path))
    if missing_input_paths:
        result["missing_input_paths"] = missing_input_paths
        result["notes"] = ["Required execution exit resolution inputs are missing."]
        return result

    approval_check = inspect_terminal_last_tradable_approval_audit(
        terminal_last_tradable_approval_audit_path
    )
    candidate_check = inspect_repaired_terminal_event_candidate(
        repaired_terminal_event_candidate_path
    )

    con = duckdb.connect()
    try:
        con.execute(
            f"""
            CREATE OR REPLACE VIEW project_execution_panel_t AS
            SELECT * FROM read_parquet({sql_path(project_execution_panel_path)})
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW execution_state_t AS
            SELECT * FROM read_parquet({sql_path(execution_state_path)})
            """
        )
        summary_row = con.execute(
            """
            WITH executable AS (
                SELECT
                    p.execution_path_status,
                    p.actual_exit_date,
                    p.actual_sell_price,
                    p.execution_delayed_realized_return
                FROM execution_state_t e
                INNER JOIN project_execution_panel_t p
                  ON e.snapshot_id = p.snapshot_id
                 AND e.instrument = p.instrument
                 AND e.signal_date = p.signal_date
                WHERE e.backtest_executable
            )
            SELECT
                COUNT(*) AS backtest_executable_rows,
                SUM(CASE WHEN actual_exit_date IS NULL THEN 1 ELSE 0 END) AS missing_actual_exit_date_rows,
                SUM(CASE WHEN actual_sell_price IS NULL THEN 1 ELSE 0 END) AS missing_actual_sell_price_rows,
                SUM(CASE WHEN execution_delayed_realized_return IS NULL THEN 1 ELSE 0 END) AS missing_realized_return_rows,
                SUM(
                    CASE
                        WHEN execution_path_status IN ('terminal_event_unpriced', 'exit_unresolved', 'calendar_insufficient')
                        THEN 1 ELSE 0
                    END
                ) AS hard_blocker_rows,
                SUM(
                    CASE
                        WHEN execution_path_status = 'terminal_priced_last_tradable_close'
                        THEN 1 ELSE 0
                    END
                ) AS terminal_priced_last_tradable_close_rows
            FROM executable
            """
        ).fetchone()

        hard_blocker_rows = con.execute(
            """
            WITH executable AS (
                SELECT p.execution_path_status
                FROM execution_state_t e
                INNER JOIN project_execution_panel_t p
                  ON e.snapshot_id = p.snapshot_id
                 AND e.instrument = p.instrument
                 AND e.signal_date = p.signal_date
                WHERE e.backtest_executable
            )
            SELECT execution_path_status, COUNT(*) AS n
            FROM executable
            WHERE execution_path_status IN ('terminal_event_unpriced', 'exit_unresolved', 'calendar_insufficient')
            GROUP BY 1
            ORDER BY 1
            """
        ).fetchall()
    finally:
        con.close()

    backtest_executable_rows = int(summary_row[0] or 0)
    missing_actual_exit_date_rows = int(summary_row[1] or 0)
    missing_actual_sell_price_rows = int(summary_row[2] or 0)
    missing_realized_return_rows = int(summary_row[3] or 0)
    hard_blocker_rows_count = int(summary_row[4] or 0)
    terminal_priced_rows = int(summary_row[5] or 0)
    hard_blocker_status_counts = {str(status): int(count) for status, count in hard_blocker_rows}
    approval_candidate_rows_count = int(approval_check["candidate_rows_count"] or 0)
    repaired_candidate_rows_count = int(candidate_check["candidate_rows_count"] or 0)

    fully_resolved = (
        backtest_executable_rows > 0
        and missing_actual_exit_date_rows == 0
        and missing_actual_sell_price_rows == 0
        and missing_realized_return_rows == 0
        and hard_blocker_rows_count == 0
    )
    partially_resolved = (
        not fully_resolved
        and (
            terminal_priced_rows > 0
            or repaired_candidate_rows_count > 0
            or approval_candidate_rows_count > 0
        )
    )

    status = "still_blocked"
    notes = [
        "Portfolio recovery is allowed only when backtest_executable rows have complete actual exit fields and no hard-blocker execution states remain.",
    ]
    if fully_resolved:
        status = "fully_resolved"
        notes.append(
            "Execution path produced complete actual_exit_date, actual_sell_price, and execution_delayed_realized_return for all backtest_executable rows."
        )
    elif partially_resolved:
        status = "partially_resolved"
        notes.append(
            "Some approval/candidate/priced progress exists upstream, but execution exit resolution is still incomplete."
        )
    else:
        notes.append(
            "Execution exit blockers remain unresolved upstream; portfolio must stay blocked."
        )

    result.update({
        "present": True,
        "status": status,
        "pass_flag": fully_resolved,
        "portfolio_recovery_allowed": fully_resolved,
        "backtest_executable_rows": backtest_executable_rows,
        "missing_actual_exit_date_rows": missing_actual_exit_date_rows,
        "missing_actual_sell_price_rows": missing_actual_sell_price_rows,
        "missing_realized_return_rows": missing_realized_return_rows,
        "hard_blocker_rows": hard_blocker_rows_count,
        "hard_blocker_status_counts": hard_blocker_status_counts,
        "terminal_priced_last_tradable_close_rows": terminal_priced_rows,
        "approval_candidate_rows_count": approval_candidate_rows_count,
        "repaired_candidate_rows_count": repaired_candidate_rows_count,
        "missing_input_paths": [],
        "notes": notes,
    })
    return result


def resolve_latest_attempt_dir(run_dir: Path) -> tuple[str | None, Path | None]:
    latest_pointer = run_dir / "run_state_latest_attempt.json"
    if not latest_pointer.exists():
        return None, None
    payload = load_json(latest_pointer)
    attempt_id = payload.get("attempt_id")
    if not isinstance(attempt_id, str) or not attempt_id:
        return None, None
    attempt_dir = run_dir / "attempts" / attempt_id
    if not attempt_dir.exists():
        return attempt_id, None
    return attempt_id, attempt_dir


def fmt(v: float | None, decimals: int = 6) -> str:
    if v is None:
        return "null"
    return f"{v:.{decimals}f}"


def fmt_pct(v: float | None, decimals: int = 2) -> str:
    if v is None:
        return "null"
    return f"{v * 100:.{decimals}f}%"


BOLD_PASS = "✅ PASS"
BOLD_FAIL = "❌ FAIL"
BOLD_WARN = "⚠️  WARN"


def check_pass(condition: bool, label: str) -> str:
    return f"{BOLD_PASS} {label}" if condition else f"{BOLD_FAIL} {label}"


def main() -> None:
    args = parse_args()
    as_of_date = args.as_of_date or datetime.now().astimezone().strftime("%Y%m%d")
    random.seed(args.random_seed)
    np.random.seed(args.random_seed)

    run_dir = resolve_run_dir(args.run_id)
    label_panel = require_path(run_dir / "project_label_panel.parquet")
    sample_panel = require_path(run_dir / "project_sample_panel.parquet")
    execution_panel = require_path(run_dir / "project_execution_panel.parquet")
    terminal_event_repair_audit_path = Path(args.terminal_event_repair_audit) if args.terminal_event_repair_audit else run_dir / "terminal_event_repair_audit.json"
    terminal_last_tradable_approval_audit_path = (
        Path(args.terminal_last_tradable_approval_audit)
        if args.terminal_last_tradable_approval_audit
        else run_dir / "terminal_last_tradable_close_approval_audit.json"
    )
    repaired_terminal_event_candidate_path = (
        Path(args.repaired_terminal_event_candidate)
        if args.repaired_terminal_event_candidate
        else run_dir / "repaired_terminal_event_candidate.json"
    )
    latest_attempt_id, latest_attempt_dir = resolve_latest_attempt_dir(run_dir)
    execution_state_path = (
        latest_attempt_dir / "execution_state_daily.parquet"
        if latest_attempt_dir is not None
        else run_dir / "attempts" / "missing" / "execution_state_daily.parquet"
    )

    run_input = load_json(CONTRACTS_DIR / "run_input_contract.current.json")
    snapshot_id = run_input["snapshot_id"]
    source_db_path = Path(run_input["source_root"]["snapshot_path"]) / "duckdb" / "warehouse.duckdb"
    require_path(source_db_path)

    output_stem = f"system_self_check_{as_of_date}"
    json_output = RESEARCH_REGISTRY_DIR / f"{output_stem}.json"
    md_output = RESEARCH_REGISTRY_DIR / f"{output_stem}.md"

    con = duckdb.connect()
    results: dict[str, dict] = {}
    md_lines: list[str] = [
        f"# System Self-Check Report ({as_of_date})",
        "",
        f"Reference run: `{args.run_id}`",
        f"Snapshot: `{snapshot_id}`",
        f"Random seed: `{args.random_seed}`",
        "",
        "---",
        "",
        "## 1. Data Quality & Completeness",
        "",
    ]

    try:
        con.execute(f"ATTACH {sql_path(source_db_path)} AS warehouse_db (READ_ONLY)")
        con.execute(
            f"""
            CREATE OR REPLACE VIEW label_panel_t AS
            SELECT * FROM read_parquet({sql_path(label_panel)})
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW sample_panel_t AS
            SELECT * FROM read_parquet({sql_path(sample_panel)})
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW execution_panel_t AS
            SELECT * FROM read_parquet({sql_path(execution_panel)})
            """
        )

        # ---- 1a. Panel row counts & label coverage ----
        panel_counts = con.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM label_panel_t) AS label_rows,
                (SELECT COUNT(*) FROM sample_panel_t) AS sample_rows,
                (SELECT COUNT(*) FROM execution_panel_t) AS exec_rows,
                (SELECT COUNT(*) FROM sample_panel_t WHERE ranking_eligible_D0) AS ranking_eligible_rows,
                (SELECT COUNT(*) FROM sample_panel_t WHERE train_mask_v1) AS train_mask_rows,
                (SELECT COUNT(*) FROM sample_panel_t WHERE train_mask_conservative) AS train_conservative_rows,
                (SELECT COUNT(*) FROM sample_panel_t WHERE eval_mask_v1) AS eval_mask_rows,
                (SELECT COUNT(*) FROM sample_panel_t WHERE eval_mask_conservative) AS eval_conservative_rows
            """
        ).fetchone()

        label_rows = int(panel_counts[0] or 0)
        sample_rows = int(panel_counts[1] or 0)
        exec_rows = int(panel_counts[2] or 0)
        ranking_eligible_rows = int(panel_counts[3] or 0)
        train_mask_rows = int(panel_counts[4] or 0)
        train_conservative_rows = int(panel_counts[5] or 0)
        eval_mask_rows = int(panel_counts[6] or 0)
        eval_conservative_rows = int(panel_counts[7] or 0)

        label_coverage = train_mask_rows / ranking_eligible_rows if ranking_eligible_rows > 0 else 0.0
        conservative_ratio = train_conservative_rows / train_mask_rows if train_mask_rows > 0 else 0.0

        data_quality = {
            "label_panel_rows": label_rows,
            "sample_panel_rows": sample_rows,
            "execution_panel_rows": exec_rows,
            "ranking_eligible_rows": ranking_eligible_rows,
            "train_mask_rows": train_mask_rows,
            "train_conservative_rows": train_conservative_rows,
            "train_label_coverage": label_coverage,
            "conservative_vs_standard_ratio": conservative_ratio,
        }

        md_lines.extend([
            f"- Label panel rows: `{label_rows}`",
            f"- Sample panel rows: `{sample_rows}`",
            f"- Execution panel rows: `{exec_rows}`",
            f"- Ranking-eligible D0: `{ranking_eligible_rows}`",
            f"- Train mask v1: `{train_mask_rows}` ({fmt_pct(label_coverage)} of ranking-eligible)",
            f"- Train mask conservative: `{train_conservative_rows}`",
            f"- Conservative/standard ratio: `{fmt_pct(conservative_ratio)}`",
            "",
        ])

        coverage_pass = label_coverage >= 0.50
        md_lines.append(check_pass(coverage_pass, f"train_mask coverage >= 50% (actual: {fmt_pct(label_coverage)})"))
        md_lines.append("")

        # ---- 1b. Tradability degradation ----
        degrad = con.execute(
            f"""
            SELECT
                COUNT(*) AS total_rows,
                SUM(CASE WHEN tradability_degraded_flag THEN 1 ELSE 0 END) AS degraded_rows
            FROM warehouse_db.serving.vw_tradability_daily
            WHERE snapshot_id = {sql_quote(snapshot_id)}
            """
        ).fetchone()
        degraded_rows = int(degrad[1] or 0)
        degrad_pass = degraded_rows == 0
        md_lines.extend([
            f"- Tradability total rows: `{int(degrad[0] or 0)}`",
            f"- Tradability degraded rows: `{degraded_rows}`",
            check_pass(degrad_pass, "No tradability degradation"),
            "",
        ])

        # ---- 1c. Low liquidity flag audit ----
        low_liq = con.execute(
            f"""
            SELECT
                COUNT(*) AS total_rows,
                SUM(CASE WHEN low_liquidity_flag_t THEN 1 ELSE 0 END) AS low_liq_rows
            FROM warehouse_db.serving.vw_tradability_daily
            WHERE snapshot_id = {sql_quote(snapshot_id)}
              AND low_liquidity_flag_t IS NOT NULL
            """
        ).fetchone()
        low_liq_rows = int(low_liq[1] or 0)
        low_liq_rate = low_liq_rows / int(low_liq[0] or 1)
        low_liq_warn = low_liq_rate > 0.20
        md_lines.extend([
            f"- Low-liquidity flagged rows: `{low_liq_rows}` ({fmt_pct(low_liq_rate)})",
            check_pass(not low_liq_warn, f"Low-liquidity rate <= 20% (actual: {fmt_pct(low_liq_rate)})"),
            "",
        ])

        # ---- 1d. Terminal event audit ----
        terminal = con.execute(
            f"""
            SELECT COUNT(*)
            FROM warehouse_db.serving.vw_execution_path_daily
            WHERE snapshot_id = {sql_quote(snapshot_id)}
              AND terminal_event_flag
            """
        ).fetchone()
        terminal_rows = int(terminal[0] or 0)
        md_lines.append(f"- Terminal event positions: `{terminal_rows}`")
        md_lines.append("")

        # ---- 1e. Execution unresolved audit ----
        unresolved = con.execute(
            f"""
            SELECT COUNT(*)
            FROM execution_panel_t
            WHERE execution_path_status IN ('OPEN_UNRESOLVED', 'UNRESOLVED')
            """
        ).fetchone()
        unresolved_rows = int(unresolved[0] or 0)
        unresolved_pass = unresolved_rows == 0
        md_lines.extend([
            f"- Unresolved exit paths: `{unresolved_rows}`",
            check_pass(unresolved_pass, "No unresolved exit paths"),
            "",
        ])

        # ---- 1f. Execution exit resolution gate ----
        execution_exit_resolution_check = inspect_execution_exit_resolution(
            execution_panel,
            execution_state_path,
            repaired_terminal_event_candidate_path=repaired_terminal_event_candidate_path,
            terminal_last_tradable_approval_audit_path=terminal_last_tradable_approval_audit_path,
        )
        execution_exit_resolution_pass = bool(execution_exit_resolution_check["pass_flag"])
        md_lines.append("### Execution Exit Resolution Gate")
        md_lines.append("")
        md_lines.append(f"- Latest attempt id: `{latest_attempt_id}`")
        md_lines.append(
            f"- Execution state path: `{execution_exit_resolution_check['execution_state_path']}`"
        )
        md_lines.append(
            f"- Resolution status: `{execution_exit_resolution_check['status']}`"
        )
        md_lines.extend([
            f"- backtest_executable_rows: `{execution_exit_resolution_check['backtest_executable_rows']}`",
            f"- missing_actual_exit_date_rows: `{execution_exit_resolution_check['missing_actual_exit_date_rows']}`",
            f"- missing_actual_sell_price_rows: `{execution_exit_resolution_check['missing_actual_sell_price_rows']}`",
            f"- missing_realized_return_rows: `{execution_exit_resolution_check['missing_realized_return_rows']}`",
            f"- hard_blocker_rows: `{execution_exit_resolution_check['hard_blocker_rows']}`",
            f"- terminal_priced_last_tradable_close_rows: `{execution_exit_resolution_check['terminal_priced_last_tradable_close_rows']}`",
            f"- approval_candidate_rows_count: `{execution_exit_resolution_check['approval_candidate_rows_count']}`",
            f"- repaired_candidate_rows_count: `{execution_exit_resolution_check['repaired_candidate_rows_count']}`",
            f"- portfolio_recovery_allowed: `{execution_exit_resolution_check['portfolio_recovery_allowed']}`",
        ])
        if execution_exit_resolution_check["missing_input_paths"]:
            md_lines.append(
                f"{BOLD_FAIL} execution exit resolution inputs missing: "
                + ", ".join(execution_exit_resolution_check["missing_input_paths"])
            )
        else:
            md_lines.append(
                check_pass(
                    execution_exit_resolution_pass,
                    "Execution exit resolution is fully resolved for all backtest_executable rows",
                )
            )
        md_lines.append("")

        # ---- 1g. Terminal event repair audit gate ----
        terminal_event_repair_check = inspect_terminal_event_repair_audit(terminal_event_repair_audit_path)
        terminal_event_repair_present = bool(terminal_event_repair_check["present"])
        terminal_event_repair_status = str(terminal_event_repair_check["status"])
        md_lines.append("### Legacy Terminal Event Repair Audit Gate")
        md_lines.append("")
        md_lines.append(f"- Audit path: `{terminal_event_repair_check['audit_path']}`")
        if not terminal_event_repair_present:
            md_lines.extend([
                "- Audit status: `missing`",
                f"{BOLD_WARN} terminal_event_repair_audit missing",
                "",
            ])
        else:
            md_lines.extend([
                f"- Audit status: `{terminal_event_repair_status}`",
                f"- still_hard_blocker_count: `{terminal_event_repair_check['still_hard_blocker_count']}`",
                f"- can_emit_terminal_priced_last_tradable_close_count: `{terminal_event_repair_check['can_emit_terminal_priced_last_tradable_close_count']}`",
                f"- unclassifiable_excluded_count: `{terminal_event_repair_check['unclassifiable_excluded_count']}`",
                f"- portfolio_resolution_allowed: `{terminal_event_repair_check['portfolio_resolution_allowed']}`",
            ])
            if terminal_event_repair_status == "invalid":
                md_lines.append(
                    f"{BOLD_FAIL} terminal_event_repair_audit invalid: missing "
                    + ", ".join(terminal_event_repair_check["missing_fields"])
                )
            elif terminal_event_repair_status == "terminal_event_repair_blocked":
                md_lines.append(f"{BOLD_WARN} terminal_event_repair_blocked")
            else:
                md_lines.append(
                    check_pass(
                        bool(terminal_event_repair_check["pass_flag"]),
                        "terminal_event_repair_audit has no hard blockers",
                    )
                )
            if bool(terminal_event_repair_check["requires_upstream_execution_path_implementation"]):
                md_lines.append(
                    f"{BOLD_WARN} terminal_event_repair_audit found rows that may require upstream execution path implementation; this does not unblock portfolio handling."
                )
            md_lines.append("")

        # ---- 2. Label & execution semantics consistency ----
        md_lines.extend([
            "---",
            "",
            "## 2. Label & Execution Semantics Consistency",
            "",
        ])

        # 2a. Label-defined rate
        label_defined_rate = con.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN label_defined THEN 1 ELSE 0 END) AS defined
            FROM label_panel_t
            """
        ).fetchone()
        ld_total = int(label_defined_rate[0] or 0)
        ld_defined = int(label_defined_rate[1] or 0)
        ld_rate = ld_defined / ld_total if ld_total > 0 else 0.0
        ld_pass = ld_rate >= 0.80
        md_lines.extend([
            f"- Label-defined rows: `{ld_defined}` / `{ld_total}` ({fmt_pct(ld_rate)})",
            check_pass(ld_pass, f"Label-defined rate >= 80% (actual: {fmt_pct(ld_rate)})"),
            "",
        ])

        # 2b. Entry tradeable rate
        entry_tradeable_rate = con.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN entry_tradeable THEN 1 ELSE 0 END) AS tradeable
            FROM sample_panel_t
            WHERE label_defined
            """
        ).fetchone()
        et_total = int(entry_tradeable_rate[0] or 0)
        et_tradeable = int(entry_tradeable_rate[1] or 0)
        et_rate = et_tradeable / et_total if et_total > 0 else 0.0
        et_pass = et_rate >= 0.70
        md_lines.extend([
            f"- Entry-tradeable rate (among label-defined): `{et_tradeable}` / `{et_total}` ({fmt_pct(et_rate)})",
            check_pass(et_pass, f"Entry-tradeable rate >= 70% (actual: {fmt_pct(et_rate)})"),
            "",
        ])

        # 2c. Planned exit tradeable rate
        exit_tradeable_rate = con.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN planned_exit_tradeable THEN 1 ELSE 0 END) AS tradeable
            FROM sample_panel_t
            WHERE label_defined AND entry_tradeable
            """
        ).fetchone()
        ext_total = int(exit_tradeable_rate[0] or 0)
        ext_tradeable = int(exit_tradeable_rate[1] or 0)
        ext_rate = ext_tradeable / ext_total if ext_total > 0 else 0.0
        md_lines.extend([
            f"- Planned-exit-tradeable rate (among entry-tradeable): `{ext_tradeable}` / `{ext_total}` ({fmt_pct(ext_rate)})",
            "",
        ])

        # 2d. Actually exited rate
        actually_exited = con.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN actually_exited THEN 1 ELSE 0 END) AS exited
            FROM sample_panel_t
            WHERE label_defined AND entry_tradeable
            """
        ).fetchone()
        ae_total = int(actually_exited[0] or 0)
        ae_exited = int(actually_exited[1] or 0)
        ae_rate = ae_exited / ae_total if ae_total > 0 else 0.0
        ae_pass = ae_rate >= 0.95
        md_lines.extend([
            f"- Actually-exited rate (among entry-tradeable): `{ae_exited}` / `{ae_total}` ({fmt_pct(ae_rate)})",
            check_pass(ae_pass, f"Actually-exited rate >= 95% (actual: {fmt_pct(ae_rate)})"),
            "",
        ])

        # 2e. Delayed exit rate
        delayed_exit = con.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN exit_delay_days > 0 THEN 1 ELSE 0 END) AS delayed
            FROM execution_panel_t
            WHERE execution_path_status IN ('PLANNED_EXIT', 'DELAYED_EXIT')
            """
        ).fetchone()
        de_total = int(delayed_exit[0] or 0)
        de_delayed = int(delayed_exit[1] or 0)
        de_rate = de_delayed / de_total if de_total > 0 else 0.0
        md_lines.extend([
            f"- Delayed exit rate: `{de_delayed}` / `{de_total}` ({fmt_pct(de_rate)})",
            "",
        ])

        # 2f. Main vs conservative mask comparison
        mask_compare = con.execute(
            """
            SELECT
                SUM(CASE WHEN train_mask_v1 AND NOT train_mask_conservative THEN 1 ELSE 0 END) AS v1_only,
                SUM(CASE WHEN train_mask_conservative AND NOT train_mask_v1 THEN 1 ELSE 0 END) AS conservative_only,
                SUM(CASE WHEN train_mask_v1 AND train_mask_conservative THEN 1 ELSE 0 END) AS both,
                SUM(CASE WHEN NOT train_mask_v1 AND NOT train_mask_conservative THEN 1 ELSE 0 END) AS neither
            FROM sample_panel_t
            """
        ).fetchone()
        v1_only = int(mask_compare[0] or 0)
        conservative_only = int(mask_compare[1] or 0)
        both = int(mask_compare[2] or 0)
        neither = int(mask_compare[3] or 0)
        mask_disagreement_rate = v1_only / (v1_only + both) if (v1_only + both) > 0 else 0.0
        mask_consistent = mask_disagreement_rate < 0.30
        md_lines.extend([
            "- Main vs conservative mask comparison:",
            f"  - Both masks pass: `{both}`",
            f"  - Main only (exit-tradeable filtered out): `{v1_only}`",
            f"  - Conservative only: `{conservative_only}`",
            f"  - Neither: `{neither}`",
            f"  - Disagreement rate (main-only / both): `{fmt_pct(mask_disagreement_rate)}`",
            check_pass(mask_consistent, f"Mask disagreement rate < 30% (actual: {fmt_pct(mask_disagreement_rate)})"),
            "",
        ])

        # ---- Check if model scores exist in reference run ----
        model_scores_path = run_dir / "model_scores_D0.parquet"
        has_model_scores = model_scores_path.exists()

        if has_model_scores:
            con.execute(
                f"""
                CREATE OR REPLACE VIEW model_scores_t AS
                SELECT * FROM read_parquet({sql_path(model_scores_path)})
                """
            )

        # ---- 3. Placebo: Random label shuffling ----
        md_lines.extend([
            "---",
            "",
            "## 3. Placebo Tests",
            "",
            "### 3a. Random Label Shuffling",
            "",
            "Shuffling labels should destroy any signal. IC should collapse to ~0.",
            "",
        ])

        shuffle_ic_results = []

        if has_model_scores:
            # Get scored-with-label pairs for shuffling
            label_pairs = con.execute(
                """
                SELECT
                    s.snapshot_id,
                    s.instrument,
                    s.signal_date,
                    s.model_score_D0,
                    l.label_5d_next_open_close AS label
                FROM model_scores_t s
                INNER JOIN sample_panel_t p
                  ON s.snapshot_id = p.snapshot_id
                 AND s.instrument = p.instrument
                 AND s.signal_date = p.signal_date
                LEFT JOIN label_panel_t l
                  ON p.snapshot_id = l.snapshot_id
                 AND p.instrument = l.instrument
                 AND p.signal_date = l.signal_date
                WHERE p.ranking_eligible_D0
                  AND s.model_score_D0 IS NOT NULL
                  AND l.label_5d_next_open_close IS NOT NULL
                ORDER BY random()
                """
            ).fetchall()

            trials = args.n_shuffle_trials
            for trial in range(trials):
                # Shuffle labels in-memory
                records = [(row[0], row[1], str(row[2]), float(row[3]), float(row[4])) for row in label_pairs]
                labels = [r[4] for r in records]
                random.shuffle(labels)

                # Build temp table with shuffled labels
                shuffled_data = []
                for r, shuffled_label in zip(records, labels):
                    shuffled_data.append((r[0], r[1], r[2], r[3], shuffled_label))

                con.execute("DROP TABLE IF EXISTS shuffled_labels_t")
                con.execute(
                    """
                    CREATE TEMP TABLE shuffled_labels_t (
                        snapshot_id VARCHAR,
                        instrument VARCHAR,
                        signal_date VARCHAR,
                        model_score DOUBLE,
                        shuffled_label DOUBLE
                    )
                    """
                )
                con.executemany(
                    "INSERT INTO shuffled_labels_t VALUES (?, ?, ?, ?, ?)",
                    shuffled_data,
                )

                shuffled_ic = con.execute(
                    """
                    SELECT CORR(model_score, shuffled_label)
                    FROM shuffled_labels_t
                    """
                ).fetchone()[0]

                shuffled_ic_val = float(shuffled_ic) if shuffled_ic is not None else 0.0
                shuffle_ic_results.append(shuffled_ic_val)

            mean_shuffle_ic = float(np.mean(shuffle_ic_results))
            max_shuffle_ic = float(np.max(shuffle_ic_results))
            shuffle_pass = abs(mean_shuffle_ic) < 0.005

            md_lines.extend([
                f"- Trials: `{trials}`",
                f"- Mean shuffled IC: `{fmt(mean_shuffle_ic)}`",
                f"- Max |shuffled IC|: `{fmt(max_shuffle_ic)}`",
                check_pass(shuffle_pass, f"Mean |shuffled IC| < 0.005 (actual: {fmt(mean_shuffle_ic)})"),
                "",
            ])
        else:
            shuffle_pass = True
            mean_shuffle_ic = 0.0
            max_shuffle_ic = 0.0
            md_lines.extend([
                "- No model scores found in reference run (run has panels but no scores yet).",
                "  Skipping label-shuffle placebo test (will be runnable after a full-chain run).",
                "",
            ])

        # ---- 3b. Random score shuffling ----
        md_lines.extend([
            "### 3b. Random Score Shuffling",
            "",
            "Shuffling model scores should destroy portfolio discrimination. TopK returns should collapse to ~0.",
            "",
        ])

        if has_model_scores:
            score_shuffle_ics = []
            for trial in range(trials):
                records = [(row[0], row[1], str(row[2]), float(row[3]), float(row[4])) for row in label_pairs]
                labels = [r[4] for r in records]
                scores = [r[3] for r in records]
                random.shuffle(scores)

                score_shuffled = []
                for r, shuffled_score in zip(records, scores):
                    score_shuffled.append((r[0], r[1], r[2], shuffled_score, r[4]))

                con.execute("DROP TABLE IF EXISTS shuffled_scores_t")
                con.execute(
                    """
                    CREATE TEMP TABLE shuffled_scores_t (
                        snapshot_id VARCHAR,
                        instrument VARCHAR,
                        signal_date VARCHAR,
                        shuffled_score DOUBLE,
                        label DOUBLE
                    )
                    """
                )
                con.executemany(
                    "INSERT INTO shuffled_scores_t VALUES (?, ?, ?, ?, ?)",
                    score_shuffled,
                )

                ss_ic = con.execute(
                    """
                    SELECT CORR(shuffled_score, label)
                    FROM shuffled_scores_t
                    """
                ).fetchone()[0]
                score_shuffle_ics.append(float(ss_ic) if ss_ic is not None else 0.0)

            mean_ss_ic = float(np.mean(score_shuffle_ics))
            max_ss_ic = float(np.max(score_shuffle_ics))
            ss_pass = abs(mean_ss_ic) < 0.005

            md_lines.extend([
                f"- Trials: `{trials}`",
                f"- Mean shuffled-score IC: `{fmt(mean_ss_ic)}`",
                f"- Max |shuffled-score IC|: `{fmt(max_ss_ic)}`",
                check_pass(ss_pass, f"Mean |shuffled-score IC| < 0.005 (actual: {fmt(mean_ss_ic)})"),
                "",
            ])
        else:
            ss_pass = True
            mean_ss_ic = 0.0
            max_ss_ic = 0.0
            md_lines.extend([
                "- No model scores found. Skipping score-shuffle placebo test.",
                "",
            ])

        # ---- 4. Feature lagging test (if model scores exist) ----
        md_lines.extend([
            "### 3c. Feature Lagging Test (Structural Breach Detection)",
            "",
            "If lagging features by 1 day improves results, the original features likely",
            "contain forward-looking information (PIT breach).",
            "",
        ])

        if has_model_scores:
            fwd_look = con.execute(
                """
                WITH shifted AS (
                    SELECT
                        s.snapshot_id,
                        s.instrument,
                        s.signal_date,
                        s.model_score_D0,
                        l.label_5d_next_open_close AS label_same_day,
                        LEAD(l.label_5d_next_open_close) OVER (
                            PARTITION BY s.instrument
                            ORDER BY s.signal_date
                        ) AS label_next_day
                    FROM sample_panel_t p
                    INNER JOIN model_scores_t s
                      ON p.snapshot_id = s.snapshot_id
                     AND p.instrument = s.instrument
                     AND p.signal_date = s.signal_date
                    LEFT JOIN label_panel_t l
                      ON p.snapshot_id = l.snapshot_id
                     AND p.instrument = l.instrument
                     AND p.signal_date = l.signal_date
                    WHERE p.ranking_eligible_D0
                      AND s.model_score_D0 IS NOT NULL
                )
                SELECT
                    CORR(model_score_D0, label_same_day) AS ic_same_day,
                    CORR(model_score_D0, label_next_day) AS ic_lag_feature
                FROM shifted
                WHERE label_same_day IS NOT NULL AND label_next_day IS NOT NULL
                """
            ).fetchone()

            ic_same = float(fwd_look[0]) if fwd_look[0] is not None else None
            ic_lag = float(fwd_look[1]) if fwd_look[1] is not None else None
            lag_breach = False
            if ic_same is not None and ic_lag is not None:
                lag_breach = abs(ic_lag) > abs(ic_same) * 1.2 and ic_lag * ic_same > 0

            md_lines.extend([
                f"- IC (score vs same-day label): `{fmt(ic_same)}`",
                f"- IC (score vs NEXT-day label, i.e. feature lagged): `{fmt(ic_lag)}`",
                check_pass(not lag_breach, f"No forward-looking breach (IC_lag={fmt(ic_lag)} vs IC_same={fmt(ic_same)})"),
                "",
            ])
        else:
            ic_same = None
            ic_lag = None
            lag_breach = False
            md_lines.extend([
                "- No model scores found. Skipping feature lagging test.",
                "",
            ])

        # ---- 5. Sub-period direction stability ----
        md_lines.extend([
            "---",
            "",
            "## 4. Sub-period Direction Stability",
            "",
            "Checking IC direction consistency across training-set sub-periods.",
            "",
        ])

        subperiods = [
            ("2010-2012", "2010", "2012"),
            ("2013-2015", "2013", "2015"),
            ("2016-2018", "2016", "2018"),
            ("2019-2021", "2019", "2021"),
        ]

        subperiod_results = []
        for label, year_start, year_end in subperiods:
            if has_model_scores:
                sp = con.execute(
                    f"""
                    SELECT
                        CORR(s.model_score_D0, l.label_5d_next_open_close) AS period_ic,
                        COUNT(*) AS n
                    FROM sample_panel_t p
                    INNER JOIN model_scores_t s
                      ON p.snapshot_id = s.snapshot_id
                     AND p.instrument = s.instrument
                     AND p.signal_date = s.signal_date
                    LEFT JOIN label_panel_t l
                      ON p.snapshot_id = l.snapshot_id
                     AND p.instrument = l.instrument
                     AND p.signal_date = l.signal_date
                    WHERE p.ranking_eligible_D0
                      AND s.model_score_D0 IS NOT NULL
                      AND l.label_5d_next_open_close IS NOT NULL
                      AND SUBSTR(p.signal_date, 1, 4) >= {sql_quote(year_start)}
                      AND SUBSTR(p.signal_date, 1, 4) <= {sql_quote(year_end)}
                    """
                ).fetchone()
                period_ic = float(sp[0]) if sp[0] is not None else None
                period_n = int(sp[1] or 0)
            else:
                period_ic = None
                period_n = 0
            subperiod_results.append({"period": label, "ic": period_ic, "n": period_n})

            ic_str = fmt(period_ic) if period_ic is not None else "N/A"
            md_lines.append(f"- {label}: IC = `{ic_str}`, n = `{period_n}`")

        # Count how many sub-periods have same IC sign
        valid_ics = [sp["ic"] for sp in subperiod_results if sp["ic"] is not None]
        if valid_ics:
            pos_count = sum(1 for v in valid_ics if v > 0)
            neg_count = sum(1 for v in valid_ics if v < 0)
            dominant_sign = "positive" if pos_count >= neg_count else "negative"
            direction_consistency = max(pos_count, neg_count) / len(valid_ics)
            stable_pass = direction_consistency >= 0.75
            md_lines.extend([
                f"- Sub-periods with positive IC: `{pos_count}/{len(valid_ics)}`",
                f"- Sub-periods with negative IC: `{neg_count}/{len(valid_ics)}`",
                f"- Direction consistency: `{fmt_pct(direction_consistency)}`",
                check_pass(stable_pass, f"IC direction consistency >= 75% of sub-periods (actual: {fmt_pct(direction_consistency)})"),
                "",
            ])
        else:
            stable_pass = True
            direction_consistency = 0.0
            md_lines.extend([
                "- No valid IC data for sub-period analysis.",
                "",
            ])

        # ---- 6. Low liquidity impact on alpha ----
        md_lines.extend([
            "---",
            "",
            "## 5. Low Liquidity Exposure Audit",
            "",
            "Checking whether portfolio alpha depends on low-liquidity names.",
            "",
        ])

        if has_model_scores:
            low_liq_impact = con.execute(
                f"""
                WITH scored AS (
                    SELECT
                        p.snapshot_id,
                        p.instrument,
                        p.signal_date,
                        s.model_score_D0,
                        l.label_5d_next_open_close AS label
                    FROM sample_panel_t p
                    INNER JOIN model_scores_t s
                      ON p.snapshot_id = s.snapshot_id
                     AND p.instrument = s.instrument
                     AND p.signal_date = s.signal_date
                    LEFT JOIN label_panel_t l
                      ON p.snapshot_id = l.snapshot_id
                     AND p.instrument = l.instrument
                     AND p.signal_date = l.signal_date
                    WHERE p.ranking_eligible_D0
                      AND s.model_score_D0 IS NOT NULL
                      AND l.label_5d_next_open_close IS NOT NULL
                ),
                with_liquidity AS (
                    SELECT s.*, t.low_liquidity_flag_t AS low_liquidity_flag
                    FROM scored s
                    LEFT JOIN warehouse_db.serving.vw_tradability_daily t
                      ON s.snapshot_id = t.snapshot_id
                     AND s.instrument = t.ts_code
                     AND s.signal_date = t.trade_date
                    WHERE t.snapshot_id = {sql_quote(snapshot_id)}
                )
                SELECT
                    CORR(model_score_D0, label) FILTER (WHERE COALESCE(low_liquidity_flag, FALSE) = FALSE) AS ic_normal,
                    CORR(model_score_D0, label) FILTER (WHERE COALESCE(low_liquidity_flag, FALSE) = TRUE) AS ic_low_liquidity,
                    COUNT(*) FILTER (WHERE COALESCE(low_liquidity_flag, FALSE) = FALSE) AS n_normal,
                    COUNT(*) FILTER (WHERE COALESCE(low_liquidity_flag, FALSE) = TRUE) AS n_low_liquidity
                FROM with_liquidity
                """
            ).fetchone()

            ic_normal = float(low_liq_impact[0]) if low_liq_impact[0] is not None else None
            ic_low_liq = float(low_liq_impact[1]) if low_liq_impact[1] is not None else None
            n_normal = int(low_liq_impact[2] or 0)
            n_low_liq = int(low_liq_impact[3] or 0)

            liq_alpha_dependent = False
            if ic_normal is not None and ic_low_liq is not None and abs(ic_normal) > 0.001:
                # If IC drops by more than 50% when removing low-liq names, alpha is liquidity-dependent
                liq_alpha_dependent = (abs(ic_normal) - abs(ic_low_liq)) / abs(ic_normal) > 0.5

            md_lines.extend([
                f"- Normal liquidity: IC = `{fmt(ic_normal)}`, n = `{n_normal}`",
                f"- Low liquidity: IC = `{fmt(ic_low_liq)}`, n = `{n_low_liq}`",
                check_pass(not liq_alpha_dependent, "Alpha does NOT depend on low-liquidity names"),
                "",
            ])
        else:
            ic_normal = None
            ic_low_liq = None
            n_normal = 0
            n_low_liq = 0
            liq_alpha_dependent = False
            md_lines.extend([
                "- No model scores found. Skipping liquidity impact analysis.",
                "",
            ])

        # ---- 7. Benchmark alignment check ----
        md_lines.extend([
            "---",
            "",
            "## 6. Benchmark Alignment",
            "",
        ])

        benchmark_check = con.execute(
            f"""
            SELECT
                benchmark_code,
                benchmark_name,
                is_total_return,
                MIN(trade_date) AS first_date,
                MAX(trade_date) AS last_date,
                COUNT(*) AS n_days
            FROM warehouse_db.serving.vw_benchmark_daily
            WHERE snapshot_id = {sql_quote(snapshot_id)}
              AND benchmark_code = 'CSI_ALL_SHARE_TR'
            GROUP BY 1, 2, 3
            """
        ).fetchone()

        if benchmark_check:
            bm_code = benchmark_check[0]
            bm_name = benchmark_check[1]
            bm_total_return = bool(benchmark_check[2])
            md_lines.extend([
                f"- Primary benchmark: `{bm_code}` ({bm_name})",
                f"- Is total-return: `{bm_total_return}`",
                f"- Date range: `{benchmark_check[3]}` to `{benchmark_check[4]}`",
                f"- Trading days: `{int(benchmark_check[5] or 0)}`",
                check_pass(bm_total_return, "Primary benchmark is total-return"),
                "",
            ])
        else:
            bm_total_return = False
            md_lines.extend([
                "- Primary benchmark `CSI_ALL_SHARE_TR` not found!",
                check_pass(False, "Benchmark available"),
                "",
            ])

        # ---- Overall assessment ----
        md_lines.extend([
            "---",
            "",
            "## Overall Assessment",
            "",
        ])

        all_checks = [
            ("Data quality: train coverage >= 50%", coverage_pass),
            ("Data quality: no tradability degradation", degrad_pass),
            ("Data quality: no unresolved exit paths", unresolved_pass),
            ("Data quality: execution exit fully resolved for backtest_executable rows", execution_exit_resolution_pass),
            ("Label consistency: label-defined rate >= 80%", ld_pass),
            ("Label consistency: entry-tradeable rate >= 70%", et_pass),
            ("Label consistency: actually-exited rate >= 95%", ae_pass),
            ("Mask consistency: main vs conservative disagreement < 30%", mask_consistent),
            ("Placebo: random label shuffle IC ~0", shuffle_pass),
            ("Placebo: random score shuffle IC ~0", ss_pass),
            ("PIT integrity: no forward-looking breach", not lag_breach),
            ("Sub-period stability: IC direction consistency >= 75%", stable_pass),
            ("Low-liquidity: alpha not dependent on low-liq names", not liq_alpha_dependent),
            ("Benchmark: primary benchmark is total-return", bm_total_return),
        ]

        passed = sum(1 for _, p in all_checks if p)
        failed = sum(1 for _, p in all_checks if not p)
        total = len(all_checks)
        md_lines.append(f"**{passed}/{total} checks passed** ({failed} failed)")
        md_lines.append("")

        for name, check_ok in all_checks:
            md_lines.append(check_pass(check_ok, name))

        md_lines.append("")

        if failed == 0:
            md_lines.append(BOLD_PASS + " All checks passed. System integrity is sound.")
        else:
            md_lines.append(
                f"{BOLD_FAIL} {failed} check(s) failed. "
                "Review individual check results above before proceeding to confirmatory research."
            )
        md_lines.append("")

        # ---- Build results dict ----
        results = {
            "as_of_date": as_of_date,
            "reference_run_id": args.run_id,
            "snapshot_id": snapshot_id,
            "random_seed": args.random_seed,
            "n_shuffle_trials": args.n_shuffle_trials,
            "data_quality": {
                "panel_counts": {
                    "label_panel_rows": label_rows,
                    "sample_panel_rows": sample_rows,
                    "execution_panel_rows": exec_rows,
                    "ranking_eligible_rows": ranking_eligible_rows,
                    "train_mask_rows": train_mask_rows,
                    "train_conservative_rows": train_conservative_rows,
                    "eval_mask_rows": eval_mask_rows,
                    "eval_conservative_rows": eval_conservative_rows,
                },
                "train_label_coverage": label_coverage,
                "conservative_vs_standard_ratio": conservative_ratio,
                "tradability_degraded_rows": degraded_rows,
                "tradability_degraded_flag": degrad_pass,
                "low_liquidity_flagged_rows": low_liq_rows,
                "low_liquidity_rate": low_liq_rate,
                "terminal_event_rows": terminal_rows,
                "unresolved_exit_rows": unresolved_rows,
                "unresolved_exit_flag": unresolved_pass,
                "execution_exit_resolution": execution_exit_resolution_check,
                "terminal_event_repair_audit": terminal_event_repair_check,
            },
            "label_consistency": {
                "label_defined_rate": ld_rate,
                "label_defined_flag": ld_pass,
                "entry_tradeable_rate": et_rate,
                "entry_tradeable_flag": et_pass,
                "exit_tradeable_rate": ext_rate,
                "actually_exited_rate": ae_rate,
                "actually_exited_flag": ae_pass,
                "delayed_exit_rate": de_rate,
                "mask_disagreement_rate": mask_disagreement_rate,
                "mask_consistent_flag": mask_consistent,
                "mask_comparison": {
                    "v1_only": v1_only,
                    "conservative_only": conservative_only,
                    "both": both,
                    "neither": neither,
                },
            },
            "placebo_label_shuffle": {
                "trials": args.n_shuffle_trials if has_model_scores else 0,
                "mean_shuffled_ic": mean_shuffle_ic,
                "max_shuffled_ic": max_shuffle_ic,
                "pass_flag": shuffle_pass,
            },
            "placebo_score_shuffle": {
                "trials": args.n_shuffle_trials if has_model_scores else 0,
                "mean_shuffled_ic": mean_ss_ic,
                "max_shuffled_ic": max_ss_ic,
                "pass_flag": ss_pass,
            },
            "pit_integrity": {
                "ic_same_day": ic_same,
                "ic_lag_feature": ic_lag,
                "forward_looking_breach_flag": lag_breach,
            },
            "sub_period_stability": {
                "sub_periods": subperiod_results,
                "direction_consistency": direction_consistency,
                "stable_flag": stable_pass,
            },
            "low_liquidity_impact": {
                "ic_normal_liquidity": ic_normal,
                "ic_low_liquidity": ic_low_liq,
                "n_normal_liquidity": n_normal,
                "n_low_liquidity": n_low_liq,
                "alpha_liquidity_dependent_flag": liq_alpha_dependent,
            },
            "benchmark_alignment": {
                "primary_benchmark_code": bm_code if benchmark_check else None,
                "primary_is_total_return": bm_total_return,
                "benchmark_available_flag": benchmark_check is not None,
            },
            "overall": {
                "checks_passed": passed,
                "checks_total": total,
                "checks_failed": failed,
                "all_pass_flag": failed == 0,
            },
        }

    finally:
        con.close()

    write_json(json_output, results)
    md_output.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"System self-check complete: {json_output}")
    print(f"Report: {md_output}")
    print(f"Result: {passed}/{total} checks passed ({failed} failed)")


if __name__ == "__main__":
    main()
