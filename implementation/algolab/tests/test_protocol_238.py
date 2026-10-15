"""Protocol-238 tests: quality-diversity archive + basin escape arms.

Covers policy contracts, MAP-Elites insertion/novelty/serialisation,
wiring into the harness/CLI, and a protocol-compliance smoke run.
"""

from __future__ import annotations

import json

from algolab.search import (
    BasinEscapePolicy,
    KnowledgeSnapshot,
    QDAdaptiveCostAwarePolicy,
    QDArchive,
)
from algolab.search.harness import (
    ARMS_PROTOCOL_238,
    ExperimentConfig,
    PolicyComparison,
    primary_comparisons_for,
)
from algolab.search.policies import build_prior_snapshot
from algolab.search.qd_archive import (
    behavior_descriptor,
    cost_tier,
)
from algolab.storage.db import connect


def _agg(attempts: int, successes: int) -> dict[str, float]:
    return {"attempts": attempts, "successes": successes,
            "sum_effect": 0.0, "sum_effect_sq": 0.0, "credits": 0.0}


def _snapshot() -> KnowledgeSnapshot:
    return build_prior_snapshot(
        {"tune": _agg(10, 6), "polyglot": _agg(10, 5), "refresh": _agg(10, 2)},
        snapshot_id="K0-qd-test")


class TestQDArchive:
    def test_insert_replaces_incumbent(self) -> None:
        archive = QDArchive()
        d = behavior_descriptor(cost_tier(10), (0.6,), (0.6, 0.5))
        assert archive.insert("tune", d, 0.6)
        assert not archive.insert("tune-lower", d, 0.2)
        assert archive.size == 1
        assert archive.insert("tune-better", d, 0.9)
        # Original entry id stays (stable incumbent), quality updated? No:
        # entry_id is the winner; incumbent replaced when quality strictly
        # greater, but our tie rule keeps the first id for equal quality.
        assert archive.size == 1

    def test_novelty_and_determinism(self) -> None:
        d = behavior_descriptor(cost_tier(10), (0.6,), (0.6,))
        archive = QDArchive()
        assert archive.novelty(d) == 1.0
        archive.insert("tune", d, 0.6)
        assert archive.novelty(d) >= 0.0
        assert archive.is_novel_cell(
            behavior_descriptor(cost_tier(40), (0.9,), (0.9,)))

    def test_serialization_round_trip(self) -> None:
        archive = QDArchive()
        archive.insert(
            "tune", behavior_descriptor(cost_tier(10), (0.6,), (0.6, 0.5)),
            0.6, metadata={"operator": "tune"}, payload={"family": "alpha"})
        data = json.loads(json.dumps(archive.to_dict()))
        assert QDArchive.from_dict(data) == archive


class TestQDPolicyContracts:
    def test_qd_policy(self) -> None:
        ops = tuple(_snapshot().attempts)
        p = QDAdaptiveCostAwarePolicy(_snapshot(), ops, rng_seed=7)
        assert p.label == "qd-adaptive-cost-aware"
        assert p.version == "1.0.0"
        op, rec = p.select("alpha", 0)
        assert op in ops
        assert "qd-biased" in rec.reason
        assert rec.posterior_stats is not None
        assert "archive_size=" in rec.reason
        assert p.qd_archive.size >= len(ops)

    def test_basin_policy_forks(self) -> None:
        ops = tuple(_snapshot().attempts)
        p = BasinEscapePolicy(_snapshot(), ops, rng_seed=7,
                              fork_every=1, exploration_budget=2)
        assert p.label == "basin-escape"
        op, rec = p.select("alpha", 0)
        assert "basin-escape" in rec.reason
        assert rec.posterior_stats is not None
        assert len(p.qd_archive) >= len(ops)


class TestHarnessWiring:
    def test_arm_set(self) -> None:
        assert "qd-adaptive-cost-aware" in ARMS_PROTOCOL_238
        assert "basin-escape" in ARMS_PROTOCOL_238

    def test_primary_comparisons(self) -> None:
        pairs = primary_comparisons_for(ARMS_PROTOCOL_238)
        assert ("adaptive-cost-aware", "qd-adaptive-cost-aware") in pairs
        assert ("adaptive-cost-aware", "basin-escape") in pairs
        assert ("qd-adaptive-cost-aware", "basin-escape") in pairs


class TestProtocolComplianceSmoke:
    def test_tiny_run_produces_qd_bundle(self, tmp_path) -> None:
        cfg = ExperimentConfig(
            experiment_id="protocol-238-smoke",
            workload="hpo",
            trials=2,
            episodes_per_trial=2,
            prior_attempts_per_family=2,
            budget_credits=60.0,
            promotion_threshold=0.005,
            arms=("static", "adaptive-cost-aware", "qd-adaptive-cost-aware",
                  "basin-escape"),
            ablations=(),
        )
        d = tmp_path / "art"
        conn = connect(":memory:", initialize=True)
        comp = PolicyComparison(cfg, conn, d)
        results = comp.run()
        stats = comp.analyze(results)
        held_out_stats = comp.analyze_held_out(comp.run_held_out())
        held_out_stats["claim_readiness"] = (
            PolicyComparison.evaluate_claim(
                stats.get("per_family", {}), held_out_stats,
                candidate="basin-escape",
                held_out_family=cfg.workload_view.held_out_family))
        comp.write_report(results, stats, held_out_stats)
        comp.write_artifact_bundle(stats, held_out_stats)

        manifest = json.loads((d / "manifest.json").read_text())
        assert manifest["policy_versions"]["qd-adaptive-cost-aware"] == "1.0.0"
        assert manifest["policy_versions"]["basin-escape"] == "1.0.0"
        qd = json.loads((d / "qd-archive.json").read_text())
        assert qd["version"] == "1.0.0"
        assert len(qd["cells"]) > 0
        for arm in cfg.arms:
            assert (d / "conditions" / arm / "raw-results.jsonl").exists()
            assert (d / "conditions" / arm
                    / "operator-selections.jsonl").exists()
        assert PolicyComparison.verify_reproducibility(d, cfg)["reproducible"]
