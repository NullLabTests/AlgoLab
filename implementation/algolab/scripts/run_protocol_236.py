"""Run the frozen protocol-236-v1 experiment (auditable driver).

Mirrors the executed protocol-235-v1 bundle except for the two registered
236 levers: trials 32 -> 96 and the alpha discovery-margin recalibration
(0.0035), implemented in algolab.search.workload_hpo. Everything else is
byte-frozen (spec/research/236_HIGHER_N_REAL_WORKLOAD_PROMOTION.md).

Usage (from implementation/algolab, using the project venv):

    .venv/bin/python scripts/run_protocol_236.py \\
        [--force] [--db /tmp/algolab-236.sqlite3]

Artifacts are written to experiments/protocol-236-v1.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from algolab.search import ExperimentConfig, main
from algolab.search import workload_hpo as hpo
from algolab.search.harness import ARMS_PROTOCOL_234
from algolab.storage.db import connect

EXPERIMENT_ID = "protocol-236-v1"
CHANGES_FROM_235 = (
    "trials 32->96; alpha discovery margin 0.005->0.0035 (lattice "
    "recalibration); HPO_WORKLOAD_VERSION 1.1.0->1.2.0; "
    "discovery_gate_version 1.0.0->1.1.0; everything else frozen "
    "identical to the executed protocol-235-v1 bundle."
)


def build_cfg() -> ExperimentConfig:
    return ExperimentConfig(
        experiment_id=EXPERIMENT_ID,
        workload="hpo",
        trials=96,
        episodes_per_trial=2,
        prior_attempts_per_family=20,
        budget_credits=150.0,
        promotion_threshold=hpo.DISCOVERY_MARGIN,
        arms=ARMS_PROTOCOL_234,
        ablations=(),
        analysis_seed=11,
        prior_seed=101,
        seed_base=7,
        top_k=3,
        producer="research",
        notes=f"protocol 236 {CHANGES_FROM_235}",
    )


def main_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                        help="overwrite an existing committed bundle")
    parser.add_argument(
        "--db", default="/tmp/algolab-236.sqlite3",
        help="scratch sqlite path for attempt persistence (default: "
             "/tmp/algolab-236.sqlite3)")
    parser.add_argument(
        "--out", default=None,
        help="artifact directory (default: experiments/protocol-236-v1)")
    args = parser.parse_args(argv)

    artifact_dir = (
        Path(args.out) if args.out
        else Path(__file__).resolve().parents[1] / "experiments" / EXPERIMENT_ID)
    if artifact_dir.exists() and not args.force \
            and (artifact_dir / "manifest.json").exists():
        print(f"error: {artifact_dir} already has a manifest; "
              "use --force to overwrite", file=sys.stderr)
        return 1

    cfg = build_cfg()
    conn: sqlite3.Connection = connect(args.db, initialize=args.force)
    print(f"writing artifacts to: {artifact_dir}")
    return main(cfg, conn, artifact_dir, force=args.force, out=sys.stdout)


if __name__ == "__main__":
    raise SystemExit(main_cli())
