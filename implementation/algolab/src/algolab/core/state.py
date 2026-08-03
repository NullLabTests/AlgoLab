"""Lifecycle state machines.

Transitions are fail-closed: an invalid transition raises
``InvalidStateTransition`` *before* anything is persisted.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

# Experiment statuses come from schemas/experiment.schema.json.
EXPERIMENT_STATUSES: Final[tuple[str, ...]] = (
    "draft",
    "planned",
    "approved",
    "running",
    "analyzing",
    "completed",
    "failed",
    "cancelled",
    "archived",
)

EXPERIMENT_TRANSITIONS: Final[Mapping[str, frozenset[str]]] = {
    "draft": frozenset({"planned", "cancelled", "archived"}),
    # REVISED (MASTER_SPEC.md §5) is modelled as failed -> draft.
    "planned": frozenset({"approved", "cancelled", "archived"}),
    "approved": frozenset({"running", "cancelled"}),
    "running": frozenset({"analyzing", "failed", "cancelled"}),
    "analyzing": frozenset({"completed", "failed"}),
    "completed": frozenset({"archived"}),
    "failed": frozenset({"draft", "archived"}),
    "cancelled": frozenset({"archived"}),
    "archived": frozenset(),
}

RUN_STATUSES: Final[tuple[str, ...]] = (
    "pending",
    "running",
    "completed",
    "failed",
    "cancelled",
)

RUN_TRANSITIONS: Final[Mapping[str, frozenset[str]]] = {
    "pending": frozenset({"running", "cancelled"}),
    "running": frozenset({"completed", "failed", "cancelled"}),
    "completed": frozenset(),
    "failed": frozenset(),
    "cancelled": frozenset(),
}


class InvalidStateTransition(ValueError):
    """Raised when a transition is not permitted by the state machine."""


class StateMachine:
    """Acyclic-ish state machine with an explicit transition table.

    ``require_transition`` is the only way to change ``status`` on an entity;
    it raises before any write occurs.
    """

    def __init__(self, transitions: Mapping[str, frozenset[str]]) -> None:
        self._transitions = {
            state: frozenset(targets) for state, targets in transitions.items()
        }
        for targets in self._transitions.values():
            for target in targets:
                if target not in self._transitions:
                    raise ValueError(
                        f"transition table has unknown target {target!r}"
                    )

    def states(self) -> tuple[str, ...]:
        return tuple(self._transitions)

    def can_transition(self, current: str, target: str) -> bool:
        return target in self._transitions.get(current, frozenset())

    def require_transition(self, current: str, target: str) -> None:
        if current not in self._transitions:
            raise InvalidStateTransition(
                f"unknown state {current!r}; known states: {list(self._transitions)}"
            )
        if not self.can_transition(current, target):
            raise InvalidStateTransition(
                f"invalid transition {current!r} -> {target!r} for this lifecycle; "
                f"allowed targets from {current!r}: "
                f"{sorted(self._transitions[current])}"
            )


EXPERIMENT_MACHINE: Final[StateMachine] = StateMachine(EXPERIMENT_TRANSITIONS)
RUN_MACHINE: Final[StateMachine] = StateMachine(RUN_TRANSITIONS)
