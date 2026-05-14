from __future__ import annotations

import re
from pathlib import Path


DOC_PATH = Path("docs/topk_failure_mechanism_map_after_data_regime_stop.md")


def test_topk_failure_mechanism_map_exists(repo_root: Path) -> None:
    assert (repo_root / DOC_PATH).exists()


def test_map_declares_exploratory_descriptive_boundary(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    assert "exploratory descriptive research" in text
    assert "no portfolio" in text
    assert "no frozen test" in text
    assert "not OOS" in text
    assert "p98` / `multi_equal_weight_v1` conditional reference only" in text


def test_map_contains_at_least_eight_mechanisms(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    mechanisms = re.findall(r"^\| \d+\. ", text, flags=re.MULTILINE)

    assert len(mechanisms) >= 8


def test_map_contains_required_mechanisms(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    required = [
        "extreme reversal failure",
        "high-liquidity dilution",
        "limit / state anomaly exposure",
        "TopK large loser concentration",
        "nextK / rank31-100 stronger than TopK",
        "full-cross-section RankIC not converting to TopK edge",
        "p98 conditional reference remains stronger but not clean",
        "composite improves TopK but damages RankIC",
        "liquidity_quality improves RankIC but not TopK",
        "mid-rank edge direction exists but yearly stability insufficient",
    ]

    for phrase in required:
        assert phrase in text


def test_each_mechanism_table_has_required_columns(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    assert "current evidence" in text
    assert "current evidence does not support" in text
    assert "D0-visible?" in text
    assert "stable?" in text
    assert "candidate use now?" in text
    assert "future paper-only pre-registration need" in text


def test_map_contains_required_outputs(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    assert "## Mechanism Map" in text
    assert "## Evidence Table" in text
    assert "## Rejected Interpretations" in text
    assert "## Allowed Paper-Only Future Questions" in text


def test_map_blocks_strategy_restart(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    assert "no strategy restart from this document" in text
    assert "does not create a candidate" in text
    assert "does not design a trading rule" in text
    assert "does not open v4" in text
