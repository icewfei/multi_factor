from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


SCRIPT_PATH = "scripts/diagnose_clean_topk_selection_failure.py"


def write_parquet(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows), path)


def build_fixture(tmp_path: Path) -> dict[str, Path]:
    days = [
        ("20230101", "train"),
        ("20240101", "validation"),
        ("20250101", "validation"),
    ]
    instruments = ["AAA", "BBB", "CCC", "DDD", "EEE"]
    returns = {"AAA": -0.04, "BBB": 0.03, "CCC": 0.08, "DDD": 0.07, "EEE": -0.01}
    amount = {"AAA": 1000.0, "BBB": 700.0, "CCC": 400.0, "DDD": 350.0, "EEE": 200.0}
    reversal = {"AAA": -0.20, "BBB": -0.14, "CCC": -0.08, "DDD": -0.06, "EEE": -0.02}
    rank_maps = {
        "no_p98": {"AAA": 5.0, "BBB": 4.0, "CCC": 3.0, "DDD": 2.0, "EEE": 1.0},
        "liq": {"AAA": 5.0, "BBB": 4.0, "CCC": 3.0, "DDD": 2.0, "EEE": 1.0},
        "comp": {"AAA": 5.0, "BBB": 4.0, "CCC": 3.0, "DDD": 2.0, "EEE": 1.0},
        "limit": {"AAA": 5.0, "BBB": 4.0, "CCC": 3.0, "DDD": 2.0, "EEE": 1.0},
        "board": {"AAA": 5.0, "BBB": 4.0, "CCC": 3.0, "DDD": 2.0, "EEE": 1.0},
        "trad": {"AAA": 5.0, "BBB": 4.0, "CCC": 3.0, "DDD": 2.0, "EEE": 1.0},
        "p98": {"CCC": 5.0, "DDD": 4.0, "BBB": 3.0, "EEE": 2.0, "AAA": 1.0},
        "multi": {"CCC": 5.0, "DDD": 4.0, "BBB": 3.0, "EEE": 2.0, "AAA": 1.0},
    }
    candidate_ids = {
        "no_p98": "no_p98_reversal_baseline_v1",
        "liq": "clean_reversal_5d_liquidity_quality_v1",
        "comp": "clean_composite_reversal_tradability_v1",
        "limit": "clean_reversal_5d_limit_aware_v1",
        "board": "clean_reversal_5d_board_neutral_v1",
        "trad": "clean_reversal_5d_tradability_filtered_v1",
        "p98": "reversal_tail_exclude_p98_v1",
        "multi": "multi_equal_weight_v1",
    }

    label_rows = []
    split_rows = []
    exposure_rows = []
    score_rows = {key: [] for key in candidate_ids}
    for date, split in days:
        for instrument in instruments:
            base = {"snapshot_id": "snap", "instrument": instrument, "signal_date": date}
            label_rows.append(base | {"label_defined": True, "label_5d_next_open_close": returns[instrument]})
            split_rows.append(base | {"train_flag": split == "train", "validation_flag": split == "validation", "test_flag": False})
            exposure_rows.append(
                base
                | {
                    "reversal_5d_raw": reversal[instrument],
                    "amount": amount[instrument],
                    "entry_buyable": True,
                    "is_suspended": False,
                    "no_trade_flag": False,
                    "volume_zero_flag": False,
                    "amount_zero_flag": False,
                    "is_limit_up": False,
                    "is_limit_down": instrument == "AAA",
                    "open_at_up_limit": False,
                    "close_at_down_limit": instrument == "AAA",
                    "listing_age_days": 500,
                    "board_type": "main" if instrument in {"AAA", "BBB", "EEE"} else "gem",
                    "exchange": "SZ" if instrument in {"AAA", "CCC", "EEE"} else "SH",
                }
            )
            for key, ranks in rank_maps.items():
                value = ranks[instrument]
                score_rows[key].append(
                    base
                    | {
                        "candidate_scheme_id": candidate_ids[key],
                        "model_score_D0": (-value if key not in {"p98", "multi"} else value),
                    }
                )

    paths = {
        "label": tmp_path / "label.parquet",
        "split": tmp_path / "split.parquet",
        "exposure": tmp_path / "exposure.parquet",
        "no_p98": tmp_path / "no_p98.parquet",
        "liq": tmp_path / "liq.parquet",
        "comp": tmp_path / "comp.parquet",
        "limit": tmp_path / "limit.parquet",
        "board": tmp_path / "board.parquet",
        "trad": tmp_path / "trad.parquet",
        "p98": tmp_path / "p98.parquet",
        "multi": tmp_path / "multi.parquet",
        "json": tmp_path / "out.json",
        "md": tmp_path / "out.md",
    }
    write_parquet(paths["label"], label_rows)
    write_parquet(paths["split"], split_rows)
    write_parquet(paths["exposure"], exposure_rows)
    for key in candidate_ids:
        write_parquet(paths[key], score_rows[key])
    return paths


