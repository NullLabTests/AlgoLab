"""Historical replay environment (Phases 4, 10).

The environment reconstructs the *decisions available at a recorded state* and
runs an alternative policy against them.  It is deliberately unable to invent
outcomes:

* OBSERVED            - the selected branch exists in the historical trace;
* COUNTERFACTUAL      - the decision is recorded, but no outcome exists because
                        that branch was never explored (all outcome fields are
                        ``None`` and ``uncertain`` is true);
* ESTIMATED           - reserved for explicitly supplied external estimates;
* PROSPECTIVE         - can only be produced by a real experiment, never here.

Any attempt to present replay output as prospective evidence is rejected by
:func:`assert_not_prospective`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

from algolab.meta_search.policies import Observation, SearchPolicy
from algolab.meta_search.traces import DiscoveryTrace, TraceNode

REPLAY_SCHEMA_VERSION = "meta-replay/1.0"


class OutcomeKind(StrEnum):
    OBSERVED = "observed"
    COUNTERFACTUAL_UNCERTAIN = "counterfactual_uncertain"
    ESTIMATED = "estimated"
    PROSPECTIVE = "prospective"


@dataclass(frozen=True)
class ReplayDecision:
    state_node_id: str
    depth: int
    available_methods: tuple[str, ...]
    chosen_method: str
    historically_chosen_method: str | None
    outcome_kind: OutcomeKind
    observed_outcome: dict[str, Any] | None = None
    estimated_outcome: dict[str, Any] | None = None
    uncertain: bool = True
    uncertainty_reason: str = ""
    matches_historical: bool = False
    agreement_applicable: bool = True
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        raw["outcome_kind"] = self.outcome_kind.value
        raw["available_methods"] = list(self.available_methods)
        return raw


@dataclass
class ReplayResult:
    schema_version: str = REPLAY_SCHEMA_VERSION
    trace_id: str = ""
    policy_id: str = ""
    decisions: list[ReplayDecision] = field(default_factory=list)

    @property
    def observed_count(self) -> int:
        return sum(d.outcome_kind == OutcomeKind.OBSERVED for d in self.decisions)

    @property
    def uncertain_count(self) -> int:
        return sum(d.uncertain for d in self.decisions)

    @property
    def n_applicable(self) -> int:
        return sum(d.agreement_applicable for d in self.decisions)

    @property
    def agreement(self) -> float:
        # Agreement is only defined where the trace records an actual decision.
        applicable = self.n_applicable
        if not applicable:
            return 0.0
        return sum(
            d.matches_historical for d in self.decisions if d.agreement_applicable
        ) / applicable

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "trace_id": self.trace_id,
            "policy_id": self.policy_id,
            "evidence_class": "historical_replay",
            "is_prospective_evidence": False,
            "decisions": [d.to_dict() for d in self.decisions],
            "summary": {
                "n_decisions": len(self.decisions),
                "n_observed": self.observed_count,
                "n_uncertain": self.uncertain_count,
                "n_agreement_applicable": self.n_applicable,
                "agreement_with_history": self.agreement,
            },
        }


def assert_not_prospective(result: ReplayResult) -> None:
    """Fail closed if replay output is being presented as prospective data."""
    if any(d.outcome_kind == OutcomeKind.PROSPECTIVE for d in result.decisions):
        raise ValueError("replay produced a PROSPECTIVE outcome label -- invalid")
    if result.to_dict()["is_prospective_evidence"]:
        raise ValueError("replay result claims to be prospective evidence")


def _observation_from_node(node: TraceNode) -> Observation:
    derived = node.derived_metrics
    obs = node.observation
    mean_effect = float(derived.get("mean_effect", obs.get("mean_effect", 0.0)))
    discovery = bool(obs.get("discovery", False) or derived.get("discovery", False))
    return Observation(
        method=node.candidate_generation_method,
        cost_credits=float(node.compute_credits or obs.get("cost_credits", 1.0)),
        mean_effect=mean_effect,
        discovery=discovery,
        valid=bool(obs.get("valid", True)),
    )


def _prefix_observations(
    trace: DiscoveryTrace, node: TraceNode
) -> tuple[Observation, ...]:
    """Observations from ancestors only -- never the current/future nodes."""
    by_id = {n.node_id: n for n in trace.nodes}
    out: list[Observation] = []
    cursor = node.parent_id
    while cursor is not None:
        ancestor = by_id.get(cursor)
        if ancestor is None:
            break
        out.append(_observation_from_node(ancestor))
        cursor = ancestor.parent_id
    return tuple(reversed(out))


class ReplayEnv:
    """Reconstructs decision states from a frozen discovery trace."""

    def __init__(
        self,
        trace: DiscoveryTrace,
        *,
        unexplored_candidates: tuple[str, ...] = (),
        costs: Mapping[str, float] | None = None,
    ) -> None:
        if not trace.verify_integrity():
            raise ValueError("cannot replay a trace that fails integrity verification")
        self.trace = trace
        self.unexplored_candidates = tuple(unexplored_candidates)
        self.costs = costs

    def available_actions(self, node_id: str) -> tuple[str, ...]:
        children = self.trace.children(node_id)
        methods = list(dict.fromkeys(c.candidate_generation_method for c in children))
        for method in self.unexplored_candidates:
            if method not in methods:
                methods.append(method)
        return tuple(methods)

    def run(self, policy: SearchPolicy, *, seed: int = 0) -> ReplayResult:
        """Evaluate *policy* at every recorded internal decision state."""
        result = ReplayResult(trace_id=self.trace.trace_id, policy_id=policy.policy_id)
        for node in self.trace.nodes:
            children = self.trace.children(node.node_id)
            methods = self.available_actions(node.node_id)
            if not children and not self.unexplored_candidates:
                continue  # leaf state with no recorded decision
            observations = _prefix_observations(self.trace, node)
            selection = policy.select(
                methods, observations, seed=seed + len(observations), costs=self.costs
            )
            child_by_method = {c.candidate_generation_method: c for c in children}
            recorded = node.search_parameters.get("historical_choice")
            historical = recorded if isinstance(recorded, str) else None
            applicable = historical is not None and historical in methods
            chosen_child = child_by_method.get(selection.method)
            if chosen_child is not None:
                decision = ReplayDecision(
                    state_node_id=node.node_id,
                    depth=len(observations),
                    available_methods=methods,
                    chosen_method=selection.method,
                    historically_chosen_method=historical,
                    outcome_kind=OutcomeKind.OBSERVED,
                    observed_outcome={
                        **chosen_child.observation,
                        **chosen_child.derived_metrics,
                        "evaluation_result": chosen_child.evaluation_result,
                    },
                    estimated_outcome=None,
                    uncertain=False,
                    uncertainty_reason="",
                    matches_historical=applicable and selection.method == historical,
                    agreement_applicable=applicable,
                    rationale=selection.rationale,
                )
            else:
                decision = ReplayDecision(
                    state_node_id=node.node_id,
                    depth=len(observations),
                    available_methods=methods,
                    chosen_method=selection.method,
                    historically_chosen_method=historical,
                    outcome_kind=OutcomeKind.COUNTERFACTUAL_UNCERTAIN,
                    observed_outcome=None,
                    estimated_outcome=None,
                    uncertain=True,
                    uncertainty_reason=(
                        "branch was never explored in the historical trace; "
                        "no outcome label exists and none was manufactured"
                    ),
                    matches_historical=False,
                    agreement_applicable=applicable,
                    rationale=selection.rationale,
                )
            result.decisions.append(decision)
        assert_not_prospective(result)
        return result

    def deterministic_artifact(
        self, policy: SearchPolicy, *, seed: int = 0
    ) -> dict[str, Any]:
        """Replay artifact with an explicit limitations section."""
        result = self.run(policy, seed=seed)
        payload = result.to_dict()
        payload["limitations"] = [
            "Replay evaluates decisions at recorded states only.",
            "It cannot establish outcomes for branches never explored.",
            "Counterfactual decisions carry no outcome label (uncertain=true).",
            "Historical replay is not prospective evidence and cannot promote.",
        ]
        payload["observed_vs_counterfactual"] = {
            "observed": result.observed_count,
            "counterfactual_uncertain": result.uncertain_count,
        }
        return payload


__all__ = [
    "REPLAY_SCHEMA_VERSION",
    "OutcomeKind",
    "ReplayDecision",
    "ReplayResult",
    "ReplayEnv",
    "assert_not_prospective",
]
