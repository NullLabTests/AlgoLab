"""Protocol-231 tests: cost-aware adaptive selection (C+) and frozen
cost-ranked knowledge (B+), per spec/research/231_COST_AWARE_SELECTION.md.

Covers: ranking semantics, policy contracts, ablation wiring, comparison
matrix derivation, claim evaluation for the new candidate, and an
end-to-end v2-config run.
"""

from __future__ import annotations

import json

from algolab.search import (
    AdaptiveCostAwarePolicy,
    AdaptivePolicy,
    CostRankedKnowledgePolicy,
    KnowledgeSnapshot,
)
from algolab.search.harness import (
    ABLATION_COMPARISONS,
    ARMS_PROCEDURAL,
    PRIMARY_COMPARISONS,
    ExperimentConfig,
    PolicyComparison,
    ablation_comparisons_for,
    primary_comparisons_for,
)
from algolab.storage.db import connect


def _snapshot() -> KnowledgeSnapshot:
    """Handcrafted K0: synthesize has the best raw rate but costs 40;
    reparameterize is nearly as good at 10 credits; refresh is cheap with a
    middling rate."""
    return KnowledgeSnapshot(
        snapshot_id="K0-p231-test",
        version="1.0.0",
        event_range=["prior-alpha-0"],
        attempts={"synthesize": 10, "reparameterize": 10, "refresh": 10},
        successes={"synthesize": 7, "reparameterize": 6, "refresh": 3},
        sum_effect={"synthesize": 2.5, "reparameterize": 2.4, "refresh": 1.2},
        sum_effect_sq={"synthesize": 1.0, "reparameterize": 0.9, "refresh": 0.4},
        credits={"synthesize": 400.0, "reparameterize": 100.0,
                 "refresh": 100.0},
    )


class TestCostRankedKnowledge:
    def test_ranking_by_cost_reorders_by_rate_per_credit(self) -> None:
        snap = _snapshot()
        # rates: synth 8/12=.667(/40=.0167), reparam 7/12=.583(/10=.0583),
        # refresh 4/12=.333(/10=.0333)
        assert snap.ranking_by_cost() == [
            "reparameterize", "refresh", "synthesize"]
        # plain ranking unchanged: raw success-rate order
        assert snap.ranking() == ["synthesize", "reparameterize", "refresh"]

    def test_cost_ranked_policy_cycles_frozen_top_k(self) -> None:
        p = CostRankedKnowledgePolicy(_snapshot(), top_k=2)
        seq = [p.select("beta", i)[0] for i in range(6)]
        assert seq == ["reparameterize", "refresh"] * 3
        assert not hasattr(p, "update")
        rec = p.select("beta", 99)[1]
        assert "cost-rank" in rec.reason

    def test_default_ranking_unchanged(self) -> None:
        p = CostRankedKnowledgePolicy.__mro__  # noqa: F841 - import sanity
        from algolab.search.policies import KnowledgeInformedPolicy
        b = KnowledgeInformedPolicy(_snapshot(), top_k=1)
        assert b.select("beta", 0)[0] == "synthesize"


class TestAdaptiveCostAware:
    def test_initialization_matches_plain_adaptive(self) -> None:
        snap = _snapshot()
        c = AdaptivePolicy(snap, tuple(_snapshot().attempts), rng_seed=3)
        cp = AdaptiveCostAwarePolicy(
            snap, tuple(_snapshot().attempts), rng_seed=3)
        for op in snap.attempts:
            assert (c.posterior_stats("alpha", op)["mean"]
                    == cp.posterior_stats("alpha", op)["mean"])

    def test_equal_priors_favor_cheaper_operator(self) -> None:
        ops = ("tune", "polyglot")  # 10 vs 40 credits
        snap = KnowledgeSnapshot(
            snapshot_id="K0-eq", version="1.0.0",
            attempts={"tune": 10, "polyglot": 10},
            successes={"tune": 5, "polyglot": 5},
            sum_effect={}, sum_effect_sq={}, credits={})
        p = AdaptiveCostAwarePolicy(snap, ops, rng_seed=7)
        picks = [p.select("alpha", i)[0] for i in range(2000)]
        n_tune = picks.count("tune")
        n_polyglot = picks.count("polyglot")
        # Identical posteriors => identical theta draws; the /cost scaling
        # must dominate selection.
        assert n_tune > 10 * n_polyglot
        plain = AdaptivePolicy(snap, ops, rng_seed=7)
        plain_picks = [plain.select("alpha", i)[0] for i in range(2000)]
        # Plain C with equal priors splits roughly evenly.
        assert abs(plain_picks.count("tune") - plain_picks.count("polyglot")) \
            < 200

    def test_update_changes_posterior_and_selection(self) -> None:
        snap = _snapshot()
        ops = tuple(snap.attempts)
        p = AdaptiveCostAwarePolicy(snap, ops, rng_seed=11)
        before = p.posterior_stats("beta", "refresh")["mean"]
        for _ in range(5):
            p.update("beta", "refresh", True)
        after = p.posterior_stats("beta", "refresh")["mean"]
        assert after > before
        op, rec = p.select("beta", 0)
        assert op in ops
        assert rec.policy == "adaptive-cost-aware"
        assert "theta/cost" in rec.reason

    def test_permuted_feedback_breaks_attribution(self) -> None:
        snap = _snapshot()
        ops = tuple(snap.attempts)
        p = AdaptiveCostAwarePolicy(
            snap, ops, rng_seed=5, feedback_shuffle_seed=123)
        p.select("beta", 0)
        p.update("beta", "reparameterize", True)
        # The update landed on SOME operator; posteriors moved, but not
        # necessarily the requested one (seeded permutation).
        total = sum(p.posterior_stats("beta", op)["alpha"] for op in ops)
        assert total == sum(1 + snap.successes[op] for op in ops) + 1


