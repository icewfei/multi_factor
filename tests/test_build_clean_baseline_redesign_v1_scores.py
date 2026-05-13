from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq


SCRIPT_PATH = "scripts/build_clean_baseline_redesign_v1_scores.py"
EXPECTED_CANDIDATES = {
    "clean_reversal_5d_tradability_filtered_v1",
    "clean_reversal_5d_board_neutral_v1",
    "clean_reversal_5d_limit_aware_v1",
    "clean_reversal_5d_liquidity_quality_v1",
    "clean_reversal_5d_listing_age_calendar_v1",
    "clean_composite_reversal_tradability_v1",
}


def write_source_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    try:
        con.execute("CREATE SCHEMA serving")
        con.execute(
            """
            CREATE TABLE serving.vw_bars_daily (
                snapshot_id VARCHAR,
                ts_code VARCHAR,
                trade_date VARCHAR,
                adj_close DOUBLE,
                amount DOUBLE
            )
            """
        )
        rows = []
        for day in range(1, 9):
            date = f"202101{day:02d}"
            rows.extend(
                [
                    ("snap", "AAA.SZ", date, 100.0 - day, 1000.0 + day),
                    ("snap", "BBB.SZ", date, 100.0 + day, 800.0 + day),
                    ("snap", "CCC.SZ", date, 90.0 + day * 0.5, 20.0 + day),
                ]
            )
        con.executemany("INSERT INTO serving.vw_bars_daily VALUES (?, ?, ?, ?, ?)", rows)
    finally:
        con.close()


def write_parquet(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table(payload), path)


def build_fixture(tmp_path: Path) -> dict[str, Path]:
    source_db = tmp_path / "warehouse.duckdb"
    sample_panel = tmp_path / "clean_sample_panel.parquet"
    enrichment_path = tmp_path / "enriched_security_state_daily_v1.parquet"
    write_source_db(source_db)
    rows = {
        "snapshot_id": ["snap", "snap", "snap"],
        "instrument": ["AAA.SZ", "BBB.SZ", "CCC.SZ"],
        "signal_date": ["20210108", "20210108", "20210108"],
    }
    write_parquet(sample_panel, rows | {"ranking_eligible_D0": [True, True, True]})
    write_parquet(
        enrichment_path,
        rows
        | {
            "entry_buyable": [True, True, False],
            "is_st": [False, False, False],
            "is_suspended": [False, False, False],
            "no_trade_flag": [False, False, False],
            "volume_zero_flag": [False, False, True],
            "amount_zero_flag": [False, False, False],
            "is_limit_up": [False, False, False],
            "is_limit_down": [False, False, False],
            "open_at_up_limit": [False, False, False],
            "close_at_down_limit": [False, False, False],
            "exit_sellable": [True, True, True],
            "sellable_retry_next_open": [True, True, True],
            "listing_age_days": [500, 200, 20],
            "board_type": ["main", "main", "gem"],
            "exchange": ["SZ", "SZ", "SZ"],
            "limit_pct_rule": ["10pct", "10pct", "20pct"],
        },
    )
    return {
        "source_db": source_db,
        "sample_panel": sample_panel,
        "enrichment_path": enrichment_path,
        "output_root": tmp_path / "out",
    }


def run_builder(repo_root: Path, fixture: dict[str, Path]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(repo_root / SCRIPT_PATH),
            "--source-db",
            str(fixture["source_db"]),
            "--clean-sample-panel",
            str(fixture["sample_panel"]),
            "--enrichment-path",
            str(fixture["enrichment_path"]),
            "--output-root",
            str(fixture["output_root"]),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_redesign_score_builder_outputs_all_candidate_artifacts(repo_root: Path, tmp_path: Path) -> None:
    fixture = build_fixture(tmp_path)
    result = run_builder(repo_root, fixture)
    assert result.returncode == 0, result.stderr

    round_audit = json.loads((fixture["output_root"] / "round_score_build_audit.json").read_text(encoding="utf-8"))
    assert {item["baseline_id"] for item in round_audit["candidate_results"]} == EXPECTED_CANDIDATES
    assert round_audit["p98_used"] is False
    assert round_audit["label_diagnostics_used"] is False
    assert round_audit["frozen_test_accessed"] is False
    assert round_audit["portfolio_ran"] is False

    for baseline_id in EXPECTED_CANDIDATES:
        run_dir = fixture["output_root"] / baseline_id
        assert (run_dir / "model_scores_D0.parquet").exists()
        audit = json.loads((run_dir / "model_scores_D0_audit.json").read_text(encoding="utf-8"))
        source_chain = json.loads((run_dir / "source_chain_audit.json").read_text(encoding="utf-8"))
        assert audit["status"] == "pass"
        assert audit["p98_used"] is False
        assert audit["label_diagnostics_used"] is False
        assert audit["frozen_test_accessed"] is False
        assert audit["blocked_fields_used"] == []
        assert source_chain["source_chain_status"] == "pass"


def test_redesign_score_builder_fails_fast_on_forbidden_sample_column(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    fixture = build_fixture(tmp_path)
    write_parquet(
        fixture["sample_panel"],
        {
            "snapshot_id": ["snap"],
            "instrument": ["AAA.SZ"],
            "signal_date": ["20210108"],
            "ranking_eligible_D0": [True],
            "label_5d_next_open_close": [0.1],
        },
    )

    result = run_builder(repo_root, fixture)

    assert result.returncode != 0
    assert "forbidden clean sample panel columns" in result.stderr
