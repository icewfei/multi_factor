from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from conftest import load_json, read_text


SCRIPT_PATH = "scripts/diagnose_model_edge.py"
JSON_OUTPUT = "/private/tmp/model_edge_diagnosis.json"
MD_OUTPUT = "/private/tmp/model_edge_diagnosis.md"


@pytest.fixture
def run_diagnosis():
    """Run the diagnosis script and return the JSON output."""
    result = subprocess.run(
        ["python3", SCRIPT_PATH],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    assert result.returncode == 0, f"Script failed:\n{result.stderr}"
    return json.loads(Path(JSON_OUTPUT).read_text(encoding="utf-8"))


class TestModelEdgeDiagnosisOutput:
    """Verify the diagnosis script produces complete and correct output."""

    def test_output_files_exist(self):
        """Both JSON and Markdown outputs are written."""
        assert Path(JSON_OUTPUT).exists(), f"Missing {JSON_OUTPUT}"
        assert Path(MD_OUTPUT).exists(), f"Missing {MD_OUTPUT}"

    def test_diagnosis_label_is_not_backtest(self, run_diagnosis):
        """Output explicitly states it is NOT a backtest."""
        label = run_diagnosis["diagnosis_label"]
        assert "NOT A BACKTEST" in label
        assert "MODEL EDGE DIAGNOSIS" in label

    def test_train_validation_separate(self, run_diagnosis):
        """Train and validation diagnostics are computed separately."""
        diag = run_diagnosis["diagnostics"]
        assert "confirmed5_train" in diag
        assert "confirmed5_validation" in diag
        assert "baseline_train" in diag
        assert "baseline_validation" in diag

    def test_confirmed5_train_has_all_metrics(self, run_diagnosis):
        """Confirmed5 train diagnostics include all required metrics."""
        d = run_diagnosis["diagnostics"]["confirmed5_train"]
        assert d["n_rows"] > 1000000, "Train set should have millions of rows"
        assert d["n_signal_dates"] > 1000
        assert "score_distribution" in d
        assert "rank_ic" in d
        assert "icir" in d
        assert "decile_forward_returns" in d
        assert len(d["decile_forward_returns"]) == 10
        assert "top_bottom_spread" in d
        assert "score_autocorr_lag1" in d
        assert "yearly_stability" in d
        assert len(d["yearly_stability"]) > 0

    def test_confirmed5_validation_has_all_metrics(self, run_diagnosis):
        """Confirmed5 validation diagnostics include all required metrics."""
        d = run_diagnosis["diagnostics"]["confirmed5_validation"]
        assert d["n_rows"] > 500000
        assert d["n_signal_dates"] > 500
        assert "score_distribution" in d
        assert "rank_ic" in d
        assert "icir" in d
        assert "decile_forward_returns" in d
        assert len(d["decile_forward_returns"]) == 10
        assert "top_bottom_spread" in d
        assert "yearly_stability" in d
        assert len(d["yearly_stability"]) > 0

    def test_baseline_metrics_present(self, run_diagnosis):
        """Baseline model diagnostics are computed for comparison."""
        diag = run_diagnosis["diagnostics"]
        for key in ["baseline_train", "baseline_validation"]:
            assert key in diag, f"Missing {key}"
            d = diag[key]
            assert d["n_rows"] > 100000
            assert "rank_ic" in d
            assert "icir" in d
            assert "decile_forward_returns" in d

    def test_cross_model_comparison_present(self, run_diagnosis):
        """Cross-model comparison is computed for both splits."""
        comp = run_diagnosis["cross_model_comparison"]
        assert "train" in comp
        assert "validation" in comp
        for split in ["train", "validation"]:
            c = comp[split]
            assert "rank_ic_delta" in c
            assert "confirmed5_rank_ic" in c
            assert "baseline_rank_ic" in c

    def test_conclusion_has_recommendation(self, run_diagnosis):
        """Conclusion includes edge assessment and portfolio recommendation."""
        conc = run_diagnosis["conclusion"]
        assert "has_model_edge" in conc
        assert isinstance(conc["has_model_edge"], bool)
        assert "edge_evidence" in conc
        assert "concerns" in conc
        assert "portfolio_unblock_recommendation" in conc
        assert "caveat" in conc
        # Recommendation must mention the diagnosis does not depend on portfolio
        assert (
            "model edge diagnosis does not depend on portfolio" in conc["portfolio_unblock_recommendation"]
            or "does not depend on portfolio completion" in conc["portfolio_unblock_recommendation"]
        )

    def test_no_frozen_test_data_referenced(self, run_diagnosis):
        """Diagnosis does not reference frozen test data."""
        json_str = json.dumps(run_diagnosis)
        assert "fixed_test" not in json_str.lower(), "Must not reference frozen test data"

    def test_no_holdings_or_portfolio_output(self, run_diagnosis):
        """Diagnosis does not contain holdings, portfolio, or backtest metrics."""
        json_str = json.dumps(run_diagnosis)
        forbidden = [
            "holdings",
            "backtest_daily",
            "portfolio_daily_summary",
            "portfolio_weights",
            "total_return",
            "sharpe_ratio",
            "max_drawdown",
        ]
        for term in forbidden:
            assert term not in json_str.lower(), f"Must not contain '{term}'"

    def test_rank_ic_values_in_reasonable_range(self, run_diagnosis):
        """RankIC values are in a reasonable range for financial data."""
        d = run_diagnosis["diagnostics"]["confirmed5_train"]
        ric = d["rank_ic"]
        assert isinstance(ric, dict)
        assert -0.5 < ric["mean"] < 0.5, f"RankIC mean {ric['mean']} out of reasonable range"
        assert 0 < ric["std"] < 0.5, f"RankIC std {ric['std']} out of reasonable range"
        assert 0 <= ric["positive_ic_pct"] <= 1.0

    def test_decile_monotonicity_sanity(self, run_diagnosis):
        """Decile returns should show some structure (not purely random order)."""
        deciles = run_diagnosis["diagnostics"]["confirmed5_train"]["decile_forward_returns"]
        returns = [d["mean_forward_return"] for d in deciles]
        # At least the top and bottom should be separated
        assert returns[0] != returns[-1], "Top and bottom decile should differ"

    def test_score_distribution_bounds(self, run_diagnosis):
        """Score distribution is within [0, 1] for rank-based scores."""
        sd = run_diagnosis["diagnostics"]["confirmed5_train"]["score_distribution"]
        assert 0 <= sd["min"] <= 1.0
        assert 0 <= sd["max"] <= 1.0
        assert sd["min"] <= sd["mean"] <= sd["max"]

    def test_markdown_contains_label(self, run_diagnosis):
        """Markdown output explicitly labels the diagnosis."""
        md_content = Path(MD_OUTPUT).read_text(encoding="utf-8")
        assert "NOT A BACKTEST" in md_content
        assert "MODEL EDGE DIAGNOSIS" in md_content

    def test_markdown_has_train_validation_sections(self, run_diagnosis):
        """Markdown has separate train and validation sections."""
        md_content = Path(MD_OUTPUT).read_text(encoding="utf-8")
        assert "## 2. Train Set Diagnostics" in md_content
        assert "## 3. Validation Set Diagnostics" in md_content
        assert "## 4. Cross-Model Comparison" in md_content
        assert "## 5. Conclusion" in md_content
