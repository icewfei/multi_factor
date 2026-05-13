from __future__ import annotations

from pathlib import Path


REQUIREMENTS_PATH = Path("requirements-dev.txt")
TEST_RUNNING_DOC_PATH = Path("docs/test_running.md")
TESTS_README_PATH = Path("tests/README.md")


def test_requirements_dev_contains_audit_test_dependencies(repo_root: Path) -> None:
    text = (repo_root / REQUIREMENTS_PATH).read_text(encoding="utf-8")
    requirements = {line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#")}

    for package in [
        "duckdb",
        "jsonschema",
        "numpy",
        "pandas",
        "pyarrow",
        "pytest",
        "PyYAML",
    ]:
        assert package in requirements


def test_test_running_docs_warn_about_same_python_interpreter(repo_root: Path) -> None:
    for path in [
        TEST_RUNNING_DOC_PATH,
        TESTS_README_PATH,
    ]:
        text = (repo_root / path).read_text(encoding="utf-8")
        assert "同一个 Python 解释器" in text
        assert "subprocess" in text
