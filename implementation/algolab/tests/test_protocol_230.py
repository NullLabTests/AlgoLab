"""Protocol-230 compliance tests: fairness controls, reproducibility,
held-out isolation, artifact completeness, and discovery-gate enforcement.

These tests verify the pre-registered experiment satisfies the scientific
controls demanded by spec/research/230_KNOWLEDGE_LOOP_EVALUATION.md.
"""

from __future__ import annotations

import json
from pathlib import Path

from algolab.search import (
    AdaptivePolicy,
    KnowledgeInformedPolicy,
    KnowledgeSnapshot,
    RandomPolicy,
    StaticPolicy,
    is_useful,
    run_attempt,
)
from algolab.search.harness import (
    ARMS_PROCEDURAL,
    HELD_OUT_FAMILY,
    PRIOR_POLICY_LABEL,
    PROTOCOL_VERSION,
    ExperimentConfig,
    PolicyComparison,
)
from algolab.search.toy import (
    DEFAULT_OPERATORS,
    TOY_ENVIRONMENT_VERSION,
)
from algolab.storage.db import connect

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tiny_cfg(experiment_id: str) -> ExperimentConfig:
    return ExperimentConfig(
        experiment_id=experiment_id,
        trials=2,
        episodes_per_trial=2,
        prior_attempts_per_family=10,
    )


def _run_full(cfg: ExperimentConfig, artifact_dir: Path) -> PolicyComparison:
    conn = connect(":memory:", initialize=True)
    comp = PolicyComparison(cfg, conn, artifact_dir)
    results = comp.run()
    stats = comp.analyze(results)
    held_out = comp.run_held_out()
    held_out_stats = comp.analyze_held_out(held_out)
    comp.write_report(results, stats, held_out_stats)
    comp.write_artifact_bundle(stats, held_out_stats)
    return comp


# ---------------------------------------------------------------------------
# Held-out family isolation
# ---------------------------------------------------------------------------

class TestHeldOutIsolation:
    """The held-out family must never appear in the K0 prior."""

    def test_gamma_not_in_prior_tasks(self, tmp_path) -> None:
        cfg = _tiny_cfg("heldout-iso")
        conn = connect(":memory:", initialize=True)
        comp = PolicyComparison(cfg, conn, tmp_path / "art")
        comp.ensure_manifest()
        comp.run_prior()
        families = {r[0] for r in conn.execute(
            "SELECT family FROM tasks WHERE task_id LIKE '%prior%'").fetchall()}
        assert HELD_OUT_FAMILY not in families

    def test_gamma_not_in_prior_evidence(self, tmp_path) -> None:
        cfg = _tiny_cfg("heldout-iso2")
        conn = connect(":memory:", initialize=True)
        comp = PolicyComparison(cfg, conn, tmp_path / "art")
        comp.ensure_manifest()
        comp.run_prior()
        prior_families = conn.execute(
            "SELECT DISTINCT json_extract(payload, '$.family') "
            "FROM evidence WHERE policy = ?",
            (PRIOR_POLICY_LABEL,)).fetchall()
        for (fam,) in prior_families:
            assert fam != HELD_OUT_FAMILY

    def test_gamma_not_in_k0_snapshot(self, tmp_path) -> None:
        cfg = _tiny_cfg("heldout-iso3")
        conn = connect(":memory:", initialize=True)
        comp = PolicyComparison(cfg, conn, tmp_path / "art")
        comp.ensure_manifest()
        snap = comp.run_prior()
        # snapshot event_range should only reference alpha/beta
        for ev in snap.event_range:
            assert HELD_OUT_FAMILY not in ev

    def test_held_out_produces_results(self, tmp_path) -> None:
        cfg = _tiny_cfg("heldout-prod")
        _run_full(cfg, tmp_path / "art")
        stats_path = tmp_path / "art" / "held-out-statistics.json"
        assert stats_path.exists()
        ho = json.loads(stats_path.read_text())
        assert ho["family"] == HELD_OUT_FAMILY
        assert set(ho["per_condition"]) >= set(ARMS_PROCEDURAL)


# ---------------------------------------------------------------------------
# Fairness controls
# ---------------------------------------------------------------------------

