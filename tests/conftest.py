from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=None)
def read_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


@lru_cache(maxsize=None)
def load_json(relative_path: str) -> dict:
    return json.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8"))


def schema_properties(relative_path: str) -> dict:
    return load_json(relative_path)["properties"]


def schema_required(relative_path: str) -> list[str]:
    return load_json(relative_path).get("required", [])


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def label_formula_example() -> dict[str, float]:
    return {
        "open_D1": 10.0,
        "close_D5": 11.0,
        "adj_factor_D1": 1.2,
        "adj_factor_D5": 1.3,
    }
