"""Experiment expansion: determinism, idempotency, budget, all-or-nothing."""

import pytest

from algolab.control.budget import BudgetLedger
from algolab.control.config import AlgolabConfig
from algolab.execution.expansion import (
    BudgetInsufficient,
    ExperimentExpansion,
    ExperimentNotApproved,
)
from algolab.storage.run_repository import RunRepository
from tests.conftest import expand, grant, make_approved_experiment


def test_expansion_materializes_candidate_and_baseline_runs(conn) -> None:
    exp_id = make_approved_experiment(conn, candidate_count=2,
                                      seeds=(11, 23, 37))
    result = expand(conn, exp_id)
    # baselines (1 baseline id) x 3 seeds + candidates (2) x 3 seeds = 9 runs.
    assert result.created == 9
    runs = RunRepository(conn, producer="test").list_runs(experiment_id=exp_id)
    assert len(runs) == 9
    baselines = [r for r in runs if r.is_baseline]
    candidates = [r for r in runs if not r.is_baseline]
    assert len(baselines) == 3
    assert len(candidates) == 6
    assert all(r.status == "QUEUED" for r in runs)
    # Experiment moved to running.
    from algolab.storage.repositories import ExperimentRepository

    assert ExperimentRepository(conn, producer="test").status(exp_id) == "running"


def test_expansion_is_idempotent_by_key(conn) -> None:
    exp_id = make_approved_experiment(conn)
    first = expand(conn, exp_id, key="same")
    second = expand(conn, exp_id, key="same")
    assert second.created == 0
    assert second.existing == first.created
    assert set(second.run_ids) == set(first.run_ids)
    runs = RunRepository(conn, producer="test").list_runs(experiment_id=exp_id)
    assert len(runs) == first.created


def test_config_fingerprints_prevent_duplicates(conn) -> None:
    """Different idempotency keys cannot create duplicate runs."""
    exp_id = make_approved_experiment(conn, candidate_count=1)
    first = expand(conn, exp_id, "key-a")
    second = expand(conn, exp_id, "key-b")
    assert second.created == 0
    assert set(second.run_ids) == set(first.run_ids)


def test_expansion_requires_approved(conn) -> None:
    from algolab.storage.repositories import (
        CandidateRepository,
        ExperimentRepository,
        HypothesisRepository,
    )
    from tests.conftest import make_candidate, make_experiment, make_hypothesis

    with conn:
        h = make_hypothesis()
        hid = HypothesisRepository(conn, producer="test").create(h)
        c = make_candidate(hid)
        cid = CandidateRepository(conn, producer="test").create(c)
        exp = make_experiment(hid, cid, seeds=[11, 23, 37], status="draft")
        exp_id = ExperimentRepository(conn, producer="test").create(exp)
    grant(conn)
    with pytest.raises(ExperimentNotApproved):
        ExperimentExpansion(conn, AlgolabConfig(producer="test")).expand(
            exp_id, "k")


def test_expansion_records_audit_events(conn) -> None:
    exp_id = make_approved_experiment(conn)
    result = expand(conn, exp_id)
    from algolab.storage.event_store import EventStore

    events = EventStore(conn).list_for_entity(exp_id)
    expanded = [e for e in events if e.mutation == "expanded"]
    assert len(expanded) == 1
    assert set(expanded[0].payload["run_ids"]) == set(result.run_ids)


def test_expansion_insufficient_budget_leaves_nothing(conn) -> None:
    exp_id = make_approved_experiment(conn, candidate_count=2,
                                      seeds=(11, 23, 37))
    # No credits granted -> expansion refused and nothing persisted.
    from algolab.control.config import AlgolabConfig

    with pytest.raises(BudgetInsufficient):
        ExperimentExpansion(conn, AlgolabConfig(producer="test")).expand(
            exp_id, "k")
    assert RunRepository(conn, producer="test").list_runs() == []
    # After granting, the same call succeeds (all-or-nothing recovery).
    result = expand(conn, exp_id, "k")
    assert result.created == 9


def test_expansion_reserves_budget_per_run(conn) -> None:
    exp_id = make_approved_experiment(conn, candidate_count=1,
                                      seeds=(11, 23, 37))
    expand(conn, exp_id)
    ledger = BudgetLedger(conn, producer="test")
    balance = ledger.balance()
    assert balance["reserved_credits"] > 0
    assert balance["available_credits"] < 1e9
    runs = RunRepository(conn, producer="test").list_runs()
    for run in runs:
        assert run.reservation_id is not None
        assert run.credits_reserved > 0


def test_expansion_refused_when_run_credit_cap_exceeded(conn) -> None:
    from algolab.control.config import AlgolabConfig, BudgetConfig, ExecutionConfig

    exp_id = make_approved_experiment(conn)
    grant(conn)
    config = AlgolabConfig(
        budget=BudgetConfig(max_run_credits=0.0001),
        execution=ExecutionConfig(),
        producer="test",
    )
    with pytest.raises(BudgetInsufficient):
        ExperimentExpansion(conn, config).expand(exp_id, "k")


def test_config_fingerprint_is_content_addressable() -> None:
    from algolab.execution.expansion import config_fingerprint

    base = dict(experiment_id="EXP-11111111", workload="quadratic_optimizer",
                config={"strategy": "momentum"}, seed=5, is_baseline=False)
    assert config_fingerprint(**base) == config_fingerprint(**base)
    assert config_fingerprint(**base) != config_fingerprint(
        **{**base, "seed": 6})
