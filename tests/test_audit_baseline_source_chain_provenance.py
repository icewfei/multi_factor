from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from conftest import load_module


SCRIPT_PATH = "scripts/audit_baseline_source_chain_provenance.py"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def make_c1_registry_row(*, score_rule: str = "percentile_rank(reversal_5d_raw ASC); require min_feature_count >= 1") -> dict:
    return {
        "candidate_scheme_id": "exploratory_cross_horizon_c1_reversal_only",
        "feature_preset": "single_signal_reversal_5d_v1",
        "score_rule": score_rule,
    }


def make_attempt_row(
    tmp_path: Path,
    *,
    scores_exists: bool,
    manifest_exists: bool,
    audit_exists: bool,
) -> dict:
    scores_path = tmp_path / "artifacts" / "run_state" / "exploratory_cross_horizon_c1_reversal_only" / "model_scores_D0.parquet"
    manifest_path = tmp_path / "artifacts" / "run_state" / "exploratory_cross_horizon_c1_reversal_only" / "attempts" / "attempt_1" / "run_state_attempt_manifest.json"
    audit_path = tmp_path / "artifacts" / "run_state" / "exploratory_cross_horizon_c1_reversal_only" / "attempts" / "attempt_1" / "data_quality_audit.json"
    if scores_exists:
        scores_path.parent.mkdir(parents=True, exist_ok=True)
        scores_path.write_text("placeholder\n", encoding="utf-8")
    if manifest_exists:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(manifest_path, {"attempt_id": "attempt_1"})
    if audit_exists:
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(audit_path, {"summary_counts": {"total_rows": 1}})
    return {
        "run_id": "exploratory_cross_horizon_c1_reversal_only",
        "attempt_id": "attempt_1",
        "scores_path": str(scores_path),
        "attempt_manifest_path": str(manifest_path),
        "data_quality_audit_path": str(audit_path),
    }


def make_c1_round_prereg() -> dict:
    return {
        "candidate_scheme_ids": [
            "exploratory_cross_horizon_c1_reversal_only",
            "exploratory_cross_horizon_c2_momentum_only",
            "exploratory_cross_horizon_c3_reversal_momentum",
        ],
        "planned_candidate_scheme_ids": [
            "exploratory_cross_horizon_c1_reversal_only",
            "exploratory_cross_horizon_c2_momentum_only",
            "exploratory_cross_horizon_c3_reversal_momentum",
        ],
        "serial_rule": "三个候选在 prereg 时一次性冻结。运行顺序为串行，但非级联淘汰。",
        "forbidden": ["不能查看 2022-2025 测试集"],
        "change_detail": "仅允许使用 reversal_5d_raw 和 momentum_60_5_raw。",
    }


def make_p98_tail_prereg() -> dict:
    return {
        "baseline_primary": {
            "source": "exploratory_cross_horizon_c1_reversal_only/model_scores_D0.parquet (score × -1)",
        },
        "success_rules": {
            "dimension_b_pipeline_compatibility": {
                "top10_avg_label": "> 0",
                "top10_bot10_spread": "> 0.003",
            },
            "ic_computation_method": "CORR of score vs oracle label_5d_next_open_close",
        },
        "learnability_diagnostic_reference": "artifacts/fixed_test/learnability_diagnostic/learnability_diagnostic_20260502.md",
    }


def make_p98_promotion_prereg() -> dict:
    return {
        "artifact_inputs": {
            "reversal_source_run_id": "exploratory_cross_horizon_c1_reversal_only",
        },
        "time_partition_plan": {
            "test_window_access": "forbidden",
        },
    }


SAFE_BASELINE_BUILDER = """
CREATE OR REPLACE VIEW p98_scores AS SELECT * FROM scores;
CREATE OR REPLACE VIEW bar_features AS
SELECT adj_close, amount, vol, pct_chg FROM warehouse_db.serving.vw_bars_daily;
SELECT * FROM feature_frame WHERE ranking_eligible_D0;
trainval-only and does not access frozen test data
alpha158_cord30_raw alpha158_corr30_raw alpha158_vsumd60_raw
"""


SAFE_C1_BUILDER = """
single_signal_reversal_5d_v1
("reversal_5d_raw", "reversal_rank")
SELECT trade_date AS signal_date, adj_close
FROM warehouse_db.serving.vw_bars_daily;
SELECT (adj_close / LAG(adj_close, 5) OVER w - 1.0) AS reversal_5d_raw;
SELECT * FROM feature_frame WHERE ranking_eligible_D0 AND reversal_5d_raw IS NOT NULL;
SELECT PERCENT_RANK() OVER (
    PARTITION BY snapshot_id, signal_date
    ORDER BY reversal_5d_raw ASC, instrument ASC
) AS reversal_rank;
"""


SAFE_P98_BUILDER = """
REVERSAL_SOURCE = RUN_STATE_DIR / "exploratory_cross_horizon_c1_reversal_only" / "model_scores_D0.parquet"
SELECT * FROM sample_panel s WHERE s.ranking_eligible_D0;
SELECT -1.0 * r.model_score_D0 AS nr_score;
SELECT PERCENTILE_CONT(0.98) WITHIN GROUP (ORDER BY nr_score) AS p98;
SELECT * FROM nr_p98 WHERE n.nr_score < p.p98;
"""


