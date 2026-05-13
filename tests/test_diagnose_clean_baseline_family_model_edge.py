from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb
import pandas as pd

from conftest import REPO_ROOT, read_text


SCRIPT_PATH = "scripts/diagnose_clean_baseline_family_model_edge.py"


def write_parquet(path: Path, frame: pd.DataFrame) -> None:
    con = duckdb.connect()
    try:
        con.register("frame_view", frame)
        con.execute(f"COPY frame_view TO '{path.as_posix()}' (FORMAT PARQUET)")
    finally:
        con.close()


def build_fixture_files(tmp_path: Path) -> dict[str, Path]:
    snapshot_id = "snap"
    instruments = [f"I{i:02d}" for i in range(20)]
    dates = [
        ("20200102", "train"),
        ("20200103", "train"),
        ("20210104", "validation"),
        ("20210105", "validation"),
    ]
    label_rows: list[dict[str, object]] = []
    split_rows: list[dict[str, object]] = []
    no_p98_rows: list[dict[str, object]] = []
    momentum_rows: list[dict[str, object]] = []
    liquidity_rows: list[dict[str, object]] = []
    random_rows: list[dict[str, object]] = []
    p98_rows: list[dict[str, object]] = []
    multi_equal_rows: list[dict[str, object]] = []

    for signal_date, split_bucket in dates:
        labels = {instrument: 0.20 - i * 0.01 for i, instrument in enumerate(instruments)}
        strong_order = instruments
        medium_order = ["I00", "I02", "I01", "I03"] + instruments[4:]
        weak_order = list(reversed(instruments))

        strong_rank_scores = {instrument: rank * 0.05 for rank, instrument in enumerate(strong_order)}
        medium_rank_scores = {instrument: rank * 0.05 for rank, instrument in enumerate(medium_order)}
        weak_rank_scores = {instrument: rank * 0.05 for rank, instrument in enumerate(weak_order)}
        p98_scores = {instrument: 1.0 - rank * 0.05 for rank, instrument in enumerate(strong_order)}
        multi_equal_scores = {
            instrument: 1.0 - rank * 0.05 for rank, instrument in enumerate(medium_order)
        }

        for instrument in instruments:
            label_rows.append(
                {
                    "snapshot_id": snapshot_id,
                    "instrument": instrument,
                    "signal_date": signal_date,
                    "label_5d_next_open_close": labels[instrument],
                    "label_defined": True,
                }
            )
            split_rows.append(
                {
                    "snapshot_id": snapshot_id,
                    "instrument": instrument,
                    "signal_date": signal_date,
                    "split_bucket": split_bucket,
                    "train_flag": split_bucket == "train",
                    "validation_flag": split_bucket == "validation",
                }
            )
            no_p98_rows.append(
                {
                    "snapshot_id": snapshot_id,
                    "instrument": instrument,
                    "signal_date": signal_date,
                    "candidate_scheme_id": "no_p98_reversal_baseline_v1",
                    "model_score_D0": medium_rank_scores[instrument],
                }
            )
            momentum_rows.append(
                {
                    "snapshot_id": snapshot_id,
                    "instrument": instrument,
                    "signal_date": signal_date,
                    "candidate_scheme_id": "clean_momentum_20d_baseline_v1",
                    "model_score_D0": medium_rank_scores[instrument],
                }
            )
            liquidity_rows.append(
                {
                    "snapshot_id": snapshot_id,
                    "instrument": instrument,
                    "signal_date": signal_date,
                    "candidate_scheme_id": "clean_liquidity_adjusted_reversal_baseline_v1",
                    "model_score_D0": medium_rank_scores[instrument],
                }
            )
            random_rows.append(
                {
                    "snapshot_id": snapshot_id,
                    "instrument": instrument,
                    "signal_date": signal_date,
                    "candidate_scheme_id": "clean_equal_weight_random_eligible_baseline_v1",
                    "model_score_D0": weak_rank_scores[instrument],
                }
            )
            p98_rows.append(
                {
                    "snapshot_id": snapshot_id,
                    "instrument": instrument,
                    "signal_date": signal_date,
                    "candidate_scheme_id": "reversal_tail_exclude_p98_v1",
                    "model_score_D0": p98_scores[instrument],
                }
            )
            multi_equal_rows.append(
                {
                    "instrument": instrument,
                    "signal_date": signal_date,
                    "candidate_scheme_id": "multi_equal_weight_v1",
                    "model_score_D0": multi_equal_scores[instrument],
                }
            )

    files = {
        "no_p98_scores": tmp_path / "no_p98_scores.parquet",
        "momentum_scores": tmp_path / "momentum_scores.parquet",
        "liquidity_scores": tmp_path / "liquidity_scores.parquet",
        "random_scores": tmp_path / "random_scores.parquet",
        "p98_scores": tmp_path / "p98_scores.parquet",
        "multi_equal_scores": tmp_path / "multi_equal_scores.parquet",
        "label_panel": tmp_path / "label_panel.parquet",
        "split_panel": tmp_path / "split_panel.parquet",
        "no_p98_audit": tmp_path / "no_p98_audit.json",
        "momentum_audit": tmp_path / "momentum_audit.json",
        "liquidity_audit": tmp_path / "liquidity_audit.json",
        "random_audit": tmp_path / "random_audit.json",
        "output_json": tmp_path / "diagnosis.json",
        "output_md": tmp_path / "diagnosis.md",
    }

    write_parquet(files["no_p98_scores"], pd.DataFrame(no_p98_rows))
    write_parquet(files["momentum_scores"], pd.DataFrame(momentum_rows))
    write_parquet(files["liquidity_scores"], pd.DataFrame(liquidity_rows))
    write_parquet(files["random_scores"], pd.DataFrame(random_rows))
    write_parquet(files["p98_scores"], pd.DataFrame(p98_rows))
    write_parquet(files["multi_equal_scores"], pd.DataFrame(multi_equal_rows))
    write_parquet(files["label_panel"], pd.DataFrame(label_rows))
    write_parquet(files["split_panel"], pd.DataFrame(split_rows))

    for baseline_id, audit_path, extra in [
        ("no_p98_reversal_baseline_v1", files["no_p98_audit"], {}),
        ("clean_momentum_20d_baseline_v1", files["momentum_audit"], {}),
        (
            "clean_liquidity_adjusted_reversal_baseline_v1",
            files["liquidity_audit"],
            {
                "liquidity_field_used": "amount",
                "volume_field_source": "vol",
                "amount_field_source": "amount",
            },
        ),
        ("clean_equal_weight_random_eligible_baseline_v1", files["random_audit"], {}),
    ]:
        audit_path.write_text(
            json.dumps(
                {
                    "candidate_scheme_id": baseline_id,
                    "baseline_id": baseline_id,
                    "row_count": 80,
                    "null_score_count": 0,
                    "nonfinite_score_count": 0,
                    "score_direction": "fixture direction",
                    "p98_used": False,
                    "label_diagnostics_used": False,
                    "frozen_test_accessed": False,
                    "d0_visibility_audit": {"pass": True},
                    "leakage_audit": {"pass": True},
                }
                | extra,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return files


def run_script(repo_root: Path, files: dict[str, Path]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(repo_root / SCRIPT_PATH),
            "--no-p98-scores",
            str(files["no_p98_scores"]),
            "--no-p98-audit",
            str(files["no_p98_audit"]),
            "--momentum-scores",
            str(files["momentum_scores"]),
            "--momentum-audit",
            str(files["momentum_audit"]),
            "--liquidity-scores",
            str(files["liquidity_scores"]),
            "--liquidity-audit",
            str(files["liquidity_audit"]),
            "--random-scores",
            str(files["random_scores"]),
            "--random-audit",
            str(files["random_audit"]),
            "--p98-scores",
            str(files["p98_scores"]),
            "--multi-equal-scores",
            str(files["multi_equal_scores"]),
            "--label-panel",
            str(files["label_panel"]),
            "--split-panel",
            str(files["split_panel"]),
            "--topk",
            "5",
            "--output-json",
            str(files["output_json"]),
            "--output-md",
            str(files["output_md"]),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_clean_baseline_family_model_edge_diagnosis_outputs_expected_shape(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    files = build_fixture_files(tmp_path)
    result = run_script(repo_root, files)
    assert result.returncode == 0, result.stderr

    payload = json.loads(files["output_json"].read_text(encoding="utf-8"))
    assert payload["diagnostic_only"] is True
    assert payload["frozen_test_accessed"] is False
    assert payload["formal_metrics_generated"] is False
    assert payload["portfolio_run_executed"] is False
    assert "no_p98_reversal_baseline_v1_train" in payload["diagnostics"]
    assert "clean_momentum_20d_baseline_v1_validation" in payload["diagnostics"]
    assert "clean_liquidity_adjusted_reversal_baseline_v1_validation" in payload["diagnostics"]
    assert "clean_equal_weight_random_eligible_baseline_v1_validation" in payload["diagnostics"]
    assert "p98_conditional_reference_validation" in payload["diagnostics"]
    assert "multi_equal_weight_v1_conditional_reference_validation" in payload["diagnostics"]


def test_clean_baseline_family_model_edge_diagnosis_recommends_only_positive_clean_candidates(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    files = build_fixture_files(tmp_path)
    result = run_script(repo_root, files)
    assert result.returncode == 0, result.stderr

    payload = json.loads(files["output_json"].read_text(encoding="utf-8"))
    clean_results = payload["conclusion"]["clean_baseline_results"]
    assert clean_results["no_p98_reversal_baseline_v1"]["has_model_layer_edge"] is True
    assert clean_results["no_p98_reversal_baseline_v1"]["has_topk_head_quality"] is True
    assert clean_results["clean_liquidity_adjusted_reversal_baseline_v1"][
        "recommend_same_contract_portfolio_dry_run_preparation"
    ] is True
    assert clean_results["clean_equal_weight_random_eligible_baseline_v1"][
        "recommend_same_contract_portfolio_dry_run_preparation"
    ] is False
    assert payload["conclusion"]["can_replace_p98_conditional_baseline"] is False
    assert payload["conclusion"]["can_parallel_p98_conditional_baseline"] is True


def test_markdown_discloses_conditional_references(repo_root: Path, tmp_path: Path) -> None:
    files = build_fixture_files(tmp_path)
    result = run_script(repo_root, files)
    assert result.returncode == 0, result.stderr

    markdown = files["output_md"].read_text(encoding="utf-8")
    assert "conditional_reference_only" in markdown
    assert "p98 conditional baseline" in markdown
    assert "multi_equal_weight_v1 conditional baseline" in markdown


def test_script_text_excludes_portfolio_and_frozen_test_actions() -> None:
    script_text = read_text(SCRIPT_PATH).lower()
    assert "holdings.csv" not in script_text
    assert "portfolio_weights" not in script_text
    assert "fixed_test" not in script_text
