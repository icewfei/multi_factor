from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


SCRIPT_PATH = "scripts/diagnose_cross_model_agreement_structure.py"


def write_parquet(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows), path)


def build_fixture(tmp_path: Path) -> dict[str, Path]:
    days = [
        ("20230103", "train"),
        ("20240103", "validation"),
        ("20250103", "validation"),
    ]
    instruments = [f"S{i:03d}" for i in range(1, 121)]
    common_topk = {f"S{i:03d}" for i in range(1, 31)}
    common_nextk = {f"S{i:03d}" for i in range(31, 61)}
    common_mid = {f"S{i:03d}" for i in range(61, 101)}
    bottom = {f"S{i:03d}" for i in range(101, 121)}

    clean_models = [
        "no_p98",
        "liq",
        "board",
        "limit",
        "trad",
        "listing",
    ]
    candidate_ids = {
        "no_p98": "no_p98_reversal_baseline_v1",
        "liq": "clean_reversal_5d_liquidity_quality_v1",
        "board": "clean_reversal_5d_board_neutral_v1",
        "limit": "clean_reversal_5d_limit_aware_v1",
        "trad": "clean_reversal_5d_tradability_filtered_v1",
        "listing": "clean_reversal_5d_listing_age_calendar_v1",
        "comp": "clean_composite_reversal_tradability_v1",
        "p98": "reversal_tail_exclude_p98_v1",
        "multi": "multi_equal_weight_v1",
    }
    model_order = {
        "no_p98": sorted(common_topk) + sorted(common_nextk) + sorted(common_mid) + sorted(bottom),
        "liq": sorted(common_topk) + sorted(common_mid) + sorted(common_nextk) + sorted(bottom),
        "board": sorted(common_topk) + sorted(common_nextk) + sorted(common_mid) + sorted(bottom),
        "limit": sorted(common_topk) + sorted(common_mid) + sorted(common_nextk) + sorted(bottom),
        "trad": sorted(common_topk) + sorted(common_mid) + sorted(common_nextk) + sorted(bottom),
        "listing": sorted(common_topk) + sorted(common_nextk) + sorted(common_mid) + sorted(bottom),
    }

    # Force disagreement: a subset of common_mid gets one TopK vote in some models.
    disagreement_names = [f"S{i:03d}" for i in range(61, 71)]
    for model in ["liq", "limit", "trad"]:
        ordered = [name for name in model_order[model] if name not in disagreement_names]
        model_order[model] = disagreement_names + ordered

    model_specific_names = {
        "no_p98": "S101",
        "liq": "S102",
        "board": "S103",
        "limit": "S104",
        "trad": "S105",
        "listing": "S106",
    }
    for model, instrument in model_specific_names.items():
        ordered = [name for name in model_order[model] if name != instrument]
        model_order[model] = [instrument] + ordered

    p98_order = sorted(common_mid) + sorted(common_topk) + sorted(common_nextk) + sorted(bottom)
    multi_order = sorted(common_nextk) + sorted(common_mid) + sorted(common_topk) + sorted(bottom)
    comp_order = sorted(common_topk) + sorted(common_nextk) + sorted(common_mid) + sorted(bottom)

    label_rows = []
    split_rows = []
    exposure_rows = []
    score_rows = {key: [] for key in candidate_ids}
    for signal_date, split in days:
        for idx, instrument in enumerate(instruments, start=1):
            if instrument in common_topk:
                ret = -0.06
            elif instrument in common_nextk:
                ret = 0.05
            elif instrument in common_mid:
                ret = 0.08
            else:
                ret = -0.02

            base = {"snapshot_id": "snap", "instrument": instrument, "signal_date": signal_date}
            label_rows.append(base | {"label_defined": True, "label_5d_next_open_close": ret})
            split_rows.append(base | {"train_flag": split == "train", "validation_flag": split == "validation", "test_flag": False})
            exposure_rows.append(
                base
                | {
                    "amount": float(2000 - idx * 5) if instrument not in common_topk else float(300 - idx),
                    "entry_buyable": instrument not in common_topk,
                    "is_suspended": instrument in {"S001", "S002", "S003"},
                    "no_trade_flag": instrument in {"S001", "S004"},
                    "volume_zero_flag": instrument == "S005",
                    "amount_zero_flag": instrument == "S006",
                    "is_limit_up": False,
                    "is_limit_down": instrument in common_topk,
                    "open_at_up_limit": False,
                    "close_at_down_limit": instrument in common_topk,
                    "listing_age_days": 120 if instrument in common_topk else (220 if instrument in common_nextk else 520),
                    "board_type": "main" if idx % 2 else "gem",
                    "exchange": "SZ" if idx % 3 else "SH",
                }
            )

        for model in clean_models:
            ordered = model_order[model]
            for rank, instrument in enumerate(ordered, start=1):
                score_rows[model].append(
                    {
                        "snapshot_id": "snap",
                        "instrument": instrument,
                        "signal_date": signal_date,
                        "candidate_scheme_id": candidate_ids[model],
                        "model_score_D0": float(-1000 + rank),
                    }
                )
        for rank, instrument in enumerate(comp_order, start=1):
            score_rows["comp"].append(
                {
                    "snapshot_id": "snap",
                    "instrument": instrument,
                    "signal_date": signal_date,
                    "candidate_scheme_id": candidate_ids["comp"],
                    "model_score_D0": float(-1000 + rank),
                }
            )
        for rank, instrument in enumerate(p98_order, start=1):
            score_rows["p98"].append(
                {
                    "snapshot_id": "snap",
                    "instrument": instrument,
                    "signal_date": signal_date,
                    "candidate_scheme_id": candidate_ids["p98"],
                    "model_score_D0": float(1000 - rank),
                }
            )
        for rank, instrument in enumerate(multi_order, start=1):
            score_rows["multi"].append(
                {
                    "snapshot_id": "snapx",
                    "instrument": instrument,
                    "signal_date": signal_date,
                    "candidate_scheme_id": candidate_ids["multi"],
                    "model_score_D0": float(1000 - rank),
                }
            )

    paths = {
        "label": tmp_path / "label.parquet",
        "split": tmp_path / "split.parquet",
        "exposure": tmp_path / "exposure.parquet",
        "no_p98": tmp_path / "no_p98.parquet",
        "liq": tmp_path / "liq.parquet",
        "board": tmp_path / "board.parquet",
        "limit": tmp_path / "limit.parquet",
        "trad": tmp_path / "trad.parquet",
        "listing": tmp_path / "listing.parquet",
        "comp": tmp_path / "comp.parquet",
        "p98": tmp_path / "p98.parquet",
        "multi": tmp_path / "multi.parquet",
        "json": tmp_path / "out.json",
        "md": tmp_path / "out.md",
    }
    write_parquet(paths["label"], label_rows)
    write_parquet(paths["split"], split_rows)
    write_parquet(paths["exposure"], exposure_rows)
    for key in ["no_p98", "liq", "board", "limit", "trad", "listing", "comp", "p98", "multi"]:
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
            "--board-neutral-scores",
            str(paths["board"]),
            "--limit-aware-scores",
            str(paths["limit"]),
            "--tradability-filtered-scores",
            str(paths["trad"]),
            "--listing-age-scores",
            str(paths["listing"]),
            "--composite-scores",
            str(paths["comp"]),
            "--p98-scores",
            str(paths["p98"]),
            "--multi-equal-scores",
            str(paths["multi"]),
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


