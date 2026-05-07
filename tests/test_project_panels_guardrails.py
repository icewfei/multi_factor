from __future__ import annotations

import pytest

from conftest import load_module


def test_holding_period_days_override_is_blocked_with_audit_message() -> None:
    module = load_module("scripts/build_project_panels.py", "build_project_panels_guardrails")

    with pytest.raises(ValueError, match="当前 v1 审计阶段禁止使用 --holding-period-days"):
        module.enforce_holding_period_days_guardrail(10)

    assert "label/sample/execution panel 一致性" in module.HOLDING_PERIOD_OVERRIDE_BLOCKED_MESSAGE


def test_default_project_panels_path_keeps_holding_period_guard_inactive() -> None:
    module = load_module("scripts/build_project_panels.py", "build_project_panels_guardrails")

    assert module.enforce_holding_period_days_guardrail(None) is None
