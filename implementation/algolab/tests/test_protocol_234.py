"""Protocol-234 tests: decision-rule format isolation arms
(knowledge-informed-family-commit, knowledge-informed-family-alloc) per
spec/research/234_DECISION_RULE_FORMAT.md.
"""

from __future__ import annotations

import json

from algolab.search import (
    FamilyAllocPolicy,
    FamilyCommitPolicy,
    KnowledgeSnapshot,
)
from algolab.search.harness import (
    ExperimentConfig,
    PolicyComparison,
    primary_comparisons_for,
)
from algolab.search.policies import build_prior_snapshot
from algolab.storage.db import connect


def _agg(attempts: int, successes: int) -> dict[str, float]:
    return {"attempts": attempts, "successes": successes,
            "sum_effect": 0.0, "sum_effect_sq": 0.0, "credits": 0.0}


def _snapshots() -> tuple[dict[str, KnowledgeSnapshot], KnowledgeSnapshot]:
    alpha = build_prior_snapshot(
        {"tune": _agg(10, 8), "refresh": _agg(10, 2),
         "synthesize": _agg(10, 5)},
        snapshot_id="K0-alpha")
    beta = build_prior_snapshot(
        {"tune": _agg(10, 2), "refresh": _agg(10, 8),
         "synthesize": _agg(10, 5)},
        snapshot_id="K0-beta")
    pooled = build_prior_snapshot(
        {"tune": _agg(20, 10), "refresh": _agg(20, 10),
         "synthesize": _agg(20, 10)},
        snapshot_id="K0-pooled")
    return {"alpha": alpha, "beta": beta}, pooled


class TestCommit:
    def test_commits_to_slice_cost_argmax(self) -> None:
        by_fam, pooled = _snapshots()
        p = FamilyCommitPolicy(by_fam, pooled)
        assert all(p.select("alpha", i)[0] == "tune" for i in range(5))
        assert all(p.select("beta", i)[0] == "refresh" for i in range(5))

    def test_unknown_family_falls_back_to_pooled(self) -> None:
        by_fam, pooled = _snapshots()
        p = FamilyCommitPolicy(by_fam, pooled)
        op, rec = p.select("gamma", 0)
        assert op in ("tune", "refresh", "synthesize")
        assert "pooled fallback" in rec.reason

    def test_contract(self) -> None:
        by_fam, pooled = _snapshots()
        p = FamilyCommitPolicy(by_fam, pooled)
        assert not hasattr(p, "update")
        _, rec = p.select("beta", 0)
        assert rec.policy == "knowledge-informed-family-commit"
        assert "cost-argmax commit" in rec.reason
        assert rec.selection_probability == 1.0


class TestAlloc:
    @staticmethod
    def _full_alpha() -> KnowledgeSnapshot:
        agg = {"tune": (10, 8), "refresh": (10, 2), "synthesize": (10, 5),
               "decompose": (10, 1), "polyglot": (10, 0),
               "validate": (10, 3), "reparameterize": (10, 4),
               "rollback": (10, 2)}
        return build_prior_snapshot(
            {op: _agg(n, s) for op, (n, s) in agg.items()},
            snapshot_id="K0-alpha-full")

    @staticmethod
    def _fractions(snapshot: KnowledgeSnapshot) -> dict[str, float]:
        """Independent recomputation of the allocation fractions."""
        from algolab.knowledge.operators import OPERATOR_BUDGETS
        w = {op: snapshot.success_rate(op) / OPERATOR_BUDGETS[op]
             for op in OPERATOR_BUDGETS}
        total = sum(w.values())
        return {op: x / total for op, x in w.items()}

    def test_deficit_schedule_tracks_fractions(self) -> None:
        by_fam, pooled = _snapshots()
        snap = self._full_alpha()
        p = FamilyAllocPolicy({"alpha": snap}, pooled)
        n = 40
        picks = [p.select("alpha", i)[0] for i in range(n)]
        counts = {op: picks.count(op) for op in set(picks)}
        for op, phi in self._fractions(snap).items():
            assert abs(counts.get(op, 0) - n * phi) <= 1.0, op

    def test_first_pick_is_largest_fraction(self) -> None:
        by_fam, pooled = _snapshots()
        snap = self._full_alpha()
        p = FamilyAllocPolicy({"alpha": snap}, pooled)
        op, rec = p.select("alpha", 0)
        assert op == max(self._fractions(snap), key=self._fractions(snap).get)
        assert rec.selection_score == rec.selection_probability

    def test_long_run_converges_to_fractions(self) -> None:
        by_fam, pooled = _snapshots()
        beta_full = build_prior_snapshot(
            {op: _agg(10, s) for op, s in (
                ("tune", 2), ("refresh", 8), ("synthesize", 5),
                ("decompose", 1), ("polyglot", 0), ("validate", 3),
                ("reparameterize", 8), ("rollback", 2))},
            snapshot_id="K0-beta-full")
        p = FamilyAllocPolicy({"beta": beta_full}, pooled)
        n = 2000
        picks = [p.select("beta", i)[0] for i in range(n)]
        for op, phi in self._fractions(beta_full).items():
            assert abs(picks.count(op) / n - phi) < 0.01, op

    def test_deterministic_and_stateful(self) -> None:
        by_fam, pooled = _snapshots()

        def stream() -> list[str]:
            q = FamilyAllocPolicy(by_fam, pooled)
            return [q.select("beta", i)[0] for i in range(30)]

        assert stream() == stream()

    def test_unknown_family_falls_back_and_never_updates(self) -> None:
        by_fam, pooled = _snapshots()
        p = FamilyAllocPolicy(by_fam, pooled)
        assert not hasattr(p, "update")
        _, rec = p.select("gamma", 0)
        assert "pooled fallback" in rec.reason


