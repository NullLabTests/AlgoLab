"""Protocol-236 tests (library phase): rules library + frozen substrate.

Phase 1 (library extraction, canonical): the knowledge-loop discovery gate
is a reusable, substrate-agnostic rules library (``algolab.search.rules``).
All families keep the byte-frozen protocol-235-v1 metric — an absolute
CV-accuracy improvement of 0.005 per replicate seed on *every* family,
235-v1 byte-identical, discovery-gate version unfrozen at 1.0.0. Protocol
236 re-scopes to the S2 substrate (phase 2); its workload contract and
margins are registered separately in the S2 module.
"""

from __future__ import annotations

import json

import pytest

from algolab.search import ExperimentConfig, PolicyComparison
from algolab.search import rules as rl
from algolab.search import workload_hpo as hpo
from algolab.search.harness import resolve_workload
from algolab.storage.db import connect


class TestRulesLibrary:
    """Phase-1 deliverable: reusable, deterministic, sklearn-free gate rules."""

    def test_public_surface_and_versions(self) -> None:
        assert rl.DECISION_RULE_LIBRARY_VERSION == "1.0.0"
        assert rl.PRIOR_FACTOR_LIBRARY_VERSION == "1.0.0"
        assert rl.SELECTOR_OBJECTIVE_LIBRARY_VERSION == "1.0.0"
        for name in ("DecisionRuleSpec", "FamilyMarginTable", "PriorFactorPlan",
                     "SelectorObjectiveSpec", "normalize_success_per_credit",
                     "phrase_discovery_gate"):
            assert hasattr(rl, name)

    def test_family_margins_byte_frozen(self) -> None:
        # All families resolve to the registered 235-v1 margin (0.005): no
        # alpha recalibration exists in the canonical re-scope.
        table = rl.FamilyMarginTable(
            default_margin=hpo.DISCOVERY_MARGIN,
            margins={},
        )
        for fam in ("alpha", "beta", "gamma"):
            assert table.for_family(fam) == pytest.approx(0.005)

    def test_normalize_success_per_credit_math(self) -> None:
        # 4 successes out of 8 attempts, flat 10.0 cost => 0.05 success/credit.
        assert rl.normalize_success_per_credit(4.0, 8.0, 10.0) == \
            pytest.approx(0.05)
        # Zero-attempt / zero-credit guards are stable (no div-by-zero).
        assert rl.normalize_success_per_credit(0.0, 0.0, 10.0) == 0.0


class TestSubstrateFrozen:
    def test_hpo_workload_still_1_1_0_metrics_0_005(self) -> None:
        assert hpo.HPO_WORKLOAD_VERSION == "1.1.0"
        assert hpo.HPO_TASK_SUITE_VERSION == "1.1.0"
        assert hpo.DISCOVERY_MARGIN == 0.005
        view = resolve_workload("hpo")
        assert view.environment_version == "1.1.0"
        assert view.task_suite_version == "1.1.0"
        assert view.discovery_gate_version == "1.0.0"

    def test_deterministic_given_seeds(self) -> None:
        a1 = hpo.run_attempt("alpha", "k1", seed_base=7, trial=0,
                             episode=0, attempt=0)
        a2 = hpo.run_attempt("alpha", "k1", seed_base=7, trial=0,
                             episode=0, attempt=5)
        assert a1 == a2  # attempt index must not affect outcomes

    def test_discovery_gate_resolution_requires_both_hyps(self) -> None:
        # A threshold beyond any plausible effect must suppress discovery
        # on every family (the gate is uniform and byte-frozen).
        for fam in ("alpha", "beta", "gamma"):
            a = hpo.run_attempt(fam, "k21", seed_base=7, trial=0,
                                episode=0, attempt=0, threshold=1.0)
            assert a.discovery is False


class TestHpoEndToEnd:
    def test_tiny_hpo_run_produces_artifacts(self, tmp_path) -> None:
        cfg = ExperimentConfig(
            experiment_id="protocol-236-smoke",
            workload="hpo",
            trials=2,
            episodes_per_trial=2,
            prior_attempts_per_family=2,
            budget_credits=60.0,
            promotion_threshold=hpo.DISCOVERY_MARGIN,
            arms=("static", "adaptive-cost-aware"),
            ablations=(),
        )
        d = tmp_path / "art"
        conn = connect(":memory:", initialize=True)
        comp = PolicyComparison(cfg, conn, d)
        results = comp.run()
        stats = comp.analyze(results)
        held_out_stats = comp.analyze_held_out(comp.run_held_out())
        comp.write_report(results, stats, held_out_stats)
        comp.write_artifact_bundle(stats, held_out_stats)

        manifest = json.loads((d / "manifest.json").read_text())
        assert manifest["workload"] == "hpo"
        env = json.loads((d / "environment.json").read_text())
        assert env["environment_version"] == "1.1.0"
        stats_data = json.loads((d / "statistics.json").read_text())
        assert set(stats_data["per_family"]) == {"alpha", "beta"}
