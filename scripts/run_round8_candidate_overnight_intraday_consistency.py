#!/opt/anaconda3/envs/quant_trade/bin/python
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
CONTRACTS_DIR = ROOT / "contracts"
RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
RESEARCH_DIR = ROOT / "artifacts" / "research_registry"
PYTHON = "/opt/anaconda3/envs/quant_trade/bin/python"

ROUND_ID = "rr_price_volume_single_signal_discovery_v18_round8_orthogonal_20260428"
AS_OF_DATE = "20260428"
BASE_RUN_ID = "signaldiag_rr_price_volume_single_signal_discovery_v18_round4_20260423_base"
BASE_RUN_DIR = RUN_STATE_DIR / BASE_RUN_ID
CANDIDATE_ID = "price_volume_single_signal_overnight_intraday_consistency_20d_v1"
FIELD_NAME = "overnight_intraday_consistency_20d_raw"
RANKING_DIRECTION = "DESC"
SCORE_BUILDER = "run_round8_candidate_overnight_intraday_consistency.py"
BASELINE_REF = "price_volume_v18_refresh_hysteresis"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if raw:
            rows.append(json.loads(raw))
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_path(path: Path) -> str:
    return sql_quote(path.resolve().as_posix())


def ensure_symlink(src: Path, dst: Path) -> None:
    if dst.exists() or dst.is_symlink():
        return
    os.symlink(src, dst)


def classify_signal(payload: dict) -> str:
    ic = payload["ic_readout"]["full_sample_corr_ic"]
    avg_daily = payload["ic_readout"]["avg_daily_ic"]
    positive_share = payload["ic_readout"]["positive_daily_ic_share"]
    top10 = payload["top_slice_readout"]["avg_label_top10"]
    rank11_20 = payload["top_slice_readout"]["avg_label_rank11_20"]
    bottom10 = payload["top_slice_readout"]["avg_label_bottom10"]

    if None in (ic, avg_daily, positive_share, top10, rank11_20, bottom10):
        return "signal_edge_mixed"

    if (
        ic > 0
        and avg_daily > 0
        and positive_share > 0.52
        and top10 > rank11_20
        and top10 > bottom10
    ):
        return "signal_edge_positive"

    if (
        ic <= 0
        and avg_daily <= 0
        and positive_share < 0.50
        and top10 <= rank11_20
    ):
        return "signal_edge_negative"

    return "signal_edge_mixed"


def update_candidate_registry(diag_payload: dict, classification: str) -> None:
    registry_path = RESEARCH_DIR / "candidate_scheme_registry.jsonl"
    rows = read_jsonl(registry_path)
    by_id = {row["candidate_scheme_id"]: row for row in rows}
    ts = now_iso()
    by_id[CANDIDATE_ID] = {
        "registered_at": ts,
        "candidate_scheme_id": CANDIDATE_ID,
        "scheme_family": "price_volume_single_signal_discovery",
        "status": classification,
        "research_round_id": ROUND_ID,
        "research_tier": "exploratory",
        "owner": "codex",
        "score_builder": SCORE_BUILDER,
        "feature_source": "bars_daily_derived",
        "feature_set": [FIELD_NAME],
        "score_rule": f"percentile_rank({FIELD_NAME} {RANKING_DIRECTION}); require min_feature_count >= 1",
        "baseline_reference_candidate_scheme_id": BASELINE_REF,
        "snapshot_id": "warehouse_20260418_181408",
        "execution_logic_version": "warehouse_execution_v3",
        "changed_dimension": "atomic_signal_choice",
        "score_family_rule": "Within the frozen v18 operational contract, does this orthogonal overnight-session consistency signal show genuinely positive and head-usable cross-sectional edge without colliding with existing canonical clusters or relying on family-level composition?",
        "notes": f"Round-8 atomic candidate built from {FIELD_NAME} under frozen {BASELINE_REF}; classified as {classification}.",
        "status_updated_at": ts,
    }
    keep_order = [row["candidate_scheme_id"] for row in rows if row["candidate_scheme_id"] != CANDIDATE_ID]
    out = [by_id[cid] for cid in keep_order] + [by_id[CANDIDATE_ID]]
    write_jsonl(registry_path, out)