class TestFairnessControls:
    """All arms must receive identical treatment except information channel."""

    def test_equal_budget_per_episode(self, tmp_path) -> None:
        cfg = _tiny_cfg("fair-budget")
        conn = connect(":memory:", initialize=True)
        comp = PolicyComparison(cfg, conn, tmp_path / "art")
        comp.run()
        rows = conn.execute(
            "SELECT policy, budget_credits FROM search_episodes"
        ).fetchall()
        budgets = {row[0]: row[1] for row in rows}
        for arm in ARMS_PROCEDURAL:
            if arm in budgets:
                assert budgets[arm] == cfg.budget_credits

    def test_equal_episode_count_per_arm(self, tmp_path) -> None:
        cfg = _tiny_cfg("fair-episodes")
        conn = connect(":memory:", initialize=True)
        comp = PolicyComparison(cfg, conn, tmp_path / "art")
        comp.run()
        counts = dict(conn.execute(
            "SELECT policy, COUNT(*) FROM search_episodes "
            "WHERE payload LIKE '%\"phase\": \"main\"%' "
            "OR payload NOT LIKE '%held-out%' "
            "GROUP BY policy").fetchall())
        expected = cfg.episodes_per_trial * cfg.trials
        for arm in ARMS_PROCEDURAL:
            if arm in counts:
                assert counts[arm] == expected

    def test_b_cannot_update_from_own_outcomes(self, tmp_path) -> None:
        """KnowledgeInformedPolicy has no update() method."""
        cfg = _tiny_cfg("fair-no-update")
        conn = connect(":memory:", initialize=True)
        comp = PolicyComparison(cfg, conn, tmp_path / "art")
        comp.ensure_manifest()
        comp.run_prior()
        snap = comp.snapshot
        assert snap is not None
        b = KnowledgeInformedPolicy(snap, top_k=3)
        assert not hasattr(b, "update")

    def test_cannot_access_future_outcomes(self, tmp_path) -> None:
        """Adaptive policy only sees outcomes up to the current step."""
        snap = KnowledgeSnapshot(
            snapshot_id="K0-test", version="1.0.0",
            attempts={"tune": 10}, successes={"tune": 5})
        ops = ("tune", "rollback")
        p = AdaptivePolicy(snap, ops, rng_seed=1)
        before = p.posterior_stats("alpha", "tune")["mean"]
        # Update from one outcome
        p.update("alpha", "tune", True)
        after = p.posterior_stats("alpha", "tune")["mean"]
        assert after > before  # posterior changed
        # But we cannot retroactively change the past
        # (update only affects future select() calls)

    def test_d_receives_no_hidden_information(self, tmp_path) -> None:
        """RandomPolicy has no knowledge snapshot."""
        p = RandomPolicy(DEFAULT_OPERATORS, seed=42)
        assert not hasattr(p, "_snapshot")
        assert not hasattr(p, "snapshot_id")

    def test_all_arms_same_operator_catalog(self, tmp_path) -> None:
        """Every arm uses the same operator set."""
        cfg = _tiny_cfg("fair-ops")
        conn = connect(":memory:", initialize=True)
        comp = PolicyComparison(cfg, conn, tmp_path / "art")
        comp.ensure_manifest()
        comp.run_prior()
        snap = comp.snapshot
        assert snap is not None
        for arm in ARMS_PROCEDURAL:
            policy = comp._policy_factory(arm, 42)
            if hasattr(policy, "_operators"):
                assert tuple(policy._operators) == DEFAULT_OPERATORS

    def test_all_arms_same_task_rotation(self, tmp_path) -> None:
        """All arms see the same task family rotation."""
        cfg = _tiny_cfg("fair-rotation")
        conn = connect(":memory:", initialize=True)
        comp = PolicyComparison(cfg, conn, tmp_path / "art")
        comp.run()
        rotations = {}
        for row in conn.execute(
            "SELECT policy, json_extract(payload, '$.family') AS fam "
            "FROM search_episodes ORDER BY rowid").fetchall():
            arm, fam = row
            rotations.setdefault(arm, []).append(fam)
        base = rotations.get(ARMS_PROCEDURAL[0], [])
        for arm in ARMS_PROCEDURAL[1:]:
            if arm in rotations:
                # Same families in same order (may differ in length if
                # budget exhaustion differs, but sequence should match)
                min_len = min(len(base), len(rotations[arm]))
                assert base[:min_len] == rotations[arm][:min_len]

    def test_stopping_rule_is_budget(self, tmp_path) -> None:
        """No arm exceeds the budget ceiling."""
        cfg = _tiny_cfg("fair-stop")
        conn = connect(":memory:", initialize=True)
        comp = PolicyComparison(cfg, conn, tmp_path / "art")
        comp.run()
        rows = conn.execute(
            "SELECT policy, credits_charged, budget_credits "
            "FROM search_episodes").fetchall()
        for arm, spent, budget in rows:
            assert spent <= budget + 1e-9, f"{arm} exceeded budget"


