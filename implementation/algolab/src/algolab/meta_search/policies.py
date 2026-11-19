"""Versioned, reviewable search-policy representation (Phase 5).

A policy is a *structured, frozen* object -- never source code rewritten by an
agent.  It selects among available candidate-generation methods from prefix
observations only.  Four deterministic presets provide the protocol arms:
a fixed baseline, a DREAM-RSI-inspired replay/cost-aware heuristic, an evolved
configuration, and a seeded random control.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict, dataclass, field, replace
from typing import Any

POLICY_SCHEMA_VERSION = "meta-policy/1.0"


@dataclass(frozen=True)
class Observation:
    """A prefix-only measurement: method, cost, effect and discovery flag."""

    method: str
    cost_credits: float
    mean_effect: float
    discovery: bool
    valid: bool = True


@dataclass(frozen=True)
class Selection:
    method: str
    rationale: str
    exploration: bool = False


@dataclass(frozen=True)
class SearchPolicy:
    """A structured, independently evaluable policy proposal."""

    policy_id: str
    parent_policy_id: str | None
    version: int
    name: str
    kind: str  # fixed | replay_cost_aware | evolved | random_control
    config: dict[str, float] = field(default_factory=dict)
    exact_change: str = ""
    rationale: str = ""
    expected_effect: str = ""
    hypothesis: str = ""
    relevant_evidence: tuple[str, ...] = ()
    proposed_evaluation: str = ""
    resource_budget: float = 0.0
    rollback_path: str = ""
    schema_version: str = POLICY_SCHEMA_VERSION

    def content(self) -> dict[str, Any]:
        return asdict(self)

    def checksum(self) -> str:
        payload = json.dumps(self.content(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def validate(self) -> None:
        if self.kind not in {"fixed", "replay_cost_aware", "evolved", "random_control"}:
            raise ValueError(f"unknown policy kind: {self.kind}")
        if self.version < 1:
            raise ValueError("policy version must be >= 1")
        if not self.exact_change or not self.rollback_path:
            raise ValueError("a proposal needs exact_change and rollback_path")
        if self.schema_version != POLICY_SCHEMA_VERSION:
            raise ValueError(f"unsupported policy schema: {self.schema_version}")

    def select(
        self,
        candidates: tuple[str, ...],
        observations: tuple[Observation, ...],
        *,
        seed: int,
    ) -> Selection:
        """Choose one method from *candidates* using only prefix observations."""
        if self.kind == "random_control":
            rng = random.Random(seed)
            return Selection(rng.choice(list(candidates)), "seeded uniform control", True)
        if self.kind == "fixed":
            priority = self.config.get("priority", 0.0)
            ordered = sorted(candidates)
            # A fixed policy commits to a lexicographic priority order; ``priority``
            # rotates the starting point deterministically across episodes.
            idx = int(priority) % len(ordered)
            rotated = ordered[idx:] + ordered[:idx]
            return Selection(rotated[0], "fixed priority order (no learning)")

        # Cost-aware family: score by observed success probability and its
        # per-credit efficiency; epsilon provides bounded exploration.
        alpha = self.config.get("alpha", 1.0)
        beta = self.config.get("beta", 1.0)
        gamma = self.config.get("gamma", 0.0)
        epsilon = self.config.get("epsilon", 0.0)
        rng = random.Random(seed)
        if epsilon > 0.0 and rng.random() < epsilon:
            return Selection(rng.choice(list(candidates)), "epsilon exploration", True)

        stats: dict[str, dict[str, float]] = {}
        for obs in observations:
            bucket = stats.setdefault(
                obs.method, {"n": 0.0, "wins": 0.0, "credits": 0.0, "effect": 0.0}
            )
            bucket["n"] += 1.0
            bucket["wins"] += 1.0 if obs.discovery else 0.0
            bucket["credits"] += max(obs.cost_credits, 1e-9)
            bucket["effect"] += obs.mean_effect if obs.valid else 0.0

        def score(method: str) -> float:
            bucket = stats.get(method)
            if not bucket or bucket["n"] == 0:
                # Unknown methods get an optimistic prior so they are tried once.
                return alpha * 1.0 + beta * 1.0
            n = bucket["n"]
            win_rate = bucket["wins"] / n
            per_credit = bucket["wins"] / bucket["credits"]
            avg_effect = bucket["effect"] / n
            return alpha * win_rate + beta * per_credit + gamma * avg_effect

        chosen = max(candidates, key=lambda name: (score(name), -ord(name[0]) if name else 0, name))
        return Selection(chosen, f"score={score(chosen):.4f} (prefix observations only)")


def _preset(
    name: str,
    kind: str,
    version: int,
    config: dict[str, float],
    exact_change: str,
    rationale: str,
) -> SearchPolicy:
    policy = SearchPolicy(
        policy_id=f"pol-{name}",
        parent_policy_id=None,
        version=version,
        name=name,
        kind=kind,
        config=config,
        exact_change=exact_change,
        rationale=rationale,
        expected_effect="Measured by protocol 241 prospective evaluation",
        hypothesis="Cost-aware prefix selection improves discoveries per credit",
        proposed_evaluation="protocol-241 matched prospective + held-out confirmation",
        resource_budget=0.0,
        rollback_path="Revert active policy pointer to the previous promoted policy_id",
    )
    policy.validate()
    return policy


BASELINE_POLICY = _preset(
    "fixed-baseline", "fixed", 1, {"priority": 0},
    "Initial fixed lexicographic search policy", "Existing AlgoLab fixed search behaviour",
)
REPLAY_POLICY = _preset(
    "replay-cost-aware", "replay_cost_aware", 1,
    {"alpha": 0.25, "beta": 0.75, "gamma": 0.0, "epsilon": 0.10},
    "Score methods by observed success-per-credit with 10% exploration",
    "DREAM-RSI replay: cheap-and-good branches deserve more spend",
)
EVOLVED_POLICY = _preset(
    "evolved", "evolved", 2,
    {"alpha": 0.0, "beta": 1.0, "gamma": 0.5, "epsilon": 0.05},
    "Commit to per-credit efficiency with an effect-size term and 5% exploration",
    "Prior protocols found commitment plus cost-awareness efficient in-domain",
)
CONTROL_POLICY = _preset(
    "random-control", "random_control", 1, {},
    "Seeded uniform random method selection", "Calibration floor for any learned policy",
)


def propose_policy(
    parent: SearchPolicy,
    *,
    name: str,
    config: dict[str, float],
    exact_change: str,
    rationale: str,
    expected_effect: str = "",
    evidence: tuple[str, ...] = (),
    budget: float = 0.0,
) -> SearchPolicy:
    """Create a structured child proposal with a stable content-derived id."""
    draft = replace(
        parent,
        policy_id="",
        parent_policy_id=parent.policy_id,
        version=parent.version + 1,
        name=name,
        config=dict(config),
        exact_change=exact_change,
        rationale=rationale,
        expected_effect=expected_effect or parent.expected_effect,
        relevant_evidence=evidence,
        proposed_evaluation=parent.proposed_evaluation,
        resource_budget=budget,
    )
    digest = draft.checksum()
    proposal = replace(draft, policy_id=f"pol-{name}-{digest[:12]}")
    proposal.validate()
    return proposal


__all__ = [
    "POLICY_SCHEMA_VERSION",
    "Observation",
    "Selection",
    "SearchPolicy",
    "BASELINE_POLICY",
    "REPLAY_POLICY",
    "EVOLVED_POLICY",
    "CONTROL_POLICY",
    "propose_policy",
]