class TestComparisonMatrixDerivation:
    def test_v1_arms_yield_legacy_matrices(self) -> None:
        assert primary_comparisons_for(ARMS_PROCEDURAL) == \
            PRIMARY_COMPARISONS
        assert ablation_comparisons_for(ARMS_PROCEDURAL) == \
            ABLATION_COMPARISONS

    def test_v2_arms_extend_matrix_per_preregistration(self) -> None:
        arms = ("static", "knowledge-informed", "adaptive",
                "adaptive-cost-aware", "random",
                "knowledge-informed-cost-rank")
        pairs = primary_comparisons_for(arms)
        assert pairs[:len(PRIMARY_COMPARISONS)] == PRIMARY_COMPARISONS
        assert ("knowledge-informed", "adaptive-cost-aware") in pairs
        assert ("adaptive", "adaptive-cost-aware") in pairs
        assert ("knowledge-informed-cost-rank", "adaptive-cost-aware") in pairs
        rows = ablation_comparisons_for(arms)
        assert any(cand == "c-plus-permuted" for _, cand, _ in rows)


class TestEvaluateClaimCandidate:
    @staticmethod
    def _blocks(candidate: str, *, significant_beta: bool) -> dict:
        def block(p: float) -> dict:
            return {"comparisons": [
                {"base": base, "candidate": candidate, "delta": 0.02,
                 "ci_low": 0.005 if p < 0.05 else -0.001,
                 "ci_high": 0.03, "adjusted_p": p}
                for base in ("static", "knowledge-informed")]}

        beta_p = 0.01 if significant_beta else 0.4
        return {"alpha": block(0.01), "beta": block(beta_p)}

    @staticmethod
    def _held_out(candidate: str) -> dict:
        return {"comparisons": [
            {"base": base, "candidate": candidate, "delta": 0.03,
             "ci_low": 0.02, "ci_high": 0.04, "adjusted_p": 0.01}
            for base in ("static", "knowledge-informed")]}

    def test_candidate_adaptive_matches_v1_semantics(self) -> None:
        claim = PolicyComparison.evaluate_claim(
            self._blocks("adaptive", significant_beta=True),
            self._held_out("adaptive"))
        assert claim["claim_ready"]
        assert "C >" in claim["verdict"]

    def test_cost_aware_candidate_evaluated_by_label(self) -> None:
        claim = PolicyComparison.evaluate_claim(
            self._blocks("adaptive-cost-aware", significant_beta=True),
            self._held_out("adaptive-cost-aware"),
            candidate="adaptive-cost-aware")
        assert claim["claim_ready"]
        assert "adaptive-cost-aware >" in claim["verdict"]

    def test_cost_aware_claim_refused_when_beta_not_significant(self) -> None:
        claim = PolicyComparison.evaluate_claim(
            self._blocks("adaptive-cost-aware", significant_beta=False),
            self._held_out("adaptive-cost-aware"),
            candidate="adaptive-cost-aware")
        assert not claim["claim_ready"]
        assert any("adaptive-cost-aware>B" in part
                   for part in claim["verdict"].split(": ", 1)[-1].
                   split("; "))


class TestEndToEndV2Config:
    def test_full_run_produces_all_protocol_231_artifacts(
            self, tmp_path) -> None:
        cfg = ExperimentConfig(
            experiment_id="protocol-231-smoke",
            trials=2,
            episodes_per_trial=2,
            prior_attempts_per_family=10,
            arms=("static", "knowledge-informed", "adaptive",
                  "adaptive-cost-aware", "knowledge-informed-cost-rank",
                  "random"),
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

        for arm in cfg.arms:
            assert (d / "conditions" / arm / "raw-results.jsonl").exists()
            assert (d / "conditions" / arm
                    / "operator-selections.jsonl").exists()
        assert (d / "conditions" / "c-plus-permuted"
                / "raw-results.jsonl").exists()
        stats_data = json.loads((d / "statistics.json").read_text())
        for arm in (*cfg.arms, "c-plus-permuted"):
            assert arm in stats_data["per_condition"]
        manifest = json.loads((d / "manifest.json").read_text())
        assert manifest["policy_versions"]["adaptive-cost-aware"] == "1.0.0"
        assert (manifest["policy_versions"]
                ["knowledge-informed-cost-rank"]) == "1.0.0"
        proto = json.loads((d / "protocol.json").read_text())
        cand_pairs = [p for p in proto["primary_comparisons"]
                      if p["candidate"] == "adaptive-cost-aware"]
        assert len(cand_pairs) == 4
        assert PolicyComparison.verify_reproducibility(d, cfg)["reproducible"]
