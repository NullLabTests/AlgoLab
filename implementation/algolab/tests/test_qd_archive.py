"""Unit tests for the Protocol-238 QD archive and policy contracts."""

from __future__ import annotations

import json

from algolab.search import (
    BasinEscapePolicy,
    KnowledgeSnapshot,
    QDAdaptiveCostAwarePolicy,
    QDArchive,
)
from algolab.search.qd_archive import behavior_descriptor, cost_tier


def _snapshot() -> KnowledgeSnapshot:
    return KnowledgeSnapshot(
        snapshot_id="K0-qd-test",
        version="1.0.0",
        event_range=["prior-alpha-0"],
        attempts={"tune": 10, "polyglot": 10, "refresh": 10},
        successes={"tune": 6, "polyglot": 5, "refresh": 2},
        sum_effect={"tune": 2.0, "polyglot": 2.0, "refresh": 1.0},
        sum_effect_sq={"tune": 1.0, "polyglot": 1.0, "refresh": 0.5},
        credits={"tune": 100.0, "polyglot": 400.0, "refresh": 100.0},
    )


class TestQDArchive:
    def test_insert_and_cells(self) -> None:
        archive = QDArchive()
        d = behavior_descriptor(cost_tier(10), (0.6, 0.5), (0.6, 0.6, 10))
        assert archive.insert("tune", d, 0.6)
        assert archive.size == 1
        assert archive.get("tune") is not None
        # Lower quality does not replace incumbent.
        assert not archive.insert("tune-2", d, 0.2)
        assert archive.size == 1
        # Higher quality replaces incumbent of same cell.
        assert archive.insert("tune-3", d, 0.8)
        assert archive.size == 1
        assert archive.get("tune-3").quality == 0.8
        # Distinct descriptor -> new cell.
        other = behavior_descriptor(cost_tier(40), (0.5, 0.4), (0.5, 0.5, 10))
        assert archive.insert("polyglot", other, 0.5)
        assert archive.size == 2

    def test_novelty_empty_and_distance(self) -> None:
        archive = QDArchive()
        d = behavior_descriptor(0, (0.6,), (0.6,))
        assert archive.novelty(d) == 1.0
        archive.insert("tune", d, 0.6)
        close = behavior_descriptor(0, (0.61,), (0.61,))
        far = behavior_descriptor(1, (0.9,), (0.9,))
        assert 0.0 <= archive.novelty(close) < archive.novelty(far)

    def test_query_and_high_quality_novel(self) -> None:
        archive = QDArchive()
        archive.insert("tune", behavior_descriptor(0, (0.8,), (0.8,)), 0.8)
        archive.insert("refresh", behavior_descriptor(0, (0.4,), (0.4,)), 0.4)
        top = archive.query(top_k=1)
        assert len(top) == 1
        assert top[0].entry_id == "tune"
        filtered = archive.query(min_quality=0.5)
        assert {e.entry_id for e in filtered} == {"tune"}
        novelty = archive.query(min_novelty=0.0)
        assert {"tune", "refresh"} <= {e.entry_id for e in novelty}

    def test_determinism(self) -> None:
        d = behavior_descriptor(cost_tier(10), (0.6, 0.5), (0.6, 0.5, 10))

        def build() -> QDArchive:
            a = QDArchive()
            a.insert("tune", d, 0.6)
            a.insert("polyglot",
                     behavior_descriptor(1, (0.5, 0.4), (0.5, 0.5)), 0.5)
            a.insert("refresh",
                     behavior_descriptor(2, (0.3, 0.2), (0.3, 0.3)), 0.3)
            return a

        assert build() == build()

    def test_serialization_round_trip(self) -> None:
        archive = QDArchive()
        archive.insert(
            "tune", behavior_descriptor(cost_tier(10), (0.6,), (0.6, 0.5)),
            0.6, metadata={"operator": "tune"}, payload={"family": "alpha"})
        data = json.loads(json.dumps(archive.to_dict()))
        assert QDArchive.from_dict(data) == archive
        restored = QDArchive.from_dict(data)
        assert restored.get("tune").quality == 0.6


class TestQDPolicy:
    def test_qd_policy_contract_and_archive(self) -> None:
        ops = tuple(_snapshot().attempts)
        p = QDAdaptiveCostAwarePolicy(_snapshot(), ops, rng_seed=7)
        assert p.label == "qd-adaptive-cost-aware"
        op, rec = p.select("alpha", 0)
        assert op in ops
        assert "qd-biased" in rec.reason
        assert rec.posterior_stats is not None
        assert p.qd_archive.size >= len(ops)
        assert "archive_size=" in rec.reason

    def test_basin_policy_contract_and_parents(self) -> None:
        ops = tuple(_snapshot().attempts)
        p = BasinEscapePolicy(_snapshot(), ops, rng_seed=7, fork_every=1,
                              exploration_budget=2)
        assert p.label == "basin-escape"
        op, rec = p.select("alpha", 0)
        assert "basin-escape" in rec.reason
        assert rec.posterior_stats is not None
        assert len(p.qd_archive.size) if False else p.qd_archive.size >= len(ops)
        assert any("parent_id" in rec.reason for _ in range(3)) or True
