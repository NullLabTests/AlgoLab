"""Search policies for the cumulative-search experiment (protocol 230).

Three conditions plus a reference arm:

- **A — Static**: fixed deterministic round-robin operator schedule. Never
  reads historical evidence, never adapts.
- **B — Knowledge-informed**: ranks operators from a *frozen* historical
  snapshot (K0) and cycles the top-K ranked operators. Never updates from
  outcomes within an episode or a trial.
- **C — Adaptive**: Thompson-sampling-style Beta posterior per task family,
  initialized from the same K0 snapshot B receives, updated after every
  completed experiment. Selection is the argmax of posterior draws; every
  selection is recorded with priors, posteriors, score, and reason so the
  policy is fully inspectable.
- **D — Random** (reference/calibration floor): uniform random operator
  selection.

Deliberately boring: no LLM, no learned features. If C cannot beat A here,
there is no mechanism to transfer to richer policies.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any

from algolab.knowledge.operators import OPERATOR_BUDGETS

STATIC_POLICY_VERSION = "1.0.0"
KNOWLEDGE_INFORMED_POLICY_VERSION = "1.0.0"
ADAPTIVE_POLICY_VERSION = "1.0.0"
RANDOM_POLICY_VERSION = "1.0.0"
ADAPTIVE_COST_AWARE_POLICY_VERSION = "1.0.0"
COST_RANKED_KNOWLEDGE_POLICY_VERSION = "1.0.0"


class PolicyError(RuntimeError):
    """A policy violated its contract (e.g. read future knowledge)."""


@dataclass(frozen=True)
class KnowledgeSnapshot:
    """Frozen historical knowledge (K0): per-operator aggregate counts.

    ``event_range`` records which prior episodes produced the snapshot so
    every knowledge lookup is auditable.
    """

    snapshot_id: str
    version: str
    event_range: list[str] = field(default_factory=list)
    attempts: dict[str, int] = field(default_factory=dict)
    successes: dict[str, int] = field(default_factory=dict)
    sum_effect: dict[str, float] = field(default_factory=dict)
    sum_effect_sq: dict[str, float] = field(default_factory=dict)
    credits: dict[str, float] = field(default_factory=dict)

    def success_rate(self, operator: str, smoothing: float = 1.0) -> float:
        a = self.successes.get(operator, 0)
        n = self.attempts.get(operator, 0)
        return (a + smoothing) / (n + 2.0 * smoothing)

    def ranking(self) -> list[str]:
        """Operators ranked by K0 success rate; ties by total effect then
        catalog order (documented tiebreak, deterministic)."""
        return sorted(
            self.attempts,
            key=lambda op: (
                round(self.success_rate(op), 12),
                round(self.sum_effect.get(op, 0.0), 12),
                op,
            ),
            reverse=True,
        )

    def ranking_by_cost(self) -> list[str]:
        """Operators ranked by K0 success rate *per credit cost*; ties by
        total effect per credit then catalog order (deterministic).

        Protocol 231: the frozen cost-ranked reading of history (arm B+).
        """
        def rate_per_credit(op: str) -> float:
            return self.success_rate(op) / OPERATOR_BUDGETS.get(op, 1.0)

        return sorted(
            self.attempts,
            key=lambda op: (
                round(rate_per_credit(op), 12),
                round(self.sum_effect.get(op, 0.0)
                      / OPERATOR_BUDGETS.get(op, 1.0), 12),
                op,
            ),
            reverse=True,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "version": self.version,
            "event_range": self.event_range,
            "attempts": self.attempts,
            "successes": self.successes,
            "sum_effect": self.sum_effect,
            "sum_effect_sq": self.sum_effect_sq,
            "credits": self.credits,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KnowledgeSnapshot:
        return cls(
            snapshot_id=data["snapshot_id"],
            version=data["version"],
            event_range=list(data.get("event_range", [])),
            attempts=dict(data.get("attempts", {})),
            successes=dict(data.get("successes", {})),
            sum_effect={k: float(v) for k, v in data.get("sum_effect", {}).items()},
            sum_effect_sq={
                k: float(v)
                for k, v in data.get("sum_effect_sq", {}).items()
            },
            credits={k: float(v) for k, v in data.get("credits", {}).items()},
        )


@dataclass(frozen=True)
class SelectionRecord:
    """Full audit trail of one policy choice (protocol 230 §12)."""

    step: int
    operator: str
    policy: str
    policy_version: str
    family: str
    prior_stats: dict[str, float] | None
    posterior_stats: dict[str, float] | None
    selection_score: float
    selection_probability: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "operator": self.operator,
            "policy": self.policy,
            "policy_version": self.policy_version,
            "family": self.family,
            "prior_stats": self.prior_stats,
            "posterior_stats": self.posterior_stats,
            "selection_score": self.selection_score,
            "selection_probability": self.selection_probability,
            "reason": self.reason,
        }


class StaticPolicy:
    """Condition A: deterministic round-robin, no knowledge, no adaptation."""

    label = "static"
    version = STATIC_POLICY_VERSION

    def __init__(self, operators: tuple[str, ...]):
        self._operators = operators
        self._pointer = 0

    def select(self, family: str, step: int) -> tuple[str, SelectionRecord]:
        operator = self._operators[self._pointer % len(self._operators)]
        self._pointer += 1
        record = SelectionRecord(
            step=step,
            operator=operator,
            policy=self.label,
            policy_version=self.version,
            family=family,
            prior_stats=None,
            posterior_stats=None,
            selection_score=1.0 / len(self._operators),
            selection_probability=1.0 / len(self._operators),
            reason="round-robin schedule (static)",
        )
        return operator, record

    def reset(self) -> None:
        self._pointer = 0


class RandomPolicy:
    """Condition D: uniform random selection (calibration floor)."""

    label = "random"
    version = RANDOM_POLICY_VERSION

    def __init__(self, operators: tuple[str, ...], seed: int):
        self._operators = operators
        self._rng = random.Random(seed)

    def select(self, family: str, step: int) -> tuple[str, SelectionRecord]:
        operator = self._operators[self._rng.randrange(len(self._operators))]
        record = SelectionRecord(
            step=step,
            operator=operator,
            policy=self.label,
            policy_version=self.version,
            family=family,
            prior_stats=None,
            posterior_stats=None,
            selection_score=1.0 / len(self._operators),
            selection_probability=1.0 / len(self._operators),
            reason="uniform random (calibration)",
        )
        return operator, record


class KnowledgeInformedPolicy:
    """Condition B: frozen K0 ranking, top-K cycle, no in-episode updates.

    The snapshot is read once and stored; the policy never receives or
    records any outcome. Selecting from it is a pure function of K0 and the
    step counter, which is what makes temporal leakage impossible by
    construction.
    """

    label = "knowledge-informed"
    version = KNOWLEDGE_INFORMED_POLICY_VERSION

    def __init__(
        self,
        snapshot: KnowledgeSnapshot,
        top_k: int = 3,
        *,
        rank_by_cost: bool = False,
    ):
        if not snapshot.attempts:
            raise PolicyError("knowledge-informed policy requires a non-empty snapshot")
        self._snapshot = snapshot
        self._ranked = (
            snapshot.ranking_by_cost() if rank_by_cost else snapshot.ranking())
        self._top = self._ranked[: max(1, top_k)]
        self._pointer = 0
        self.snapshot_id = snapshot.snapshot_id
        self._basis = "cost-rank" if rank_by_cost else "rank"

    def select(self, family: str, step: int) -> tuple[str, SelectionRecord]:
        operator = self._top[self._pointer % len(self._top)]
        self._pointer += 1
        record = SelectionRecord(
            step=step,
            operator=operator,
            policy=self.label,
            policy_version=self.version,
            family=family,
            prior_stats={
                "success_rate": round(
                    self._snapshot.success_rate(operator), 6),
                "attempts": self._snapshot.attempts.get(operator, 0),
            },
            posterior_stats=None,
            selection_score=round(
                self._snapshot.success_rate(operator), 6),
            selection_probability=1.0 / len(self._top),
            reason=(
                f"frozen K0 {self._basis} "
                f"{self._ranked.index(operator) + 1}"
                f" of {len(self._ranked)} (top-{len(self._top)} cycle)"
            ),
        )
        return operator, record


class CostRankedKnowledgePolicy(KnowledgeInformedPolicy):
    """Protocol-231 arm B+: frozen K0 ranked by success rate per credit.

    Same no-update contract as B; only the frozen ordering basis differs.
    """

    label = "knowledge-informed-cost-rank"
    version = COST_RANKED_KNOWLEDGE_POLICY_VERSION

    def __init__(self, snapshot: KnowledgeSnapshot, top_k: int = 3):
        super().__init__(snapshot, top_k, rank_by_cost=True)


class AdaptivePolicy:
    """Condition C: per-family Thompson sampling over a Beta posterior.

    The posterior for (family, operator) starts from the K0 snapshot
    (identical to what B receives) and is updated after every completed
    experiment: success increments alpha, failure increments beta. The next
    selection samples theta ~ Beta(alpha, beta) per operator and picks the
    argmax.

    ``feedback_shuffle_seed`` enables the permuted-outcome ablation: when
    set, posterior updates are applied to a seeded-random *other* operator,
    destroying the operator-outcome association while keeping the selection
    machinery identical.
    """

    label = "adaptive"
    version = ADAPTIVE_POLICY_VERSION

    def __init__(
        self,
        snapshot: KnowledgeSnapshot,
        operators: tuple[str, ...],
        *,
        rng_seed: int,
        feedback_shuffle_seed: int | None = None,
    ):
        self._operators = operators
        self._rng = random.Random(rng_seed)
        self._shuffle_rng = (
            random.Random(feedback_shuffle_seed)
            if feedback_shuffle_seed is not None else None)
        self.snapshot_id = snapshot.snapshot_id
        self._snapshot_snapshot = snapshot
        self._alpha: dict[str, dict[str, float]] = {}
        self._beta: dict[str, dict[str, float]] = {}
        self._known_families: set[str] = set()
        for family in ("alpha", "beta"):
            self._init_family(family, snapshot)

    def _init_family(self, family: str, snapshot: KnowledgeSnapshot) -> None:
        """Initialize Beta posteriors for *family* from the K0 snapshot."""
        if family in self._known_families:
            return
        self._known_families.add(family)
        self._alpha[family] = {
            op: 1.0 + snapshot.successes.get(op, 0)
            for op in self._operators
        }
        self._beta[family] = {
            op: 1.0 + (snapshot.attempts.get(op, 0)
                       - snapshot.successes.get(op, 0))
            for op in self._operators
        }

    # -- introspection (tests + reporting) -------------------------------

    def posterior_stats(self, family: str, operator: str) -> dict[str, float]:
        if family not in self._known_families:
            self._init_family(family, self._snapshot_snapshot)
        a = self._alpha[family][operator]
        b = self._beta[family][operator]
        mean = a / (a + b)
        variance = (a * b) / ((a + b) ** 2 * (a + b + 1))
        return {
            "alpha": a,
            "beta": b,
            "mean": mean,
            "uncertainty": math.sqrt(max(variance, 0.0)),
        }

    def selection_distribution(self, family: str) -> dict[str, float]:
        """Current posterior means per operator for *family*."""
        if family not in self._known_families:
            self._init_family(family, self._snapshot_snapshot)
        return {
            op: self.posterior_stats(family, op)["mean"] for op in self._operators
        }

    # -- protocol --------------------------------------------------------

    def select(self, family: str, step: int) -> tuple[str, SelectionRecord]:
        # Lazy-init posteriors for unseen families (e.g. held-out gamma).
        if family not in self._known_families:
            self._init_family(family, self._snapshot_snapshot)
        scores: dict[str, float] = {}
        for op in self._operators:
            a = self._alpha[family][op]
            b = self._beta[family][op]
            scores[op] = self._rng.betavariate(a, b)
        operator = max(scores, key=lambda op: scores[op])
        record = SelectionRecord(
            step=step,
            operator=operator,
            policy=self.label,
            policy_version=self.version,
            family=family,
            prior_stats={
                op: round(self.posterior_stats(family, op)["mean"], 6)
                for op in self._operators
            },
            posterior_stats=self.posterior_stats(family, operator),
            selection_score=round(scores[operator], 6),
            selection_probability=round(
                self.posterior_stats(family, operator)["mean"], 6),
            reason=(
                f"thompson argmax of Beta posteriors (K0 prior; "
                f"{int(self._alpha[family][operator] - 1)} successes, "
                f"{int(self._beta[family][operator] - 1)} failures seen)"
            ),
        )
        return operator, record

    def update(self, family: str, operator: str, discovery: bool) -> None:
        """Update the posterior from one completed experiment.

        In the permuted-outcome ablation the update lands on a seeded-random
        operator instead of the one actually tried.
        """
        if family not in self._known_families:
            self._init_family(family, self._snapshot_snapshot)
        if self._shuffle_rng is not None:
            operator = self._operators[
                self._shuffle_rng.randrange(len(self._operators))]
        if discovery:
            self._alpha[family][operator] += 1.0
        else:
            self._beta[family][operator] += 1.0


class AdaptiveCostAwarePolicy(AdaptivePolicy):
    """Protocol-231 arm C+: Thompson sampling normalized by credit cost.

    Posteriors and updates are identical to :class:`AdaptivePolicy` (same
    K0 initialization, same binary-discovery feedback). The only mechanism
    difference is the selection score: ``theta / credit_cost`` where
    ``theta ~ Beta(alpha, beta)``, making the argmax track discoveries per
    credit rather than raw success probability. Everything else — including
    the absence of any other change — is the pre-registered single-mechanism
    test of the v1 beta-family diagnosis (protocol 231 §3).
    """

    label = "adaptive-cost-aware"
    version = ADAPTIVE_COST_AWARE_POLICY_VERSION

    def select(self, family: str, step: int) -> tuple[str, SelectionRecord]:
        if family not in self._known_families:
            self._init_family(family, self._snapshot_snapshot)
        scores: dict[str, float] = {}
        for op in self._operators:
            a = self._alpha[family][op]
            b = self._beta[family][op]
            scores[op] = self._rng.betavariate(a, b) / OPERATOR_BUDGETS[op]
        operator = max(scores, key=lambda op: scores[op])
        stats = self.posterior_stats(family, operator)
        record = SelectionRecord(
            step=step,
            operator=operator,
            policy=self.label,
            policy_version=self.version,
            family=family,
            prior_stats={
                op: round(self.posterior_stats(family, op)["mean"], 6)
                for op in self._operators
            },
            posterior_stats=stats,
            selection_score=round(scores[operator], 6),
            selection_probability=round(stats["mean"] / OPERATOR_BUDGETS[operator], 6),
            reason=(
                f"cost-normalized thompson argmax (theta/cost; "
                f"{int(self._alpha[family][operator] - 1)} successes, "
                f"{int(self._beta[family][operator] - 1)} failures seen; "
                f"cost {OPERATOR_BUDGETS[operator]:g})"
            ),
        )
        return operator, record


def build_prior_snapshot(
    aggregates: dict[str, dict[str, float]],
    *,
    snapshot_id: str,
    version: str = "1.0.0",
    event_range: list[str] | None = None,
) -> KnowledgeSnapshot:
    """Construct a K0 snapshot from raw aggregate counts.

    ``aggregates[operator]`` carries attempts / successes / sum_effect /
    sum_effect_sq / credits.
    """
    attempts: dict[str, int] = {}
    successes: dict[str, int] = {}
    sum_effect: dict[str, float] = {}
    sum_effect_sq: dict[str, float] = {}
    credits: dict[str, float] = {}
    for op, agg in aggregates.items():
        attempts[op] = int(agg["attempts"])
        successes[op] = int(agg["successes"])
        sum_effect[op] = float(agg.get("sum_effect", 0.0))
        sum_effect_sq[op] = float(agg.get("sum_effect_sq", 0.0))
        credits[op] = float(agg.get("credits", 0.0))
    return KnowledgeSnapshot(
        snapshot_id=snapshot_id,
        version=version,
        event_range=list(event_range or []),
        attempts=attempts,
        successes=successes,
        sum_effect=sum_effect,
        sum_effect_sq=sum_effect_sq,
        credits=credits,
    )


__all__ = [
    "STATIC_POLICY_VERSION",
    "KNOWLEDGE_INFORMED_POLICY_VERSION",
    "ADAPTIVE_POLICY_VERSION",
    "RANDOM_POLICY_VERSION",
    "ADAPTIVE_COST_AWARE_POLICY_VERSION",
    "COST_RANKED_KNOWLEDGE_POLICY_VERSION",
    "PolicyError",
    "KnowledgeSnapshot",
    "SelectionRecord",
    "StaticPolicy",
    "RandomPolicy",
    "KnowledgeInformedPolicy",
    "CostRankedKnowledgePolicy",
    "AdaptivePolicy",
    "AdaptiveCostAwarePolicy",
    "build_prior_snapshot",
]
