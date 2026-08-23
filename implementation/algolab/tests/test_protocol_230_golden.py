"""Golden regression guard: the generalized harness must reproduce the
committed protocol-230-v1 artifact bundle byte-for-byte (excluding files
that embed wall-clock timestamps: manifest.json, plan.json and the two
derived meta files).

This enforces the protocol 231 guarantee that adding the cost-aware arms
did not alter any pre-registered v1 behavior (spec/research/
231_COST_AWARE_SELECTION.md §7).
"""

from __future__ import annotations

from pathlib import Path

from algolab.search import ExperimentConfig, PolicyComparison
from algolab.storage.db import connect

ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "experiments" / "protocol-230-v1"

# Files whose content is fully deterministic given the manifest integers.
DETERMINISTIC_FILES = (
    "statistics.json",
    "held-out-statistics.json",
    "report.md",
    "knowledge-snapshot.json",
    "environment.json",
    "protocol.json",
)


def _regenerate_v1(tmp: Path) -> Path:
    cfg = ExperimentConfig(experiment_id="protocol-230-v1")
    conn = connect(":memory:", initialize=True)
    comp = PolicyComparison(cfg, conn, tmp / "art")
    results = comp.run()
    stats = comp.analyze(results)
    held_out = comp.analyze_held_out(comp.run_held_out())
    held_out["claim_readiness"] = PolicyComparison.evaluate_claim(
        stats.get("per_family", {}), held_out)
    comp.write_report(results, stats, held_out)
    comp.write_artifact_bundle(stats, held_out)
    return tmp / "art"


class TestV1GoldenBundle:
    def test_deterministic_artifacts_match_committed_bytes(
            self, tmp_path) -> None:
        art = _regenerate_v1(tmp_path)
        for name in DETERMINISTIC_FILES:
            assert (art / name).read_bytes() == \
                (ARTIFACT_DIR / name).read_bytes(), name

    def test_all_condition_streams_match_committed_bytes(
            self, tmp_path) -> None:
        art = _regenerate_v1(tmp_path)
        committed_streams = sorted(ARTIFACT_DIR.glob("conditions/*/*.jsonl"))
        assert committed_streams
        for p in committed_streams:
            rel = p.relative_to(ARTIFACT_DIR)
            assert (art / rel).read_bytes() == p.read_bytes(), str(rel)
