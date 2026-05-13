from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


SCRIPT_PATH = "scripts/diagnose_clean_liquidity_quality_failure.py"


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
    instruments = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"]
    returns = {"AAA": 0.01, "BBB": 0.00, "CCC": 0.08, "DDD": 0.07, "EEE": -0.05, "FFF": -0.06}
    liquidity_eff = {"AAA": 6.0, "BBB": 5.0, "CCC": 4.0, "DDD": 3.0, "EEE": 2.0, "FFF": 1.0}
    no_p98_eff = {"EEE": 6.0, "FFF": 5.0, "AAA": 4.0, "BBB": 3.0, "CCC": 2.0, "DDD": 1.0}
    p98_eff = {"CCC": 6.0, "DDD": 5.0, "AAA": 4.0, "BBB": 3.0, "EEE": 2.0, "FFF": 1.0}
    composite_eff = {"AAA": 6.0, "EEE": 5.0, "CCC": 4.0, "DDD": 3.0, "BBB": 2.0, "FFF": 1.0}
    multi_eff = p98_eff
    amount = {"AAA": 1000.0, "BBB": 900.0, "CCC": 500.0, "DDD": 450.0, "EEE": 100.0, "FFF": 80.0}

    label_rows = []
    split_rows = []
    exposure_rows = []
    score_rows = {key: [] for key in ["liquidity", "no_p98", "p98", "composite", "multi"]}
    for date, split in days:
        for instrument in instruments:
            base = {"snapshot_id": "snap", "instrument": instrument, "signal_date": date}
            label_rows.append(base | {"label_defined": True, "label_5d_next_open_close": returns[instrument]})
            split_rows.append(base | {"train_flag": split == "train", "validation_flag": split == "validation", "test_flag": False})
            exposure_rows.append(
                base
                | {
                    "amount": amount[instrument],
                    "entry_buyable": True,
                    "is_suspended": False,
                    "no_trade_flag": False,
                    "volume_zero_flag": False,
                    "amount_zero_flag": False,
                    "is_limit_up": False,
                    "is_limit_down": False,
                    "open_at_up_limit": False,
                    "close_at_down_limit": False,
                    "listing_age_days": 500,
                    "board_type": "main" if instrument in {"AAA", "BBB", "EEE"} else "gem",
                    "exchange": "SZ" if instrument in {"AAA", "CCC", "EEE"} else "SH",
                    "limit_pct_rule": "10pct",
                }
            )
            score_rows["liquidity"].append(
                base | {"candidate_scheme_id": "clean_reversal_5d_liquidity_quality_v1", "model_score_D0": -liquidity_eff[instrument]}
            )
            score_rows["no_p98"].append(
                base | {"candidate_scheme_id": "no_p98_reversal_baseline_v1", "model_score_D0": -no_p98_eff[instrument]}
            )
            score_rows["p98"].append(
                base | {"candidate_scheme_id": "reversal_tail_exclude_p98_v1", "model_score_D0": p98_eff[instrument]}
            )
            score_rows["composite"].append(
                base | {"candidate_scheme_id": "clean_composite_reversal_tradability_v1", "model_score_D0": -composite_eff[instrument]}
            )
            score_rows["multi"].append(
                base | {"candidate_scheme_id": "multi_equal_weight_v1", "model_score_D0": multi_eff[instrument]}
            )

    paths = {
        "label": tmp_path / "label.parquet",
        "split": tmp_path / "split.parquet",
        "exposure": tmp_path / "exposure.parquet",
        "liquidity": tmp_path / "liquidity.parquet",
        "no_p98": tmp_path / "no_p98.parquet",
        "p98": tmp_path / "p98.parquet",
        "composite": tmp_path / "composite.parquet",
        "multi": tmp_path / "multi.parquet",
        "json": tmp_path / "out.json",
        "md": tmp_path / "out.md",
    }
    write_parquet(paths["label"], label_rows)
    write_parquet(paths["split"], split_rows)
    write_parquet(paths["exposure"], exposure_rows)
    for key in score_rows:
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
            "--liquidity-scores",
            str(paths["liquidity"]),
            "--no-p98-scores",
            str(paths["no_p98"]),
            "--p98-scores",
            str(paths["p98"]),
            "--composite-scores",
            str(paths["composite"]),
            "--multi-equal-scores",
            str(paths["multi"]),
            "--topk",
            "2",
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


def test_fixture_captures_rankic_improvement_but_topk_failure(repo_root: Path, tmp_path: Path) -> None:
    paths = build_fixture(tmp_path)
    result = run_script(repo_root, paths)
    assert result.returncode == 0, result.stderr

    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    validation = payload["comparisons"]["liquidity_quality_vs_no_p98_reversal_baseline_v1"]["validation"]
    assert validation["rankic_delta"] > 0
    assert validation["topk_proxy_delta"] > 0
    assert payload["diagnostics"]["clean_reversal_5d_liquidity_quality_v1"]["validation"]["topk_proxy"]["topk_minus_nextk"] < 0
    assert payload["decision_summary"]["recommend_portfolio_dry_run"] is False


def test_fixture_reports_nextk_stronger_than_topk(repo_root: Path, tmp_path: Path) -> None:
    paths = build_fixture(tmp_path)
    result = run_script(repo_root, paths)
    assert result.returncode == 0, result.stderr

    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    decomp = payload["diagnostics"]["clean_reversal_5d_liquidity_quality_v1"]["validation"]["topk_nextk_decomposition"]
    assert decomp["topk_return"]["mean"] < decomp["nextk_return"]["mean"]
    assert decomp["topk_vs_nextk_daily_win_rate"] == 0
    assert decomp["rank31_100_daily_return"]["mean"] > decomp["topk_return"]["mean"]


def test_p98_is_conditional_and_blocked_fields_are_not_used(repo_root: Path, tmp_path: Path) -> None:
    paths = build_fixture(tmp_path)
    result = run_script(repo_root, paths)
    assert result.returncode == 0, result.stderr

    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    p98 = payload["comparisons"]["liquidity_quality_vs_p98_conditional_reference"]
    assert p98["reference_status"] == "conditional_reference_only"
    assert p98["p98_note"] == "p98 is conditional reference only"
    assert payload["blocked_fields_used"] == []
    assert "listing_age_trading_days" not in payload["used_exposure_fields"]
    assert "newly_listed_flag" not in payload["used_exposure_fields"]
