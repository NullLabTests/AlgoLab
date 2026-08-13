"""Run state machine + persistence behavior (M1 lifecycle)."""

import pytest

from algolab.core.state import (
    EXPERIMENT_MACHINE,
    RUN_MACHINE,
    InvalidStateTransition,
)
from tests.conftest import (
    expand,
    make_approved_experiment,
)


def test_machine_covers_all_statuses() -> None:
    for status in ("CREATED", "QUEUED", "CLAIMED", "STARTING", "RUNNING",
                   "SUCCEEDED", "FAILED", "CANCELLED", "ORPHANED"):
        assert status in RUN_MACHINE.states()


def test_rejected_transition_appends_audit_event(conn, run_repo) -> None:
    exp_id = make_approved_experiment(conn)
    run_id = expand(conn, exp_id).run_ids[0]
    with conn:
        with pytest.raises(InvalidStateTransition):
            run_repo.transition(run_id, "SUCCEEDED")  # QUEUED -> SUCCEEDED illegal

    from algolab.storage.event_store import EventStore

    events = EventStore(conn).list_for_entity(run_id)
    rejected = [e for e in events if e.mutation == "transition_rejected"]
    assert len(rejected) == 1
    assert rejected[0].old_state == "QUEUED"
    assert rejected[0].new_state == "SUCCEEDED"
    assert run_repo.get(run_id).status == "QUEUED"


def test_run_rows_are_audited_on_every_transition(conn, run_repo) -> None:
    exp_id = make_approved_experiment(conn)
    run_id = expand(conn, exp_id).run_ids[0]
    with conn:
        for target in ("CLAIMED", "STARTING", "RUNNING", "SUCCEEDED"):
            run_repo.transition(run_id, target)
    from algolab.storage.event_store import EventStore

    events = EventStore(conn).list_for_entity(run_id)
    status_events = [e for e in events if e.mutation == "status_changed"]
    assert [e.new_state for e in status_events] == [
        "QUEUED", "CLAIMED", "STARTING", "RUNNING", "SUCCEEDED",
    ]


def test_terminal_runs_are_immutable(conn, run_repo) -> None:
    exp_id = make_approved_experiment(conn)
    run_id = expand(conn, exp_id).run_ids[0]
    with conn:
        for target in ("CLAIMED", "STARTING", "RUNNING", "SUCCEEDED"):
            run_repo.transition(run_id, target)
    with pytest.raises(InvalidStateTransition):
        run_repo.transition(run_id, "FAILED")


def test_experiment_machine_unchanged() -> None:
    assert EXPERIMENT_MACHINE.can_transition("approved", "running")
    assert EXPERIMENT_MACHINE.can_transition("running", "analyzing")