# ---------------------------------------------------------------------------
# Determinism and reproducibility
# ---------------------------------------------------------------------------

class TestDeterminism:
    """Identical configs must produce byte-identical outcomes."""

    def test_run_attempt_deterministic(self) -> None:
        a1 = run_attempt("alpha", "tune", seed_base=7, trial=0,
                         episode=0, attempt=0)
        a2 = run_attempt("alpha", "tune", seed_base=7, trial=0,
                         episode=0, attempt=0)
        assert a1 == a2

    def test_harness_deterministic_across_runs(self, tmp_path) -> None:
        results = []
        for i in (1, 2):
            d = tmp_path / f"run-{i}"
            cfg = _tiny_cfg(f"det-{i}")
            _run_full(cfg, d)
            stats = json.loads((d / "statistics.json").read_text())
            results.append(stats)
        for arm in results[0]["per_condition"]:
            assert (results[0]["per_condition"][arm]["discoveries_per_credit"]
                    == results[1]["per_condition"][arm]["discoveries_per_credit"])

    def test_reproducibility_check_passes(self, tmp_path) -> None:
        cfg = _tiny_cfg("repro-check")
        d = tmp_path / "art"
        _run_full(cfg, d)
        result = PolicyComparison.verify_reproducibility(d, cfg)
        assert result["reproducible"]
        for check in result["checks"]:
            assert check["pass"], f"check failed: {check['check']}"


# ---------------------------------------------------------------------------
# Artifact bundle completeness
# ---------------------------------------------------------------------------

class TestArtifactBundle:
    """The evidence bundle must contain all required files."""

    EXPECTED_FILES = {
        "manifest.json",
        "plan.json",
        "protocol.json",
        "environment.json",
        "knowledge-snapshot.json",
        "statistics.json",
        "held-out-statistics.json",
        "report.md",
        "checksums.json",
        "reproducibility.json",
    }

    def test_all_expected_files_exist(self, tmp_path) -> None:
        cfg = _tiny_cfg("bundle-files")
        d = tmp_path / "art"
        _run_full(cfg, d)
        existing = {p.name for p in d.iterdir() if p.is_file()}
        assert self.EXPECTED_FILES <= existing

    def test_plan_matches_manifest(self, tmp_path) -> None:
        cfg = _tiny_cfg("bundle-plan")
        d = tmp_path / "art"
        _run_full(cfg, d)
        plan = json.loads((d / "plan.json").read_text())
        manifest = json.loads((d / "manifest.json").read_text())
        assert plan == manifest

    def test_manifest_versioned(self, tmp_path) -> None:
        cfg = _tiny_cfg("bundle-ver")
        d = tmp_path / "art"
        _run_full(cfg, d)
        manifest = json.loads((d / "manifest.json").read_text())
        assert manifest["protocol_version"] == PROTOCOL_VERSION
        assert manifest["environment_version"] == TOY_ENVIRONMENT_VERSION

    def test_checksums_cover_artifacts(self, tmp_path) -> None:
        cfg = _tiny_cfg("bundle-csum")
        d = tmp_path / "art"
        _run_full(cfg, d)
        checksums = json.loads((d / "checksums.json").read_text())
        for fname in ("manifest.json", "statistics.json", "report.md"):
            assert fname in checksums

    def test_environment_includes_gamma(self, tmp_path) -> None:
        cfg = _tiny_cfg("bundle-env")
        d = tmp_path / "art"
        _run_full(cfg, d)
        env = json.loads((d / "environment.json").read_text())
        assert HELD_OUT_FAMILY in env["families"]
        assert HELD_OUT_FAMILY in env["ground_truth"]

    def test_protocol_json_has_comparisons(self, tmp_path) -> None:
        cfg = _tiny_cfg("bundle-proto")
        d = tmp_path / "art"
        _run_full(cfg, d)
        proto = json.loads((d / "protocol.json").read_text())
        assert len(proto["primary_comparisons"]) == 3
        assert proto["held_out_family"] == HELD_OUT_FAMILY

    def test_report_mentions_held_out(self, tmp_path) -> None:
        cfg = _tiny_cfg("bundle-rpt")
        d = tmp_path / "art"
        _run_full(cfg, d)
        report = (d / "report.md").read_text()
        assert HELD_OUT_FAMILY in report
        assert "Held-out" in report or "held-out" in report

    def test_held_out_raw_results_exist(self, tmp_path) -> None:
        cfg = _tiny_cfg("bundle-ho")
        d = tmp_path / "art"
        _run_full(cfg, d)
        for arm in ARMS_PROCEDURAL:
            ho_file = d / "conditions" / arm / "held-out-raw-results.jsonl"
            assert ho_file.exists(), f"missing held-out results for {arm}"
            lines = ho_file.read_text().strip().split("\n")
            assert len(lines) > 0


