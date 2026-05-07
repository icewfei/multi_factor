#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Build a component-level attribution / ablation diagnosis for a mixed score family.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
RESEARCH_ROUNDS_DIR = ROOT / "artifacts" / "research_registry" / "research_rounds"
CONTRACTS_DIR = ROOT / "contracts"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build component ablation diagnosis.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--candidate-scheme-id", required=True)
    parser.add_argument("--research-round-id", required=True)
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--component-json", action="append", required=True)
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require_path(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Required path not found: {path}")
    return path


def sql_path(path: Path) -> str:
    return "'" + path.resolve().as_posix().replace("'", "''") + "'"


def write_md(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def compute_score_block(con: duckdb.DuckDBPyConnection, score_expr: str) -> dict:
    coverage = con.execute(
        f"""
        SELECT
            COUNT(*) AS rows_with_score_and_label
        FROM base_diag
        WHERE {score_expr} IS NOT NULL
          AND forward_label IS NOT NULL
        """
    ).fetchone()

    ic = con.execute(
        f"""
        SELECT CORR({score_expr}, forward_label)
        FROM base_diag
        WHERE {score_expr} IS NOT NULL
          AND forward_label IS NOT NULL
        """
    ).fetchone()[0]

    daily = con.execute(
        f"""
        WITH daily_ic AS (
            SELECT
                signal_date,
                CORR({score_expr}, forward_label) AS daily_ic
            FROM base_diag
            WHERE {score_expr} IS NOT NULL
              AND forward_label IS NOT NULL
            GROUP BY signal_date
            HAVING COUNT(*) >= 20
        )
        SELECT
            AVG(daily_ic),
            MEDIAN(daily_ic),
            AVG(CASE WHEN daily_ic > 0 THEN 1.0 ELSE 0.0 END)
        FROM daily_ic
        """
    ).fetchone()

    top_slice = con.execute(
        f"""
        WITH ranked AS (
            SELECT
                signal_date,
                instrument,
                low_liquidity_flag,
                forward_label,
                momentum_rank,
                trend_consistency_rank,
                liquidity_trend_rank,
                ROW_NUMBER() OVER (
                    PARTITION BY signal_date
                    ORDER BY {score_expr} DESC, instrument ASC
                ) AS rank_desc,
                ROW_NUMBER() OVER (
                    PARTITION BY signal_date
                    ORDER BY {score_expr} ASC, instrument ASC
                ) AS rank_asc
            FROM base_diag
            WHERE {score_expr} IS NOT NULL
              AND forward_label IS NOT NULL
        )
        SELECT
            AVG(CASE WHEN rank_desc <= 10 THEN forward_label END),
            AVG(CASE WHEN rank_desc BETWEEN 11 AND 20 THEN forward_label END),
            AVG(CASE WHEN rank_asc <= 10 THEN forward_label END),
            AVG(CASE WHEN rank_desc <= 10 THEN CASE WHEN low_liquidity_flag THEN 1.0 ELSE 0.0 END END),
            AVG(CASE WHEN rank_desc <= 10 THEN momentum_rank END),
            AVG(CASE WHEN rank_desc <= 10 THEN trend_consistency_rank END),
            AVG(CASE WHEN rank_desc <= 10 THEN liquidity_trend_rank END)
        FROM ranked
        """
    ).fetchone()

    return {
        "rows_with_score_and_label": int(coverage[0] or 0),
        "full_sample_corr_ic": float(ic) if ic is not None else None,
        "avg_daily_ic": float(daily[0]) if daily[0] is not None else None,
        "median_daily_ic": float(daily[1]) if daily[1] is not None else None,
        "positive_daily_ic_share": float(daily[2]) if daily[2] is not None else None,
        "avg_label_top10": float(top_slice[0]) if top_slice[0] is not None else None,
        "avg_label_rank11_20": float(top_slice[1]) if top_slice[1] is not None else None,
        "avg_label_bottom10": float(top_slice[2]) if top_slice[2] is not None else None,
        "top10_low_liquidity_share_proxy": float(top_slice[3]) if top_slice[3] is not None else None,
        "top10_avg_momentum_rank": float(top_slice[4]) if top_slice[4] is not None else None,
        "top10_avg_trend_consistency_rank": float(top_slice[5]) if top_slice[5] is not None else None,
        "top10_avg_liquidity_trend_rank": float(top_slice[6]) if top_slice[6] is not None else None,
    }


def main() -> None:
    args = parse_args()

    run_dir = RUN_STATE_DIR / args.run_id
    attempt_dir = run_dir / "attempts" / args.attempt_id
    round_dir = RESEARCH_ROUNDS_DIR / args.research_round_id
    round_dir.mkdir(parents=True, exist_ok=True)

    score_path = require_path(run_dir / "model_scores_D0.parquet")
    sample_path = require_path(run_dir / "project_sample_panel.parquet")
    label_path = require_path(run_dir / "project_label_panel.parquet")
    ranking_path = require_path(attempt_dir / "ranking_state_daily.parquet")

    run_input = load_json(CONTRACTS_DIR / "run_input_contract.current.json")
    snapshot_id = run_input["snapshot_id"]
    source_db_path = Path(run_input["source_root"]["snapshot_path"]) / "duckdb" / "warehouse.duckdb"
    require_path(source_db_path)

    component_payloads = {Path(p).stem: load_json(Path(p)) for p in args.component_json}

    con = duckdb.connect()
    try:
        con.execute(f"ATTACH {sql_path(source_db_path)} AS warehouse_db (READ_ONLY)")
        con.execute(f"CREATE OR REPLACE VIEW score_input AS SELECT * FROM read_parquet({sql_path(score_path)})")
        con.execute(f"CREATE OR REPLACE VIEW sample_input AS SELECT * FROM read_parquet({sql_path(sample_path)})")
        con.execute(f"CREATE OR REPLACE VIEW label_input AS SELECT * FROM read_parquet({sql_path(label_path)})")
        con.execute(f"CREATE OR REPLACE VIEW ranking_input AS SELECT * FROM read_parquet({sql_path(ranking_path)})")
        con.execute(
            f"""
            CREATE OR REPLACE VIEW tradability_input AS
            SELECT
                ts_code AS instrument,
                trade_date AS signal_date,
                low_liquidity_flag_t AS low_liquidity_flag
            FROM warehouse_db.serving.vw_tradability_daily
            WHERE snapshot_id = '{snapshot_id}'
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW base_diag AS
            SELECT
                s.instrument,
                s.signal_date,
                s.model_score_D0,
                s.momentum_rank,
                s.trend_consistency_rank,
                s.liquidity_trend_rank,
                l.label_5d_next_open_close AS forward_label,
                COALESCE(t.low_liquidity_flag, FALSE) AS low_liquidity_flag
            FROM score_input s
            INNER JOIN sample_input p
                ON s.snapshot_id = p.snapshot_id
               AND s.instrument = p.instrument
               AND s.signal_date = p.signal_date
            LEFT JOIN label_input l
                ON s.snapshot_id = l.snapshot_id
               AND s.instrument = l.instrument
               AND s.signal_date = l.signal_date
            LEFT JOIN tradability_input t
                ON s.instrument = t.instrument
               AND s.signal_date = t.signal_date
            WHERE p.ranking_eligible_D0
            """
        )

        actual_selected = con.execute(
            """
            SELECT
                AVG(momentum_rank),
                AVG(trend_consistency_rank),
                AVG(liquidity_trend_rank),
                AVG(CASE WHEN low_liquidity_flag THEN 1.0 ELSE 0.0 END)
            FROM (
                SELECT
                    b.*,
                    r.topk_frozen_D0
                FROM base_diag b
                INNER JOIN ranking_input r
                    ON b.instrument = r.instrument
                   AND b.signal_date = r.signal_date
            )
            WHERE topk_frozen_D0
            """
        ).fetchone()
    finally:
        pass

    full_score_expr = "(momentum_rank + trend_consistency_rank + liquidity_trend_rank) / 3.0"
    remove_momentum_expr = "(trend_consistency_rank + liquidity_trend_rank) / 2.0"
    remove_trend_expr = "(momentum_rank + liquidity_trend_rank) / 2.0"
    remove_liquidity_expr = "(momentum_rank + trend_consistency_rank) / 2.0"

    full_block = compute_score_block(con, full_score_expr)
    remove_momentum = compute_score_block(con, remove_momentum_expr)
    remove_trend = compute_score_block(con, remove_trend_expr)
    remove_liquidity = compute_score_block(con, remove_liquidity_expr)
    con.close()

    result = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "candidate_scheme_id": args.candidate_scheme_id,
        "research_round_id": args.research_round_id,
        "as_of_date": args.as_of_date,
        "single_signal_reference": component_payloads,
        "actual_v15_selected_profile": {
            "avg_momentum_rank": float(actual_selected[0]),
            "avg_trend_consistency_rank": float(actual_selected[1]),
            "avg_liquidity_trend_rank": float(actual_selected[2]),
            "low_liquidity_share_proxy": float(actual_selected[3]),
        },
        "ablation_blocks": {
            "full_v15": full_block,
            "remove_momentum_60_5": remove_momentum,
            "remove_trend_consistency_20d": remove_trend,
            "remove_liquidity_trend_20_60": remove_liquidity,
        },
    }

    # heuristic interpretation
    interpretations: list[str] = []
    if remove_liquidity["full_sample_corr_ic"] is not None and full_block["full_sample_corr_ic"] is not None:
        if remove_liquidity["full_sample_corr_ic"] < full_block["full_sample_corr_ic"]:
            interpretations.append(
                "liquidity_trend_20_60_raw likely contributes positively to broad edge because removing it lowers full_sample_corr_ic(全样本IC)."
            )
    if remove_liquidity["top10_low_liquidity_share_proxy"] is not None and full_block["top10_low_liquidity_share_proxy"] is not None:
        if remove_liquidity["top10_low_liquidity_share_proxy"] < full_block["top10_low_liquidity_share_proxy"]:
            interpretations.append(
                "liquidity_trend_20_60_raw likely contributes to higher low-liquidity exposure because removing it lowers top10_low_liquidity_share_proxy(前10低流动性占比代理)."
            )
    if remove_trend["avg_label_top10"] is not None and full_block["avg_label_top10"] is not None:
        if remove_trend["avg_label_top10"] >= full_block["avg_label_top10"]:
            interpretations.append(
                "trend_consistency_20d_raw may be the weakest contributor to head extraction because removing it does not worsen avg_label_top10(前10平均标签)."
            )
    if remove_momentum["full_sample_corr_ic"] is not None and full_block["full_sample_corr_ic"] is not None:
        if remove_momentum["full_sample_corr_ic"] < full_block["full_sample_corr_ic"]:
            interpretations.append(
                "momentum_60_5_raw remains a core positive component because removing it weakens broad cross-sectional edge."
            )
    result["interpretations"] = interpretations

    json_path = round_dir / f"{args.candidate_scheme_id}_component_ablation_diagnosis_{args.as_of_date}.json"
    md_path = round_dir / f"{args.candidate_scheme_id}_component_ablation_diagnosis_{args.as_of_date}.md"
    write_json(json_path, result)

    lines = [
        f"# {args.candidate_scheme_id} Component Ablation Diagnosis",
        "",
        f"- Generated at: `{result['generated_at']}`",
        f"- Candidate: `{args.candidate_scheme_id}`",
        f"- Research round: `{args.research_round_id}`",
        "",
        "## Actual v15 Selected Profile",
        "",
        f"- avg_momentum_rank（平均动量分位）: `{result['actual_v15_selected_profile']['avg_momentum_rank']:.6f}`",
        f"- avg_trend_consistency_rank（平均趋势一致性分位）: `{result['actual_v15_selected_profile']['avg_trend_consistency_rank']:.6f}`",
        f"- avg_liquidity_trend_rank（平均流动性改善分位）: `{result['actual_v15_selected_profile']['avg_liquidity_trend_rank']:.6f}`",
        f"- low_liquidity_share_proxy（低流动性占比代理）: `{result['actual_v15_selected_profile']['low_liquidity_share_proxy']:.6f}`",
        "",
        "## Ablation Blocks",
        "",
    ]

    def add_block(name: str, payload: dict) -> None:
        lines.extend(
            [
                f"### {name}",
                "",
                f"- full_sample_corr_ic（全样本IC）: `{payload['full_sample_corr_ic']:.6f}`",
                f"- avg_daily_ic（平均日IC）: `{payload['avg_daily_ic']:.6f}`",
                f"- positive_daily_ic_share（正IC日占比）: `{payload['positive_daily_ic_share']:.4f}`",
                f"- avg_label_top10（前10平均标签）: `{payload['avg_label_top10']:.6f}`",
                f"- avg_label_rank11_20（11-20名平均标签）: `{payload['avg_label_rank11_20']:.6f}`",
                f"- top10_low_liquidity_share_proxy（前10低流动性占比代理）: `{payload['top10_low_liquidity_share_proxy']:.6f}`",
                "",
            ]
        )

    add_block("full_v15", full_block)
    add_block("remove_momentum_60_5", remove_momentum)
    add_block("remove_trend_consistency_20d", remove_trend)
    add_block("remove_liquidity_trend_20_60", remove_liquidity)

    lines.append("## Interpretations")
    lines.append("")
    lines.extend([f"- {line}" for line in interpretations])
    lines.append("")
    write_md(md_path, lines)


if __name__ == "__main__":
    main()
