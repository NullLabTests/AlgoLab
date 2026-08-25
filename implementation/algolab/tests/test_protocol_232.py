"""Protocol-232 tests: family-conditioned knowledge arms
(knowledge-informed-family, knowledge-informed-family-cost-rank,
adaptive-cost-aware-family) per spec/research/232_FAMILY_CONDITIONED_KNOWLEDGE.md.
"""

from __future__ import annotations

import json

from algolab.search import (
    AdaptiveCostAwareFamilyPolicy,
    AdaptiveCostAwarePolicy,
    CostRankedFamilyKnowledgePolicy,
    FamilyConditionedKnowledgePolicy,
    KnowledgeSnapshot,
)
from algolab.search.harness import (
    ExperimentConfig,
    PolicyComparison,
    ablation_comparisons_for,
    primary_comparisons_for,
)
from algolab.search.policies import build_prior_snapshot
from algolab.storage.db import connect


def _agg(attempts: int, successes: int) -> dict[str, float]:
    return {"attempts": attempts, "successes": successes,
            "sum_effect": 0.0, "sum_effect_sq": 0.0, "credits": 0.0}


def _snapshots() -> tuple[dict[str, KnowledgeSnapshot], KnowledgeSnapshot]:
    """alpha history likes tune; beta history likes refresh; pooled is
    dominated by synthesize."""
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


class TestFamilyConditionedFrozen:
    def test_ranking_follows_family_slice(self) -> None:
        by_fam, pooled = _snapshots()
        p = FamilyConditionedKnowledgePolicy(by_fam, pooled, top_k=1)
        assert p.select("alpha", 0)[0] == "tune"
        assert p.select("beta", 0)[0] == "refresh"

    def test_unknown_family_falls_back_to_pooled(self) -> None:
        by_fam, pooled = _snapshots()
        p = FamilyConditionedKnowledgePolicy(by_fam, pooled, top_k=1)
        op, rec = p.select("gamma", 0)
        # pooled rates are tied; deterministic tiebreak picks catalog-first
        assert rec.reason.endswith("pooled fallback)")
        assert op in ("tune", "refresh", "synthesize")

    def test_never_updates_and_reason_names_basis(self) -> None:
        by_fam, pooled = _snapshots()
        for cls in (FamilyConditionedKnowledgePolicy,
                    CostRankedFamilyKnowledgePolicy):
            p = cls(by_fam, pooled, top_k=3) if cls is \
                FamilyConditionedKnowledgePolicy else \
                cls(by_fam, pooled, top_k=3)
            assert not hasattr(p, "update")
            _, rec = p.select("beta", 0)
            assert "family" in rec.reason

    def test_zero_attempt_cells_smooth_to_neutral(self) -> None:
        snap = build_prior_snapshot(
            {"tune": _agg(4, 4), "polyglot": _agg(0, 0)},
            snapshot_id="K0-zero")
        # polyglot has zero attempts; smoothed rate (0+1)/(0+2)=0.5 keeps it
        # ranked between strong and weak evidence rather than dropped.
        assert set(snap.ranking()) == {"tune", "polyglot"}


class TestAdaptiveCostAwareFamily:
    def test_family_init_used_when_available(self) -> None:
        by_fam, pooled = _snapshots()
        ops = ("tune", "refresh", "synthesize")
        fam = AdaptiveCostAwareFamilyPolicy(
            pooled, ops, rng_seed=1, snapshots_by_family=by_fam)
        plain = AdaptiveCostAwarePolicy(pooled, ops, rng_seed=1)
        # alpha posterior for tune comes from the alpha slice (8/10), not
        # pooled (10/20).
        assert fam.posterior_stats("alpha", "tune")["mean"] > \
            plain.posterior_stats("alpha", "tune")["mean"]
        a_fam = fam.posterior_stats("alpha", "tune")
        assert abs(a_fam["mean"] - (1 + 8) / (2 + 10)) < 1e-9

    def test_unknown_family_uses_pooled_init(self) -> None:
        by_fam, pooled = _snapshots()
        ops = ("tune", "refresh", "synthesize")
        fam = AdaptiveCostAwareFamilyPolicy(
            pooled, ops, rng_seed=1, snapshots_by_family=by_fam)
        plain = AdaptiveCostAwarePolicy(pooled, ops, rng_seed=1)
        for op in ops:
            assert fam.posterior_stats("gamma", op)["mean"] == \
                plain.posterior_stats("gamma", op)["mean"]

    def test_selection_machinery_unchanged(self) -> None:
        by_fam, pooled = _snapshots()
        ops = ("tune", "refresh", "synthesize")
        fam = AdaptiveCostAwareFamilyPolicy(
            pooled, ops, rng_seed=5, snapshots_by_family=by_fam)
        op, rec = fam.select("beta", 0)
        assert op in ops
        assert rec.policy == "adaptive-cost-aware-family"
        assert "theta/cost" in rec.reason
        fam.update("beta", op, True)
        before = fam.posterior_stats("beta", op)["alpha"]
        fam.update("beta", op, True)
        assert fam.posterior_stats("beta", op)["alpha"] == before + 1