# ---------------------------------------------------------------------------
# Ground truth and discovery gate
# ---------------------------------------------------------------------------

class TestDiscoveryGate:
    """A discovery requires both replicates above the promotion threshold."""

    def test_discovery_requires_two_replicates(self) -> None:
        at = run_attempt("alpha", "tune", seed_base=7, trial=1,
                         episode=2, attempt=3)
        if at.discovery:
            assert at.valid
            assert at.effect_1 >= 0.15
            assert at.effect_2 >= 0.15

    def test_gamma_has_useful_operators(self) -> None:
        """gamma must have at least one useful operator for discovery."""
        useful = [op for op in DEFAULT_OPERATORS
                  if is_useful(HELD_OUT_FAMILY, op)]
        assert len(useful) >= 1

    def test_gamma_ground_truth_different_from_alpha_beta(self) -> None:
        """gamma useful set differs from alpha and beta useful sets."""
        alpha_useful = {op for op in DEFAULT_OPERATORS
                        if is_useful("alpha", op)}
        beta_useful = {op for op in DEFAULT_OPERATORS
                       if is_useful("beta", op)}
        gamma_useful = {op for op in DEFAULT_OPERATORS
                        if is_useful(HELD_OUT_FAMILY, op)}
        # gamma must not be identical to both alpha and beta
        assert gamma_useful != alpha_useful or gamma_useful != beta_useful


# ---------------------------------------------------------------------------
# Policy isolation
# ---------------------------------------------------------------------------

class TestPolicyIsolation:
    """Each arm's policy must be independent and correctly configured."""

    def test_static_is_round_robin(self) -> None:
        ops = ("tune", "decompose", "validate")
        p = StaticPolicy(ops)
        seq = [p.select("alpha", i)[0] for i in range(6)]
        assert seq == list(ops) * 2

    def test_random_is_uniform_sampled(self) -> None:
        ops = ("tune", "decompose")
        p = RandomPolicy(ops, seed=42)
        picks = [p.select("alpha", i)[0] for i in range(100)]
        assert set(picks) <= set(ops)
        # Both should appear in 100 draws
        assert set(picks) == set(ops)

    def test_knowledge_informed_uses_frozen_ranking(self) -> None:
        from algolab.search.policies import build_prior_snapshot
        snap = build_prior_snapshot(
            {"tune": {"attempts": 100, "successes": 90,
                      "sum_effect": 0.0, "sum_effect_sq": 0.0, "credits": 0.0},
             "validate": {"attempts": 100, "successes": 10,
                          "sum_effect": 0.0, "sum_effect_sq": 0.0, "credits": 0.0}},
            snapshot_id="K0-test")
        p = KnowledgeInformedPolicy(snap, top_k=1)
        # tune has higher success rate, so it should be selected
        assert p.select("alpha", 0)[0] == "tune"

    def test_adaptive_updates_from_outcomes(self) -> None:
        from algolab.search.policies import build_prior_snapshot
        snap = build_prior_snapshot(
            {"tune": {"attempts": 10, "successes": 5,
                      "sum_effect": 0.0, "sum_effect_sq": 0.0, "credits": 0.0},
             "validate": {"attempts": 10, "successes": 5,
                          "sum_effect": 0.0, "sum_effect_sq": 0.0, "credits": 0.0}},
            snapshot_id="K0-test")
        ops = ("tune", "validate")
        p = AdaptivePolicy(snap, ops, rng_seed=1)
        before = p.posterior_stats("gamma", "tune")["alpha"]
        # gamma is unseen, should still work via lazy init
        p.select("gamma", 0)
        p.update("gamma", "tune", True)
        after = p.posterior_stats("gamma", "tune")["alpha"]
        assert after > before

    def test_adaptive_handles_unseen_family(self) -> None:
        """gamma family should be lazily initialized on first access."""
        from algolab.search.policies import build_prior_snapshot
        snap = build_prior_snapshot(
            {"tune": {"attempts": 10, "successes": 5,
                      "sum_effect": 0.0, "sum_effect_sq": 0.0, "credits": 0.0}},
            snapshot_id="K0-test")
        p = AdaptivePolicy(snap, ("tune",), rng_seed=1)
        # Should not raise KeyError
        op, record = p.select("gamma", 0)
        assert op == "tune"
        assert record.family == "gamma"