class TestComparisonDerivation234:
    def test_v3_arms_yield_232_matrix(self) -> None:
        arms = ("static", "knowledge-informed", "adaptive",
                "adaptive-cost-aware", "random", "knowledge-informed-cost-rank",
                "knowledge-informed-family",
                "knowledge-informed-family-cost-rank",
                "adaptive-cost-aware-family")
        pairs = primary_comparisons_for(arms)
        assert not any("commit" in b or "alloc" in c for b, c in pairs)

    def test_v4_arms_extend_per_preregistration(self) -> None:
        arms = ("static", "knowledge-informed", "adaptive",
                "adaptive-cost-aware", "random", "knowledge-informed-cost-rank",
                "knowledge-informed-family",
                "knowledge-informed-family-cost-rank",
                "adaptive-cost-aware-family",
                "knowledge-informed-family-commit",
                "knowledge-informed-family-alloc")
        got = {(b, c) for b, c in primary_comparisons_for(arms)}
        assert ("knowledge-informed-family-cost-rank",
                "knowledge-informed-family-commit") in got
        assert ("knowledge-informed-family-commit",
                "adaptive-cost-aware-family") in got
        assert ("knowledge-informed-family-cost-rank",
                "knowledge-informed-family-alloc") in got
        assert ("knowledge-informed-family-alloc",
                "adaptive-cost-aware-family") in got


class TestEndToEndV4Config:
    def test_full_run_produces_protocol_234_artifacts(self, tmp_path) -> None:
        cfg = ExperimentConfig(
            experiment_id="protocol-234-smoke",
            trials=2,
            episodes_per_trial=2,
            prior_attempts_per_family=10,
            arms=("static", "knowledge-informed", "adaptive",
                  "adaptive-cost-aware", "knowledge-informed-cost-rank",
                  "random", "adaptive-cost-aware-family",
                  "knowledge-informed-family",
                  "knowledge-informed-family-cost-rank",
                  "knowledge-informed-family-commit",
                  "knowledge-informed-family-alloc"),
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
                candidate="adaptive-cost-aware"))
        comp.write_report(results, stats, held_out_stats)
        comp.write_artifact_bundle(stats, held_out_stats)

        for arm in cfg.arms:
            assert (d / "conditions" / arm / "raw-results.jsonl").exists()
        stats_data = json.loads((d / "statistics.json").read_text())
        block = stats_data["per_family"]["beta"]["comparisons"]
        cand_pairs = {(c["base"], c["candidate"]) for c in block}
        assert ("knowledge-informed-family-cost-rank",
                "knowledge-informed-family-commit") in cand_pairs
        manifest = json.loads((d / "manifest.json").read_text())
        assert manifest["policy_versions"][
            "knowledge-informed-family-commit"] == "1.0.0"
        assert manifest["policy_versions"][
            "knowledge-informed-family-alloc"] == "1.0.0"
        assert PolicyComparison.verify_reproducibility(d, cfg)["reproducible"]
