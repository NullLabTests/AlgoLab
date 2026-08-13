"""State machine: allowed transitions, fail-closed behavior, no partial writes."""

import pytest

from algolab.core.ids import new_id
from algolab.core.state import (
    EXPERIMENT_MACHINE,
    RUN_MACHINE,
    InvalidStateTransition,
)
from tests.conftest import (
    approve_experiment,
    make_experiment,
    make_hypothesis,
)


def test_experiment_happy_path() -> None:
    exp = make_experiment("HYP-12345678")
    assert exp.status == "draft"
    for current, target in [
        ("draft", "planned"),
        ("planned", "approved"),
        ("approved", "running"),
        ("running", "analyzing"),
        ("analyzing", "completed"),
        ("completed", "archived"),
    ]:
        assert EXPERIMENT_MACHINE.can_transition(current, target)
        EXPERIMENT_MACHINE.require_transition(current, target)


def test_experiment_invalid_transitions_raise() -> None:
    with pytest.raises(InvalidStateTransition):
        EXPERIMENT_MACHINE.require_transition("draft", "running")
    with pytest.raises(InvalidStateTransition):
        EXPERIMENT_MACHINE.require_transition("running", "draft")
    with pytest.raises(InvalidStateTransition):
        EXPERIMENT_MACHINE.require_transition("completed", "analyzing")
    with pytest.raises(InvalidStateTransition):
        EXPERIMENT_MACHINE.require_transition("archived", "draft")


def test_experiment_failed_to_draft_is_revision() -> None:
    assert EXPERIMENT_MACHINE.can_transition("failed", "draft")
    assert EXPERIMENT_MACHINE.can_transition("failed", "archived")


def test_run_machine_happy_path() -> None:
    """M1 run lifecycle: all allowed transitions."""
    path: list[tuple[str, str]] = [
        ("CREATED", "QUEUED"),
        ("QUEUED", "CLAIMED"),
        ("CLAIMED", "STARTING"),
        ("STARTING", "RUNNING"),
        ("RUNNING", "SUCCEEDED"),
    ]
    for current, target in path:
        assert RUN_MACHINE.can_transition(current, target)
        RUN_MACHINE.require_transition(current, target)


def test_run_machine_failure_and_cancellation_paths() -> None:
    assert RUN_MACHINE.can_transition("QUEUED", "CANCELLED")
    assert RUN_MACHINE.can_transition("CLAIMED", "FAILED")
    assert RUN_MACHINE.can_transition("STARTING", "CANCELLED")
    assert RUN_MACHINE.can_transition("RUNNING", "FAILED")
    assert RUN_MACHINE.can_transition("RUNNING", "CANCELLED")
    assert RUN_MACHINE.can_transition("RUNNING", "ORPHANED")
    assert RUN_MACHINE.can_transition("ORPHANED", "QUEUED")
    assert RUN_MACHINE.can_transition("ORPHANED", "FAILED")


def test_run_machine_terminals_are_terminal() -> None:
    for terminal in ("SUCCEEDED", "FAILED", "CANCELLED"):
        assert RUN_MACHINE.states()
        assert not RUN_MACHINE.can_transition(terminal, "CREATED")
        assert not RUN_MACHINE.can_transition(terminal, "QUEUED")
        for target in RUN_MACHINE.states():
            if target != terminal:
                with pytest.raises(InvalidStateTransition):
                    RUN_MACHINE.require_transition(terminal, target)


def test_run_machine_invalid_transitions_raise() -> None:
    with pytest.raises(InvalidStateTransition):
        RUN_MACHINE.require_transition("CREATED", "CLAIMED")
    with pytest.raises(InvalidStateTransition):
        RUN_MACHINE.require_transition("QUEUED", "RUNNING")
    with pytest.raises(InvalidStateTransition):
        RUN_MACHINE.require_transition("SUCCEEDED", "FAILED")
    with pytest.raises(InvalidStateTransition):
        RUN_MACHINE.require_transition("ORPHANED", "RUNNING")
    with pytest.raises(InvalidStateTransition):
        RUN_MACHINE.require_transition("FAILED", "QUEUED")


def test_unknown_state_rejected() -> None:
    with pytest.raises(InvalidStateTransition):
        EXPERIMENT_MACHINE.require_transition("banana", "draft")


def test_invalid_transition_is_not_persisted(conn, hyp_repo, exp_repo) -> None:
    """/fail-closed: a rejected transition leaves status and events untouched."""
    hid = hyp_repo.create(make_hypothesis())
    exp_id = exp_repo.create(make_experiment(hid))
    approve_experiment(exp_repo, exp_id)

    before = exp_repo.status(exp_id)
    with pytest.raises(InvalidStateTransition):
        exp_repo.transition(exp_id, "draft")  # approved -> draft is illegal
    assert exp_repo.status(exp_id) == before

    from algolab.storage.event_store import EventStore

    events = EventStore(conn).list_for_entity(exp_id)
    assert not any(e.mutation == "status_changed"
                   and e.new_state == "draft" for e in events)


def make_id(prefix: str) -> str:
    return new_id(prefix)
