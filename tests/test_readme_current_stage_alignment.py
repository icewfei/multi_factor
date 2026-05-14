from __future__ import annotations

from pathlib import Path


README_PATH = Path("README.md")
CURRENT_STAGE_PATH = Path("docs/current_stage.md")


def test_readme_contains_current_phase(repo_root: Path) -> None:
    text = (repo_root / README_PATH).read_text(encoding="utf-8")

    assert "current_data_regime_research_stopped" in text
    assert "strategy_research: paused" in text
    assert "repository_role: audit asset and engineering asset" in text


def test_readme_contains_current_baseline_and_enrichment_status(repo_root: Path) -> None:
    text = (repo_root / README_PATH).read_text(encoding="utf-8")

    assert "p98" in text
    assert "conditional reference only" in text
    assert "clean_baseline_family: clean but insufficient TopK head quality; not portfolio-ready" in text
    assert "current D0 OHLCV + state regime: stopped" in text


def test_readme_contains_current_prohibitions(repo_root: Path) -> None:
    text = (repo_root / README_PATH).read_text(encoding="utf-8")

    assert "不读取 frozen test" in text
    assert "不跑 portfolio" in text
    assert "不开启 v4" in text
    assert "训练" in text
    assert "回测" in text
    assert "不把 trainval diagnosis 当 OOS" in text


def test_readme_contains_exploratory_sandbox_allowed_zone(repo_root: Path) -> None:
    text = (repo_root / README_PATH).read_text(encoding="utf-8")

    assert "exploratory_sandbox_policy_after_data_regime_stop.md" in text
    assert "paper-only" in text
    assert "exploratory descriptive" in text
    assert "不得宣称 alpha" in text


def test_current_stage_contains_guarded_workflow_and_no_portfolio(repo_root: Path) -> None:
    text = (repo_root / CURRENT_STAGE_PATH).read_text(encoding="utf-8")

    assert "current_data_regime_research_stopped" in text
    assert "strategy_research: paused" in text
    assert "当前不进入 portfolio" in text
    assert "listing_age_trading_days" in text
    assert "newly_listed_flag" in text


def test_current_stage_contains_exploratory_sandbox_allowed_zone(repo_root: Path) -> None:
    text = (repo_root / CURRENT_STAGE_PATH).read_text(encoding="utf-8")

    assert "只停止策略推进，不停止所有研究理解" in text
    assert "paper-only" in text
    assert "exploratory descriptive" in text
    assert "rank_band_full_profile_descriptive_research_design.md" in text
