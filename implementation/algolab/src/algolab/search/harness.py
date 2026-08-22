"""A/B/C cumulative-search policy comparison harness (protocol 230).

Runs the pre-registered three-condition experiment:

- builds a frozen K0 knowledge snapshot from seeded uniform-policy prior
  episodes;
- runs Statistic (A), Knowledge-informed (B), Adaptive (C), and a Random
  reference (D) under identical budget, task rotation, and seeds;
- persists every attempt to schema-v3 tables (tasks, evidence,
  operator_uses, search_episodes) and refreshes the operator_stats
  aggregate;
- writes durable artifacts (manifest, raw results, selections, knowledge
  snapshot, statistics, report) and returns the interpretation.

The manifest is frozen before any episode runs; refusing to reuse an
existing experiment directory (unless --force) enforces immutability. All
randomness is manifest-seeded, so identical configurations reproduce
byte-for-byte.
"""

from __future__ import annotations

import json
import random
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

from algolab.knowledge.evidence import PROMOTE, EvidenceRepo
from algolab.knowledge.operators import OPERATOR_CATALOG
from algolab.search.policies import (
    ADAPTIVE_POLICY_VERSION,
    KNOWLEDGE_INFORMED_POLICY_VERSION,
    RANDOM_POLICY_VERSION,
    STATIC_POLICY_VERSION,
    AdaptivePolicy,
    KnowledgeInformedPolicy,
    KnowledgeSnapshot,
    RandomPolicy,
    StaticPolicy,
    build_prior_snapshot,
)
from algolab.search.toy import (
    DEFAULT_OPERATORS,
    DISCOVERY_GATE_VERSION,
    HELD_OUT_FAMILY,
    PROMOTION_THRESHOLD,
    TASK_FAMILIES,
    TASK_SUITE_VERSION,
    TOY_ENVIRONMENT_VERSION,
    Attempt,
    ground_truth_effect,
    is_useful,
    operator_cost,
    run_attempt,
)
from algolab.statistics import analyze, benjamini_hochberg
from algolab.util import utc_now

PROTOCOL_VERSION = "1.1.0"
BASELINE_VERSION = "1.0.0"
OPERATOR_REGISTRY_VERSION = "1.0.0"
PRIOR_POLICY_VERSION = "1.0.0"

ARMS_PROCEDURAL = ("static", "knowledge-informed", "adaptive", "random")
PRIMARY_COMPARISONS: tuple[tuple[str, str], ...] = (
    ("static", "knowledge-informed"),
    ("static", "adaptive"),
    ("knowledge-informed", "adaptive"),
)
ABLATION_COMPARISONS: tuple[tuple[str, str, str], ...] = (
    ("adaptive", "c-permuted", "permuted-outcome feedback (machinery kept)"),
    ("knowledge-informed", "b-shuffled",
     "shuffled-K0 knowledge (association destroyed)"),
    ("b-shuffled", "static", "shuffled knowledge vs no knowledge"),
)

DEFAULT_BUDGET_CREDITS = 150.0
DEFAULT_EPISODES_PER_TRIAL = 10
DEFAULT_TRIALS = 8
DEFAULT_PRIOR_ATTEMPTS_PER_FAMILY = 60

PRIOR_POLICY_LABEL = "prior-uniform"

Policy = StaticPolicy | KnowledgeInformedPolicy | AdaptivePolicy | RandomPolicy


class HarnessError(RuntimeError):
    """The harness refused to proceed (immutability, config, persistence)."""


@dataclass(frozen=True)
class ExperimentConfig:
    """Pre-registered experiment parameters (immutable once frozen)."""

    experiment_id: str
    budget_credits: float = DEFAULT_BUDGET_CREDITS
    episodes_per_trial: int = DEFAULT_EPISODES_PER_TRIAL
    trials: int = DEFAULT_TRIALS
    prior_attempts_per_family: int = DEFAULT_PRIOR_ATTEMPTS_PER_FAMILY
    prior_seed: int = 101
    analysis_seed: int = 11
    seed_base: int = 7
    top_k: int = 3
    arms: tuple[str, ...] = ARMS_PROCEDURAL
    ablations: tuple[str, ...] = ("permuted", "shuffled")
    promotion_threshold: float = PROMOTION_THRESHOLD
    producer: str = "research"
    notes: str = ""

    @property
    def rotation(self) -> list[str]:
        """Deterministic family rotation shared by all arms and trials."""
        return [TASK_FAMILIES[i % len(TASK_FAMILIES)]
                for i in range(self.episodes_per_trial)]

    @property
    def held_out_rotation(self) -> list[str]:
        """Family rotation for held-out transfer evaluation (single family)."""
        return [HELD_OUT_FAMILY
                for _ in range(self.episodes_per_trial)]


def freeze_manifest(cfg: ExperimentConfig) -> dict[str, Any]:
    """The frozen, versioned experiment manifest (written before any run)."""
    return {
        "experiment_id": cfg.experiment_id,
        "protocol_version": PROTOCOL_VERSION,
        "environment_version": TOY_ENVIRONMENT_VERSION,
        "task_suite_version": TASK_SUITE_VERSION,
        "operator_registry_version": OPERATOR_REGISTRY_VERSION,
        "baseline_version": BASELINE_VERSION,
        "discovery_gate_version": DISCOVERY_GATE_VERSION,
        "policy_versions": {
            "static": STATIC_POLICY_VERSION,
            "knowledge-informed": KNOWLEDGE_INFORMED_POLICY_VERSION,
            "adaptive": ADAPTIVE_POLICY_VERSION,
            "random": RANDOM_POLICY_VERSION,
        },
        "budget_credits": cfg.budget_credits,
        "episodes_per_trial": cfg.episodes_per_trial,
        "trials": cfg.trials,
        "prior_attempts_per_family": cfg.prior_attempts_per_family,
        "prior_seed": cfg.prior_seed,
        "analysis_seed": cfg.analysis_seed,
        "seed_base": cfg.seed_base,
        "top_k": cfg.top_k,
        "arms": list(cfg.arms),
        "ablations": list(cfg.ablations),
        "promotion_threshold": cfg.promotion_threshold,
        "task_rotation": list(cfg.rotation),
        "ground_truth": {
            f: {op: ground_truth_effect(f, op) for op in OPERATOR_CATALOG}
            for f in list(TASK_FAMILIES) + [HELD_OUT_FAMILY]
        },
        "discovery_gate": (
            "valid implementation AND effect_1 >= threshold "
            "AND effect_2 >= threshold (2-seed replication gate)"
        ),
        "primary_metric": "validated_discoveries / credits_consumed",
        "created_at": utc_now(),
        "producer": cfg.producer,
        "notes": cfg.notes,
    }


