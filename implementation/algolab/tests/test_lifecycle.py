"""Full lifecycle: approved experiment -> worker -> artifacts -> aggregate.

Also covers the cancelled-run lifecycle: cancellation is honoured, the
reservation is released, and recovery has nothing left to do.
"""

import json
from datetime import UTC, datetime, timedelta

from algolab.execution.aggregation import aggregate_experiment
from algolab.execution.worker import Worker
from algolab.storage.db import connect
from algolab.storage.run_repository import RunRepository
from tests.conftest import (
    expand,
    grant,
    make_approved_experiment,
    tmp_config,
)


def _run_worker(config, conn) -> dict:
    import time

    from algolab.execution.queue import RunQueue

    worker = Worker(conn, config)
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        worker.run_once()
        if not RunQueue(conn, config).has_eligible():
            break
        time.sleep(0.2)
    rows = conn.execute(
        "SELECT status, COUNT(*) FROM runs GROUP BY status").fetchall()
    return {r[0]: r[1] for r in rows}


def test_full_lifecycle_all_success(tmp_path) -> None:
    config = tmp_config(tmp_path)
    conn = connect(config.storage.path, initialize=True)
    grant(conn)
    exp_id = make_approved_experiment(conn, candidate_count=3,
                                      seeds=(11, 23, 37))
    result = expand(conn, exp_id)
    assert len(result.run_ids) == 12

    statuses = _run_worker(config, conn)
    assert statuses == {"SUCCEEDED": 12}

    run_dirs = list((config.storage.artifacts_dir / "runs").iterdir())
    assert len(run_dirs) == 12
    for run_dir in run_dirs:
        completion = json.loads(
            (run_dir / "completion.json").read_text())
        assert completion["status"] == "SUCCEEDED"
        assert completion["exit_code"] == 0
        assert completion["credits"] > 0
        assert (run_dir / "metrics.json").exists()
        assert (run_dir / "artifact_manifest.json").exists()

    report = aggregate_experiment(conn, exp_id)
    assert report["succeeded_runs"] == 12
    assert report["run_counts"]["SUCCEEDED"] == 12
    metric = report["metrics"]["final_objective"]
    assert metric["baseline"]["count"] == 3
    assert len(metric["candidates"]) == 3
    assert len(metric["effect"]) == 3
    # Every candidate converged: objective is tiny (values depend on the
    # candidate's strategy, but all are well below the initial objective).
    assert all(cand["mean"] < 0.05 for cand in metric["candidates"].values())
    conn.close()


def test_cancelled_run_releases_reservation(tmp_path) -> None:
    config = tmp_config(tmp_path)
    conn = connect(config.storage.path, initialize=True)
    grant(conn)
    exp_id = make_approved_experiment(conn, candidate_count=3,
                                      seeds=(11, 23, 37))
    result = expand(conn, exp_id)
    victim = result.run_ids[0]
    from algolab.control.budget import BudgetLedger

    reservation_id = RunRepository(conn, producer="test").get(
        victim).reservation_id
    with conn:
        RunRepository(conn, producer="test").request_cancellation(victim)

    statuses = _run_worker(config, conn)
    assert statuses == {"SUCCEEDED": 11, "CANCELLED": 1}
    assert BudgetLedger(conn, producer="test").reservation_status(
        reservation_id) == "released"
    conn.close()


def test_worker_requeues_are_rerun(tmp_path) -> None:
    """A run whose worker died mid-flight is retried and succeeds."""
    config = tmp_config(tmp_path)
    conn = connect(config.storage.path, initialize=True)
    grant(conn)
    exp_id = make_approved_experiment(conn, candidate_count=1,
                                      seeds=(11, 23, 37))
    result = expand(conn, exp_id)
    run_id = result.run_ids[0]

    # Simulate a failed first attempt (e.g. lost lease): reset to QUEUED
    # exactly as recovery would.
    repo = RunRepository(conn, producer="test")
    next_at = (datetime.now(UTC) + timedelta(seconds=2)
               ).isoformat(timespec="seconds")
    with conn:
        repo.transition(run_id, "CLAIMED")
        repo.transition(run_id, "STARTING")
        repo.transition(run_id, "RUNNING")
        conn.execute(
            "UPDATE runs SET lease_expires_at = '2000-01-01T00:00:00+00:00', "
            "attempt_number = 1 WHERE run_id = ?", (run_id,))
        repo.transition(run_id, "ORPHANED")
        repo.transition(run_id, "QUEUED")
        repo.requeue(run_id, next_at)

    statuses = _run_worker(config, conn)
    assert statuses == {"SUCCEEDED": 6}
    run = RunRepository(conn, producer="test").get(run_id)
    assert run.status == "SUCCEEDED" and run.attempt_number == 2
    conn.close()
