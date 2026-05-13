from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb
import pandas as pd

from conftest import REPO_ROOT, read_text


SCRIPT_PATH = "scripts/diagnose_no_p98_clean_baseline_model_edge.py"


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
    p98_rows: list[dict[str, object]] = []
    confirmed5_rows: list[dict[str, object]] = []
    v2_rows: list[dict[str, object]] = []
    baseline_rows: list[dict[str, object]] = []

    for signal_date, split_bucket in dates:
        labels = {instrument: 0.20 - i * 0.01 for i, instrument in enumerate(instruments)}
        p98_order = instruments
        no_p98_order = instruments[:]
        if split_bucket == "validation":
            # Keep the full-cross-section ordering weakly positive while damaging the head.
            no_p98_order = ["I15", "I16", "I17", "I18", "I19"] + instruments[:15]
        v2_order = ["I02", "I00", "I01", "I03"] + instruments[4:]
        baseline_order = ["I00", "I01", "I02", "I03"] + instruments[4:]

        p98_scores = {instrument: 1.0 - rank * 0.05 for rank, instrument in enumerate(p98_order)}
        no_p98_scores = {instrument: rank * 0.05 for rank, instrument in enumerate(no_p98_order)}
        v2_scores = {instrument: 1.0 - rank * 0.05 for rank, instrument in enumerate(v2_order)}
        baseline_scores = {instrument: 1.0 - rank * 0.05 for rank, instrument in enumerate(baseline_order)}

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
                    "model_score_D0": no_p98_scores[instrument],
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
            confirmed5_rows.append(
                {
                    "snapshot_id": snapshot_id,
                    "instrument": instrument,
                    "signal_date": signal_date,
                    "candidate_scheme_id": "nlc_v1_confirmed5_lgbm_depth3_seed42",
                    "model_score_D0": p98_scores[instrument],
                }
            )
            v2_rows.append(
                {
                    "snapshot_id": snapshot_id,
                    "instrument": instrument,
                    "signal_date": signal_date,
                    "candidate_scheme_id": "nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42",
                    "model_score_D0": v2_scores[instrument],
                }
            )
            baseline_rows.append(
                {
                    "instrument": instrument,
                    "signal_date": signal_date,
                    "candidate_scheme_id": "multi_equal_weight_v1",
                    "model_score_D0": baseline_scores[instrument],
                }
            )

    files = {
        "no_p98_scores": tmp_path / "no_p98_scores.parquet",
        "p98_scores": tmp_path / "p98_scores.parquet",
        "confirmed5_scores": tmp_path / "confirmed5_scores.parquet",
        "v2_scores": tmp_path / "v2_scores.parquet",
        "baseline_scores": tmp_path / "baseline_scores.parquet",
        "label_panel": tmp_path / "label_panel.parquet",
        "split_panel": tmp_path / "split_panel.parquet",
        "no_p98_audit": tmp_path / "no_p98_audit.json",
        "output_json": tmp_path / "diagnosis.json",
        "output_md": tmp_path / "diagnosis.md",
    }

    write_parquet(files["no_p98_scores"], pd.DataFrame(no_p98_rows))
    write_parquet(files["p98_scores"], pd.DataFrame(p98_rows))
    write_parquet(files["confirmed5_scores"], pd.DataFrame(confirmed5_rows))
    write_parquet(files["v2_scores"], pd.DataFrame(v2_rows))
    write_parquet(files["baseline_scores"], pd.DataFrame(baseline_rows))
    write_parquet(files["label_panel"], pd.DataFrame(label_rows))
    write_parquet(files["split_panel"], pd.DataFrame(split_rows))
    files["no_p98_audit"].write_text(
        json.dumps(
            {
                "candidate_scheme_id": "no_p98_reversal_baseline_v1",
                "baseline_id": "no_p98_reversal_baseline_v1",
                "score_direction": "ASC / reversal_rank",
                "p98_used": False,
                "label_diagnostics_used": False,
                "frozen_test_accessed": False,
                "d0_visibility_audit": {"pass": True},
                "leakage_audit": {"pass": True},
            },
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
            "--p98-scores",
            str(files["p98_scores"]),
            "--confirmed5-scores",
            str(files["confirmed5_scores"]),
            "--v2-scores",
            str(files["v2_scores"]),
            "--baseline-scores",
            str(files["baseline_scores"]),
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


def test_no_p98_model_edge_diagnosis_outputs_expected_shape(repo_root: Path, tmp_path: Path) -> None:
    files = build_fixture_files(tmp_path)
    result = run_script(repo_root, files)
    assert result.returncode == 0, result.stderr

    payload = json.loads(files["output_json"].read_text(encoding="utf-8"))
    assert payload["diagnostic_only"] is True
    assert payload["frozen_test_accessed"] is False
    assert payload["formal_metrics_generated"] is False
    assert payload["portfolio_run_executed"] is False
    assert payload["no_p98_score_layer_metadata"]["score_direction"] == "ASC / reversal_rank"
    assert "no_p98_train" in payload["diagnostics"]
    assert "p98_validation" in payload["diagnostics"]
    assert "baseline_validation" in payload["diagnostics"]
    assert "confirmed5_train" in payload["diagnostics"]
    assert "v2_validation" in payload["diagnostics"]


def test_no_p98_model_edge_diagnosis_captures_p98_edge_loss_and_blocks_dry_run(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    files = build_fixture_files(tmp_path)
    result = run_script(repo_root, files)
    assert result.returncode == 0, result.stderr

    payload = json.loads(files["output_json"].read_text(encoding="utf-8"))
    validation_delta = payload["cross_model_comparison"]["validation"]["no_p98_vs_p98"]["rank_ic_delta"]
    assert validation_delta is not None
    assert validation_delta < 0
    assert payload["conclusion"]["recommend_same_contract_portfolio_dry_run_preparation"] is False
    assert payload["conclusion"]["recommendation"] == "do_not_prepare_same_contract_portfolio_dry_run_yet"


def test_script_text_excludes_portfolio_and_frozen_test_actions() -> None:
    script_text = read_text(SCRIPT_PATH).lower()
    assert "holdings.csv" not in script_text
    assert "portfolio_weights" not in script_text
    assert "fixed_test" not in script_text
