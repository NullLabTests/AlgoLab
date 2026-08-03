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


def test_run_machine() -> None:
    assert RUN_MACHINE.can_transition("pending", "running")
    assert RUN_MACHINE.can_transition("running", "completed")
    assert RUN_MACHINE.can_transition("running", "failed")
    with pytest.raises(InvalidStateTransition):
        RUN_MACHINE.require_transition("pending", "completed")
    with pytest.raises(InvalidStateTransition):
        RUN_MACHINE.require_transition("completed", "running")


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
