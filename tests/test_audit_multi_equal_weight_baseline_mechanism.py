from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from conftest import load_module, read_text


SCRIPT_PATH = "scripts/audit_multi_equal_weight_baseline_mechanism.py"
DOC_PATH = "docs/multi_equal_weight_baseline_mechanism_audit.md"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def make_readout(
    *,
    primary_id: str,
    baseline_id: str = "multi_equal_weight_v1",
    cash_delta_train: float,
    cash_delta_validation: float,
    invested_delta_train: float,
    invested_delta_validation: float,
    turnover_delta_train: float,
    turnover_delta_validation: float,
) -> dict:
    return {
        "readout_label": "TRAINVAL PORTFOLIO DRY-RUN ESTIMATE ONLY — NOT FROZEN TEST — NOT A FORMAL STRATEGY CONCLUSION",
        "frozen_test_accessed": False,
        "formal_metrics_generated": False,
        "split_config": {
            "train_start": "20100101",
            "train_end": "20181231",
            "validation_start": "20190101",
            "validation_end": "20211231",
            "test_excluded_start": "20220101",
            "test_excluded_end": "20251231",
        },
        "primary_run": {
            "run_id": f"run_{primary_id}",
            "attempt_id": "attempt_terminal_resolved_panel",
            "candidate_scheme_id": primary_id,
            "run_state_acceptance_overall_passed": True,
        },
        "baseline_run": {
            "run_id": "run_baseline",
            "attempt_id": "attempt_terminal_resolved_panel",
            "candidate_scheme_id": baseline_id,
            "run_state_acceptance_overall_passed": True,
        },
        "windows": {
            "primary": {
                "train": {
                    "avg_cash_weight": 0.74,
                    "avg_invested_weight": 0.26,
                    "avg_turnover_daily": 0.12,
                    "annual_relative_return_trainval_dry_run_estimate": 0.01,
                    "relative_ir_estimate": 0.1,
                },
                "validation": {
                    "avg_cash_weight": 0.75,
                    "avg_invested_weight": 0.25,
                    "avg_turnover_daily": 0.11,
                    "annual_relative_return_trainval_dry_run_estimate": -0.02,
                    "relative_ir_estimate": -0.2,
                },
            },
            "baseline": {
                "train": {
                    "avg_cash_weight": 0.76,
                    "avg_invested_weight": 0.24,
                    "avg_turnover_daily": 0.10,
                    "annual_relative_return_trainval_dry_run_estimate": 0.03,
                    "relative_ir_estimate": 0.2,
                },
                "validation": {
                    "avg_cash_weight": 0.78,
                    "avg_invested_weight": 0.22,
                    "avg_turnover_daily": 0.09,
                    "annual_relative_return_trainval_dry_run_estimate": 0.01,
                    "relative_ir_estimate": 0.1,
                },
            },
            "comparison": {
                "train": {
                    "avg_cash_weight_delta_vs_baseline": cash_delta_train,
                    "avg_invested_weight_delta_vs_baseline": invested_delta_train,
                    "avg_turnover_daily_delta_vs_baseline": turnover_delta_train,
                },
                "validation": {
                    "avg_cash_weight_delta_vs_baseline": cash_delta_validation,
                    "avg_invested_weight_delta_vs_baseline": invested_delta_validation,
                    "avg_turnover_daily_delta_vs_baseline": turnover_delta_validation,
                },
            },
        },
    }