def load_payload(repo_root: Path, tmp_path: Path) -> dict:
    paths = build_fixture(tmp_path)
    result = run_script(repo_root, paths)
    assert result.returncode == 0, result.stderr
    return json.loads(paths["json"].read_text(encoding="utf-8"))


def test_fixture_covers_agreement_count_aggregation(repo_root: Path, tmp_path: Path) -> None:
    payload = load_payload(repo_root, tmp_path)
    validation = payload["diagnostics"]["validation"]["agreement_count_buckets_topk"]

    assert validation["6"]["returns"]["count"] > 0
    assert validation["1"]["returns"]["count"] > 0
    assert validation["6"]["returns"]["mean_return"] < validation["1"]["returns"]["mean_return"]


def test_fixture_covers_common_topk_vs_model_specific_topk(repo_root: Path, tmp_path: Path) -> None:
    payload = load_payload(repo_root, tmp_path)
    validation = payload["diagnostics"]["validation"]["common_topk_vs_model_specific_topk"]

    assert validation["common_topk"]["returns"]["mean_return"] < validation["model_specific_topk"]["returns"]["mean_return"]
    assert validation["common_topk"]["returns"]["worst_5pct_damage"] is not None
    assert validation["common_topk"]["exposure"]["limit_tradability"]["is_limit_down"]["true_share"] > 0
    assert validation["model_specific_topk_per_model"]["clean_reversal_5d_limit_aware_v1"]["returns"]["count"] >= 0


def test_fixture_covers_common_nextk_mid_head_and_disagreement(repo_root: Path, tmp_path: Path) -> None:
    payload = load_payload(repo_root, tmp_path)
    validation = payload["diagnostics"]["validation"]["agreement_in_near_head_bands"]

    assert validation["common_mid_head"]["returns"]["mean_return"] > validation["common_topk"]["returns"]["mean_return"]
    assert validation["common_nextk"]["returns"]["mean_return"] > validation["common_topk"]["returns"]["mean_return"]
    assert validation["near_head_disagreement"]["returns"]["count"] > 0


def test_fixture_covers_p98_conditional_reference_and_blocked_fields(repo_root: Path, tmp_path: Path) -> None:
    payload = load_payload(repo_root, tmp_path)
    p98 = payload["diagnostics"]["validation"]["conditional_reference_comparison"]["p98_conditional_reference"]

    assert p98["reference_status"] == "conditional_reference_only"
    assert "conditional reference only" in p98["note"]
    assert payload["blocked_fields_used"] == []
    assert "listing_age_trading_days" not in payload["used_exposure_fields"]
    assert "newly_listed_flag" not in payload["used_exposure_fields"]


def test_fixture_preserves_descriptive_boundaries_and_stability(repo_root: Path, tmp_path: Path) -> None:
    payload = load_payload(repo_root, tmp_path)

    assert payload["diagnosis_label"] == "DESCRIPTIVE_ONLY_TRAINVAL_NOT_OOS_NOT_PORTFOLIO"
    assert payload["governance"]["portfolio_run_executed"] is False
    assert payload["governance"]["frozen_test_accessed"] is False
    assert payload["governance"]["trainval_not_oos"] is True
    assert payload["governance"]["strategy_research_restarted"] is False
    assert payload["stability"]["high_agreement_topk_is_stably_weaker_than_model_specific_topk"]["status"] in {
        "consistent",
        "inconsistent",
        "insufficient_evidence",
    }