class TestComparisonDerivation232:
    def test_v2_arms_yield_231_matrix(self) -> None:
        arms_231 = ("static", "knowledge-informed", "adaptive",
                    "adaptive-cost-aware", "random",
                    "knowledge-informed-cost-rank")
        pairs = primary_comparisons_for(arms_231)
        assert not any("family" in b or "family" in c for b, c in pairs)

    def test_v3_arms_extend_per_preregistration(self) -> None:
        arms = ("static", "knowledge-informed", "adaptive",
                "adaptive-cost-aware", "random",
                "knowledge-informed-cost-rank",
                "knowledge-informed-family",
                "knowledge-informed-family-cost-rank",
                "adaptive-cost-aware-family")
        pairs = primary_comparisons_for(arms)
        assert ("knowledge-informed", "knowledge-informed-family") in pairs
        assert ("knowledge-informed-family",
                "knowledge-informed-family-cost-rank") in pairs
        assert ("knowledge-informed-family-cost-rank",
                "adaptive-cost-aware") in pairs
        assert ("adaptive-cost-aware", "adaptive-cost-aware-family") in pairs
        rows = ablation_comparisons_for(arms)
        assert any(cand == "c-plus-permuted" for _, cand, _ in rows)


class TestEndToEndV3Config:
    def test_full_run_produces_protocol_232_artifacts(self, tmp_path) -> None:
        cfg = ExperimentConfig(
            experiment_id="protocol-232-smoke",
            trials=2,
            episodes_per_trial=2,
            prior_attempts_per_family=10,
            arms=("static", "knowledge-informed", "adaptive",
                  "adaptive-cost-aware", "knowledge-informed-cost-rank",
                  "random", "adaptive-cost-aware-family",
                  "knowledge-informed-family",
                  "knowledge-informed-family-cost-rank"),
        )
        d = tmp_path / "art"
        conn = connect(":memory:", initialize=True)
        comp = PolicyComparison(cfg, conn, d)
        results = comp.run()
        stats = comp.analyze(results)
        held_out_results = comp.run_held_out()
        held_out_stats = comp.analyze_held_out(held_out_results)
        held_out_stats["claim_readiness"] = (
            PolicyComparison.evaluate_claim(
                stats.get("per_family", {}), held_out_stats,
                candidate="adaptive-cost-aware"))
        comp.write_report(results, stats, held_out_stats)
        comp.write_artifact_bundle(stats, held_out_stats)

        by_fam = json.loads(
            (d / "knowledge-snapshot-by-family.json").read_text())
        assert set(by_fam) == {"alpha", "beta"}
        assert all("gamma" not in k for k in by_fam)
        for arm in cfg.arms:
            assert (d / "conditions" / arm / "raw-results.jsonl").exists()
        stats_data = json.loads((d / "statistics.json").read_text())
        block = stats_data["per_family"]["alpha"]["comparisons"]
        cand_pairs = {(c["base"], c["candidate"]) for c in block}
        assert ("knowledge-informed", "knowledge-informed-family") in cand_pairs
        assert ("adaptive-cost-aware",
                "adaptive-cost-aware-family") in cand_pairs
        manifest = json.loads((d / "manifest.json").read_text())
        assert manifest["policy_versions"][
            "knowledge-informed-family-cost-rank"] == "1.0.0"
        assert PolicyComparison.verify_reproducibility(d, cfg)["reproducible"]
