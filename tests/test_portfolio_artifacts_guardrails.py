from __future__ import annotations

from conftest import read_text


def test_portfolio_artifacts_contains_unresolved_exit_guard() -> None:
    script_text = read_text("scripts/build_portfolio_artifacts.py")

    assert "ensure_no_unresolved_backtest_exits" in script_text
    assert "WHERE backtest_executable" in script_text
    assert "actual_exit_date IS NULL" in script_text
    assert "unresolved exit would cause holdings/portfolio path mismatch" in script_text
