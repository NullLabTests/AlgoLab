"""Repository behavior: creates, references, transitions, lineage, events."""

import pytest

from algolab.core.state import InvalidStateTransition
from algolab.storage.event_store import EventStore
from algolab.storage.repositories import (
    EntityNotFound,
    InvariantViolation,
    LineageQuery,
)
from tests.conftest import (
    approve_experiment,
    expand,
    make_approved_experiment,
    make_candidate,
    make_experiment,
    make_hypothesis,
    make_result,
)


def test_hypothesis_create_get(conn, hyp_repo) -> None:
    h = make_hypothesis()
    with conn:
        hyp_repo.create(h)
    assert hyp_repo.get(h.id) == h


def test_candidate_requires_existing_hypothesis(conn, cand_repo) -> None:
    c = make_candidate("HYP-00000000")
    with conn:
        with pytest.raises(InvariantViolation):
            cand_repo.create(c)


def test_candidate_lineage_parent_must_exist(conn, hyp_repo, cand_repo) -> None:
    h = make_hypothesis()
    with conn:
        hyp_repo.create(h)
        c = make_candidate(h.id, parent_ids=["CAND-00000000"])
        with pytest.raises(InvariantViolation):
            cand_repo.create(c)


def test_experiment_requires_hypothesis_and_candidate(conn, hyp_repo, cand_repo,
                                                     exp_repo) -> None:
    with conn:
        with pytest.raises(InvariantViolation):
            exp_repo.create(make_experiment("HYP-00000000"))
        h = make_hypothesis()
        hyp_repo.create(h)
        c = make_candidate(h.id)
        cand_repo.create(c)
        exp_repo.create(make_experiment(h.id, c.id))


def test_run_requires_approved_experiment(conn, hyp_repo, cand_repo, exp_repo,
                                          run_repo) -> None:
    with conn:
        h = make_hypothesis()
        hyp_repo.create(h)
        c = make_candidate(h.id)
        cand_repo.create(c)
        exp_id = exp_repo.create(make_experiment(h.id, c.id))

        # draft experiment -> expansion refused (all-or-nothing)
        from algolab.control.config import AlgolabConfig
        from algolab.execution.expansion import (
            ExperimentExpansion,
            ExperimentNotApproved,
        )

        with pytest.raises(ExperimentNotApproved):
            ExperimentExpansion(
                conn, AlgolabConfig(producer="test")).expand(exp_id, "k")

        approve_experiment(exp_repo, exp_id)
        result = expand(conn, exp_id)
        assert len(result.run_ids) >= 1
        run = run_repo.get(result.run_ids[0])
        assert run.status in ("QUEUED", "CLAIMED")
        assert run.experiment_id == exp_id


def test_run_requires_existing_experiment(conn, run_repo) -> None:
    from algolab.control.config import AlgolabConfig
    from algolab.execution.expansion import ExperimentExpansion
    from algolab.storage.run_repository import RunNotFound

    with pytest.raises(RunNotFound):
        ExperimentExpansion(
            conn, AlgolabConfig(producer="test")).expand("EXP-00000000", "k")


def test_experiment_lifecycle_and_events(conn, hyp_repo, cand_repo, exp_repo) -> None:
    with conn:
        h = make_hypothesis()
        hyp_repo.create(h)
        c = make_candidate(h.id)
        cand_repo.create(c)
        exp_id = exp_repo.create(make_experiment(h.id, c.id))
        approve_experiment(exp_repo, exp_id)
    events = EventStore(conn).list_for_entity(exp_id)
    mutations = [e.mutation for e in events]
    assert mutations == [
        "created", "status_changed", "status_changed",
    ]
    assert [e.new_state for e in events] == ["draft", "planned", "approved"]
    assert exp_repo.status(exp_id) == "approved"


def test_run_transitions_and_events(conn, run_repo) -> None:
    exp_id = make_approved_experiment(conn)
    result = expand(conn, exp_id)
    run_id = result.run_ids[0]
    with conn:
        run_repo.transition(run_id, "CLAIMED")
        run_repo.transition(run_id, "STARTING")
        run_repo.transition(run_id, "RUNNING")
        run_repo.transition(run_id, "SUCCEEDED")
    events = EventStore(conn).list_for_entity(run_id)
    assert [e.mutation for e in events] == ["created", "status_changed",
                                            "status_changed", "status_changed",
                                            "status_changed", "status_changed"]
    assert [e.new_state for e in events] == [
        "CREATED", "QUEUED", "CLAIMED", "STARTING", "RUNNING", "SUCCEEDED",
    ]


def test_rejected_transition_is_audited(conn, run_repo) -> None:
    exp_id = make_approved_experiment(conn)
    run_id = expand(conn, exp_id).run_ids[0]
    with conn:
        with pytest.raises(InvalidStateTransition):
            run_repo.transition(run_id, "RUNNING")  # QUEUED -> RUNNING illegal
    events = EventStore(conn).list_for_entity(run_id)
    rejected = [e for e in events if e.mutation == "transition_rejected"]
    assert len(rejected) == 1
    assert rejected[0].old_state == "QUEUED"
    assert rejected[0].new_state == "RUNNING"
    # Status unchanged.
    assert run_repo.get(run_id).status == "QUEUED"


def test_result_requires_run(conn, res_repo) -> None:
    with conn:
        with pytest.raises(InvariantViolation):
            res_repo.create(make_result("RUN-00000000"))


def test_lineage_walk(conn, hyp_repo, cand_repo) -> None:
    with conn:
        root_h = make_hypothesis()
        hyp_repo.create(root_h)
        base = make_candidate(root_h.id, parent_ids=[])
        cand_repo.create(base)
        child = make_candidate(root_h.id, parent_ids=[base.id])
        cand_repo.create(child)
    lineage = LineageQuery(conn)
    ancestors = lineage.ancestors(child.id)
    assert base.id in ancestors
    assert root_h.id not in ancestors  # parent_ids only; hypotheses not parents


def test_get_unknown_entity(conn, hyp_repo) -> None:
    with pytest.raises(EntityNotFound):
        hyp_repo.get("HYP-00000000")
