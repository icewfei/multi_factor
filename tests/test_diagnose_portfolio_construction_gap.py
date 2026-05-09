from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT_PATH = Path("scripts/diagnose_portfolio_construction_gap.py")


def load_module():
    spec = spec_from_file_location("diagnose_portfolio_construction_gap", SCRIPT_PATH)
    assert spec is not None
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_compute_set_turnover() -> None:
    module = load_module()
    signal_to_names = {
        "20100101": {"A", "B", "C"},
        "20100102": {"A", "D", "E"},
        "20190101": {"X", "Y"},
        "20190102": {"Y", "Z"},
    }
    split = {
        "train_start": "20100101",
        "train_end": "20181231",
        "validation_start": "20190101",
        "validation_end": "20211231",
    }
    result = module.compute_set_turnover(signal_to_names, split)
    assert result["train"]["n_transitions"] == 1
    assert result["train"]["avg_overlap_count"] == 1.0
    assert result["validation"]["n_transitions"] == 2
    assert result["validation"]["avg_overlap_count"] == 0.5


def test_compute_pairwise_overlap() -> None:
    module = load_module()
    left = {"20100101": {"A", "B"}, "20190101": {"X", "Y"}}
    right = {"20100101": {"B", "C"}, "20190101": {"Y", "Z"}}
    split = {
        "train_start": "20100101",
        "train_end": "20181231",
        "validation_start": "20190101",
        "validation_end": "20211231",
    }
    result = module.compute_pairwise_overlap(left, right, split)
    assert result["train"]["avg_overlap_count"] == 1.0
    assert round(result["train"]["avg_jaccard"], 4) == 0.3333
    assert result["validation"]["avg_overlap_count"] == 1.0


def test_extract_readout_metrics() -> None:
    module = load_module()
    payload = {
        "windows": {
            "primary": {
                "train": {
                    "final_total_equity_estimate": 1.2,
                    "annual_relative_return_trainval_dry_run_estimate": 0.03,
                    "relative_ir_estimate": 0.4,
                    "avg_cash_weight": 0.7,
                    "avg_invested_weight": 0.3,
                    "avg_turnover_daily": 0.1,
                    "max_drawdown_trainval_dry_run_estimate": -0.1,
                },
                "validation": {
                    "final_total_equity_estimate": 1.1,
                    "annual_relative_return_trainval_dry_run_estimate": -0.02,
                    "relative_ir_estimate": -0.3,
                    "avg_cash_weight": 0.75,
                    "avg_invested_weight": 0.25,
                    "avg_turnover_daily": 0.08,
                    "max_drawdown_trainval_dry_run_estimate": -0.05,
                },
            }
        }
    }
    path = Path("tmp_readout_test.json")
    path.write_text(__import__("json").dumps(payload), encoding="utf-8")
    try:
        result = module.extract_readout_metrics(path, "primary")
    finally:
        path.unlink()
    assert result["train"]["total_equity"] == 1.2
    assert result["validation"]["avg_invested_weight"] == 0.25


def test_infer_failure_causes_prefers_portfolio_axis() -> None:
    module = load_module()
    candidates = {
        "baseline": {
            "portfolio_metrics": {"validation": {"avg_invested_weight": 0.21, "total_equity": 10.0, "relative_return": -0.13, "max_drawdown": -0.07}},
            "selected_head_realized": {"validation": {"realized_return_distribution": {"mean": 0.01}}},
            "topk_turnover": {"validation": {"avg_turnover_ratio": 0.6}},
        },
        "confirmed5": {
            "portfolio_metrics": {"validation": {"avg_invested_weight": 0.25, "total_equity": 2.0, "relative_return": -0.21, "max_drawdown": -0.21}},
            "selected_head_realized": {"validation": {"realized_return_distribution": {"mean": 0.004}}},
            "topk_turnover": {"validation": {"avg_turnover_ratio": 0.9}},
        },
        "v2": {
            "portfolio_metrics": {"validation": {"avg_invested_weight": 0.20, "total_equity": 2.1, "relative_return": -0.15, "max_drawdown": -0.06}},
            "selected_head_realized": {"validation": {"realized_return_distribution": {"mean": 0.003}}},
            "topk_turnover": {"validation": {"avg_turnover_ratio": 0.5}},
        },
    }
    result = module.infer_failure_causes(candidates)
    assert result["baseline_is_not_winning_just_by_more_invested_weight"] is True
    assert result["confirmed5_loses_with_higher_turnover"] is True
    assert result["v2_reduced_turnover_but_not_enough"] is True
    assert result["recommended_v3_research_axis"] == "portfolio_construction_and_capital_deployment"
