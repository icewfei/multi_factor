from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/nonlinear_confirmed5_challenger_decision_record.md")


def load_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_decision_record_exists() -> None:
    assert DOC_PATH.exists()


def test_decision_record_contains_required_conclusions() -> None:
    text = load_doc()

    assert "confirmed5 model-layer 有正 edge" in text
    assert "execution-layer 已通过" in text
    assert "portfolio-layer same-contract comparison 弱于 baseline" in text
    assert "不建议进入 confirmatory / shadow" in text
    assert "不允许围绕 validation 继续调 confirmed5 参数" in text


def test_decision_record_contains_required_prohibited_phrases() -> None:
    text = load_doc()

    assert "不能说 `策略有效`" in text
    assert "不能说 `OOS 通过`" in text
    assert "不能说 `可以实盘`" in text
    assert "不能把 `trainval dry-run` 当 `fixed/frozen test`" in text


def test_decision_record_contains_next_step_boundaries() -> None:
    text = load_doc()

    assert "必须新建 challenger" in text
    assert "必须新建 research round" in text
    assert "必须新建 manifest" in text
    assert "最低门槛" in text
