from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


SCRIPT_PATH = "scripts/diagnose_rank_band_full_profile.py"


def write_parquet(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows), path)


def build_fixture(tmp_path: Path) -> dict[str, Path]:
    instruments = [f"S{i:04d}" for i in range(1, 651)]
    days = [("20230103", "train"), ("20240103", "validation"), ("20250103", "validation")]
    candidate_ids = {
        "no_p98": "no_p98_reversal_baseline_v1",
        "liq": "clean_reversal_5d_liquidity_quality_v1",
        "comp": "clean_composite_reversal_tradability_v1",
        "limit": "clean_reversal_5d_limit_aware_v1",
        "board": "clean_reversal_5d_board_neutral_v1",
        "trad": "clean_reversal_5d_tradability_filtered_v1",
        "listing": "clean_reversal_5d_listing_age_calendar_v1",
        "p98": "reversal_tail_exclude_p98_v1",
        "multi": "multi_equal_weight_v1",
    }
    label_rows = []
    split_rows = []
    exposure_rows = []
    score_rows = {key: [] for key in candidate_ids}
    for date, split in days:
        for idx, instrument in enumerate(instruments, start=1):
            base = {"snapshot_id": "snap", "instrument": instrument, "signal_date": date}
            if idx <= 30:
                ret = -0.03
            elif idx <= 200:
                ret = 0.04
            elif idx <= 600:
                ret = 0.01
            else:
                ret = -0.05
            ret += (idx % 7) * 0.001
            label_rows.append(base | {"label_defined": True, "label_5d_next_open_close": ret})
            split_rows.append(base | {"train_flag": split == "train", "validation_flag": split == "validation", "test_flag": False})
            exposure_rows.append(
                base
                | {
                    "amount": float(1000000 - idx),
                    "entry_buyable": idx % 17 != 0,
                    "is_suspended": idx % 101 == 0,
                    "no_trade_flag": idx % 103 == 0,
                    "volume_zero_flag": idx % 107 == 0,
                    "amount_zero_flag": idx % 109 == 0,
                    "is_limit_up": idx % 113 == 0,
                    "is_limit_down": idx % 31 == 0,
                    "open_at_up_limit": idx % 127 == 0,
                    "close_at_down_limit": idx % 29 == 0,
                    "listing_age_days": idx * 3,
                    "board_type": "main" if idx % 3 else "chinext",
                    "exchange": "SH" if idx % 2 else "SZ",
                }
            )
            for key, cid in candidate_ids.items():
                score = float(idx)
                if key in {"p98", "multi"}:
                    score = float(10000 - idx)
                score_rows[key].append(base | {"candidate_scheme_id": cid, "model_score_D0": score})
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
        "listing": tmp_path / "listing.parquet",
        "p98": tmp_path / "p98.parquet",
        "multi": tmp_path / "multi.parquet",
        "json": tmp_path / "rank_band.json",
        "md": tmp_path / "rank_band.md",
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
            "--label-panel", str(paths["label"]),
            "--split-panel", str(paths["split"]),
            "--exposure-panel", str(paths["exposure"]),
            "--no-p98-scores", str(paths["no_p98"]),
            "--liquidity-scores", str(paths["liq"]),
            "--composite-scores", str(paths["comp"]),
            "--limit-aware-scores", str(paths["limit"]),
            "--board-neutral-scores", str(paths["board"]),
            "--tradability-filtered-scores", str(paths["trad"]),
            "--listing-age-scores", str(paths["listing"]),
            "--p98-scores", str(paths["p98"]),
            "--multi-equal-scores", str(paths["multi"]),
            "--output-json", str(paths["json"]),
            "--output-md", str(paths["md"]),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def load_payload(repo_root: Path, tmp_path: Path) -> dict:
    paths = build_fixture(tmp_path)
    result = run_script(repo_root, paths)
    assert result.returncode == 0, result.stderr
    return json.loads(paths["json"].read_text(encoding="utf-8"))


def test_fixture_covers_fixed_rank_bands(repo_root: Path, tmp_path: Path) -> None:
    payload = load_payload(repo_root, tmp_path)

    expected = {
        "rank_1_30": "1-30",
        "rank_31_60": "31-60",
        "rank_31_100": "31-100",
        "rank_31_200": "31-200",
        "rank_101_300": "101-300",
        "rank_301_600": "301-600",
        "bottom_30": "bottom 30",
    }
    assert {key: value["label"] for key, value in payload["fixed_rank_bands"].items()} == expected
    profiles = payload["diagnostics"]["no_p98_reversal_baseline_v1"]["validation"]["band_profiles"]
    assert set(expected).issubset(profiles)
    for band_name in expected:
        band = profiles[band_name]
        for metric in [
            "mean",
            "median",
            "volatility",
            "daily_win_rate_vs_0",
            "yearly_mean",
            "best_5pct_contribution",
            "worst_5pct_damage",
        ]:
            assert metric in band


def test_fixture_reports_exposure_profiles(repo_root: Path, tmp_path: Path) -> None:
    payload = load_payload(repo_root, tmp_path)
    exposure = payload["diagnostics"]["clean_reversal_5d_liquidity_quality_v1"]["validation"]["band_profiles"]["rank_31_100"]["exposure"]

    assert exposure["amount_bucket"]["status"] == "available"
    assert exposure["board_type"]["status"] == "available"
    assert exposure["exchange"]["status"] == "available"
    assert exposure["listing_age_days_bucket"]["status"] == "available"
    assert exposure["limit_tradability"]["entry_buyable"]["status"] == "available"
    assert exposure["limit_tradability"]["is_limit_down"]["status"] == "available"


def test_fixture_p98_and_multi_are_conditional_references(repo_root: Path, tmp_path: Path) -> None:
    payload = load_payload(repo_root, tmp_path)

    assert payload["diagnostics"]["p98_conditional_reference"]["status"] == "conditional_reference_only"
    assert payload["diagnostics"]["multi_equal_weight_v1_conditional_reference"]["status"] == "conditional_reference_only"
    assert payload["governance"]["p98_conditional_reference_only"] is True
    assert payload["governance"]["multi_equal_weight_v1_conditional_reference_only"] is True


def test_fixture_preserves_descriptive_boundaries(repo_root: Path, tmp_path: Path) -> None:
    payload = load_payload(repo_root, tmp_path)

    assert payload["diagnosis_label"] == "DESCRIPTIVE_ONLY_TRAINVAL_NOT_OOS_NOT_PORTFOLIO"
    assert payload["governance"]["portfolio_run_executed"] is False
    assert payload["governance"]["frozen_test_accessed"] is False
    assert payload["governance"]["trainval_not_oos"] is True
    assert payload["governance"]["alpha_claim"] is False
    assert payload["governance"]["candidate_created"] is False
    assert payload["governance"]["training_run_executed"] is False
    assert payload["governance"]["backtest_run_executed"] is False
