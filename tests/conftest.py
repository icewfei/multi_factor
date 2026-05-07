from __future__ import annotations

import json
import importlib.util
import re
import sys
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


def normalize_markdown_text(text: str) -> str:
    text = text.replace("`", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


@lru_cache(maxsize=None)
def load_module(relative_path: str, module_name: str):
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


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
