"""Persistent queue: atomic claims, leases, heartbeats, cancellation."""

import threading
from datetime import UTC, datetime, timedelta

import pytest

from algolab.control.config import AlgolabConfig
from algolab.core.ids import new_id
from algolab.execution.queue import LeaseExpired, RunQueue
from algolab.storage.db import connect
from algolab.storage.run_repository import RunRepository, RunSpec
from tests.conftest import grant, make_approved_experiment


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _later(seconds: float) -> str:
    return (
        datetime.now(UTC) + timedelta(seconds=seconds)
    ).isoformat(timespec="seconds")


@pytest.fixture
def queue(conn) -> RunQueue:
    return RunQueue(conn, AlgolabConfig(producer="test"))


def _queued_run(conn, *, priority: int = 0, next_eligible_at: str | None = None,
                exp_id: str | None = None) -> str:
    """Insert exactly one QUEUED run row (no budget involved)."""
    exp_id = exp_id or make_approved_experiment(conn)
    spec = RunSpec(
        run_id=new_id("RUN"),
        experiment_id=exp_id,
        seed=11,
        workload="quadratic_optimizer",
        config={},
        config_fingerprint=f"q-{new_id('EVT')}",
        next_eligible_at=next_eligible_at or _now(),
        priority=priority,
        max_attempts=1,
    )
    with conn:
        RunRepository(conn, producer="test").create(spec)
    return spec.run_id


def test_claim_moves_run_to_claimed(queue, conn) -> None:
    run_id = _queued_run(conn)
    claimed = queue.claim_next("worker-1", _now())
    assert claimed is not None
    assert claimed.run_id == run_id
    assert claimed.status == "CLAIMED"
    assert claimed.worker_id == "worker-1"
    assert claimed.lease_expires_at is not None
    # The same run is not claimable again.
    assert queue.claim_next("worker-2", _now()) is None


def test_no_double_claim_under_contention(tmp_path) -> None:
    """8 workers (own connections) racing to claim one run: one winner."""
    from algolab.control.config import StorageConfig

    db_path = tmp_path / "race.sqlite3"
    main = connect(db_path, initialize=True)
    config = AlgolabConfig(
        storage=StorageConfig(path=db_path,
                              artifacts_dir=tmp_path / "artifacts"),
        producer="test",
    )
    _queued_run(main)
    winners: list[str] = []
    lock = threading.Lock()

    def worker(n: int) -> None:
        conn = connect(db_path, initialize=False)
        try:
            claimed = RunQueue(conn, config).claim_next(f"worker-{n}", _now())
            if claimed is not None:
                with lock:
                    winners.append(claimed.run_id)
        finally:
            conn.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(winners) == 1


def test_heartbeat_extends_lease(queue, conn, run_repo) -> None:
    run_id = _queued_run(conn)
    claimed = queue.claim_next("worker-1", _now())
    assert claimed is not None
    first_lease = claimed.lease_expires_at
    # Heartbeat some seconds later: the lease is extended from *now*.
    queue.heartbeat(run_id, "worker-1", _later(30))
    assert run_repo.get(run_id).lease_expires_at > first_lease


def test_heartbeat_rejected_for_wrong_worker(queue, conn) -> None:
    run_id = _queued_run(conn)
    queue.claim_next("worker-1", _now())
    with pytest.raises(LeaseExpired):
        queue.heartbeat(run_id, "worker-2", _now())


def test_priority_ordering(queue, conn, run_repo) -> None:
    high = _queued_run(conn, priority=10)
    low = _queued_run(conn, priority=0)
    mid = _queued_run(conn, priority=5)
    assert queue.claim_next("w", _now()).run_id == high
    assert queue.claim_next("w", _now()).run_id == mid
    assert queue.claim_next("w", _now()).run_id == low
    assert queue.claim_next("w", _now()) is None


def test_cancel_queued_run_is_immediate(queue, conn) -> None:
    run_id = _queued_run(conn)
    status = queue.cancel(run_id)
    assert status == "CANCELLED"
    assert queue.claim_next("w", _now()) is None


def test_cancel_active_run_requests_flag(queue, conn, run_repo) -> None:
    run_id = _queued_run(conn)
    queue.claim_next("w", _now())
    status = queue.cancel(run_id)
    assert status == "CLAIMED"
    assert run_repo.get(run_id).cancellation_requested is True


def test_not_yet_eligible_runs_are_skipped(queue, conn) -> None:
    run_id = _queued_run(conn)
    assert queue.claim_next("w", _now()).run_id == run_id
    _queued_run(conn, next_eligible_at=_later(3600))
    assert queue.claim_next("w", _now()) is None
    assert queue.has_eligible(_now()) is False


def test_grant_and_claim_are_independent_of_budget(queue, conn) -> None:
    """Claiming does not require credits; only expansion does."""
    grant(conn, credits=1.0)
    run_id = _queued_run(conn)
    assert queue.claim_next("w", _now()).run_id == run_id