def update_round_registry(classification: str) -> None:
    path = RESEARCH_DIR / "research_round_registry.jsonl"
    rows = read_jsonl(path)
    ts = now_iso()
    for row in rows:
        if row.get("research_round_id") != ROUND_ID:
            continue
        existing = row.get("candidate_scheme_ids", [])
        if CANDIDATE_ID not in existing:
            existing.append(CANDIDATE_ID)
        row["candidate_scheme_ids"] = existing
        row["status"] = "in_progress_partial"
        row["status_updated_at"] = ts
        row["notes"] = (
            f"Round8 is in progress. First candidate completed: {CANDIDATE_ID} -> {classification}. "
            "Remaining planned candidates are pending."
        )
    write_jsonl(path, rows)


def main() -> None:
    preflight = subprocess.run(
        [
            PYTHON,
            str(ROOT / "scripts" / "preflight_single_signal_round.py"),
            "--research-round-id",
            ROUND_ID,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if preflight.stdout.strip():
        print(preflight.stdout.strip())
    if preflight.returncode != 0:
        raise RuntimeError(f"Preflight failed for {ROUND_ID}")

    sample_panel = BASE_RUN_DIR / "project_sample_panel.parquet"
    label_panel = BASE_RUN_DIR / "project_label_panel.parquet"
    if not sample_panel.exists() or not label_panel.exists():
        raise FileNotFoundError("Missing shared base panels for round8 candidate run.")

    run_input = read_json(CONTRACTS_DIR / "run_input_contract.current.json")
    snapshot_id = run_input["snapshot_id"]
    source_db_path = Path(run_input["source_root"]["snapshot_path"]) / "duckdb" / "warehouse.duckdb"
    if not source_db_path.exists():
        raise FileNotFoundError(f"Shared warehouse DB not found: {source_db_path}")

    run_id = f"signaldiag_{CANDIDATE_ID}_{AS_OF_DATE}"
    run_dir = RUN_STATE_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    ensure_symlink(sample_panel, run_dir / "project_sample_panel.parquet")
    ensure_symlink(label_panel, run_dir / "project_label_panel.parquet")

    con = duckdb.connect()
    try:
        con.execute(f"ATTACH {sql_path(source_db_path)} AS warehouse_db (READ_ONLY)")
        con.execute(
            f"CREATE OR REPLACE VIEW project_sample_panel AS SELECT * FROM read_parquet({sql_path(sample_panel)})"
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW bar_features AS
            WITH bars AS (
                SELECT
                    ts_code AS instrument,
                    trade_date AS signal_date,
                    adj_open,
                    adj_close
                FROM warehouse_db.serving.vw_bars_daily
                WHERE snapshot_id = {sql_quote(snapshot_id)}
            ),
            daily AS (
                SELECT
                    instrument,
                    signal_date,
                    CASE
                        WHEN LAG(adj_close, 1) OVER w > 0
                        THEN adj_open / LAG(adj_close, 1) OVER w - 1.0
                        ELSE NULL
                    END AS overnight_ret,
                    CASE
                        WHEN adj_open > 0
                        THEN adj_close / adj_open - 1.0
                        ELSE NULL
                    END AS intraday_ret
                FROM bars
                WINDOW w AS (PARTITION BY instrument ORDER BY signal_date)
            )
            SELECT
                instrument,
                signal_date,
                AVG(
                    CASE
                        WHEN overnight_ret IS NOT NULL AND intraday_ret IS NOT NULL
                        THEN overnight_ret * intraday_ret
                        ELSE NULL
                    END
                ) OVER (
                    PARTITION BY instrument
                    ORDER BY signal_date
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                ) AS overnight_intraday_consistency_20d_raw
            FROM daily
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW feature_frame AS
            SELECT
                p.snapshot_id,
                p.instrument,
                p.signal_date,
                p.ranking_eligible_D0,
                b.overnight_intraday_consistency_20d_raw
            FROM project_sample_panel p
            LEFT JOIN bar_features b
              ON p.instrument = b.instrument
             AND p.signal_date = b.signal_date
            """
        )
        score_path = run_dir / "model_scores_D0.parquet"
        con.execute(
            f"""
            COPY (
                WITH ranked AS (
                    SELECT
                        snapshot_id,
                        instrument,
                        signal_date,
                        ranking_eligible_D0,
                        {FIELD_NAME} AS raw_signal_value,
                        PERCENT_RANK() OVER (
                            PARTITION BY snapshot_id, signal_date
                            ORDER BY {FIELD_NAME} DESC, instrument ASC
                        ) AS rank_value
                    FROM feature_frame
                    WHERE ranking_eligible_D0
                      AND {FIELD_NAME} IS NOT NULL
                )
                SELECT
                    p.snapshot_id,
                    p.instrument,
                    p.signal_date,
                    CAST({sql_quote(CANDIDATE_ID)} AS VARCHAR) AS candidate_scheme_id,
                    CASE WHEN p.ranking_eligible_D0 THEN r.rank_value ELSE CAST(NULL AS DOUBLE) END AS model_score_D0,
                    CASE WHEN r.rank_value IS NOT NULL THEN 1 ELSE 0 END AS score_component_count,
                    r.raw_signal_value
                FROM project_sample_panel p
                LEFT JOIN ranked r
                  ON p.snapshot_id = r.snapshot_id
                 AND p.instrument = r.instrument
                 AND p.signal_date = r.signal_date
            ) TO {sql_path(score_path)} (FORMAT PARQUET)
            """
        )
        audit_path = run_dir / "model_scores_D0_audit.json"
        counts = con.execute(
            f"""
            SELECT
                COUNT(*) AS total_rows,
                SUM(CASE WHEN p.ranking_eligible_D0 THEN 1 ELSE 0 END) AS ranking_eligible_rows,
                SUM(CASE WHEN s.model_score_D0 IS NOT NULL THEN 1 ELSE 0 END) AS scored_rows
            FROM read_parquet({sql_path(score_path)}) s
            INNER JOIN project_sample_panel p
              ON s.snapshot_id = p.snapshot_id
             AND s.instrument = p.instrument
             AND s.signal_date = p.signal_date
            """
        ).fetchone()
        write_json(
            audit_path,
            {
                "candidate_scheme_id": CANDIDATE_ID,
                "field_name": FIELD_NAME,
                "ranking_direction": RANKING_DIRECTION,
                "score_builder": SCORE_BUILDER,
                "summary_counts": {
                    "total_rows": int(counts[0] or 0),
                    "ranking_eligible_rows": int(counts[1] or 0),
                    "scored_rows": int(counts[2] or 0),
                },
            },
        )
    finally:
        con.close()

    subprocess.run(
        [
            PYTHON,
            str(ROOT / "scripts" / "build_signal_edge_diagnosis.py"),
            "--run-id",
            run_id,
            "--candidate-scheme-id",
            CANDIDATE_ID,
            "--research-round-id",
            ROUND_ID,
            "--title",
            CANDIDATE_ID,
            "--as-of-date",
            AS_OF_DATE,
            "--input-dir",
            str(run_dir),
        ],
        check=True,
    )

    diag_path = (
        RESEARCH_DIR
        / "research_rounds"
        / ROUND_ID
        / f"{CANDIDATE_ID}_signal_edge_diagnosis_{AS_OF_DATE}.json"
    )
    diag_payload = read_json(diag_path)
    classification = classify_signal(diag_payload)
    update_candidate_registry(diag_payload, classification)
    update_round_registry(classification)
    print(json.dumps({"candidate_scheme_id": CANDIDATE_ID, "classification": classification, "run_id": run_id}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