def test_audit_script_cli_help_runs(repo_root: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(repo_root / SCRIPT_PATH), "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--c1-builder" in result.stdout
    assert "--scheme-attempt-log" in result.stdout
    assert "--output-json" in result.stdout


def test_future_field_fixture_is_forbidden() -> None:
    module = load_module(SCRIPT_PATH, "audit_baseline_source_chain_provenance_module_future")

    payload = module.inspect_c1_builder(
        SAFE_C1_BUILDER + "\nSELECT next_open, close_D1 FROM labels;",
        Path("/tmp/build_baseline_model_scores.py"),
        make_c1_registry_row(),
    )

    assert "next_open" in payload["future_field_hits"]


def test_label_and_realized_return_fixture_is_forbidden() -> None:
    module = load_module(SCRIPT_PATH, "audit_baseline_source_chain_provenance_module_label")

    payload = module.inspect_p98_builder(
        SAFE_P98_BUILDER + "\nSELECT label_5d_next_open_close, execution_delayed_realized_return FROM t;",
        Path("/tmp/build_reversal_tail_composite_model_scores.py"),
        {"candidate_scheme_id": "reversal_tail_exclude_p98_v1"},
    )

    assert "label_" in payload["label_or_realized_return_hits"]
    assert "execution_delayed_realized_return" in payload["label_or_realized_return_hits"]


def test_d0_visibility_fixture_passes_for_safe_history_only_builder() -> None:
    module = load_module(SCRIPT_PATH, "audit_baseline_source_chain_provenance_module_d0")

    payload = module.inspect_c1_builder(
        SAFE_C1_BUILDER,
        Path("/tmp/build_baseline_model_scores.py"),
        make_c1_registry_row(),
    )

    assert payload["required_patterns"]["trade_date_as_signal_date"] is True
    assert payload["required_patterns"]["reversal_formula_present"] is True
    assert payload["required_patterns"]["ranking_guard_present"] is True
    assert payload["required_patterns"]["no_lead_usage"] is True
    assert payload["required_patterns"]["no_following_usage"] is True


def test_partial_missing_provenance_is_conditional_pass() -> None:
    module = load_module(SCRIPT_PATH, "audit_baseline_source_chain_provenance_module_partial")

    payload = module.inspect_artifact_reproducibility(
        make_attempt_row(Path("/tmp"), scores_exists=True, manifest_exists=False, audit_exists=False)
    )

    assert payload["status"] == "conditional_pass"


def test_missing_provenance_blocks_final_status(repo_root: Path, tmp_path: Path) -> None:
    baseline_builder = tmp_path / "build_multi_equal_weight_v1_scores.py"
    c1_builder = tmp_path / "build_baseline_model_scores.py"
    p98_builder = tmp_path / "build_reversal_tail_composite_model_scores.py"
    candidate_registry = tmp_path / "candidate_scheme_registry.jsonl"
    scheme_attempt_log = tmp_path / "scheme_attempt_log.jsonl"
    c1_round_prereg = tmp_path / "c1_round_prereg.json"
    p98_tail_prereg = tmp_path / "p98_tail_prereg.json"
    p98_promotion_prereg = tmp_path / "p98_promotion_prereg.json"
    p98_audit = tmp_path / "p98_audit.json"
    output_json = tmp_path / "audit.json"
    output_md = tmp_path / "audit.md"

    baseline_builder.write_text(SAFE_BASELINE_BUILDER, encoding="utf-8")
    c1_builder.write_text(SAFE_C1_BUILDER, encoding="utf-8")
    p98_builder.write_text(SAFE_P98_BUILDER, encoding="utf-8")
    write_jsonl(candidate_registry, [make_c1_registry_row()])
    write_jsonl(
        scheme_attempt_log,
        [make_attempt_row(tmp_path, scores_exists=False, manifest_exists=False, audit_exists=False)],
    )
    write_json(c1_round_prereg, make_c1_round_prereg())
    write_json(p98_tail_prereg, make_p98_tail_prereg())
    write_json(p98_promotion_prereg, make_p98_promotion_prereg())
    write_json(
        p98_audit,
        {
            "candidate_scheme_id": "reversal_tail_exclude_p98_v1",
            "source_runs": {"reversal_source_run_id": "exploratory_cross_horizon_c1_reversal_only"},
        },
    )

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / SCRIPT_PATH),
            "--baseline-builder",
            str(baseline_builder),
            "--c1-builder",
            str(c1_builder),
            "--p98-builder",
            str(p98_builder),
            "--candidate-registry",
            str(candidate_registry),
            "--scheme-attempt-log",
            str(scheme_attempt_log),
            "--c1-round-prereg",
            str(c1_round_prereg),
            "--p98-tail-prereg",
            str(p98_tail_prereg),
            "--p98-promotion-prereg",
            str(p98_promotion_prereg),
            "--p98-audit",
            str(p98_audit),
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
    assert payload["final_status"] == "blocked"
    assert payload["baseline_status_recommendation"] == "keep_conditional_pass_and_retain_blocker"
    assert any("attempt_manifest_path missing locally" in item for item in payload["missing_evidence"])
    assert any("data_quality_audit_path missing locally" in item for item in payload["missing_evidence"])
