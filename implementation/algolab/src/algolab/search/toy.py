"""Deterministic toy algorithm-discovery environment (M5, protocol 230).

The environment provides a falsifiable substrate for the cumulative-search
hypothesis: each task family has a hidden per-operator ground-truth effect
(useful / neutral / harmful), measurement is seeded and noisy, and a
replication gate must pass for an attempt to count as a *validated
discovery*.

The environment is deliberately boring: no ML, no LLM. It exists so the
A/B/C harness can detect a genuine search-policy advantage (or fail to).
All randomness is seeded by deterministic integers derived from the
experiment manifest, so identical manifests reproduce byte-for-byte.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from algolab.knowledge.operators import OPERATOR_BUDGETS, OPERATOR_CATALOG

TOY_ENVIRONMENT_VERSION = "1.1.0"
TASK_SUITE_VERSION = "1.1.0"
DISCOVERY_GATE_VERSION = "1.0.0"

TASK_FAMILIES: tuple[str, ...] = ("alpha", "beta")
HELD_OUT_FAMILY: str = "gamma"

PROMOTION_THRESHOLD = 0.15      # effect must be >= this on the primary metric
EFFECT_SIGMA = 0.12             # measurement noise
VALIDATION_PROBABILITY = 0.90   # P(implementation is valid)

# Hidden ground truth per family (versioned; never exposed to policies).
# mu_useful / mu_neutral / mu_harmful.
# gamma is the held-out family: never seen by prior (K0), so B and C receive
# no information about it before evaluation.  It has a different useful
# operator set from alpha/beta, providing evidence on whether the adaptive
# advantage transfers beyond training families (though it does not by itself
# rule out all forms of benchmark-specific adaptation).
_GROUND_TRUTH: dict[str, dict[str, float]] = {
    "alpha": {
        "tune": 0.35, "decompose": 0.35, "validate": 0.35,
        "reparameterize": 0.02, "synthesize": 0.02, "refresh": 0.02,
        "polyglot": -0.35, "rollback": -0.35,
    },
    "beta": {
        "reparameterize": 0.35, "synthesize": 0.35, "refresh": 0.35,
        "tune": 0.02, "decompose": 0.02, "validate": 0.02,
        "polyglot": -0.35, "rollback": -0.35,
    },
    "gamma": {
        "decompose": 0.35, "reparameterize": 0.35, "refresh": 0.35,
        "tune": 0.02, "validate": 0.02, "synthesize": 0.02,
        "polyglot": -0.35, "rollback": -0.35,
    },
}

DEFAULT_OPERATORS: tuple[str, ...] = tuple(OPERATOR_CATALOG)

VALIDATION_SEED_SCALE = 1_000_000
EFFECT_SEED_SCALE = 2_000_000


@dataclass(frozen=True)
class Attempt:
    """One operator application with a two-seed replicate measurement."""

    operator: str
    cost_credits: float
    valid: bool
    effect_1: float
    effect_2: float
    mean_effect: float
    discovery: bool


def operator_cost(operator: str) -> float:
    return OPERATOR_BUDGETS[operator]


def ground_truth_effect(family: str, operator: str) -> float:
    return _GROUND_TRUTH[family][operator]


def is_useful(family: str, operator: str) -> bool:
    return ground_truth_effect(family, operator) >= 0.30


def is_harmful(family: str, operator: str) -> bool:
    return ground_truth_effect(family, operator) <= -0.30


def _measure_seed(seed_base: int, trial: int, episode: int,
                  attempt: int, replicate: int) -> int:
    """Deterministic, collision-free seed for one replicate measurement."""
    return (trial * 100_000_000 + episode * 1_000_000
            + attempt * 1000 + replicate + seed_base)


def run_attempt(family: str, operator: str, *, seed_base: int,
                trial: int, episode: int, attempt: int,
                threshold: float = PROMOTION_THRESHOLD) -> Attempt:
    """Measure one operator application on *family* with 2 replicate seeds.

    Deterministic given the manifest integers. A discovery requires both
    replicates to pass the promotion threshold (the replication gate).
    """
    mu = _GROUND_TRUTH[family][operator]
    cost = operator_cost(operator)

    def _measure(replicate: int) -> tuple[bool, float]:
        rng = random.Random(
            _measure_seed(seed_base, trial, episode, attempt, replicate))
        valid = rng.random() < VALIDATION_PROBABILITY
        effect = mu + EFFECT_SIGMA * rng.gauss(0.0, 1.0)
        return valid, effect

    v1, e1 = _measure(1)
    v2, e2 = _measure(2)
    valid = v1 and v2
    mean = (e1 + e2) / 2.0
    discovery = valid and e1 >= threshold and e2 >= threshold
    return Attempt(
        operator=operator,
        cost_credits=cost,
        valid=valid,
        effect_1=e1,
        effect_2=e2,
        mean_effect=mean,
        discovery=discovery,
    )


__all__ = [
    "TOY_ENVIRONMENT_VERSION",
    "TASK_SUITE_VERSION",
    "DISCOVERY_GATE_VERSION",
    "TASK_FAMILIES",
    "HELD_OUT_FAMILY",
    "PROMOTION_THRESHOLD",
    "EFFECT_SIGMA",
    "VALIDATION_PROBABILITY",
    "Attempt",
    "operator_cost",
    "ground_truth_effect",
    "is_useful",
    "is_harmful",
    "run_attempt",
    "DEFAULT_OPERATORS",
]
