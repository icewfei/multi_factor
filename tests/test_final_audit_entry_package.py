from __future__ import annotations

from pathlib import Path


FINAL_AUDIT_ENTRY_PATH = Path("docs/final_audit_entry_package.md")
README_PATH = Path("README.md")


def test_final_audit_entry_package_exists_and_fixes_current_status(repo_root: Path) -> None:
    text = (repo_root / FINAL_AUDIT_ENTRY_PATH).read_text(encoding="utf-8")

    assert "Final Audit Entry Package" in text
    assert "current_data_regime_research_stopped" in text
    assert "strategy_research: paused" in text
    assert "sandbox_understanding: completed" in text
    assert "repository_role: audit asset and engineering asset" in text


def test_final_audit_entry_package_contains_minimal_reading_path(repo_root: Path) -> None:
    text = (repo_root / FINAL_AUDIT_ENTRY_PATH).read_text(encoding="utf-8")

    for path in [
        "README.md",
        "docs/current_stage.md",
        "docs/final_project_review_after_data_regime_stop.md",
        "docs/audit_boundary.md",
        "artifacts/README.md",
    ]:
        assert path in text


def test_final_audit_entry_package_preserves_forbidden_misreadings(repo_root: Path) -> None:
    text = (repo_root / FINAL_AUDIT_ENTRY_PATH).read_text(encoding="utf-8")

    assert "unconditional gold standard" in text
    assert "portfolio-ready" in text
    assert "trainval-only" in text
    assert "OOS" in text
    assert "fixed_test" in text


def test_final_audit_entry_package_names_restart_conditions(repo_root: Path) -> None:
    text = (repo_root / FINAL_AUDIT_ENTRY_PATH).read_text(encoding="utf-8")

    assert "新的信息源" in text
    assert "新的数据模态" in text
    assert "独立预注册的新研究问题" in text


def test_readme_points_to_final_audit_entry_package_first(repo_root: Path) -> None:
    text = (repo_root / README_PATH).read_text(encoding="utf-8")
    reading_section = text.split("## 如何阅读本仓库", maxsplit=1)[1]
    first_item = next(line for line in reading_section.splitlines() if line.startswith("1. "))

    assert "docs/final_audit_entry_package.md" in first_item
