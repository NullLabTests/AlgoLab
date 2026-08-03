"""Repository behavior: creates, references, transitions, lineage, events."""

import pytest

from algolab.storage.event_store import EventStore
from algolab.storage.repositories import (
    EntityNotFound,
    InvariantViolation,
    LineageQuery,
)
from tests.conftest import (
    approve_experiment,
    make_candidate,
    make_experiment,
    make_hypothesis,
    make_result,
    make_run,
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

        # draft experiment -> run refused
        with pytest.raises(InvariantViolation):
            run_repo.create(make_run(exp_id))

        approve_experiment(exp_repo, exp_id)
        run_id = run_repo.create(make_run(exp_id))
        assert run_repo.get(run_id).status == "pending"


def test_run_requires_existing_experiment(conn, run_repo) -> None:
    with conn:
        with pytest.raises(InvariantViolation):
            run_repo.create(make_run("EXP-00000000"))


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


def test_run_transitions_and_events(conn, hyp_repo, cand_repo, exp_repo,
                                    run_repo) -> None:
    with conn:
        h = make_hypothesis()
        hyp_repo.create(h)
        c = make_candidate(h.id)
        cand_repo.create(c)
        exp_id = exp_repo.create(make_experiment(h.id, c.id))
        approve_experiment(exp_repo, exp_id)
        run_id = run_repo.create(make_run(exp_id, seed=23))
        run_repo.transition(run_id, "running")
        run_repo.transition(run_id, "completed")
    events = EventStore(conn).list_for_entity(run_id)
    assert [e.mutation for e in events] == ["created", "status_changed",
                                            "status_changed"]
    assert [e.new_state for e in events] == ["pending", "running", "completed"]


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
