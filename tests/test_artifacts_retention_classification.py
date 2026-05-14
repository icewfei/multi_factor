from __future__ import annotations

from pathlib import Path


ARTIFACTS_README_PATH = Path("artifacts/README.md")


def test_artifacts_readme_classifies_retention_and_archive_policy(repo_root: Path) -> None:
    text = (repo_root / ARTIFACTS_README_PATH).read_text(encoding="utf-8")

    assert "current_data_regime_research_stopped" in text
    assert "必须保留在项目内" in text
    assert "优先归档到项目外" in text
    assert "可重建或可删除" in text


def test_artifacts_readme_preserves_evidence_boundary(repo_root: Path) -> None:
    text = (repo_root / ARTIFACTS_README_PATH).read_text(encoding="utf-8")

    assert "trainval-only" in text
    assert "不得被表述为独立 OOS 证据" in text
    assert "不应从本目录继续挑选 candidate" in text
    assert "读取 frozen test" in text


def test_artifacts_readme_keeps_core_artifacts_in_project(repo_root: Path) -> None:
    text = (repo_root / ARTIFACTS_README_PATH).read_text(encoding="utf-8")

    for required_path in [
        "artifacts/research_registry/",
        "artifacts/fixed_test/",
        "artifacts/run_state/project_panels_research_trainval_20211231_20260429/",
    ]:
        assert required_path in text


def test_artifacts_readme_names_large_run_state_archive_patterns(repo_root: Path) -> None:
    text = (repo_root / ARTIFACTS_README_PATH).read_text(encoding="utf-8")

    for archive_pattern in [
        "artifacts/run_state/signaldiag_*",
        "artifacts/run_state/screendiag_*",
        "artifacts/run_state/fullchain_*",
        "artifacts/run_state/baseline_chain_20260417_105228",
    ]:
        assert archive_pattern in text
