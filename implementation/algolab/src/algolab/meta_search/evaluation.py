"""Multi-stage policy evaluation and fail-closed promotion (Phases 6, 9).

Stage A (historical replay) can *only* diagnose; it can never promote.
Stage B (prospective) compares the candidate to the fixed baseline on fresh,
matched seeds using AlgoLab's deterministic toy substrate.
Stage C (independent confirmation) uses a held-out family with fresh seeds.
Stage D (promotion) is explicit, auditable and replayable.  Missing, failed or
degraded evidence fails closed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

from algolab.knowledge.operators import OPERATOR_BUDGETS
from algolab.meta_search.policies import Observation, SearchPolicy
from algolab.meta_search.replay import ReplayEnv, ReplayResult
from algolab.search.toy import (
    DEFAULT_OPERATORS,
    HELD_OUT_FAMILY,
    run_attempt,
)
from algolab.statistics import EffectAnalysis, analyze

EVALUATION_SCHEMA_VERSION = "meta-eval/1.0"
PRIMARY_METRIC = "discoveries_per_credit"
SECONDARY_METRIC = "distinct_useful_per_credit"


class PromotionStatus(StrEnum):
    PROMOTED = "PROMOTED"
    REJECTED_HISTORICAL_ONLY = "REJECTED_HISTORICAL_ONLY"
    REJECTED_PROSPECTIVE = "REJECTED_PROSPECTIVE"
    REJECTED_INDEPENDENT = "REJECTED_INDEPENDENT"
    REJECTED_INCOMPLETE = "REJECTED_INCOMPLETE"


@dataclass(frozen=True)
class PromotionDecision:
    status: PromotionStatus
    candidate_policy_id: str
    baseline_policy_id: str
    reasons: tuple[str, ...]
    evidence: dict[str, Any] = field(default_factory=dict)
    schema_version: str = EVALUATION_SCHEMA_VERSION

    def checksum(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        raw["status"] = self.status.value
        raw["promotion_checksum"] = self.checksum()
        return raw


def replay_evaluation(
    env: ReplayEnv, policy: SearchPolicy, *, seed: int = 0
) -> dict[str, Any]:
    """Stage A: decision quality, efficiency, coverage and explicit limits."""
    result: ReplayResult = env.run(policy, seed=seed)
    observed = [d for d in result.decisions if d.observed_outcome]
    spent = sum(
        float(
            (d.observed_outcome or {})
            .get("evaluation_result", {})
            .get("cost_credits", 1.0)
        )
        for d in observed
    )
    chosen_methods = [d.chosen_method for d in result.decisions]
    return {
        "stage": "A_historical_replay",
        "is_prospective_evidence": False,
        "decision_quality_agreement": result.agreement,
        "n_agreement_applicable": result.n_applicable,
        "n_decisions": len(result.decisions),
        "n_observed": result.observed_count,
        "n_counterfactual_uncertain": result.uncertain_count,
        "search_efficiency_credits": spent,
        "candidate_diversity": len(set(chosen_methods)),
        "coverage": len(set(chosen_methods)) / max(len(set(DEFAULT_OPERATORS)), 1),
        "failure_patterns": sorted(
            {
                str((d.observed_outcome or {}).get("fail_class"))
                for d in observed
                if (d.observed_outcome or {}).get("fail_class")
            }
        ),
        "replay_limitations": [
            "no outcome labels for unexplored branches",
            "cannot measure what would have happened off the recorded tree",
            "decision agreement is not a causal performance estimate",
        ],
    }


def _trial_score(
    policy: SearchPolicy,
    *,
    family: str,
    seed_base: int,
    trial: int,
    episodes: int,
    budget: float,
) -> dict[str, float]:
    """One deterministic prospective trial of a policy on one task family."""
    observations: list[Observation] = []
    credits = 0.0
    discoveries = 0
    useful_found: set[str] = set()
    for episode in range(episodes):
        selection = policy.select(
            tuple(DEFAULT_OPERATORS),
            tuple(observations),
            seed=seed_base + trial * 100_000 + episode,
            costs=OPERATOR_BUDGETS,
        )
        attempt = run_attempt(
            family,
            selection.method,
            seed_base=seed_base,
            trial=trial,
            episode=episode,
            attempt=episode,
        )
        credits += attempt.cost_credits
        if credits > budget:
            break
        if attempt.discovery:
            discoveries += 1
            useful_found.add(selection.method)
        observations.append(
            Observation(
                method=selection.method,
                cost_credits=attempt.cost_credits,
                mean_effect=attempt.mean_effect,
                discovery=attempt.discovery,
                valid=attempt.valid,
            )
        )
    denom = max(credits, 1e-9)
    return {
        "credits": credits,
        "discoveries": float(discoveries),
        PRIMARY_METRIC: discoveries / denom,
        SECONDARY_METRIC: len(useful_found) / denom,
    }


def _stage(
    policy: SearchPolicy,
    baseline: SearchPolicy,
    *,
    families: tuple[str, ...],
    seed_base: int,
    trials: int,
    episodes: int,
    budget: float,
    bootstrap_iterations: int,
    alpha: float,
) -> dict[str, Any]:
    primary: EffectAnalysis = analyze(
        [
            _trial_score(
                baseline,
                family=f,
                seed_base=seed_base,
                trial=t,
                episodes=episodes,
                budget=budget,
            )[PRIMARY_METRIC]
            for f in families
            for t in range(trials)
        ],
        [
            _trial_score(
                policy,
                family=f,
                seed_base=seed_base,
                trial=t,
                episodes=episodes,
                budget=budget,
            )[PRIMARY_METRIC]
            for f in families
            for t in range(trials)
        ],
        metric=PRIMARY_METRIC,
        seed=seed_base + 1,
        bootstrap_iterations=bootstrap_iterations,
        alpha=alpha,
    )
    secondary: EffectAnalysis = analyze(
        [
            _trial_score(
                baseline,
                family=f,
                seed_base=seed_base,
                trial=t,
                episodes=episodes,
                budget=budget,
            )[SECONDARY_METRIC]
            for f in families
            for t in range(trials)
        ],
        [
            _trial_score(
                policy,
                family=f,
                seed_base=seed_base,
                trial=t,
                episodes=episodes,
                budget=budget,
            )[SECONDARY_METRIC]
            for f in families
            for t in range(trials)
        ],
        metric=SECONDARY_METRIC,
        seed=seed_base + 2,
        bootstrap_iterations=bootstrap_iterations,
        alpha=alpha,
    )
    return {
        "families": list(families),
        "trials_per_family": trials,
        "episodes": episodes,
        "budget": budget,
        "seed_base": seed_base,
        "primary": {
            "delta": primary.delta,
            "ci_low": primary.ci_low,
            "ci_high": primary.ci_high,
            "p_value": primary.p_value,
            "effect_size": primary.effect_size,
            "baseline_mean": primary.baseline.mean,
            "candidate_mean": primary.candidate.mean,
        },
        "secondary": {
            "delta": secondary.delta,
            "ci_low": secondary.ci_low,
            "ci_high": secondary.ci_high,
            "p_value": secondary.p_value,
        },
    }


def evaluate_policy(
    policy: SearchPolicy,
    baseline: SearchPolicy,
    *,
    replay_env: ReplayEnv | None = None,
    families: tuple[str, ...] = ("alpha", "beta"),
    confirmation_family: str = HELD_OUT_FAMILY,
    seed_base: int = 424_242,
    confirmation_seed_base: int = 989_898,
    trials: int = 4,
    episodes: int = 8,
    budget: float = 10.0,
    bootstrap_iterations: int = 1000,
    alpha: float = 0.05,
) -> dict[str, Any]:
    """Run stages A/B/C and return a structured, reproducible evaluation."""
    stage_a = replay_evaluation(replay_env, policy) if replay_env is not None else None
    if stage_a is not None:
        stage_a["policy_checksum"] = policy.checksum()
    stage_b = _stage(
        policy,
        baseline,
        families=families,
        seed_base=seed_base,
        trials=trials,
        episodes=episodes,
        budget=budget,
        bootstrap_iterations=bootstrap_iterations,
        alpha=alpha,
    )
    stage_b["stage"] = "B_prospective"
    stage_b["is_prospective_evidence"] = True
    stage_c = _stage(
        policy,
        baseline,
        families=(confirmation_family,),
        seed_base=confirmation_seed_base,
        trials=trials,
        episodes=episodes,
        budget=budget,
        bootstrap_iterations=bootstrap_iterations,
        alpha=alpha,
    )
    stage_c["stage"] = "C_independent_confirmation"
    stage_c["is_prospective_evidence"] = True
    return {
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "candidate_policy_id": policy.policy_id,
        "baseline_policy_id": baseline.policy_id,
        "stage_a": stage_a,
        "stage_b": stage_b,
        "stage_c": stage_c,
        "preregistered": True,
    }


def promote(
    candidate: SearchPolicy,
    baseline: SearchPolicy,
    evaluation: dict[str, Any],
    *,
    alpha: float = 0.05,
    min_confirmation_delta: float = -0.001,
) -> PromotionDecision:
    """Stage D: fail-closed promotion with an auditable reason list."""
    reasons: list[str] = []
    stage_a = evaluation.get("stage_a")
    stage_b = evaluation.get("stage_b")
    stage_c = evaluation.get("stage_c")
    if not stage_a or not stage_b or not stage_c:
        return PromotionDecision(
            PromotionStatus.REJECTED_INCOMPLETE,
            candidate.policy_id,
            baseline.policy_id,
            ("missing one or more evaluation stages",),
            evaluation,
        )
    # Rule 1: replay alone can never promote.
    if stage_b.get("is_prospective_evidence") is not True:
        reasons.append("stage B is not prospective evidence")
    # Rule 2: must beat baseline prospectively with a positive lower CI bound.
    b = stage_b["primary"]
    # When several arms are tested, preregistered BH-FDR q-values replace raw p.
    effective_p = float(b.get("p_adjusted", b["p_value"]))
    if not (b["delta"] > 0 and b["ci_low"] > 0 and effective_p < alpha):
        reasons.append(
            "prospective primary metric did not significantly beat baseline "
            f"(delta={b['delta']:.6g}, ci_low={b['ci_low']:.6g}, p={effective_p:.6g})"
        )
    if stage_b["secondary"]["ci_low"] < 0:
        reasons.append("prospective secondary metric shows significant degradation")
    # Rule 3: independent held-out confirmation must not degrade generalization.
    c = stage_c["primary"]
    if not (c["delta"] >= 0 and c["ci_low"] >= min_confirmation_delta):
        reasons.append(
            "independent confirmation degraded on the held-out family "
            f"(delta={c['delta']:.6g}, ci_low={c['ci_low']:.6g})"
        )
    if stage_c.get("is_prospective_evidence") is not True:
        reasons.append("stage C is not prospective evidence")
    if reasons:
        return PromotionDecision(
            PromotionStatus.REJECTED_PROSPECTIVE
            if "prospective primary" in " ".join(reasons)
            else PromotionStatus.REJECTED_INDEPENDENT,
            candidate.policy_id,
            baseline.policy_id,
            tuple(reasons),
            evaluation,
        )
    return PromotionDecision(
        PromotionStatus.PROMOTED,
        candidate.policy_id,
        baseline.policy_id,
        ("all promotion gates passed",),
        evaluation,
    )


__all__ = [
    "EVALUATION_SCHEMA_VERSION",
    "PRIMARY_METRIC",
    "SECONDARY_METRIC",
    "PromotionStatus",
    "PromotionDecision",
    "replay_evaluation",
    "evaluate_policy",
    "promote",
]