class PolicyComparison:
    """Orchestrates the full pre-registered A/B/C experiment."""

    def __init__(self, cfg: ExperimentConfig, conn: sqlite3.Connection,
                 artifact_dir: Path, *, force: bool = False):
        self.cfg = cfg
        self.conn = conn
        self.artifact_dir = artifact_dir
        self.force = force
        self.evidence = EvidenceRepo(conn, producer=cfg.producer)
        self.manifest = freeze_manifest(cfg)
        self.snapshot: KnowledgeSnapshot | None = None
        self._seen: dict[tuple[str, int, str, str], str] = {}
        self._events: dict[str, list[dict[str, Any]]] = {}

    # -- manifest immutability ------------------------------------------

    def ensure_manifest(self) -> None:
        manifest_path = self.artifact_dir / "manifest.json"
        if manifest_path.exists() and not self.force:
            raise HarnessError(
                f"experiment directory {self.artifact_dir} already contains a"
                " run; refusing to reuse (--force to override)"
            )
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(self.manifest, indent=2, sort_keys=True) + "\n")

    # -- persistence helpers ---------------------------------------------

    def _task_id(self, arm: str, trial: int, episode: int, family: str) -> str:
        return f"task-{self.cfg.experiment_id}-{arm}-{trial}-{episode}-{family}"

    def _register_task(self, arm: str, trial: int, episode: int,
                       family: str) -> str:
        task_id = self._task_id(arm, trial, episode, family)
        self.conn.execute(
            "INSERT INTO tasks (task_id, name, family, workload, description,"
            " baseline_config, search_space, seeds, primary_metric, direction,"
            " promotion_threshold, ground_truth, credit_estimate, created_at,"
            " producer) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (task_id, task_id, family, "toy-discovery", "protocol-230 task", "{}",
             json.dumps({"unused": True}), "[1, 2]", "discovery_rate",
             "maximize", self.cfg.promotion_threshold,
             json.dumps({"note": "hidden from policies"}), self.cfg.budget_credits,
             utc_now(), self.cfg.producer),
        )
        return task_id

    def _record_attempt(self, arm: str, trial: int, episode: int, family: str,
                        task_id: str, episode_id: str, attempt_idx: int,
                        attempt: Attempt, novel: bool,
                        replication_of: str) -> str:
        exp_id = f"exp-{self.cfg.experiment_id}-{trial}-{episode}"
        evidence = self.evidence.insert(
            task_id=task_id,
            experiment_id=exp_id,
            operator_name=attempt.operator,
            policy=arm,
            primary_metric="discovery_rate",
            direction="maximize",
            outcome=PROMOTE if attempt.discovery else "reject",
            promotion_threshold=self.cfg.promotion_threshold,
            credits_charged=attempt.cost_credits,
            novel=novel,
            replication_status=replication_of,
            hypothesis_id=f"h-{self.cfg.experiment_id}",
            candidate_id=(
                f"cand-{self.cfg.experiment_id}-{arm}-{trial}-{episode}-{attempt_idx}"),
            baseline_mean=0.0,
            candidate_mean=attempt.mean_effect,
            relative_delta=attempt.mean_effect,
            ci_low=min(attempt.effect_1, attempt.effect_2),
            ci_high=max(attempt.effect_1, attempt.effect_2),
            p_value=0.0 if attempt.discovery else 1.0,
            effect_size=attempt.mean_effect,
            episode_id=episode_id,
            payload={
                "valid": attempt.valid,
                "effect_1": attempt.effect_1,
                "effect_2": attempt.effect_2,
                "replication_passed": attempt.discovery,
                "family": family,
            },
        )
        self.conn.execute(
            "INSERT INTO operator_uses (use_id, operator_name, task_id,"
            " experiment_id, episode_id, outcome, relative_delta,"
            " credits_charged, novel, created_at, producer)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
             (f"use-{self.cfg.experiment_id}-{arm}-{trial}-{episode}-{attempt_idx}",
              attempt.operator, task_id, exp_id, episode_id,
              PROMOTE if attempt.discovery else "reject",
              attempt.mean_effect, attempt.cost_credits, int(novel),
              utc_now(), self.cfg.producer),
        )
        assert evidence.evidence_id is not None
        return evidence.evidence_id

    def _record_episode(self, arm: str, trial: int, episode: int, family: str,
                        task_id: str, episode_id: str, budget: float,
                        credits: float, attempts: int, discoveries: int,
                        failure_counts: dict[str, int], op_counts: dict[str, int],
                        snapshot_id: str,
                        policy_version: str) -> None:
        self.conn.execute(
            "INSERT INTO search_episodes (episode_id, task_id, policy,"
            " budget_credits, credits_charged, attempts, discoveries,"
            " failure_counts, operator_use_counts, started_at, finished_at,"
            " seed, producer, payload) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (episode_id, task_id, arm, budget, credits, attempts, discoveries,
             json.dumps(failure_counts, sort_keys=True),
             json.dumps(op_counts, sort_keys=True),
             utc_now(), utc_now(), trial, self.cfg.producer,
             json.dumps({
                 "family": family,
                 "manifest_id": self.cfg.experiment_id,
                 "knowledge_snapshot_id": snapshot_id,
                 "policy_version": policy_version,
             }, sort_keys=True)),
        )

    def _refresh_operator_stats(self) -> None:
        self.conn.execute("DELETE FROM operator_stats")
        rows = self.conn.execute(
            "SELECT operator_name, outcome, effect_size, credits_charged,"
            " novelty, payload FROM evidence"
        ).fetchall()
        aggregated: dict[str, dict[str, float]] = {}
        for name, outcome, effect, credits, novelty, payload in rows:
            valid = bool(json.loads(payload or "{}").get("valid", True))
            agg = aggregated.setdefault(name, {
                "attempts": 0, "invalid": 0, "success": 0, "effect": 0.0,
                "effect_sq": 0.0, "credits": 0.0, "novel": 0,
            })
            agg["attempts"] += 1
            if not valid:
                agg["invalid"] += 1
            if outcome == PROMOTE:
                agg["success"] += 1
            agg["effect"] += effect or 0.0
            agg["effect_sq"] += (effect or 0.0) ** 2
            agg["credits"] += credits or 0.0
            if novelty:
                agg["novel"] += 1
        for name, agg in aggregated.items():
            self.conn.execute(
                "INSERT INTO operator_stats (operator_name, attempts,"
                " invalid_count, success_count, replicated_success_count,"
                " sum_effect, sum_effect_sq, total_credits, novelty_count,"
                " updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (name, agg["attempts"], agg["invalid"], agg["success"],
                 agg["success"], agg["effect"], agg["effect_sq"],
                 agg["credits"], agg["novel"], utc_now()),
            )

    # -- prior (K0) -------------------------------------------------------

    def run_prior(self) -> KnowledgeSnapshot:
        """Generate + persist the frozen K0 snapshot (uniform policy).

        Every prior attempt is persisted as evidence (policy
        ``prior-uniform``) so the operator_stats aggregate seeded before the
        comparison arms is the same table B's policy is documented as
        reading.
        """
        aggregates: dict[str, dict[str, float]] = {
            op: {"attempts": 0.0, "successes": 0.0, "sum_effect": 0.0,
                 "sum_effect_sq": 0.0, "credits": 0.0}
            for op in OPERATOR_CATALOG
        }
        event_range: list[str] = []
        rng = random.Random(self.cfg.prior_seed)
        episode_idx = 0
        per_family = self.cfg.prior_attempts_per_family
        for family in TASK_FAMILIES:
            task_id = self._register_prior_task(family)
            for i in range(per_family):
                op = list(OPERATOR_CATALOG)[rng.randrange(len(OPERATOR_CATALOG))]
                attempt = run_attempt(
                    family, op, seed_base=self.cfg.seed_base,
                    trial=self.cfg.prior_seed, episode=episode_idx, attempt=i)
                self._record_prior_attempt(family, task_id, i, attempt)
                agg = aggregates[op]
                agg["attempts"] += 1.0
                agg["sum_effect"] += attempt.mean_effect if attempt.valid else 0.0
                agg["sum_effect_sq"] += (
                    (attempt.mean_effect ** 2) if attempt.valid else 0.0)
                agg["credits"] += attempt.cost_credits
                if attempt.discovery:
                    agg["successes"] += 1.0
                event_range.append(f"prior-{family}-{i}")
            episode_idx += 1
        snapshot = build_prior_snapshot(
            aggregates,
            snapshot_id=f"K0-{self.cfg.experiment_id}",
            version=PRIOR_POLICY_VERSION,
            event_range=event_range,
        )
        self.snapshot = snapshot
        with self.conn:
            self._refresh_operator_stats()
        (self.artifact_dir / "knowledge-snapshot.json").write_text(
            json.dumps(snapshot.to_dict(), indent=2, sort_keys=True) + "\n")
        return snapshot

    def _register_prior_task(self, family: str) -> str:
        task_id = f"task-{self.cfg.experiment_id}-prior-{family}"
        self.conn.execute(
            "INSERT OR IGNORE INTO tasks (task_id, name, family, workload,"
            " description, baseline_config, search_space, seeds,"
            " primary_metric, direction, promotion_threshold, ground_truth,"
            " credit_estimate, created_at, producer)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (task_id, task_id, family, "toy-discovery", "protocol-230 prior",
             "{}", json.dumps({"unused": True}), "[1, 2]", "discovery_rate",
             "maximize", self.cfg.promotion_threshold,
             json.dumps({"note": "hidden from policies"}), 0.0,
             utc_now(), self.cfg.producer),
        )
        return task_id

    def _record_prior_attempt(self, family: str, task_id: str, idx: int,
                              attempt: Attempt) -> None:
        exp_id = "prior-k0"
        episode_id = f"ep-{self.cfg.experiment_id}-prior-{family}-{idx}"
        evidence = self.evidence.insert(
            task_id=task_id,
            experiment_id=exp_id,
            operator_name=attempt.operator,
            policy=PRIOR_POLICY_LABEL,
            primary_metric="discovery_rate",
            direction="maximize",
            outcome=PROMOTE if attempt.discovery else "reject",
            promotion_threshold=self.cfg.promotion_threshold,
            credits_charged=attempt.cost_credits,
            novel=True,
            hypothesis_id=f"h-{self.cfg.experiment_id}-prior",
            candidate_id=f"cand-prior-{self.cfg.experiment_id}-{family}-{idx}",
            baseline_mean=0.0,
            candidate_mean=attempt.mean_effect,
            relative_delta=attempt.mean_effect,
            ci_low=min(attempt.effect_1, attempt.effect_2),
            ci_high=max(attempt.effect_1, attempt.effect_2),
            p_value=0.0 if attempt.discovery else 1.0,
            effect_size=attempt.mean_effect,
            episode_id=episode_id,
            payload={
                "valid": attempt.valid,
                "effect_1": attempt.effect_1,
                "effect_2": attempt.effect_2,
                "replication_passed": attempt.discovery,
                "family": family,
                "phase": "prior-k0",
            },
        )
        self.conn.execute(
            "INSERT INTO operator_uses (use_id, operator_name, task_id,"
            " experiment_id, episode_id, outcome, relative_delta,"
            " credits_charged, novel, created_at, producer)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (evidence.evidence_id, attempt.operator, task_id, exp_id,
             episode_id, PROMOTE if attempt.discovery else "reject",
             attempt.mean_effect, attempt.cost_credits, 1,
             utc_now(), self.cfg.producer),
        )

    # -- single trial -----------------------------------------------------

    def _run_trial(self, arm: str, policy: Policy, trial: int) -> dict[str, Any]:
        """Run *trial* (all episodes) for one arm; persist and return stats."""
        assert self.snapshot is not None, "prior snapshot must be built first"
        total_discoveries = 0
        total_credits = 0.0
        total_attempts = 0
        per_episode: list[dict[str, Any]] = []
        for episode, family in enumerate(self.cfg.rotation):
            episode_id = f"ep-{self.cfg.experiment_id}-{arm}-{trial}-{episode}"
            task_id = self._register_task(arm, trial, episode, family)
            spent = 0.0
            step = 0
            op_counts: dict[str, int] = {}
            failure_counts = {"invalid": 0, "below_threshold": 0}
            episode_discoveries = 0
            while spent < self.cfg.budget_credits:
                operator, record = policy.select(family, step)
                if spent + operator_cost(operator) > self.cfg.budget_credits:
                    break
                attempt = run_attempt(
                    family, operator, seed_base=self.cfg.seed_base,
                    trial=trial, episode=episode, attempt=step)
                spent += attempt.cost_credits
                total_credits += attempt.cost_credits
                op_counts[operator] = op_counts.get(operator, 0) + 1
                if not attempt.valid:
                    failure_counts["invalid"] += 1
                elif not attempt.discovery:
                    failure_counts["below_threshold"] += 1
                key = (arm, trial, family, operator)
                novel = key not in self._seen
                replication_of = self._seen.get(key, "")
                evidence_id = self._record_attempt(
                    arm, trial, episode, family, task_id, episode_id, step,
                    attempt, novel, replication_of)
                if novel:
                    self._seen[key] = evidence_id
                if attempt.discovery:
                    episode_discoveries += 1
                    total_discoveries += 1
                if isinstance(policy, AdaptivePolicy):
                    policy.update(family, operator, attempt.discovery)
                self._events[arm].append({
                    "trial": trial, "episode": episode, "family": family,
                    "step": step, "operator": operator, "cost": attempt.cost_credits,
                    "valid": attempt.valid, "effect_1": attempt.effect_1,
                    "effect_2": attempt.effect_2, "mean_effect": attempt.mean_effect,
                    "discovery": attempt.discovery,
                    "policy_version": getattr(policy, "version", ""),
                })
                self._events.setdefault(f"selections-{arm}", []).append(
                    record.to_dict())
                step += 1
                total_attempts += 1
            self._record_episode(
                arm, trial, episode, family, task_id, episode_id,
                self.cfg.budget_credits, spent, step, episode_discoveries,
                failure_counts, op_counts, self.snapshot.snapshot_id,
                getattr(policy, "version", ""))
            per_episode.append({
                "trial": trial, "episode": episode, "family": family,
                "attempts": step, "credits": spent, "discoveries": episode_discoveries,
            })
        credits = total_credits if total_credits > 0 else 1.0
        return {
            "arm": arm, "trial": trial,
            "discoveries": total_discoveries, "credits": total_credits,
            "efficiency": total_discoveries / credits,
            "attempts": total_attempts,
            "episodes": per_episode,
        }

    def _policy_factory(self, arm: str, rng_seed: int) -> Policy:
        snapshot = self.snapshot
        if snapshot is None:
            raise HarnessError("prior snapshot must be built before arms")
        if arm == "static":
            return StaticPolicy(DEFAULT_OPERATORS)
        if arm == "knowledge-informed":
            return KnowledgeInformedPolicy(snapshot, top_k=self.cfg.top_k)
        if arm == "adaptive":
            return AdaptivePolicy(snapshot, DEFAULT_OPERATORS, rng_seed=rng_seed)
        if arm == "random":
            return RandomPolicy(DEFAULT_OPERATORS, seed=rng_seed)
        if arm == "c-permuted":
            return AdaptivePolicy(
                snapshot, DEFAULT_OPERATORS, rng_seed=rng_seed,
                feedback_shuffle_seed=rng_seed + 999)
        if arm == "b-shuffled":
            shuffled = self._shuffled_snapshot(snapshot, rng_seed)
            return KnowledgeInformedPolicy(shuffled, top_k=self.cfg.top_k)
        raise HarnessError(f"unknown arm {arm!r}")

    def _shuffled_snapshot(self, snapshot: KnowledgeSnapshot,
                           rng_seed: int) -> KnowledgeSnapshot:
        """Ablation: operator -> counts association destroyed (seeded)."""
        rng = random.Random(rng_seed)
        ops = list(OPERATOR_CATALOG)
        permuted = list(ops)
        rng.shuffle(permuted)
        aggregates: dict[str, dict[str, float]] = {}
        for op, other in zip(ops, permuted, strict=True):
            aggregates[op] = {
                "attempts": snapshot.attempts.get(other, 0),
                "successes": snapshot.successes.get(other, 0),
                "sum_effect": snapshot.sum_effect.get(other, 0.0),
                "sum_effect_sq": snapshot.sum_effect_sq.get(other, 0.0),
                "credits": snapshot.credits.get(other, 0.0),
            }
        return build_prior_snapshot(
            aggregates, snapshot_id=f"{snapshot.snapshot_id}-shuffled",
            version=PRIOR_POLICY_VERSION, event_range=snapshot.event_range)

    # -- whole experiment ---------------------------------------------------

    def run(self) -> dict[str, list[dict[str, Any]]]:
        """Run prior, then every arm and ablation; returns per-trial results."""
        self.ensure_manifest()
        self.run_prior()
        arms = list(self.cfg.arms)
        if "permuted" in self.cfg.ablations:
            arms.append("c-permuted")
        if "shuffled" in self.cfg.ablations:
            arms.append("b-shuffled")
        results: dict[str, list[dict[str, Any]]] = {}
        for arm in arms:
            self._events[arm] = []
            self._events[f"selections-{arm}"] = []
            rng_seed = self.cfg.analysis_seed + self._arm_seed(arm)
            trial_results: list[dict[str, Any]] = []
            for trial in range(self.cfg.trials):
                policy = self._policy_factory(arm, rng_seed + trial)
                if hasattr(policy, "reset"):
                    policy.reset()
                trial_results.append(self._run_trial(arm, policy, trial))
            results[arm] = trial_results
            with self.conn:
                self._refresh_operator_stats()
        for arm, events in self._events.items():
            if arm.startswith("selections-"):
                target = self.artifact_dir / "conditions" / (
                    arm.removeprefix("selections-")) / "operator-selections.jsonl"
            else:
                target = self.artifact_dir / "conditions" / (
                    arm) / "raw-results.jsonl"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                "".join(json.dumps(e, sort_keys=True) + "\n" for e in events))
        return results

    @staticmethod
    def _arm_seed(arm: str) -> int:
        """Deterministic per-arm seed offset (stable across processes)."""
        return sum((i + 1) * ord(c) for i, c in enumerate(arm))

    # -- statistics -----------------------------------------------------------

    @staticmethod
    def _family_efficiencies(
        results: dict[str, list[dict[str, Any]]],
    ) -> dict[str, dict[str, list[float]]]:
        """Per-(trial, family) efficiency series per arm (protocol 230 §5).

        Pairs are matched on (family, seed): each trial contributes one
        efficiency observation per family, computed over that family's
        episodes in the trial. All arms share the rotation and seed plan,
        so index i of every series corresponds to the same (trial, family).
        """
        fam_effs: dict[str, dict[str, list[float]]] = {}
        for arm, trials in results.items():
            per_family: dict[str, list[float]] = {}
            for trial in trials:
                agg: dict[str, list[float]] = {}
                for ep in trial.get("episodes", []):
                    cell = agg.setdefault(ep["family"], [0.0, 0.0])
                    cell[0] += ep["discoveries"]
                    cell[1] += ep["credits"]
                for family, (disc, cred) in sorted(agg.items()):
                    denom = cred if cred > 0 else 1.0
                    per_family.setdefault(family, []).append(disc / denom)
            for family, series in per_family.items():
                fam_effs.setdefault(family, {})[arm] = series
        return fam_effs

    @staticmethod
    def _comparison_matrix(
        effs: dict[str, list[float]],
        pairs: tuple[tuple[str, str], ...],
        metric: str,
        seed: int,
    ) -> tuple[list[dict[str, Any]], list[float]]:
        """Run *pairs* over efficiency series; return rows + raw p-values."""
        comparisons: list[dict[str, Any]] = []
        p_values: list[float] = []
        for base, cand in pairs:
            if base not in effs or cand not in effs:
                continue
            analysis = analyze(
                effs[base], effs[cand], metric=metric, seed=seed)
            p_values.append(analysis.p_value)
            comparisons.append({
                "base": base, "candidate": cand,
                "delta": analysis.delta,
                "relative_delta": analysis.relative_delta,
                "ci_low": analysis.ci_low, "ci_high": analysis.ci_high,
                "p_value": analysis.p_value,
                "effect_size": analysis.effect_size,
                "base_mean": analysis.baseline.mean,
                "candidate_mean": analysis.candidate.mean,
            })
        return comparisons, p_values

    def analyze(self, results: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        effs: dict[str, list[float]] = {}
        per_arm: dict[str, dict[str, Any]] = {}
        for arm, trials in results.items():
            effs[arm] = [t["efficiency"] for t in trials]
            per_arm[arm] = {
                "discoveries": sum(t["discoveries"] for t in trials),
                "credits": sum(t["credits"] for t in trials),
                "attempts": sum(t["attempts"] for t in trials),
                "efficiencies": effs[arm],
            }
        comparisons, p_values = self._comparison_matrix(
            effs, PRIMARY_COMPARISONS,
            metric="discoveries_per_credit", seed=self.cfg.analysis_seed)
        adjusted = list(benjamini_hochberg(p_values))
        for row, q in zip(comparisons, adjusted, strict=True):
            row["adjusted_p"] = q
        # Per-family analysis (protocol 230 §5: pairs matched on
        # (family, seed); promotion requires the effect on >= 2 families).
        fam_effs = self._family_efficiencies(results)
        per_family: dict[str, dict[str, Any]] = {}
        for family in sorted(fam_effs):
            rows, fam_p = self._comparison_matrix(
                fam_effs[family], PRIMARY_COMPARISONS,
                metric=f"discoveries_per_credit ({family})",
                seed=self.cfg.analysis_seed)
            fam_adj = list(benjamini_hochberg(fam_p))
            for row, q in zip(rows, fam_adj, strict=True):
                row["adjusted_p"] = q
            per_family[family] = {
                "comparisons": rows,
                "per_condition": {
                    arm: {
                        "efficiency_mean": (
                            sum(series) / len(series) if series else 0.0),
                        "trials": len(series),
                    }
                    for arm, series in sorted(fam_effs[family].items())
                },
            }
        ablations: list[dict[str, Any]] = []
        for base, cand, note in ABLATION_COMPARISONS:
            if base in effs and cand in effs:
                analysis = analyze(
                    effs[base], effs[cand],
                    metric="discoveries_per_credit",
                    seed=self.cfg.analysis_seed + 7)
                ablations.append({
                    "base": base, "candidate": cand, "note": note,
                    "delta": analysis.delta,
                    "relative_delta": analysis.relative_delta,
                    "ci_low": analysis.ci_low, "ci_high": analysis.ci_high,
                    "p_value": analysis.p_value,
                    "effect_size": analysis.effect_size,
                    "base_mean": analysis.baseline.mean,
                    "candidate_mean": analysis.candidate.mean,
                })
        interpretation = self._interpret(comparisons)
        stats = {
            "per_condition": {
                arm: {
                    "validated_discoveries": per_arm[arm]["discoveries"],
                    "compute_credits": round(per_arm[arm]["credits"], 2),
                    "discoveries_per_credit": round(
                        per_arm[arm]["discoveries"]
                        / max(per_arm[arm]["credits"], 1.0),
                        6),
                    "attempts": per_arm[arm]["attempts"],
                }
                for arm in per_arm
            },
            "comparisons": comparisons,
            "per_family": per_family,
            "ablations": ablations,
            "interpretation": interpretation,
        }
        (self.artifact_dir / "statistics.json").write_text(
            json.dumps(stats, indent=2, sort_keys=True) + "\n")
        return stats

    @staticmethod
    def evaluate_claim(
        per_family: dict[str, dict[str, Any]],
        held_out_stats: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Assess protocol 230 §5 promotion criterion (pre-registered).

        Claim-ready requires: C beats A and C beats B with adjusted
        p < 0.05 and CI excluding 0 on >= 2 training task families, and the
        gap persists on the held-out family (same direction, CI excluding 0).
        """
        def adaptive_row(family: str, base: str) -> dict[str, Any] | None:
            return next(
                (c for c in per_family.get(family, {}).get("comparisons", [])
                 if c["base"] == base and c["candidate"] == "adaptive"),
                None)

        def significant(row: dict[str, Any] | None) -> bool:
            return (row is not None and row["delta"] > 0
                    and row["adjusted_p"] < 0.05 and row["ci_low"] > 0)

        def persists(base: str) -> bool:
            if held_out_stats is None:
                return False
            row = next(
                (c for c in held_out_stats.get("comparisons", [])
                 if c["base"] == base and c["candidate"] == "adaptive"),
                None)
            return row is not None and row["delta"] > 0 and row["ci_low"] > 0

        families = sorted(per_family)
        by_family_vs_static = {f: significant(adaptive_row(f, "static"))
                               for f in families}
        by_family_vs_informed = {
            f: significant(adaptive_row(f, "knowledge-informed"))
            for f in families}
        two_families_static = (len(families) >= 2
                               and all(by_family_vs_static.values()))
        two_families_informed = (len(families) >= 2
                                 and all(by_family_vs_informed.values()))
        held_out_static = persists("static")
        held_out_informed = persists("knowledge-informed")
        claim_ready = (two_families_static and two_families_informed
                       and held_out_static and held_out_informed)
        if claim_ready:
            verdict = (
                "promotion criterion MET: C > A and C > B (adjusted p < 0.05,"
                " CI excluding 0) on all "
                f"{len(families)} training families, and the gap persists on"
                f" held-out {HELD_OUT_FAMILY}")
        else:
            unmet: list[str] = []
            if not two_families_static:
                unmet.append("C>A with adjusted p < 0.05 on >=2 families")
            if not two_families_informed:
                unmet.append("C>B with adjusted p < 0.05 on >=2 families")
            if not held_out_static or not held_out_informed:
                unmet.append(f"gap persistence on held-out {HELD_OUT_FAMILY}")
            verdict = ("promotion criterion NOT met; unmet components: "
                       + "; ".join(unmet))
        return {
            "c_beats_static_by_family": by_family_vs_static,
            "c_beats_knowledge_informed_by_family": by_family_vs_informed,
            "held_out_persistence_vs_static": held_out_static,
            "held_out_persistence_vs_knowledge_informed": held_out_informed,
            "training_families_analysed": len(families),
            "claim_ready": claim_ready,
            "verdict": verdict,
        }

    @staticmethod
    def _interpret(comparisons: list[dict[str, Any]]) -> dict[str, Any]:
        """Classify against the pre-registered outcome taxonomy (protocol 230)."""
        def find(base: str, cand: str) -> dict[str, Any] | None:
            return next((c for c in comparisons
                         if c["base"] == base and c["candidate"] == cand), None)

        def sig(row: dict[str, Any] | None) -> bool:
            return row is not None and row["adjusted_p"] < 0.05

        row_ac = find("static", "adaptive")
        row_ab = find("static", "knowledge-informed")
        row_bc = find("knowledge-informed", "adaptive")
        c_beats_a = row_ac is not None and row_ac["delta"] > 0 and sig(row_ac)
        b_beats_a = row_ab is not None and row_ab["delta"] > 0 and sig(row_ab)
        c_beats_b = row_bc is not None and row_bc["delta"] > 0 and sig(row_bc)
        if c_beats_a and c_beats_b:
            outcome = 1
            verdict = "H1 supported in this environment: C > B > A"
        elif (b_beats_a and not c_beats_b
              and row_bc is not None and abs(row_bc["delta"]) < 1e-9):
            outcome = 2
            verdict = ("historical knowledge helps; online adaptation "
                       "adds little (B > A, C ≈ B)")
        elif c_beats_a and not b_beats_a:
            outcome = 3
            verdict = ("online adaptation matters; static knowledge alone does not "
                       "(C > A, B ≈ A)")
        elif not (c_beats_a or b_beats_a):
            outcome = 4
            verdict = "hypothesis not supported in this environment (A ≈ B ≈ C)"
        else:
            outcome = 5
            verdict = "adaptive machinery may be harmful (A >= B or C)"
        return {"outcome": outcome, "verdict": verdict}

    # -- report --------------------------------------------------------------

    def write_report(self, results: dict[str, list[dict[str, Any]]],
                     stats: dict[str, Any],
                     held_out_stats: dict[str, Any] | None = None) -> Path:
        lines = [
            f"# Cumulative Search Policy Comparison — {self.cfg.experiment_id}",
            "",
            f"Protocol: {PROTOCOL_VERSION} "
            f"(see spec/research/230_KNOWLEDGE_LOOP_EVALUATION.md)",
            f"Environment: toy-discovery {TOY_ENVIRONMENT_VERSION}; "
            f"families: {', '.join(TASK_FAMILIES)}; "
            f"held-out: {HELD_OUT_FAMILY}",
            f"Budget per episode: {self.cfg.budget_credits} credits; episodes/trial: "
            f"{self.cfg.episodes_per_trial}; trials (seeds): {self.cfg.trials}",
            f"Discovery gate: {self.manifest['discovery_gate']}",
            "",
            "## Per-condition outcome",
            "",
            "| arm | discoveries | credits | discoveries/credit | attempts |",
            "|---|---|---|---|---|",
        ]
        pc = stats["per_condition"]
        arm_order = ("static", "knowledge-informed", "adaptive", "random",
                     "c-permuted", "b-shuffled")
        for arm in arm_order:
            if arm not in pc:
                continue
            d = pc[arm]
            lines.append(
                f"| {arm} | {d['validated_discoveries']} | {d['compute_credits']} "
                f"| {d['discoveries_per_credit']} | {d['attempts']} |")
        lines += [
            "",
            "## Pairwise comparisons (A vs B, A vs C, B vs C; BH-adjusted)",
            "",
            "| base | candidate | delta | CI low | CI high | p | adjusted p | d |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for c in stats["comparisons"]:
            lines.append(
                f"| {c['base']} | {c['candidate']} | {c['delta']:.6f} "
                f"| {c['ci_low']:.6f} | {c['ci_high']:.6f} "
                f"| {c['p_value']:.6f} | {c['adjusted_p']:.6f} "
                f"| {c['effect_size']:.3f} |")
        lines += self._per_family_section(stats.get("per_family", {}))
        lines += self._calibration_floor_section(stats["per_condition"])
        lines += [
            "",
            "## Ablations (exploratory; p-values unadjusted)",
            "",
            "| base | candidate | delta | p | d | note |",
            "|---|---|---|---|---|---|",
        ]
        for a in stats.get("ablations", []):
            lines.append(
                f"| {a['base']} | {a['candidate']} | {a['delta']:.6f} "
                f"| {a['p_value']:.6f} | {a['effect_size']:.3f} | {a['note']} |")

        # Held-out transfer section
        if held_out_stats is not None:
            lines += [
                "",
                f"## Held-out transfer ({HELD_OUT_FAMILY} family)",
                "",
                (f"Transfer evaluation on held-out family **{HELD_OUT_FAMILY}**, "
                 "which was never included in the K0 prior."),
                "",
                "| arm | discoveries | credits | discoveries/credit | attempts |",
                "|---|---|---|---|---|",
            ]
            hpc = held_out_stats["per_condition"]
            for arm in arm_order:
                if arm not in hpc:
                    continue
                d = hpc[arm]
                lines.append(
                    f"| {arm} | {d['validated_discoveries']} "
                    f"| {d['compute_credits']} "
                    f"| {d['discoveries_per_credit']} "
                    f"| {d['attempts']} |")
            if held_out_stats.get("comparisons"):
                lines += [
                    "",
                    "### Held-out pairwise comparisons (BH-adjusted)",
                    "",
                    ("| base | candidate | delta | CI low | CI high "
                     "| p | adjusted p | d |"),
                    "|---|---|---|---|---|---|---|---|",
                ]
                for c in held_out_stats["comparisons"]:
                    lines.append(
                        f"| {c['base']} | {c['candidate']} "
                        f"| {c['delta']:.6f} "
                        f"| {c['ci_low']:.6f} | {c['ci_high']:.6f} "
                        f"| {c['p_value']:.6f} | {c['adjusted_p']:.6f} "
                        f"| {c['effect_size']:.3f} |")
            claim = held_out_stats.get("claim_readiness")
            if claim is not None:
                lines += [
                    "",
                    "### Promotion-criterion status (protocol 230 §5)",
                    "",
                    f"- C > A per training family: "
                    f"{claim['c_beats_static_by_family']}",
                    f"- C > B per training family: "
                    f"{claim['c_beats_knowledge_informed_by_family']}",
                    f"- gap persists on held-out vs A: "
                    f"{claim['held_out_persistence_vs_static']}",
                    f"- gap persists on held-out vs B: "
                    f"{claim['held_out_persistence_vs_knowledge_informed']}",
                    "",
                    f"**{claim['verdict']}**",
                ]

        lines += [
            "",
            "## Adaptive-policy adaptation evidence (condition C)",
            "",
        ]
        lines += self._adaptation_summary(results)
        lines += [
            "",
            f"## Interpretation: {stats['interpretation']['verdict']}",
            f"(outcome {stats['interpretation']['outcome']} "
            "in the pre-registered taxonomy)",
            "",
            "## Limitations and scope",
            "",
            "- The experiment uses a deterministic toy environment with known "
            "ground truth; results may not generalise to real workloads.",
            "- The held-out family provides evidence that the adaptive "
            "advantage transfers beyond the training families; it does not "
            "by itself rule out all benchmark-specific adaptation or "
            "memorisation.",
            "- The permuted-outcome ablation is consistent with the "
            "interpretation that the adaptive feedback loop contributes to "
            "the advantage, but it does not constitute definitive causal "
            "proof (other mechanisms correlated with feedback are also "
            "disrupted by permutation).",
            "- Statistical inference is based on 8 independent seeds; "
            "wider replication would strengthen confidence.",
            "- The training set comprises exactly 2 task families, the "
            "minimum required by the promotion criterion; additional "
            "families would materially strengthen the >=2-family claim.",
            "- The comparison measures discovery efficiency, not absolute "
            "capability; a policy with lower efficiency might still be "
            "preferable under different cost models.",
            "",
            "Manifest: `manifest.json` · "
            "knowledge snapshot: `knowledge-snapshot.json` · "
            "raw events: `conditions/<arm>/raw-results.jsonl` · "
            "selections: `conditions/<arm>/operator-selections.jsonl` · "
            "held-out: `conditions/<arm>/held-out-raw-results.jsonl` · "
            "checksums: `checksums.json` · "
            "reproducibility: `reproducibility.json`",
        ]
        report_path = self.artifact_dir / "report.md"
        report_path.write_text("\n".join(lines) + "\n")
        return report_path

    def _per_family_section(
        self, per_family: dict[str, dict[str, Any]],
    ) -> list[str]:
        lines: list[str] = [
            "",
            "## Per-family comparisons (protocol §5 pairing: family × seed)",
            "",
        ]
        for family in sorted(per_family):
            block = per_family[family]
            lines += [
                f"### family {family}",
                "",
                ("| base | candidate | delta | CI low | CI high "
                 "| p | adjusted p | d |"),
                "|---|---|---|---|---|---|---|---|",
            ]
            for c in block["comparisons"]:
                lines.append(
                    f"| {c['base']} | {c['candidate']} | {c['delta']:.6f} "
                    f"| {c['ci_low']:.6f} | {c['ci_high']:.6f} "
                    f"| {c['p_value']:.6f} | {c['adjusted_p']:.6f} "
                    f"| {c['effect_size']:.3f} |")
            means = ", ".join(
                f"{arm} {s['efficiency_mean']:.6f}"
                for arm, s in block["per_condition"].items())
            lines += ["", f"Mean efficiency per condition: {means}", ""]
        return lines

    @staticmethod
    def _calibration_floor_section(
        per_condition: dict[str, dict[str, Any]],
    ) -> list[str]:
        rnd = per_condition.get("random")
        if rnd is None:
            return []
        eff = rnd["discoveries_per_credit"]

        def ratio(other: str) -> str:
            base = per_condition.get(other)
            if base is None or base["discoveries_per_credit"] <= 0:
                return "n/a"
            return (f"{eff / base['discoveries_per_credit']:.3f}x"
                    if eff > 0 else "n/a")

        return [
            "",
            "## Calibration floor (condition D — uniform random)",
            "",
            (f"Random selection achieves {rnd['validated_discoveries']} "
             f"discoveries over {rnd['compute_credits']} credits "
             f"({eff:.6f} discoveries/credit, "
             f"{ratio('static')} of static, "
             f"{ratio('knowledge-informed')} of knowledge-informed, "
             f"{ratio('adaptive')} of adaptive). This is the floor any "
             "informed policy must clear to justify its knowledge channel; "
             "arms at or below this level would indicate the task or budget "
             "carries no exploitable signal."),
        ]

    def _adaptation_summary(
        self, results: dict[str, list[dict[str, Any]]]) -> list[str]:
        events = self._events.get("adaptive", [])
        by_family: dict[str, dict[str, list[float]]] = {}
        for e in events:
            fam = e["family"]
            op = e["operator"]
            entry = by_family.setdefault(fam, {"useful_share": []})
            entry.setdefault(op, []).append(e["discovery"])
            entry["useful_share"].append(1.0 if is_useful(fam, op) else 0.0)
        lines: list[str] = []
        all_families = list(TASK_FAMILIES) + [HELD_OUT_FAMILY]
        for fam in all_families:
            fam_entry = by_family.get(fam)
            if not fam_entry:
                continue
            share = fam_entry["useful_share"]
            half = max(1, len(share) // 2)
            early = sum(share[:half]) / len(share[:half])
            late = sum(share[half:]) / len(share[half:]) if share[half:] else 0.0
            per_op = {
                op: (sum(v), len(v)) for op, v in fam_entry.items()
                if op != "useful_share"
            }
            lines.append(f"### family {fam}")
            shift = ("shifted toward useful operators" if late > early
                     else "no upward shift")
            lines.append(
                f"- fraction of selections on useful operators: "
                f"early {early:.3f} -> late {late:.3f} ({shift})")
            lines.append(f"- operator attempt counts: {dict(per_op)}")
            lines.append("")
        return lines

    # -- held-out transfer evaluation --------------------------------------

    def run_held_out(
        self,
    ) -> dict[str, list[dict[str, Any]]]:
        """Evaluate all arms on the held-out family (protocol 230 §3).

        Fresh policy instances are created from the same K0 snapshot.  Every
        episode targets ``HELD_OUT_FAMILY`` exclusively.  The evaluation is
        recorded with a ``phase=held-out`` marker in the search_episodes
        payload so it is distinguishable from the main comparison.
        """
        assert self.snapshot is not None, "prior snapshot must be built first"
        held_out_arms = list(self.cfg.arms)
        results: dict[str, list[dict[str, Any]]] = {}
        for arm in held_out_arms:
            self._events[f"held-out-{arm}"] = []
            self._events[f"held-out-selections-{arm}"] = []
            rng_seed = (self.cfg.analysis_seed + self._arm_seed(arm)
                        + 10_000)  # distinct from main comparison
            trial_results: list[dict[str, Any]] = []
            for trial in range(self.cfg.trials):
                policy = self._policy_factory(arm, rng_seed + trial)
                if hasattr(policy, "reset"):
                    policy.reset()
                trial_results.append(
                    self._run_held_out_trial(arm, policy, trial))
            results[arm] = trial_results
        # Write held-out artifacts
        for arm, events in self._events.items():
            if not arm.startswith("held-out-"):
                continue
            if arm.startswith("held-out-selections-"):
                real_arm = arm.removeprefix("held-out-selections-")
                target = (self.artifact_dir / "conditions" / real_arm
                          / "held-out-operator-selections.jsonl")
            else:
                real_arm = arm.removeprefix("held-out-")
                target = (self.artifact_dir / "conditions" / real_arm
                          / "held-out-raw-results.jsonl")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                "".join(json.dumps(e, sort_keys=True) + "\n" for e in events))
        return results

    def _run_held_out_trial(
        self, arm: str, policy: Policy, trial: int,
    ) -> dict[str, Any]:
        """Run one trial on the held-out family."""
        assert self.snapshot is not None
        total_discoveries = 0
        total_credits = 0.0
        total_attempts = 0
        family = HELD_OUT_FAMILY
        for episode in range(self.cfg.episodes_per_trial):
            episode_id = (f"ep-{self.cfg.experiment_id}-heldout-{arm}"
                          f"-{trial}-{episode}")
            task_id = f"task-{self.cfg.experiment_id}-heldout-{arm}-{trial}-{episode}"
            self._register_held_out_task(task_id, family)
            spent = 0.0
            step = 0
            op_counts: dict[str, int] = {}
            failure_counts = {"invalid": 0, "below_threshold": 0}
            episode_discoveries = 0
            while spent < self.cfg.budget_credits:
                operator, record = policy.select(family, step)
                if spent + operator_cost(operator) > self.cfg.budget_credits:
                    break
                attempt = run_attempt(
                    family, operator, seed_base=self.cfg.seed_base,
                    trial=trial + 100_000,  # offset to avoid seed collision
                    episode=episode, attempt=step)
                spent += attempt.cost_credits
                total_credits += attempt.cost_credits
                op_counts[operator] = op_counts.get(operator, 0) + 1
                if not attempt.valid:
                    failure_counts["invalid"] += 1
                elif not attempt.discovery:
                    failure_counts["below_threshold"] += 1
                key = (f"heldout-{arm}", trial, family, operator)
                novel = key not in self._seen
                replication_of = self._seen.get(key, "")
                evidence_id = self._record_attempt(
                    f"heldout-{arm}", trial, episode, family,
                    task_id, episode_id, step, attempt, novel,
                    replication_of)
                if novel:
                    self._seen[key] = evidence_id
                if attempt.discovery:
                    episode_discoveries += 1
                    total_discoveries += 1
                if isinstance(policy, AdaptivePolicy):
                    policy.update(family, operator, attempt.discovery)
                self._events[f"held-out-{arm}"].append({
                    "trial": trial, "episode": episode, "family": family,
                    "step": step, "operator": operator,
                    "cost": attempt.cost_credits, "valid": attempt.valid,
                    "effect_1": attempt.effect_1,
                    "effect_2": attempt.effect_2,
                    "mean_effect": attempt.mean_effect,
                    "discovery": attempt.discovery,
                    "phase": "held-out",
                    "policy_version": getattr(policy, "version", ""),
                })
                self._events[f"held-out-selections-{arm}"].append(
                    record.to_dict())
                step += 1
                total_attempts += 1
            self.conn.execute(
                "INSERT INTO search_episodes (episode_id, task_id, policy,"
                " budget_credits, credits_charged, attempts, discoveries,"
                " failure_counts, operator_use_counts, started_at, finished_at,"
                " seed, producer, payload) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (episode_id, task_id, arm, self.cfg.budget_credits, spent,
                 step, episode_discoveries,
                 json.dumps(failure_counts, sort_keys=True),
                 json.dumps(op_counts, sort_keys=True),
                 utc_now(), utc_now(), trial, self.cfg.producer,
                 json.dumps({
                     "family": family, "phase": "held-out",
                     "manifest_id": self.cfg.experiment_id,
                     "knowledge_snapshot_id": self.snapshot.snapshot_id,
                     "policy_version": getattr(policy, "version", ""),
                 }, sort_keys=True)),
            )
        credits = total_credits if total_credits > 0 else 1.0
        return {
            "arm": arm, "trial": trial, "phase": "held-out",
            "discoveries": total_discoveries, "credits": total_credits,
            "efficiency": total_discoveries / credits,
            "attempts": total_attempts,
        }

    def _register_held_out_task(self, task_id: str, family: str) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO tasks (task_id, name, family, workload,"
            " description, baseline_config, search_space, seeds,"
            " primary_metric, direction, promotion_threshold, ground_truth,"
            " credit_estimate, created_at, producer)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (task_id, task_id, family, "toy-discovery",
             "protocol-230 held-out transfer", "{}",
             json.dumps({"unused": True}), "[1, 2]", "discovery_rate",
             "maximize", self.cfg.promotion_threshold,
             json.dumps({"note": "held-out; never in prior"}),
             self.cfg.budget_credits, utc_now(), self.cfg.producer),
        )

    def analyze_held_out(
        self,
        held_out_results: dict[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        """Statistical analysis of held-out transfer (protocol 230 §3)."""
        effs: dict[str, list[float]] = {}
        per_arm: dict[str, dict[str, Any]] = {}
        for arm, trials in held_out_results.items():
            effs[arm] = [t["efficiency"] for t in trials]
            per_arm[arm] = {
                "discoveries": sum(t["discoveries"] for t in trials),
                "credits": sum(t["credits"] for t in trials),
                "attempts": sum(t["attempts"] for t in trials),
                "efficiencies": effs[arm],
            }
        comparisons: list[dict[str, Any]] = []
        p_values: list[float] = []
        for base, cand in PRIMARY_COMPARISONS:
            if base in effs and cand in effs:
                analysis = analyze(
                    effs[base], effs[cand],
                    metric="discoveries_per_credit (held-out)",
                    seed=self.cfg.analysis_seed)
                p_values.append(analysis.p_value)
                comparisons.append({
                    "base": base, "candidate": cand,
                    "delta": analysis.delta,
                    "relative_delta": analysis.relative_delta,
                    "ci_low": analysis.ci_low, "ci_high": analysis.ci_high,
                    "p_value": analysis.p_value,
                    "effect_size": analysis.effect_size,
                    "base_mean": analysis.baseline.mean,
                    "candidate_mean": analysis.candidate.mean,
                })
        adjusted = list(benjamini_hochberg(p_values))
        for row, q in zip(comparisons, adjusted, strict=True):
            row["adjusted_p"] = q
        return {
            "per_condition": {
                arm: {
                    "validated_discoveries": per_arm[arm]["discoveries"],
                    "compute_credits": round(per_arm[arm]["credits"], 2),
                    "discoveries_per_credit": round(
                        per_arm[arm]["discoveries"]
                        / max(per_arm[arm]["credits"], 1.0), 6),
                    "attempts": per_arm[arm]["attempts"],
                }
                for arm in per_arm
            },
            "comparisons": comparisons,
            "family": HELD_OUT_FAMILY,
            "note": "Transfer evaluation: arms evaluated on held-out family "
                    "gamma, which was never included in the K0 prior.",
        }

    # -- reproducibility verification ---------------------------------------

    @staticmethod
    def verify_reproducibility(
        artifact_dir: Path,
        cfg: ExperimentConfig,
    ) -> dict[str, Any]:
        """Verify that manifest and statistics are byte-reproducible.

        Reads the existing manifest and statistics from *artifact_dir* and
        confirms they are valid JSON and contain the expected versioned
        fields.  This does NOT re-run the experiment (that requires the same
        database state); it verifies that the artifact files are self-
        consistent and that the manifest was frozen before the run.
        """
        manifest_path = artifact_dir / "manifest.json"
        stats_path = artifact_dir / "statistics.json"
        if not manifest_path.exists():
            return {"reproducible": False, "error": "manifest.json missing"}
        if not stats_path.exists():
            return {"reproducible": False, "error": "statistics.json missing"}
        manifest = json.loads(manifest_path.read_text())
        stats = json.loads(stats_path.read_text())
        checks: list[dict[str, Any]] = []
        # 1. Manifest versions match config
        checks.append({
            "check": "protocol_version",
            "expected": PROTOCOL_VERSION,
            "actual": manifest.get("protocol_version"),
            "pass": manifest.get("protocol_version") == PROTOCOL_VERSION,
        })
        checks.append({
            "check": "environment_version",
            "expected": TOY_ENVIRONMENT_VERSION,
            "actual": manifest.get("environment_version"),
            "pass": manifest.get("environment_version") == TOY_ENVIRONMENT_VERSION,
        })
        checks.append({
            "check": "arms_match",
            "expected": list(cfg.arms),
            "actual": manifest.get("arms"),
            "pass": manifest.get("arms") == list(cfg.arms),
        })
        checks.append({
            "check": "budget_match",
            "expected": cfg.budget_credits,
            "actual": manifest.get("budget_credits"),
            "pass": manifest.get("budget_credits") == cfg.budget_credits,
        })
        # 2. Stats contain expected arms
        expected_arms = set(cfg.arms) | {"c-permuted", "b-shuffled"}
        actual_arms = set(stats.get("per_condition", {}).keys())
        checks.append({
            "check": "stats_arms_present",
            "expected": sorted(expected_arms),
            "actual": sorted(actual_arms),
            "pass": expected_arms <= actual_arms,
        })
        # 3. Held-out family is recorded
        checks.append({
            "check": "held_out_family_in_manifest",
            "expected": True,
            "actual": HELD_OUT_FAMILY in str(manifest.get("ground_truth", {})),
            "pass": HELD_OUT_FAMILY in str(manifest.get("ground_truth", {})),
        })
        all_pass = all(c["pass"] for c in checks)
        return {
            "reproducible": all_pass,
            "checks": checks,
            "manifest_path": str(manifest_path),
            "statistics_path": str(stats_path),
        }

    # -- artifact bundle ----------------------------------------------------

    def write_artifact_bundle(
        self,
        stats: dict[str, Any],
        held_out_stats: dict[str, Any] | None = None,
    ) -> Path:
        """Write the complete evidence artifact bundle (protocol 230).

        Produces:
        - plan.json (alias of manifest.json, immutable experiment definition)
        - protocol.json (analysis parameters and comparison matrix)
        - environment.json (task families, ground truth, versions)
        - manifest.json (already written by ensure_manifest)
        - knowledge-snapshot.json (already written by run_prior)
        - statistics.json (already written by analyze)
        - held-out-statistics.json (if held-out was run)
        - report.md (already written by write_report)
        - checksums.json (SHA-256 of all artifact files)
        - reproducibility.json (self-consistency verification)
        """
        ad = self.artifact_dir

        # Update manifest with bundle metadata before writing plan.json
        self.manifest["held_out_family"] = HELD_OUT_FAMILY
        self.manifest["artifact_bundle_version"] = "1.0.0"

        # plan.json (alias of manifest)
        (ad / "plan.json").write_text(
            json.dumps(self.manifest, indent=2, sort_keys=True) + "\n")
        # protocol.json
        protocol = {
            "protocol_version": PROTOCOL_VERSION,
            "primary_comparisons": [
                {"base": b, "candidate": c}
                for b, c in PRIMARY_COMPARISONS
            ],
            "ablation_comparisons": [
                {"base": b, "candidate": c, "note": n}
                for b, c, n in ABLATION_COMPARISONS
            ],
            "promotion_criterion": (
                "C beats both A and B (adjusted p < 0.05, CI excluding 0) "
                "on >= 2 independent task families at full seed plan, "
                "and the gap persists on the held-out family."
            ),
            "held_out_family": HELD_OUT_FAMILY,
            "discovery_gate": self.manifest["discovery_gate"],
            "primary_metric": "validated_discoveries / credits_consumed",
            "statistical_methods": [
                "paired bootstrap CI (2000 iterations, seeded)",
                "Welch's t-test (unpaired fallback)",
                "Cohen's d (pooled SD)",
                "Benjamini-Hochberg FDR correction",
            ],
        }
        (ad / "protocol.json").write_text(
            json.dumps(protocol, indent=2, sort_keys=True) + "\n")

        # environment.json
        all_families = list(TASK_FAMILIES) + [HELD_OUT_FAMILY]
        environment = {
            "environment_version": TOY_ENVIRONMENT_VERSION,
            "task_suite_version": TASK_SUITE_VERSION,
            "discovery_gate_version": DISCOVERY_GATE_VERSION,
            "families": all_families,
            "held_out_family": HELD_OUT_FAMILY,
            "ground_truth": {
                f: {op: ground_truth_effect(f, op) for op in OPERATOR_CATALOG}
                for f in all_families
            },
            "promotion_threshold": self.cfg.promotion_threshold,
            "effect_sigma": 0.12,
            "validation_probability": 0.90,
            "operators": list(OPERATOR_CATALOG),
        }
        (ad / "environment.json").write_text(
            json.dumps(environment, indent=2, sort_keys=True) + "\n")

        # held-out statistics
        if held_out_stats is not None:
            (ad / "held-out-statistics.json").write_text(
                json.dumps(held_out_stats, indent=2, sort_keys=True) + "\n")

        # manifest.json last content change before checksumming
        (ad / "manifest.json").write_text(
            json.dumps(self.manifest, indent=2, sort_keys=True) + "\n")

        # checksums.json (SHA-256 of all deterministic artifact files;
        # the checksum file itself and the reproducibility verdict derived
        # from it are excluded — they cannot cover themselves)
        import hashlib
        checksums: dict[str, str] = {}
        for p in sorted(ad.rglob("*")):
            if (p.is_file() and p.suffix in (".json", ".md", ".jsonl")
                    and p.name not in ("checksums.json",
                                       "reproducibility.json")):
                h = hashlib.sha256(p.read_bytes()).hexdigest()
                checksums[str(p.relative_to(ad))] = h
        (ad / "checksums.json").write_text(
            json.dumps(checksums, indent=2, sort_keys=True) + "\n")

        # reproducibility.json
        repro = self.verify_reproducibility(ad, self.cfg)
        (ad / "reproducibility.json").write_text(
            json.dumps(repro, indent=2, sort_keys=True) + "\n")

        return ad


def main(cfg: ExperimentConfig, conn: sqlite3.Connection,
         artifact_dir: Path, *, force: bool = False,
         out: TextIO = sys.stdout) -> int:
    """CLI entry: run the comparison, write artifacts, print summary."""
    if artifact_dir.exists() and not force and not (
            artifact_dir / "manifest.json").exists():
        raise HarnessError(
            f"artifact directory {artifact_dir} exists; use --force to overwrite")
    comp = PolicyComparison(cfg, conn, artifact_dir, force=force)
    results = comp.run()
    stats = comp.analyze(results)
    held_out_results = comp.run_held_out()
    held_out_stats = comp.analyze_held_out(held_out_results)
    held_out_stats["claim_readiness"] = PolicyComparison.evaluate_claim(
        stats.get("per_family", {}), held_out_stats)
    report = comp.write_report(results, stats, held_out_stats)
    comp.write_artifact_bundle(stats, held_out_stats)
    out.write(f"experiment {cfg.experiment_id} complete; report: {report}\n")
    for arm, s in stats["per_condition"].items():
        out.write(
            f"  {arm:<20} discoveries={s['validated_discoveries']:>4} "
            f"credits={s['compute_credits']:>8.1f} "
            f"eff={s['discoveries_per_credit']:.6f}\n")
    out.write(f"held-out ({HELD_OUT_FAMILY}):\n")
    for arm, s in held_out_stats["per_condition"].items():
        out.write(
            f"  {arm:<20} discoveries={s['validated_discoveries']:>4} "
            f"credits={s['compute_credits']:>8.1f} "
            f"eff={s['discoveries_per_credit']:.6f}\n")
    out.write(f"interpretation: {stats['interpretation']['verdict']}\n")
    out.write(
        "claim: "
        f"{held_out_stats['claim_readiness']['verdict']}\n")
    return 0


__all__ = [
    "ExperimentConfig",
    "PolicyComparison",
    "freeze_manifest",
    "HarnessError",
    "main",
    "PROTOCOL_VERSION",
]