def test_audit_script_cli_help_runs(repo_root: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(repo_root / SCRIPT_PATH), "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--baseline-builder" in result.stdout
    assert "--confirmed5-readout" in result.stdout
    assert "--output-json" in result.stdout


def test_static_builder_audit_detects_no_future_fields() -> None:
    module = load_module(SCRIPT_PATH, "audit_multi_equal_weight_baseline_mechanism_module")
    safe_builder = """
    CREATE OR REPLACE VIEW bars AS
    SELECT trade_date AS signal_date, adj_close, amount, vol, pct_chg
    FROM warehouse_db.serving.vw_bars_daily;
    SELECT LAG(adj_close, 1) OVER (PARTITION BY instrument ORDER BY signal_date);
    WINDOW w30 AS (PARTITION BY instrument ORDER BY signal_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW);
    WINDOW w60 AS (PARTITION BY instrument ORDER BY signal_date ROWS BETWEEN 59 PRECEDING AND CURRENT ROW);
    SELECT * FROM feature_frame WHERE ranking_eligible_D0;
    trainval-only and does not access frozen test data
    """

    payload = module.inspect_multi_equal_weight_builder(safe_builder, Path("/tmp/builder.py"))

    assert payload["future_field_usage_detected"] is False
    assert payload["required_patterns"]["trade_date_as_signal_date"] is True
    assert payload["required_patterns"]["rolling_window_30"] is True
    assert payload["required_patterns"]["rolling_window_60"] is True
    assert payload["required_patterns"]["ranking_eligible_d0_guard"] is True


def test_audit_script_builds_conditional_pass_from_small_fixture(repo_root: Path, tmp_path: Path) -> None:
    baseline_builder = tmp_path / "build_multi_equal_weight_v1_scores.py"
    p98_builder = tmp_path / "build_reversal_tail_composite_model_scores.py"
    p98_audit = tmp_path / "p98_audit.json"
    confirmed5_readout = tmp_path / "confirmed5_readout.json"
    v2_readout = tmp_path / "v2_readout.json"
    terminal_approval = tmp_path / "terminal_approval.json"
    repaired_candidate = tmp_path / "repaired_candidate.json"
    project_status_doc = tmp_path / "project_status.md"
    confirmed5_doc = tmp_path / "confirmed5.md"
    v2_doc = tmp_path / "v2.md"
    output_json = tmp_path / "audit.json"
    output_md = tmp_path / "audit.md"

    baseline_builder.write_text(
        """
        SELECT trade_date AS signal_date, adj_close, amount, vol, pct_chg
        FROM warehouse_db.serving.vw_bars_daily;
        SELECT LAG(adj_close, 1) OVER (PARTITION BY instrument ORDER BY signal_date);
        WINDOW w30 AS (PARTITION BY instrument ORDER BY signal_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW);
        WINDOW w60 AS (PARTITION BY instrument ORDER BY signal_date ROWS BETWEEN 59 PRECEDING AND CURRENT ROW);
        SELECT * FROM feature_frame WHERE ranking_eligible_D0;
        trainval-only and does not access frozen test data
        project_sample_panel
        """.strip()
        + "\n",
        encoding="utf-8",
    )
    p98_builder.write_text(
        """
        SELECT * FROM sample_panel s WHERE s.ranking_eligible_D0;
        SELECT PERCENTILE_CONT(0.98) WITHIN GROUP (ORDER BY nr_score);
        SELECT * FROM nr_p98 WHERE n.nr_score < p.p98;
        """.strip()
        + "\n",
        encoding="utf-8",
    )
    write_json(
        p98_audit,
        {
            "candidate_scheme_id": "reversal_tail_exclude_p98_v1",
            "source_runs": {"reversal_source_run_id": "exploratory_cross_horizon_c1_reversal_only"},
            "summary_counts": {"total_rows": 100, "scored_rows": 90},
        },
    )
    write_json(
        confirmed5_readout,
        make_readout(
            primary_id="nlc_v1_confirmed5_lgbm_depth3_seed42",
            cash_delta_train=-0.02,
            cash_delta_validation=-0.03,
            invested_delta_train=0.02,
            invested_delta_validation=0.03,
            turnover_delta_train=0.02,
            turnover_delta_validation=0.01,
        ),
    )
    write_json(
        v2_readout,
        make_readout(
            primary_id="nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42",
            cash_delta_train=0.01,
            cash_delta_validation=0.01,
            invested_delta_train=-0.01,
            invested_delta_validation=-0.01,
            turnover_delta_train=-0.01,
            turnover_delta_validation=-0.01,
        ),
    )
    write_json(
        terminal_approval,
        {
            "approval_policy_version": "terminal_exit_policy_v1",
            "contract_ref": "contracts/terminal_exit_policy.v1.json",
            "summary": {"approval_gate_passed_count": 10},
            "notes": [
                "Approval gate passed does not mean the row is priced.",
                "approval audit never backfills actual_exit_date, actual_sell_price, or execution_delayed_realized_return.",
            ],
        },
    )
    write_json(
        repaired_candidate,
        {
            "summary": {
                "candidate_rows_count": 10,
                "still_hard_blocker_count": 10,
                "priced_rows_count": 0,
            },
            "notes": [
                "No pricing, no actual_exit_date, and no actual_sell_price are backfilled by this builder."
            ],
        },
    )
    policy_text = "\n".join(
        [
            "同 train / validation split",
            "同 execution contract",
            "同 terminal exit policy",
            "同 portfolio construction rules",
            "同 cash / invested capital 口径",
            "same-contract baseline comparison 是最低门槛",
        ]
    )
    project_status_doc.write_text(policy_text + "\n", encoding="utf-8")
    confirmed5_doc.write_text(policy_text + "\n", encoding="utf-8")
    v2_doc.write_text(policy_text + "\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / SCRIPT_PATH),
            "--baseline-builder",
            str(baseline_builder),
            "--p98-builder",
            str(p98_builder),
            "--p98-audit",
            str(p98_audit),
            "--upstream-reversal-audit",
            str(tmp_path / "missing_upstream_reversal_audit.json"),
            "--confirmed5-readout",
            str(confirmed5_readout),
            "--v2-readout",
            str(v2_readout),
            "--terminal-approval",
            str(terminal_approval),
            "--repaired-candidate",
            str(repaired_candidate),
            "--project-status-doc",
            str(project_status_doc),
            "--confirmed5-decision-doc",
            str(confirmed5_doc),
            "--v2-decision-doc",
            str(v2_doc),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["frozen_test_accessed"] is False
    assert payload["formal_metrics_generated"] is False
    assert payload["baseline_score_construction_audit"]["future_field_usage_detected"] is False
    assert payload["d0_visibility_audit"]["d0_visibility_guardrails"]["historical_windows_end_at_current_row"] is True
    assert payload["universe_mask_tradability_alignment_audit"]["same_contract_policy_checks"]["same_execution_contract_required"] is True
    assert payload["baseline_minimum_hurdle_recommendation"]["status"] == "conditional_pass"
    assert payload["hidden_advantage_found"] is False
    assert any("Upstream reversal source run-state audit" in item for item in payload["blockers"])
    assert "Frozen test accessed: `False`." in output_md.read_text(encoding="utf-8")


def test_audit_doc_captures_d0_visibility_same_contract_and_no_frozen_test() -> None:
    text = read_text(DOC_PATH)

    assert "D0 Visibility Audit" in text
    assert "same-contract comparison" in text
    assert "不读取 `frozen test`" in text
    assert "conditional pass" in text
    assert "继续允许 `multi_equal_weight_v1` 作为最低门槛" in text
