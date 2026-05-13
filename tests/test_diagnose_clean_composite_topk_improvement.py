from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


SCRIPT_PATH = "scripts/diagnose_clean_composite_topk_improvement.py"


def write_parquet(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows), path)


def build_fixture(tmp_path: Path) -> dict[str, Path]:
    days = [
        ("20230101", "train"),
        ("20230102", "train"),
        ("20240101", "validation"),
        ("20250101", "validation"),
    ]
    returns = {"AAA": 0.08, "BBB": 0.06, "CCC": 0.03, "DDD": -0.10}
    composite_eff = {"AAA": 4.0, "DDD": 3.0, "CCC": 2.0, "BBB": 1.0}
    no_p98_eff = {"BBB": 4.0, "AAA": 3.0, "CCC": 2.0, "DDD": 1.0}
    liquidity_eff = {"BBB": 4.0, "CCC": 3.0, "AAA": 2.0, "DDD": 1.0}
    p98_eff = {"AAA": 4.0, "BBB": 3.0, "CCC": 2.0, "DDD": 1.0}
    instruments = ["AAA", "BBB", "CCC", "DDD"]

    label_rows = []
    split_rows = []
    exposure_rows = []
    score_rows = {
        "composite": [],
        "no_p98": [],
        "liquidity": [],
        "p98": [],
    }
    for date, split in days:
        for idx, instrument in enumerate(instruments):
            base = {"snapshot_id": "snap", "instrument": instrument, "signal_date": date}
            label_rows.append(base | {"label_defined": True, "label_5d_next_open_close": returns[instrument]})
            split_rows.append(
                base
                | {
                    "train_flag": split == "train",
                    "validation_flag": split == "validation",
                    "test_flag": False,
                }
            )
            exposure_rows.append(
                base
                | {
                    "amount": float(1000 - idx * 100),
                    "entry_buyable": instrument != "DDD",
                    "is_suspended": False,
                    "no_trade_flag": False,
                    "volume_zero_flag": False,
                    "amount_zero_flag": False,
                    "is_limit_up": False,
                    "is_limit_down": instrument == "DDD",
                    "open_at_up_limit": False,
                    "close_at_down_limit": instrument == "DDD",
                    "listing_age_days": 400 + idx * 100,
                    "board_type": "main" if instrument in {"AAA", "BBB"} else "gem",
                    "exchange": "SZ" if instrument in {"AAA", "CCC"} else "SH",
                }
            )
            score_rows["composite"].append(
                base
                | {
                    "candidate_scheme_id": "clean_composite_reversal_tradability_v1",
                    "model_score_D0": -composite_eff[instrument],
                }
            )
            score_rows["no_p98"].append(
                base
                | {
                    "candidate_scheme_id": "no_p98_reversal_baseline_v1",
                    "model_score_D0": -no_p98_eff[instrument],
                }
            )
            score_rows["liquidity"].append(
                base
                | {
                    "candidate_scheme_id": "clean_reversal_5d_liquidity_quality_v1",
                    "model_score_D0": -liquidity_eff[instrument],
                }
            )
            score_rows["p98"].append(
                base
                | {
                    "candidate_scheme_id": "reversal_tail_exclude_p98_v1",
                    "model_score_D0": p98_eff[instrument],
                }
            )

    paths = {
        "label": tmp_path / "label.parquet",
        "split": tmp_path / "split.parquet",
        "exposure": tmp_path / "exposure.parquet",
        "composite": tmp_path / "composite.parquet",
        "no_p98": tmp_path / "no_p98.parquet",
        "liquidity": tmp_path / "liquidity.parquet",
        "p98": tmp_path / "p98.parquet",
        "json": tmp_path / "out.json",
        "md": tmp_path / "out.md",
    }
    write_parquet(paths["label"], label_rows)
    write_parquet(paths["split"], split_rows)
    write_parquet(paths["exposure"], exposure_rows)
    for key in ["composite", "no_p98", "liquidity", "p98"]:
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
            "--composite-scores",
            str(paths["composite"]),
            "--no-p98-scores",
            str(paths["no_p98"]),
            "--liquidity-scores",
            str(paths["liquidity"]),
            "--p98-scores",
            str(paths["p98"]),
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


def test_decomposition_fixture_captures_topk_improvement_but_rankic_damage(repo_root: Path, tmp_path: Path) -> None:
    paths = build_fixture(tmp_path)
    result = run_script(repo_root, paths)
    assert result.returncode == 0, result.stderr

    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    validation = payload["comparisons"]["composite_vs_no_p98_reversal_baseline_v1"]["validation"]
    assert validation["topk_proxy_delta"] > 0
    assert validation["topk_minus_nextk_delta"] > 0
    assert validation["rankic_delta"] < 0
    assert payload["decision_summary"]["recommend_portfolio_dry_run"] is False


def test_decomposition_reports_topk_overlap_and_divergence(repo_root: Path, tmp_path: Path) -> None:
    paths = build_fixture(tmp_path)
    result = run_script(repo_root, paths)
    assert result.returncode == 0, result.stderr

    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    overlap = payload["topk_overlap_divergence"]["validation"]["composite_vs_no_p98_reversal_baseline_v1"]
    assert overlap["overlap_count"]["total"] == 0
    assert overlap["jaccard"]["mean"] == 0
    assert overlap["composite_only_realized_return"]["mean"] > overlap["comparator_only_realized_return"]["mean"]


def test_decomposition_marks_p98_conditional_and_does_not_use_blocked_fields(repo_root: Path, tmp_path: Path) -> None:
    paths = build_fixture(tmp_path)
    result = run_script(repo_root, paths)
    assert result.returncode == 0, result.stderr

    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    p98 = payload["comparisons"]["composite_vs_p98_conditional_reference"]
    assert p98["reference_status"] == "conditional_reference_only"
    assert p98["p98_note"] == "p98 is conditional reference only"
    assert payload["blocked_fields_used"] == []
    assert "listing_age_trading_days" not in payload["used_exposure_fields"]
    assert "newly_listed_flag" not in payload["used_exposure_fields"]