def run_script(repo_root: Path, paths: dict[str, Path]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(repo_root / SCRIPT_PATH),
            "--label-panel",
            str(paths["label"]),
            "--split-panel",
            str(paths["split"]),
            "--exposure-panel",
            str(paths["exposure"]),
            "--no-p98-scores",
            str(paths["no_p98"]),
            "--liquidity-scores",
            str(paths["liq"]),
            "--composite-scores",
            str(paths["comp"]),
            "--limit-aware-scores",
            str(paths["limit"]),
            "--board-neutral-scores",
            str(paths["board"]),
            "--tradability-filtered-scores",
            str(paths["trad"]),
            "--p98-scores",
            str(paths["p98"]),
            "--multi-equal-scores",
            str(paths["multi"]),
            "--topk",
            "1",
            "--output-json",
            str(paths["json"]),
            "--output-md",
            str(paths["md"]),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_fixture_captures_topk_lt_nextk_and_rank31_100(repo_root: Path, tmp_path: Path) -> None:
    paths = build_fixture(tmp_path)
    result = run_script(repo_root, paths)
    assert result.returncode == 0, result.stderr
    payload = json.loads(paths["json"].read_text(encoding="utf-8"))

    validation = payload["cross_model_common_failure"]["validation"]
    assert validation["n_clean_models_topk_lt_nextk"] == 6
    assert validation["n_clean_models_topk_lt_rank31_100"] == 6


def test_fixture_reports_common_failure_across_models(repo_root: Path, tmp_path: Path) -> None:
    paths = build_fixture(tmp_path)
    result = run_script(repo_root, paths)
    assert result.returncode == 0, result.stderr
    payload = json.loads(paths["json"].read_text(encoding="utf-8"))

    for model in [
        "no_p98_reversal_baseline_v1",
        "clean_reversal_5d_liquidity_quality_v1",
        "clean_composite_reversal_tradability_v1",
        "clean_reversal_5d_limit_aware_v1",
        "clean_reversal_5d_board_neutral_v1",
        "clean_reversal_5d_tradability_filtered_v1",
    ]:
        item = payload["cross_model_common_failure"]["per_model_direction_consistency"][model]
        assert item["train_validation_topk_lt_nextk_same_direction"] is True
        assert item["validation_yearly_topk_lt_rank31_100_same_direction"] is True


def test_fixture_marks_unstable_or_insufficient_head_exclusion_as_not_promoted(repo_root: Path, tmp_path: Path) -> None:
    paths = build_fixture(tmp_path)
    result = run_script(repo_root, paths)
    assert result.returncode == 0, result.stderr
    payload = json.loads(paths["json"].read_text(encoding="utf-8"))

    assert payload["head_exclusion_evidence"]["status"] == "insufficient"
    assert payload["decision_summary"]["recommend_next_preregistered_head_exclusion_candidate_design"] is False
    assert payload["decision_summary"]["recommend_portfolio_dry_run"] is False


def test_p98_is_conditional_and_blocked_fields_are_not_used(repo_root: Path, tmp_path: Path) -> None:
    paths = build_fixture(tmp_path)
    result = run_script(repo_root, paths)
    assert result.returncode == 0, result.stderr
    payload = json.loads(paths["json"].read_text(encoding="utf-8"))

    overlap = payload["overlap_divergence"]["validation"]["overlap_with_p98_conditional_reference"]
    assert overlap["reference_status"] == "conditional_reference_only"
    assert payload["blocked_fields_used"] == []
    assert "listing_age_trading_days" not in payload["used_exposure_fields"]
    assert "newly_listed_flag" not in payload["used_exposure_fields"]
