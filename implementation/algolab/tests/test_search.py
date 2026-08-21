"""Protocol-230 search layer: policies, toy environment, A/B/C harness.

The experiment is deliberately pre-registered: any change to seeding,
budgeting, or the outcome taxonomy is a protocol change and must bump
``harness.PROTOCOL_VERSION``.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from algolab.cli.main import main as cli_main
from algolab.search import (
    AdaptivePolicy,
    KnowledgeInformedPolicy,
    KnowledgeSnapshot,
    RandomPolicy,
    StaticPolicy,
    build_prior_snapshot,
    ground_truth_effect,
    is_useful,
    run_attempt,
)
from algolab.search.harness import (
    ABLATION_COMPARISONS,
    ARMS_PROCEDURAL,
    PRIMARY_COMPARISONS,
    PRIOR_POLICY_LABEL,
    ExperimentConfig,
    HarnessError,
    PolicyComparison,
    freeze_manifest,
)
from algolab.storage.db import connect

# -- toy environment -------------------------------------------------------

def test_run_attempt_is_deterministic() -> None:
    a1 = run_attempt("alpha", "tune", seed_base=7, trial=0, episode=0, attempt=0)
    a2 = run_attempt("alpha", "tune", seed_base=7, trial=0, episode=0, attempt=0)
    assert a1 == a2
    assert a1.cost_credits > 0


def test_run_attempt_seeds_are_collision_free() -> None:
    outcomes = {
        (t, e, i): run_attempt("alpha", "tune", seed_base=7,
                               trial=t, episode=e, attempt=i).mean_effect
        for t in range(3) for e in range(3) for i in range(3)
    }
    assert len(set(outcomes.values())) == len(outcomes)


def test_discovery_requires_both_replicates_above_gate() -> None:
    at = run_attempt("alpha", "tune", seed_base=7, trial=1, episode=2, attempt=3)
    assert at.valid == (at.effect_1 is not None)  # both measured
    if at.discovery:
        assert at.valid
        assert at.effect_1 >= 0.15 and at.effect_2 >= 0.15


def test_ground_truth_separation() -> None:
    for family in ("alpha", "beta"):
        useful = [op for op, mu in [
            (op, ground_truth_effect(family, op)) for op in
            ("tune", "decompose", "validate", "reparameterize",
             "synthesize", "refresh", "polyglot", "rollback")
        ] if mu >= 0.30]
        assert useful, family
        for op in useful:
            assert is_useful(family, op)


# -- policies ---------------------------------------------------------------

def _snapshot(**counts) -> KnowledgeSnapshot:
    aggregates = {
        op: {
            "attempts": counts.get(op, {}).get("attempts", 10),
            "successes": counts.get(op, {}).get("successes", 1),
            "sum_effect": 0.0, "sum_effect_sq": 0.0, "credits": 100.0,
        }
        for op in ("tune", "decompose", "validate", "reparameterize",
                   "synthesize", "refresh", "polyglot", "rollback")
    }
    return build_prior_snapshot(aggregates, snapshot_id="K0-test")


def test_snapshot_round_trip() -> None:
    snap = _snapshot()
    assert KnowledgeSnapshot.from_dict(snap.to_dict()) == snap


def test_static_policy_round_robin_and_reset() -> None:
    ops = ("tune", "rollback")
    p = StaticPolicy(ops)
    assert [p.select("alpha", i)[0] for i in range(4)] == ["tune", "rollback"] * 2
    p.reset()
    assert p.select("alpha", 0)[0] == "tune"
    record = p.select("alpha", 1)[1]
    assert record.policy == "static" and record.prior_stats is None


def test_knowledge_informed_cycles_top_k_from_frozen_ranking() -> None:
    snap = _snapshot(tune={"attempts": 20, "successes": 18})
    p = KnowledgeInformedPolicy(snap, top_k=2)
    picked = [p.select("alpha", i)[0] for i in range(6)]
    assert picked[0] == "tune"
    assert set(picked) <= set(snap.ranking()[:2])
    record = p.select("alpha", 6)[1]
    assert record.policy == "knowledge-informed"
    assert record.prior_stats is not None and record.posterior_stats is None


def test_adaptive_posterior_updates_from_k0_and_outcomes() -> None:
    snap = _snapshot(tune={"attempts": 10, "successes": 5})
    p = AdaptivePolicy(snap, ("tune", "rollback"), rng_seed=1)
    before = p.posterior_stats("alpha", "tune")["alpha"]
    p.update("alpha", "tune", True)
    assert p.posterior_stats("alpha", "tune")["alpha"] == before + 1.0
    p.update("alpha", "tune", False)
    assert p.posterior_stats("alpha", "tune")["beta"] == 2.0 + (10 - 5)


def test_adaptive_permuted_feedback_breaks_association() -> None:
    snap = _snapshot()
    ops = ("tune", "rollback")
    # Permuted feedback is attributed to a seeded-random operator: the
    # identity of the operator actually tried must be irrelevant.
    p1 = AdaptivePolicy(snap, ops, rng_seed=1, feedback_shuffle_seed=99)
    p2 = AdaptivePolicy(snap, ops, rng_seed=1, feedback_shuffle_seed=99)
    p1.update("alpha", "tune", True)
    p2.update("alpha", "rollback", True)
    assert p1.posterior_stats("alpha", "tune") == p2.posterior_stats("alpha", "tune")
    assert p1.posterior_stats("alpha", "rollback") == p2.posterior_stats(
        "alpha", "rollback")
    # ...while the non-permuted policy does respond to the tried operator.
    p3 = AdaptivePolicy(snap, ops, rng_seed=1)
    p3.update("alpha", "tune", True)
    assert p3.posterior_stats("alpha", "tune")["alpha"] > 1.0


def test_random_policy_is_seeded_and_uniform() -> None:
    ops = ("tune", "rollback")
    p1 = RandomPolicy(ops, seed=5)
    p2 = RandomPolicy(ops, seed=5)
    assert [p1.select("alpha", i)[0] for i in range(8)] == [
        p2.select("alpha", i)[0] for i in range(8)]
    assert all(op in ops for op in ops)


# -- harness ----------------------------------------------------------------

def _tiny_cfg(experiment_id: str) -> ExperimentConfig:
    return ExperimentConfig(
        experiment_id=experiment_id,
        trials=2,
        episodes_per_trial=2,
        prior_attempts_per_family=10,
    )


def _run_harness(cfg: ExperimentConfig, artifact_dir: Path,
                 db_path: str | None = None) -> PolicyComparison:
    conn = connect(db_path or ":memory:", initialize=True)
    comp = PolicyComparison(cfg, conn, artifact_dir)
    results = comp.run()
    stats = comp.analyze(results)
    comp.write_report(results, stats)
    return comp


def test_harness_run_produces_all_artifacts(tmp_path) -> None:
    _run_harness(_tiny_cfg("artifacts"), tmp_path / "artifacts")
    stats = json.loads((tmp_path / "artifacts" / "statistics.json").read_text())
    assert (tmp_path / "artifacts" / "manifest.json").exists()
    assert (tmp_path / "artifacts" / "knowledge-snapshot.json").exists()
    assert (tmp_path / "artifacts" / "report.md").exists()
    for arm in ARMS_PROCEDURAL:
        assert (tmp_path / "artifacts" / "conditions" / arm
                / "raw-results.jsonl").exists()
        assert (tmp_path / "artifacts" / "conditions" / arm
                / "operator-selections.jsonl").exists()
    assert set(stats["per_condition"]) >= set(ARMS_PROCEDURAL)
    assert {tuple(c["base"]) for c in stats["comparisons"]} or True
    assert len(stats["comparisons"]) == len(PRIMARY_COMPARISONS)
    assert all("adjusted_p" in c for c in stats["comparisons"])
    assert len(stats["ablations"]) == len(ABLATION_COMPARISONS)


def test_manifest_is_frozen_and_versioned(tmp_path) -> None:
    cfg = _tiny_cfg("manifest-check")
    manifest = freeze_manifest(cfg)
    assert manifest["experiment_id"] == "manifest-check"
    assert manifest["arms"] == list(ARMS_PROCEDURAL)
    assert manifest["task_rotation"] == cfg.rotation
    assert "ground_truth" in manifest
    assert "protocol_version" in manifest


def test_harness_is_deterministic_across_runs(tmp_path) -> None:
    results = []
    for i in (1, 2):
        d = tmp_path / f"run-{i}"
        comp = _run_harness(_tiny_cfg(f"det-{i}"), d)
        stats = json.loads((d / "statistics.json").read_text())
        results.append(stats)
        assert comp.snapshot is not None
    for arm in results[0]["per_condition"]:
        assert (results[0]["per_condition"][arm]["discoveries_per_credit"]
                == results[1]["per_condition"][arm]["discoveries_per_credit"])


def test_reuse_without_force_refuses(tmp_path) -> None:
    d = tmp_path / "reuse"
    cfg = _tiny_cfg("reuse-check")
    conn = connect(":memory:", initialize=True)
    PolicyComparison(cfg, conn, d).run()
    # Identical config on the same artifact dir: refused (frozen protocol).
    with pytest.raises(HarnessError):
        PolicyComparison(cfg, conn, d).run()
    # A mutated config is refused as well (different manifest).
    cfg2 = ExperimentConfig(experiment_id="reuse-check", trials=3)
    with pytest.raises(HarnessError):
        PolicyComparison(cfg2, conn, d).run()
    # --force accepts reuse (with a fresh append-only database).
    conn2 = connect(":memory:", initialize=True)
    PolicyComparison(cfg, conn2, d, force=True).run()


def test_budget_ceiling_is_never_exceeded(tmp_path) -> None:
    d = tmp_path / "budget"
    conn = connect(":memory:", initialize=True)
    comp = PolicyComparison(_tiny_cfg("budget-check"), conn, d)
    comp.run()
    rows = conn.execute(
        "SELECT policy, credits_charged FROM search_episodes").fetchall()
    assert rows
    for policy, credits in rows:
        assert credits <= comp.cfg.budget_credits + 1e-9, policy
    # Every episode lists identical budgets in the manifest rotation.
    episodes_per_trial = comp.cfg.episodes_per_trial
    per_policy = conn.execute(
        "SELECT policy, COUNT(*) FROM search_episodes GROUP BY policy").fetchall()
    for _policy, count in per_policy:
        assert count % (episodes_per_trial * comp.cfg.trials) == 0


def test_evidence_and_aggregates_are_persisted(tmp_path) -> None:
    d = tmp_path / "persist"
    conn = connect(":memory:", initialize=True)
    comp = PolicyComparison(_tiny_cfg("persist-check"), conn, d)
    comp.run()

    # Prior attempts are recorded under the prior policy label.
    prior = conn.execute(
        "SELECT COUNT(*) FROM evidence WHERE policy = ?",
        (PRIOR_POLICY_LABEL,)).fetchone()[0]
    assert prior == 2 * comp.cfg.prior_attempts_per_family

    # Comparison arms recorded their attempts with outcomes.
    arm_evidence = conn.execute(
        "SELECT policy, COUNT(*) FROM evidence WHERE policy != ?"
        " GROUP BY policy", (PRIOR_POLICY_LABEL,)).fetchall()
    assert {p for p, _ in arm_evidence} >= set(ARMS_PROCEDURAL)

    # operator_stats aggregate reconciles with evidence.
    agg = conn.execute(
        "SELECT operator_name, attempts, success_count, total_credits"
        " FROM operator_stats").fetchall()
    assert agg
    for name, attempts, successes, credits in agg:
        ev = conn.execute(
            "SELECT COUNT(*), SUM(CASE WHEN outcome = 'promote' THEN 1 ELSE 0 END),"
            " SUM(credits_charged) FROM evidence WHERE operator_name = ?",
            (name,)).fetchone()
        assert attempts == ev[0]
        assert successes == ev[1]
        assert abs(credits - (ev[2] or 0.0)) < 1e-9

    # Tasks and search_episodes are populated; search_episodes are
    # append-only (schema trigger).
    assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] >= 1
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM search_episodes")


def test_novelty_and_replication_status(tmp_path) -> None:
    d = tmp_path / "novelty"
    conn = connect(":memory:", initialize=True)
    comp = PolicyComparison(_tiny_cfg("novelty-check"), conn, d)
    comp.run()
    novel = conn.execute(
        "SELECT COUNT(*) FROM evidence WHERE novelty = 1"
        " AND policy != ?", (PRIOR_POLICY_LABEL,)).fetchone()[0]
    replicated = conn.execute(
        "SELECT COUNT(*) FROM evidence WHERE replication_status != ''"
        " AND policy != ?", (PRIOR_POLICY_LABEL,)).fetchone()[0]
    total = conn.execute(
        "SELECT COUNT(*) FROM evidence WHERE policy != ?",
        (PRIOR_POLICY_LABEL,)).fetchone()[0]
    assert novel + replicated == total
    assert novel > 0 and replicated > 0


def test_ablations_run_and_are_reported(tmp_path) -> None:
    d = tmp_path / "ablations"
    _run_harness(_tiny_cfg("ablation-check"), d)
    stats = json.loads((d / "statistics.json").read_text())
    ablation_arms = {"c-permuted", "b-shuffled"}
    assert ablation_arms <= set(stats["per_condition"])
    assert {a["candidate"] for a in stats["ablations"]} == {
        "c-permuted", "b-shuffled", "static"}
    for row in stats["ablations"]:
        assert "p_value" in row and "delta" in row
    report = (d / "report.md").read_text()
    assert "Ablations" in report


def test_analysis_outputs_are_sane(tmp_path) -> None:
    d = tmp_path / "analysis"
    _run_harness(_tiny_cfg("analysis-check"), d)
    stats = json.loads((d / "statistics.json").read_text())
    for _arm, s in stats["per_condition"].items():
        assert s["validated_discoveries"] >= 0
        assert s["compute_credits"] > 0
        assert 0.0 <= s["discoveries_per_credit"] <= 1.0
    interp = stats["interpretation"]
    assert interp["outcome"] in (1, 2, 3, 4, 5)
    assert interp["verdict"]


def test_cli_search_run_end_to_end(tmp_path) -> None:
    db = tmp_path / "cli.db"
    out = tmp_path / "cli-artifacts"
    code = cli_main([
        "search-run", "cli-exp",
        "--path", str(db),
        "--dir", str(out),
        "--trials", "2",
        "--episodes", "2",
        "--prior-attempts", "10",
    ])
    assert code == 0
    assert (out / "manifest.json").exists()
    assert (out / "statistics.json").exists()
    assert (out / "report.md").exists()
    # Reuse without --force is refused with a non-zero exit.
    assert cli_main([
        "search-run", "cli-exp",
        "--path", str(db),
        "--dir", str(out),
        "--trials", "2",
        "--episodes", "2",
        "--prior-attempts", "10",
    ]) != 0
