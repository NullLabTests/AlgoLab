"""Protocol-239 tests: typed feature-transform substrate + powered QD eval."""

from __future__ import annotations

import json

from algolab.search import ExperimentConfig, PolicyComparison
from algolab.search import workload_transform as wt
from algolab.search.harness import resolve_workload
from algolab.storage.db import connect


class TestTransformWorkload:
    def test_deterministic_given_seeds(self) -> None:
        a1 = wt.run_attempt("beta", "log1p", seed_base=7, trial=0,
                             episode=0, attempt=0)
        a2 = wt.run_attempt("beta", "log1p", seed_base=7, trial=0,
                             episode=0, attempt=99)
        assert a1 == a2

    def test_costs_vary_and_positive(self) -> None:
        costs = wt.OPERATOR_COSTS
        assert len(costs) == 14
        assert min(costs.values()) < max(costs.values())
        for op in wt.operators():
            assert wt.operator_cost(op) > 0

    def test_gamma_isolated(self) -> None:
        a_alpha = wt.run_attempt("alpha", "log1p", seed_base=7,
                                 trial=0, episode=0, attempt=0)
        a_gamma = wt.run_attempt(wt.HELD_OUT_FAMILY, "log1p",
                                 seed_base=7, trial=0, episode=0, attempt=0)
        assert (a_alpha.effect_1, a_alpha.effect_2) != \
            (a_gamma.effect_1, a_gamma.effect_2)

    def test_view_resolution(self) -> None:
        view = resolve_workload("transform")
        assert not view.has_oracle
        assert view.held_out_family == "gamma"
        assert len(view.operators) == 14
        assert view.costs is not None

    def test_prior_phase_never_touches_gamma(self, tmp_path) -> None:
        cfg = ExperimentConfig(
            experiment_id="protocol-239-prior",
            workload="transform",
            trials=1, episodes_per_trial=2,
            prior_attempts_per_family=2, budget_credits=60.0,
            promotion_threshold=wt.DISCOVERY_MARGIN,
            arms=("static",), ablations=(),
        )
        d = tmp_path / "art"
        conn = connect(":memory:", initialize=True)
        comp = PolicyComparison(cfg, conn, d)
        comp.ensure_manifest()
        comp.run_prior()
        by_fam = json.loads(
            (d / "knowledge-snapshot-by-family.json").read_text())
        assert set(by_fam) == {"alpha", "beta"}


class TestProtocol239ComplianceSmoke:
    def test_tiny_run_produces_bundle(self, tmp_path) -> None:
        cfg = ExperimentConfig(
            experiment_id="protocol-239-smoke",
            workload="transform",
            trials=2, episodes_per_trial=2,
            prior_attempts_per_family=2, budget_credits=60.0,
            promotion_threshold=wt.DISCOVERY_MARGIN,
            arms=("static", "adaptive-cost-aware",
                  "knowledge-informed-family-commit",
                  "qd-adaptive-cost-aware", "basin-escape"),
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
        assert manifest["workload"] == "transform"
        assert manifest["policy_versions"]["qd-adaptive-cost-aware"] == "1.0.0"
        assert manifest["policy_versions"]["basin-escape"] == "1.0.0"
        qd = json.loads((d / "qd-archive.json").read_text())
        assert qd["version"] == "1.0.0"
        assert len(qd["cells"]) > 0
        env = json.loads((d / "environment.json").read_text())
        assert env["workload_metadata"]["nominal_costs_flat"] is False
        for arm in cfg.arms:
            assert (d / "conditions" / arm / "raw-results.jsonl").exists()
        assert PolicyComparison.verify_reproducibility(d, cfg)["reproducible"]
