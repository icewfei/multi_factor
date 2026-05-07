#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Run round11b canonical batch02: exact qlib Alpha158 features 31-60,
implemented independently on this project's own data contracts.
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from alpha158_canonical_common import build_candidate_specs, build_feature_batch, build_feature_views
from single_signal_batch_common import materialize_ranked_single_signal, run_single_signal_batch


ROOT = Path("/Users/wy/MiscProject/multi_factor")
RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
REGISTRY_DIR = ROOT / "artifacts" / "research_registry"
ROUND_ID = "rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch02_20260428"
AS_OF_DATE = "20260428"
BASE_RUN_ID = "signaldiag_rr_price_volume_single_signal_discovery_v18_round4_20260423_base"
BASE_RUN_DIR = RUN_STATE_DIR / BASE_RUN_ID
ROUND_DIR = REGISTRY_DIR / "research_rounds" / ROUND_ID
CANDIDATE_REGISTRY_PATH = REGISTRY_DIR / "candidate_scheme_registry.jsonl"
ROUND_REGISTRY_PATH = REGISTRY_DIR / "research_round_registry.jsonl"
BUILD_DIAGNOSIS_SCRIPT = ROOT / "scripts" / "build_signal_edge_diagnosis.py"
SCORE_BUILDER_NAME = "run_round11b_canonical_batch02_single_signal_batch.py"


FEATURE_BATCH = build_feature_batch(start_slot=31, count=30)
CANDIDATES = build_candidate_specs(FEATURE_BATCH)


def build_feature_views_for_batch(
    con: duckdb.DuckDBPyConnection,
    sample_panel: Path,
    source_db_path: Path,
    snapshot_id: str,
) -> None:
    build_feature_views(
        con=con,
        sample_panel=sample_panel,
        source_db_path=source_db_path,
        snapshot_id=snapshot_id,
        feature_batch=FEATURE_BATCH,
    )


def materialize_single_signal(con: duckdb.DuckDBPyConnection, spec, run_dir: Path) -> dict:
    return materialize_ranked_single_signal(
        con=con,
        spec=spec,
        run_dir=run_dir,
        score_builder_name=SCORE_BUILDER_NAME,
    )


def main() -> None:
    run_single_signal_batch(
        round_id=ROUND_ID,
        as_of_date=AS_OF_DATE,
        round_label="Round-11b-Canonical-Batch02",
        base_run_dir=BASE_RUN_DIR,
        round_dir=ROUND_DIR,
        candidate_registry_path=CANDIDATE_REGISTRY_PATH,
        round_registry_path=ROUND_REGISTRY_PATH,
        build_diagnosis_script=BUILD_DIAGNOSIS_SCRIPT,
        score_builder_name=SCORE_BUILDER_NAME,
        candidates=CANDIDATES,
        build_feature_views_fn=build_feature_views_for_batch,
        materialize_single_signal_fn=materialize_single_signal,
        status_question=(
            "Within exact round11b canonical Alpha158 serial-only execution, does this independently implemented "
            "standard feature show positive and head-usable signal-edge under frozen v18 contract?"
        ),
        positive_reason=(
            "Canonical batch02 produced at least one clean positive exact-Alpha158 keeper, but controller policy still "
            "blocks family reopening and requires continued serial-only canonical execution."
        ),
        zero_reason=(
            "Canonical batch02 produced zero clean positive keepers; continue serial-only exact Alpha158 discovery and "
            "do not reopen family construction."
        ),
        summary_intro=(
            "This batch is the second exact qlib Alpha158 canonical execution tranche under round11b governance. "
            "All 30 features are implemented independently on the project's own adjusted-price daily-bar contracts."
        ),
        round_note_prefix="Round11b canonical batch02 serial run completed under exact Alpha158 governance.",
    )


if __name__ == "__main__":
    main()
