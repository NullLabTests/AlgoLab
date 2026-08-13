"""Recovery: orphans, lease expiry, finalize/requeue/fail, no double charge."""


import pytest

from algolab.control.budget import BudgetLedger
from algolab.control.config import AlgolabConfig, StorageConfig
from algolab.execution.artifacts import RunArtifacts
from algolab.execution.expansion import ExperimentExpansion
from algolab.execution.recovery import recover_runs
from algolab.storage.db import connect
from algolab.storage.run_repository import RunRepository
from tests.conftest import grant, make_approved_experiment


@pytest.fixture
def config(tmp_path) -> AlgolabConfig:
    return AlgolabConfig(
        storage=StorageConfig(path=tmp_path / "db.sqlite3",
                              artifacts_dir=tmp_path / "artifacts"),
        producer="test",
    )


def _expand(config: AlgolabConfig) -> tuple[object, str]:
    conn = connect(config.storage.path, initialize=True)
    grant(conn, credits=5000.0)
    exp_id = make_approved_experiment(conn, candidate_count=1)
    result = ExperimentExpansion(conn, config).expand(exp_id, "k")
    return conn, result.run_ids[0]


def _orphan(conn, config: AlgolabConfig, run_id: str, *,
            attempts: int = 0, max_attempts: int = 2) -> None:
    repo = RunRepository(conn, producer="test")
    with conn:
        repo.transition(run_id, "CLAIMED")
        repo.transition(run_id, "STARTING")
        repo.transition(run_id, "RUNNING")
        conn.execute(
            "UPDATE runs SET lease_expires_at = '2000-01-01T00:00:00+00:00', "
            "attempt_number = ?, max_attempts = ? WHERE run_id = ?",
            (attempts, max_attempts, run_id),
        )


def test_orphan_with_complete_artifacts_finalizes_without_double_charge(
    config,
) -> None:
    conn, run_id = _expand(config)
    artifacts = RunArtifacts(config.storage.artifacts_dir, run_id)
    artifacts.create()
    artifacts.write_json("metrics.json", {
        "final_objective": 0.01, "initial_objective": 1.0,
        "converged": True, "iterations": 10, "compute_units": 160.0,
        "gradient_norm": 1e-9, "strategy": "gradient_descent",
        "seed": 11, "dim": 16,
    })
    run = RunRepository(conn, producer="test").get(run_id)
    credits = run.credits_reserved
    artifacts.write_completion(
        status="SUCCEEDED", error_code=None, exit_code=0,
        started_at="2026-01-01T00:00:00+00:00",
        finished_at="2026-01-01T00:00:01+00:00",
        credits=credits, cost=0.0, reservation_id=run.reservation_id)
    artifacts.write_artifact_manifest()
    _orphan(conn, config, run_id)

    report = recover_runs(conn, config)
    assert report.orphaned == 1
    assert report.finalized_succeeded == 1
    final = RunRepository(conn, producer="test").get(run_id)
    assert final.status == "SUCCEEDED"
    assert final.credits_charged == pytest.approx(credits)
    ledger = BudgetLedger(conn, producer="test")
    assert ledger.reservation_status(run.reservation_id) == "charged"

    # Second pass is a no-op (idempotent, no double charge).
    report2 = recover_runs(conn, config)
    assert report2.orphaned == 0
    assert ledger.balance()["charged_credits"] == pytest.approx(credits)


def test_orphan_with_tampered_artifacts_is_requeued(config) -> None:
    conn, run_id = _expand(config)
    artifacts = RunArtifacts(config.storage.artifacts_dir, run_id)
    artifacts.create()
    artifacts.write_json("metrics.json", {"converged": True})
    artifacts.write_artifact_manifest()
    artifacts.write_json("metrics.json", {"converged": False})  # tamper
    artifacts.write_completion(
        status="SUCCEEDED", error_code=None, exit_code=0,
        started_at="2026-01-01T00:00:00+00:00",
        finished_at="2026-01-01T00:00:01+00:00",
        credits=0.1, cost=0.0, reservation_id=None)
    _orphan(conn, config, run_id)

    report = recover_runs(conn, config)
    assert report.requeued == 1
    run = RunRepository(conn, producer="test").get(run_id)
    assert run.status == "QUEUED"
    assert run.attempt_number == 1


def test_orphan_without_artifacts_requeues_then_fails(config) -> None:
    conn, run_id = _expand(config)
    _orphan(conn, config, run_id, attempts=0, max_attempts=2)
    report = recover_runs(conn, config)
    assert report.requeued == 1
    run = RunRepository(conn, producer="test").get(run_id)
    assert run.status == "QUEUED" and run.attempt_number == 1

    # Orphan again (no artifacts ever written).
    with conn:
        repo = RunRepository(conn, producer="test")
        repo.transition(run_id, "CLAIMED")
        repo.transition(run_id, "STARTING")
        repo.transition(run_id, "RUNNING")
        conn.execute(
            "UPDATE runs SET lease_expires_at = '2000-01-01T00:00:00+00:00' "
            "WHERE run_id = ?", (run_id,))
    report2 = recover_runs(conn, config)
    assert report2.failed == 1  # orphaned again, then failed (exhausted)
    run = RunRepository(conn, producer="test").get(run_id)
    assert run.status == "FAILED"
    assert run.error_code == "ATTEMPTS_EXHAUSTED"
    assert run.attempt_number == 1


def test_orphan_release_reservation_when_failed(config) -> None:
    conn, run_id = _expand(config)
    _orphan(conn, config, run_id, attempts=3, max_attempts=2)
    report = recover_runs(conn, config)
    assert report.failed == 1
    ledger = BudgetLedger(conn, producer="test")
    run = RunRepository(conn, producer="test").get(run_id)
    assert ledger.reservation_status(run.reservation_id) == "released"
    assert ledger.balance()["available_credits"] > 0


def test_runs_with_live_leases_are_not_orphaned(config) -> None:
    conn, run_id = _expand(config)
    with conn:
        RunRepository(conn, producer="test").transition(run_id, "CLAIMED")
        conn.execute(
            "UPDATE runs SET lease_expires_at = '2099-01-01T00:00:00+00:00' "
            "WHERE run_id = ?", (run_id,))
    report = recover_runs(conn, config)
    assert report.orphaned == 0
    assert RunRepository(conn, producer="test").get(run_id).status == "CLAIMED"


def test_recovery_audits_every_decision(config) -> None:
    conn, run_id = _expand(config)
    _orphan(conn, config, run_id, attempts=3, max_attempts=2)
    recover_runs(conn, config)
    from algolab.storage.event_store import EventStore

    events = EventStore(conn).list_for_entity(run_id)
    mutations = [e.mutation for e in events]
    assert mutations.count("status_changed") >= 2
    orphan_event = next(e for e in events
                        if e.new_state == "ORPHANED"
                        and e.payload.get("reason") == "worker lease expired")
    assert orphan_event is not None
