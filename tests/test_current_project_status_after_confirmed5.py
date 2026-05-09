from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/current_project_status_after_confirmed5.md")


def load_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_project_status_doc_exists() -> None:
    assert DOC_PATH.exists()


def test_project_status_doc_contains_confirmed5_conclusions() -> None:
    text = load_doc()

    assert "model-layer 有正 edge" in text
    assert "execution-layer 通过" in text
    assert "portfolio dry-run 通过" in text
    assert "same-contract baseline comparison 弱于 baseline" in text
    assert "不晋级 confirmatory / shadow" in text


def test_project_status_doc_contains_prohibited_actions() -> None:
    text = load_doc()

    assert "不允许继续调 `confirmed5`" in text
    assert "不允许围绕 validation 结果反复筛优" in text
    assert "不允许读取 frozen test" in text
    assert "不允许把 trainval dry-run 当 OOS" in text
    assert "不允许宣称策略有效" in text


def test_project_status_doc_contains_next_challenger_entry_conditions() -> None:
    text = load_doc()

    assert "必须新建 `research_round_id`" in text
    assert "必须新建 manifests" in text
    assert "必须预注册变更维度" in text
    assert "必须在 same-contract comparison 中优于 baseline" in text
