from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from test_diagnose_rank_band_full_profile import build_fixture


SCRIPT_PATH = "scripts/diagnose_market_state_conditional_rank_band_profile.py"


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
    paths["json"] = tmp_path / "market_state.json"
    paths["md"] = tmp_path / "market_state.md"
    result = run_script(repo_root, paths)
    assert result.returncode == 0, result.stderr
    return json.loads(paths["json"].read_text(encoding="utf-8"))


def test_fixture_covers_condition_rank_band_aggregation(repo_root: Path, tmp_path: Path) -> None:
    payload = load_payload(repo_root, tmp_path)
    conditions = payload["diagnostics"]["no_p98_reversal_baseline_v1"]["validation"]["conditions"]

    amount = conditions["amount_bucket_3"]
    assert amount["status"] == "available"
    assert "top_20pct" in amount["values"]
    rank_payload = amount["values"]["top_20pct"]["rank_1_30"]
    for metric in [
        "count",
        "mean_return",
        "median_return",
        "daily_win_rate_vs_0",
        "topk_minus_rank31_100_within_condition",
        "rank31_100_minus_topk_within_condition",
        "worst_5pct_damage",
        "best_5pct_contribution",
        "condition_worsens_head_failure",
        "condition_strengthens_mid_rank",
    ]:
        assert metric in rank_payload

    assert conditions["board_type"]["status"] == "available"
    assert conditions["exchange"]["status"] == "available"
    assert conditions["is_limit_down"]["status"] == "available"
    assert conditions["listing_age_days_bucket"]["status"] == "available"
    assert conditions["daily_amount_aggregate_bucket"]["status"] == "available"
    assert "condition_direction_consistency_summary" in payload


def test_fixture_blocks_forbidden_and_blocked_fields(repo_root: Path, tmp_path: Path) -> None:
    payload = load_payload(repo_root, tmp_path)

    assert payload["blocked_fields_used"] == []
    assert payload["forbidden_conditioning_fields_used"] == []
    assert "listing_age_trading_days" not in payload["condition_dimensions"]
    assert "newly_listed_flag" not in payload["condition_dimensions"]


def test_fixture_marks_unavailable_fields(repo_root: Path, tmp_path: Path) -> None:
    payload = load_payload(repo_root, tmp_path)

    assert payload["field_availability"]["exit_sellable"] == "unavailable"
    assert payload["field_availability"]["sellable_retry_next_open"] == "unavailable"
    assert payload["field_availability"]["daily_universe_median_return"] == "unavailable"
    assert payload["field_availability"]["daily_universe_volatility_proxy"] == "unavailable"
    unavailable = payload["diagnostics"]["no_p98_reversal_baseline_v1"]["validation"]["conditions"]["exit_sellable"]
    assert unavailable["status"] == "unavailable"


def test_fixture_p98_conditional_reference_and_boundaries(repo_root: Path, tmp_path: Path) -> None:
    payload = load_payload(repo_root, tmp_path)

    assert payload["diagnostics"]["p98_conditional_reference"]["status"] == "conditional_reference_only"
    assert payload["diagnostics"]["multi_equal_weight_v1_conditional_reference"]["status"] == "conditional_reference_only"
    assert payload["governance"]["p98_conditional_reference_only"] is True
    assert payload["governance"]["multi_equal_weight_v1_conditional_reference_only"] is True
    assert payload["governance"]["portfolio_run_executed"] is False
    assert payload["governance"]["portfolio_dry_run_executed"] is False
    assert payload["governance"]["frozen_test_accessed"] is False
    assert payload["governance"]["trainval_not_oos"] is True
    assert payload["governance"]["training_run_executed"] is False
    assert payload["governance"]["backtest_run_executed"] is False
    assert payload["governance"]["trading_rule_designed"] is False
