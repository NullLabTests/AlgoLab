"""Run the protocol-236-v1 experiment (auditable driver).

Protocol 236 is the higher-N real-workload promotion
(spec/research/236_HIGHER_N_REAL_WORKLOAD_PROMOTION.md). Its single registered
lever is an alpha-side discovery-margin recalibration (0.005 -> 0.0035) with
per-family margins and a workload-version bump (1.1.0 -> 1.2.0).

WARNING — NOT YET CONFORMANT (D-2). The alpha-margin recalibration is
registered but NOT implemented: ``algolab.search.workload_hpo`` still ships
1.1.0 / 0.005 / gate 1.0.0 and the harness gate is not family-keyed. This
driver therefore sets only the trials lever (32 -> 96) and would seal a
``protocol-236-v1`` bundle that does NOT match the pre-registration. Do not run
or seal until the lever is implemented and the machinery-invariant control
(trials 0..31 must byte-reproduce protocol-235-v1 beta/gamma) is checked. See
``docs/quality/protocol-236-conflict.md`` and ``docs/audits/initial-audit.md``
D-2.

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
    "trials 32->96 ONLY. The registered alpha discovery-margin recalibration "
    "(0.005->0.0035 with per-family margins, HPO_WORKLOAD_VERSION "
    "1.1.0->1.2.0, discovery_gate_version 1.0.0->1.1.0) is NOT yet "
    "implemented; a bundle sealed by this driver is therefore NOT conformant "
    "to protocol 236 (see docs/audits/initial-audit.md D-2)."
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
    print(
        "WARNING: this driver is NOT yet conformant to protocol 236 — only the "
        "trials lever is set; the registered alpha-margin recalibration "
        "(0.0035) is not implemented, so the sealed bundle would not match the "
        "pre-registration (see docs/audits/initial-audit.md D-2).",
        file=sys.stderr,
    )
    conn: sqlite3.Connection = connect(args.db, initialize=args.force)
    print(f"writing artifacts to: {artifact_dir}")
    return main(cfg, conn, artifact_dir, force=args.force, out=sys.stdout)


if __name__ == "__main__":
    raise SystemExit(main_cli())
