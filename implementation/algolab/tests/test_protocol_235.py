"""Protocol-235 tests: the micro-HPO real-workload bridge.

Covers workload determinism, held-out isolation, harness indirection
(toy byte-compat is covered by test_protocol_230_golden), and an
end-to-end smoke run on the hpo workload.
"""

from __future__ import annotations

import json

from algolab.search import ExperimentConfig, PolicyComparison
from algolab.search import workload_hpo as hpo
from algolab.search.harness import resolve_workload
from algolab.storage.db import connect


class TestHpoWorkload:
    def test_deterministic_given_seeds(self) -> None:
        a1 = hpo.run_attempt("beta", "k21", seed_base=7, trial=0,
                             episode=0, attempt=0)
        a2 = hpo.run_attempt("beta", "k21", seed_base=7, trial=0,
                             episode=0, attempt=99)
        assert a1 == a2  # attempt index must not affect outcomes

    def test_gamma_isolated_from_training_families(self) -> None:
        # gamma uses a different dataset; outcomes differ from alpha/beta
        a_alpha = hpo.run_attempt("alpha", "manhattan", seed_base=7,
                                  trial=0, episode=0, attempt=0)
        a_gamma = hpo.run_attempt(hpo.HELD_OUT_FAMILY, "manhattan",
                                  seed_base=7, trial=0, episode=0, attempt=0)
        assert (a_alpha.effect_1, a_alpha.effect_2) != \
            (a_gamma.effect_1, a_gamma.effect_2)

    def test_costs_are_flat_and_positive(self) -> None:
        assert set(hpo.NOMINAL_COSTS.values()) == {10.0}
        for op in hpo.operators():
            assert hpo.operator_cost(op) > 0

    def test_view_resolution(self) -> None:
        toy = resolve_workload("toy")
        assert toy.has_oracle and toy.is_useful is not None
        view = resolve_workload("hpo")
        assert not view.has_oracle and view.is_useful is None
        assert view.ground_truth_effect is None
        assert view.held_out_family == "gamma"
        assert "manhattan" in view.operators


class TestHpoEndToEnd:
    def test_tiny_hpo_run_produces_artifacts(self, tmp_path) -> None:
        cfg = ExperimentConfig(
            experiment_id="protocol-235-smoke",
            workload="hpo",
            trials=2,
            episodes_per_trial=2,
            prior_attempts_per_family=2,
            budget_credits=60.0,
            promotion_threshold=hpo.DISCOVERY_MARGIN,
            arms=("static", "knowledge-informed", "adaptive-cost-aware",
                  "knowledge-informed-family-commit"),
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
                candidate="adaptive-cost-aware",
                held_out_family=cfg.workload_view.held_out_family))
        comp.write_report(results, stats, held_out_stats)
        comp.write_artifact_bundle(stats, held_out_stats)

        manifest = json.loads((d / "manifest.json").read_text())
        assert manifest["workload"] == "hpo"
        assert manifest["ground_truth"] is None
        env = json.loads((d / "environment.json").read_text())
        assert env["ground_truth"] is None
        assert env["workload_metadata"]["base_estimator"] == \
            "StandardScaler->KNeighborsClassifier"
        stats_data = json.loads((d / "statistics.json").read_text())
        assert set(stats_data["per_family"]) == {"alpha", "beta"}
        for arm in cfg.arms:
            assert arm in stats_data["per_condition"]
        report = (d / "report.md").read_text()
        assert "held-out" in report
        assert PolicyComparison.verify_reproducibility(d, cfg)["reproducible"]

    def test_prior_phase_never_touches_gamma(self, tmp_path) -> None:
        cfg = ExperimentConfig(
            experiment_id="protocol-235-prior",
            workload="hpo",
            trials=1,
            episodes_per_trial=2,
            prior_attempts_per_family=2,
            budget_credits=60.0,
            promotion_threshold=hpo.DISCOVERY_MARGIN,
            arms=("static",),
            ablations=(),
        )
        d = tmp_path / "art"
        conn = connect(":memory:", initialize=True)
        comp = PolicyComparison(cfg, conn, d)
        comp.ensure_manifest()
        comp.run_prior()
        by_fam = json.loads(
            (d / "knowledge-snapshot-by-family.json").read_text())
        assert set(by_fam) == {"alpha", "beta"}
        snap = json.loads((d / "knowledge-snapshot.json").read_text())
        for ev in snap["event_range"]:
            assert "gamma" not in ev
