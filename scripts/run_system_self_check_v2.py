#!/opt/anaconda3/envs/quant_trade/bin/python
"""
System self-check v2 — pure DuckDB implementation, no Python-memory row loading.
Uses SQL-internal shuffling and optional row sampling for speed.

Per 框架 14.3: data quality, mask consistency, placebo shuffles,
PIT breach detection, sub-period stability, low-liquidity audit, benchmark check.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from datetime import datetime
from pathlib import Path

import duckdb

ROOT = Path("/Users/wy/MiscProject/multi_factor")
CONTRACTS_DIR = ROOT / "contracts"
ARTIFACTS_RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
REGISTRY_DIR = ROOT / "artifacts" / "research_registry"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="System self-check v2 (pure DuckDB).")
    p.add_argument("--run-id", default="confirmatory_baseline_v1_trainval_20260429")
    p.add_argument("--as-of-date", default=None)
    p.add_argument("--random-seed", type=int, default=42)
    p.add_argument("--n-shuffle-trials", type=int, default=3)
    p.add_argument("--max-shuffle-rows", type=int, default=2_000_000)
    return p.parse_args()


def sql_quote(v: str) -> str:
    return "'" + v.replace("'", "''") + "'"


def sql_path(p: Path) -> str:
    return sql_quote(str(p.resolve()))


def write_json(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".inprogress")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def fmt(v, d=6):
    if v is None: return "null"
    return f"{v:.{d}f}"


def main():
    args = parse_args()
    as_of = args.as_of_date or datetime.now().astimezone().strftime("%Y%m%d")

    run_dir = ARTIFACTS_RUN_STATE_DIR / args.run_id
    score_path = run_dir / "model_scores_D0.parquet"
    if not score_path.exists():
        raise FileNotFoundError(f"model_scores not found: {score_path}")

    ri = json.loads((CONTRACTS_DIR / "run_input_contract.current.json").read_text("utf-8"))
    sid = ri["snapshot_id"]
    db_path = Path(ri["source_root"]["snapshot_path"]) / "duckdb" / "warehouse.duckdb"

    con = duckdb.connect()
    results = {}
    lines = [
        f"# System Self-Check ({as_of})",
        f"",
        f"Run: `{args.run_id}` | Snapshot: `{sid}` | Seed: `{args.random_seed}`",
        f"",
    ]

    try:
        con.execute(f"ATTACH {sql_path(db_path)} AS w (READ_ONLY)")
        con.execute(f"CREATE VIEW scores AS SELECT * FROM read_parquet({sql_path(score_path)})")
        con.execute(f"CREATE VIEW panels AS SELECT * FROM read_parquet({sql_path(run_dir / 'project_sample_panel.parquet')})")
        con.execute(f"CREATE VIEW labels AS SELECT * FROM read_parquet({sql_path(run_dir / 'project_label_panel.parquet')})")

        con.execute("""
        CREATE VIEW diag AS
        SELECT p.snapshot_id, p.instrument, p.signal_date, p.ranking_eligible_D0,
               p.train_mask_v1, p.train_mask_conservative, p.entry_tradeable,
               s.model_score_D0, l.label_5d_next_open_close AS label
        FROM panels p
        INNER JOIN scores s ON p.snapshot_id=s.snapshot_id AND p.instrument=s.instrument AND p.signal_date=s.signal_date
        LEFT JOIN labels l ON p.snapshot_id=l.snapshot_id AND p.instrument=l.instrument AND p.signal_date=l.signal_date
        WHERE p.ranking_eligible_D0 AND s.model_score_D0 IS NOT NULL
        """)

        # ── 1. Data quality ──
        lines.append("## 1. Data Quality")
        r = con.execute("SELECT COUNT(*), SUM(CASE WHEN label IS NOT NULL THEN 1 ELSE 0 END), SUM(CASE WHEN train_mask_v1 THEN 1 ELSE 0 END), SUM(CASE WHEN train_mask_conservative THEN 1 ELSE 0 END) FROM diag").fetchone()
        t = int(r[0]); scored = int(r[1]); main = int(r[2]); consv = int(r[3])
        mask_gap = (main - consv) / max(main, 1)
        lines.extend([
            f"- Scored eligible rows: `{t}`",
            f"- With label: `{scored}` ({scored/max(t,1)*100:.1f}%)",
            f"- Main mask: `{main}` | Conservative: `{consv}`",
            f"- Mask disagreement: `{mask_gap*100:.1f}%`",
            f"- {'✅ PASS' if mask_gap < 0.30 else '❌ FAIL'} (threshold < 30%)",
            f"",
        ])

        # ── 2. IC baseline ──
        ic = con.execute("SELECT CORR(model_score_D0, label) FROM diag WHERE label IS NOT NULL").fetchone()[0]
        daily = con.execute("""
        WITH d AS (
            SELECT signal_date, CORR(model_score_D0, label) AS dic
            FROM diag WHERE label IS NOT NULL GROUP BY signal_date HAVING COUNT(*) >= 20
        )
        SELECT AVG(dic), MEDIAN(dic), AVG(CASE WHEN dic>0 THEN 1.0 ELSE 0.0 END), COUNT(*) FROM d
        """).fetchone()
        lines.extend([
            "## 2. Signal Baseline",
            f"- Full-sample IC: `{fmt(ic)}`",
            f"- Avg daily IC: `{fmt(daily[0])}` | Median: `{fmt(daily[1])}`",
            f"- Positive IC days: `{fmt(daily[2]*100,1)}%` ({int(daily[3])} days)",
            f"",
        ])

        # ── 3. Placebo: shuffled labels (SQL-internal) ──
        lines.append("## 3. Placebo Tests")
        lines.append("### 3a. Shuffled Labels")
        shuffle_ics = []
        for trial in range(args.n_shuffle_trials):
            con.execute(f"SELECT setseed({args.random_seed + trial}::DOUBLE / 1000.0)")
            sic = con.execute(f"""
            WITH sampled AS (
                SELECT model_score_D0, label FROM diag
                WHERE label IS NOT NULL
                ORDER BY random() LIMIT {args.max_shuffle_rows}
            ),
            shuffled AS (
                SELECT model_score_D0,
                       label AS shuffled_label
                FROM sampled
                ORDER BY random()
            ),
            paired AS (
                SELECT s.model_score_D0, sh.shuffled_label
                FROM (SELECT model_score_D0, ROW_NUMBER() OVER () AS rn FROM sampled) s
                INNER JOIN (SELECT shuffled_label, ROW_NUMBER() OVER () AS rn FROM shuffled) sh
                ON s.rn = sh.rn
            )
            SELECT CORR(model_score_D0, shuffled_label) FROM paired
            """).fetchone()[0]
            shuffle_ics.append(float(sic or 0.0))

        mean_sic = sum(shuffle_ics) / len(shuffle_ics)
        max_abs_sic = max(abs(v) for v in shuffle_ics)
        shuffle_ok = abs(mean_sic) < 0.005
        lines.extend([
            f"- Trials: `{args.n_shuffle_trials}`, max rows: `{args.max_shuffle_rows}`",
            f"- Mean shuffled IC: `{fmt(mean_sic)}` | Max |IC|: `{fmt(max_abs_sic)}`",
            f"- {'✅ PASS' if shuffle_ok else '❌ FAIL'} (|mean| < 0.005)",
            f"",
        ])

        # ── 3b. Shuffled scores ──
        lines.append("### 3b. Shuffled Scores")
        ss_ics = []
        for trial in range(args.n_shuffle_trials):
            con.execute(f"SELECT setseed({args.random_seed + 100 + trial}::DOUBLE / 1000.0)")
            sic = con.execute(f"""
            WITH sampled AS (
                SELECT model_score_D0, label FROM diag
                WHERE label IS NOT NULL
                ORDER BY random() LIMIT {args.max_shuffle_rows}
            ),
            shuffled AS (
                SELECT label, model_score_D0 AS shuffled_score
                FROM sampled ORDER BY random()
            ),
            paired AS (
                SELECT sh.shuffled_score, s.label
                FROM (SELECT label, ROW_NUMBER() OVER () AS rn FROM sampled) s
                INNER JOIN (SELECT shuffled_score, ROW_NUMBER() OVER () AS rn FROM shuffled) sh
                ON s.rn = sh.rn
            )
            SELECT CORR(shuffled_score, label) FROM paired
            """).fetchone()[0]
            ss_ics.append(float(sic or 0.0))

        mean_ss = sum(ss_ics) / len(ss_ics)
        max_abs_ss = max(abs(v) for v in ss_ics)
        ss_ok = abs(mean_ss) < 0.005
        lines.extend([
            f"- Trials: `{args.n_shuffle_trials}`",
            f"- Mean shuffled-score IC: `{fmt(mean_ss)}` | Max |IC|: `{fmt(max_abs_ss)}`",
            f"- {'✅ PASS' if ss_ok else '❌ FAIL'} (|mean| < 0.005)",
            f"",
        ])

        # ── 4. PIT breach (feature lagging) ──
        lines.append("### 3c. PIT Integrity (Feature Lagging)")
        pit = con.execute("""
        WITH shifted AS (
            SELECT s.model_score_D0, s.label AS label_same,
                   LEAD(s.label) OVER (PARTITION BY s.instrument ORDER BY s.signal_date) AS label_next
            FROM diag s
            WHERE s.label IS NOT NULL
        )
        SELECT CORR(model_score_D0, label_same), CORR(model_score_D0, label_next)
        FROM shifted WHERE label_same IS NOT NULL AND label_next IS NOT NULL
        """).fetchone()
        ic_same = float(pit[0] or 0) if pit[0] is not None else None
        ic_lag = float(pit[1] or 0) if pit[1] is not None else None
        breach = False
        if ic_same and ic_lag and abs(ic_same) > 0.001:
            breach = abs(ic_lag) > abs(ic_same) * 1.2 and ic_lag * ic_same > 0
        lines.extend([
            f"- IC (score vs same-day label): `{fmt(ic_same)}`",
            f"- IC (score vs NEXT-day label): `{fmt(ic_lag)}`",
            f"- {'✅ PASS' if not breach else '❌ FAIL — possible forward-looking leak'}",
            f"",
        ])

        # ── 5. Sub-period stability ──
        lines.append("## 4. Sub-period Direction Stability")
        sub_ics = []
        for lbs, ys, ye in [("2010-2012","2010","2012"),("2013-2015","2013","2015"),("2016-2018","2016","2018"),("2019-2021","2019","2021")]:
            sp = con.execute(f"SELECT CORR(model_score_D0, label) FROM diag WHERE label IS NOT NULL AND signal_date >= '{ys}0101' AND signal_date <= '{ye}1231'").fetchone()[0]
            sub_ics.append(sp)
            lines.append(f"- {lbs}: IC = `{fmt(sp)}`")
        if sub_ics:
            pos = sum(1 for v in sub_ics if v and v > 0)
            cons = pos / len(sub_ics)
            lines.append(f"- Direction consistency: `{pos}/{len(sub_ics)}` = `{cons*100:.0f}%`")
            lines.append(f"- {'✅ PASS' if cons >= 0.75 else '❌ FAIL'} (threshold >= 75%)")
        lines.append("")

        # ── 6. Low liquidity audit ──
        lines.append("## 5. Low Liquidity Exposure")
        ll = con.execute(f"""
        WITH liq AS (
            SELECT d.*, COALESCE(t.low_liquidity_flag_t, FALSE) AS ll_flag
            FROM diag d
            LEFT JOIN w.serving.vw_tradability_daily t
              ON d.snapshot_id=t.snapshot_id AND d.instrument=t.ts_code AND d.signal_date=t.trade_date
            WHERE d.label IS NOT NULL AND t.snapshot_id='{sid}'
        )
        SELECT
            CORR(model_score_D0, label) FILTER (WHERE NOT ll_flag) AS ic_normal,
            CORR(model_score_D0, label) FILTER (WHERE ll_flag) AS ic_low,
            COUNT(*) FILTER (WHERE NOT ll_flag) AS n_normal,
            COUNT(*) FILTER (WHERE ll_flag) AS n_low
        FROM liq
        """).fetchone()
        ic_n = float(ll[0] or 0); ic_l = float(ll[1] or 0)
        ll_dep = False
        if ic_n and ic_l and abs(ic_n) > 0.001:
            ll_dep = (abs(ic_n) - abs(ic_l)) / abs(ic_n) > 0.5
        lines.extend([
            f"- Normal liq IC: `{fmt(ic_n)}` (n={ll[2]})",
            f"- Low liq IC: `{fmt(ic_l)}` (n={ll[3]})",
            f"- {'✅ PASS' if not ll_dep else '❌ FAIL — alpha depends on low-liquidity names'}",
            f"",
        ])

        # ── 7. Benchmark ──
        lines.append("## 6. Benchmark")
        bm = con.execute(f"SELECT benchmark_code, is_total_return, COUNT(*) FROM w.serving.vw_benchmark_daily WHERE benchmark_code='CSI_ALL_SHARE_TR' AND snapshot_id='{sid}' GROUP BY 1,2").fetchone()
        bm_ok = bm is not None and bool(bm[1])
        lines.extend([
            f"- Benchmark: `{bm[0] if bm else 'MISSING'}` total-return=`{bm[1] if bm else 'N/A'}` days=`{bm[2] if bm else 0}`",
            f"- {'✅ PASS' if bm_ok else '❌ FAIL'}",
            f"",
        ])

        # ── Overall ──
        checks = [
            ("Mask consistency", mask_gap < 0.30),
            ("Placebo: shuffled labels", shuffle_ok),
            ("Placebo: shuffled scores", ss_ok),
            ("PIT integrity (no forward-looking breach)", not breach),
            ("Sub-period direction consistency >= 75%", cons >= 0.75),
            ("Alpha not low-liquidity dependent", not ll_dep),
            ("Benchmark total-return available", bm_ok),
        ]
        passed = sum(1 for _, ok in checks if ok)
        fail = len(checks) - passed
        lines.append("## Overall")
        lines.append(f"**{passed}/{len(checks)} checks passed** ({fail} failed)")
        for name, ok in checks:
            lines.append(f"- {'✅' if ok else '❌'} {name}")
        lines.append("")
        if fail == 0:
            lines.append("✅ **All checks passed. System integrity confirmed on trainval snapshot.**")
            lines.append("The 5-signal baseline is standing on a clean data foundation with no structural placebo or PIT breaches.")
        else:
            lines.append(f"❌ **{fail} check(s) failed.** Review individual results before proceeding to confirmatory research.")

        results = {
            "as_of": as_of, "run_id": args.run_id, "snapshot_id": sid,
            "ic_baseline": ic,
            "avg_daily_ic": float(daily[0] or 0),
            "positive_daily_share": float(daily[2] or 0),
            "shuffle_label": {"mean_ic": mean_sic, "max_abs_ic": max_abs_sic, "pass": shuffle_ok},
            "shuffle_score": {"mean_ic": mean_ss, "max_abs_ic": max_abs_ss, "pass": ss_ok},
            "pit_breach": not breach,
            "sub_period_consistency": cons,
            "low_liq_dependent": ll_dep,
            "benchmark_available": bm_ok,
            "overall": {"passed": passed, "total": len(checks), "failed": fail},
        }
    finally:
        con.close()

    jout = REGISTRY_DIR / f"system_self_check_{as_of}.json"
    mout = REGISTRY_DIR / f"system_self_check_{as_of}.md"
    write_json(jout, results)
    mout.write_text("\n".join(lines), encoding="utf-8")
    print(f"Done: {jout} | {mout}")
    print(f"Result: {passed}/{len(checks)} passed ({fail} failed)")


if __name__ == "__main__":
    main()
