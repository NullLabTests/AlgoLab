"""Worker integration tests: real subprocesses against a file-based DB."""

import json
import threading
import time

import pytest

from algolab.control.config import AlgolabConfig, ExecutionConfig, StorageConfig
from algolab.execution.artifacts import MANIFEST_FILES
from algolab.execution.expansion import ExperimentExpansion
from algolab.execution.queue import RunQueue
from algolab.execution.worker import Worker
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


def _expand(config: AlgolabConfig, *, changes=None, seeds=(11, 23, 37),
            **overrides) -> tuple[object, str, str]:
    """Expand an experiment; returns (conn, run_ids, exp_id)."""
    conn = connect(config.storage.path, initialize=True)
    grant(conn, credits=5000.0)
    exp_id = make_approved_experiment(conn, candidate_count=1,
                                      candidate_changes=changes,
                                      seeds=seeds, **overrides)
    result = ExperimentExpansion(conn, config).expand(exp_id, "k")
    return conn, result.run_ids, exp_id


def _bump_priority(conn, run_id: str) -> None:
    with conn:
        conn.execute("UPDATE runs SET priority = 100 WHERE run_id = ?",
                     (run_id,))


def _status(conn, run_id: str) -> str:
    return RunRepository(conn, producer="test").get(run_id).status


def test_worker_success_path(config) -> None:
    conn, run_ids, _ = _expand(config)
    worker = Worker(conn, config, worker_id="w-1")
    assert worker.run_once() is True
    run_id = run_ids[0]
    assert _status(conn, run_id) == "SUCCEEDED"
    run = RunRepository(conn, producer="test").get(run_id)
    assert run.metrics["converged"] is True
    assert run.metrics["seed"] == 11
    assert run.artifact_dir is not None
    assert run.credits_charged > 0
    assert run.error_code is None

    # Artifact layout complete.
    artifacts_dir = config.storage.artifacts_dir / "runs" / run_id
    for name in MANIFEST_FILES:
        assert (artifacts_dir / name).is_file(), name
    completion = json.loads(
        (artifacts_dir / "completion.json").read_text())
    assert completion["status"] == "SUCCEEDED"
    manifest = json.loads(
        (artifacts_dir / "artifact_manifest.json").read_text())
    assert len(manifest["artifacts"]) >= 7


def test_worker_claims_and_executes_all_runs(config) -> None:
    conn, run_ids, _ = _expand(config)
    worker = Worker(conn, config, worker_id="w-all")
    worker.run_loop(poll_interval=0.1)
    repo = RunRepository(conn, producer="test")
    assert all(repo.get(rid).status == "SUCCEEDED" for rid in run_ids)


def test_worker_charges_actual_credits(config) -> None:
    conn, run_ids, _ = _expand(config)
    Worker(conn, config, worker_id="w-1").run_once()
    run = RunRepository(conn, producer="test").get(run_ids[0])
    from algolab.control.budget import BudgetLedger

    ledger = BudgetLedger(conn, producer="test")
    # Actual consumption may be < the reservation (early convergence), in
    # which case the un-used remainder is released back to the pool.
    assert ledger.reservation_status(run.reservation_id) in ("charged", "released")
    expected = round(
        run.metrics["compute_units"] * config.budget.compute_credit_rate, 6)
    assert run.credits_charged == pytest.approx(expected)
    assert ledger.balance()["charged_credits"] == pytest.approx(expected)


def test_worker_timeout_terminates_subprocess(config) -> None:
    conn, run_ids, _ = _expand(config, changes=[{"sleep_seconds": 30,
                                                 "timeout_seconds": 1}])
    run_id = run_ids[-1]  # the candidate run
    _bump_priority(conn, run_id)
    worker = Worker(conn, config, worker_id="w-timeout")
    started = time.monotonic()
    worker.run_once()
    elapsed = time.monotonic() - started
    assert elapsed < 15
    run = RunRepository(conn, producer="test").get(run_id)
    assert run.status == "FAILED"
    assert run.error_code == "TIMEOUT"


def test_worker_cancellation_kills_subprocess(config) -> None:
    conn, run_ids, _ = _expand(config, changes=[{"sleep_seconds": 30}])
    run_id = run_ids[-1]
    _bump_priority(conn, run_id)
    worker = Worker(conn, config, worker_id="w-cancel")

    def cancel_later() -> None:
        time.sleep(1.0)
        c2 = connect(config.storage.path, initialize=False)
        try:
            RunQueue(c2, config).cancel(run_id)
        finally:
            c2.close()

    t = threading.Thread(target=cancel_later)
    t.start()
    worker.run_once()
    t.join()
    run = RunRepository(conn, producer="test").get(run_id)
    assert run.status == "CANCELLED"
    assert run.error_code == "CANCELLED"
    from algolab.control.budget import BudgetLedger

    ledger = BudgetLedger(conn, producer="test")
    assert ledger.reservation_status(run.reservation_id) == "released"


def test_worker_subprocess_failure(config) -> None:
    conn, run_ids, _ = _expand(config, changes=[{"raise_on_start": True}])
    run_id = run_ids[-1]
    _bump_priority(conn, run_id)
    Worker(conn, config, worker_id="w-fail").run_once()
    run = RunRepository(conn, producer="test").get(run_id)
    assert run.status == "FAILED"
    assert run.error_code == "SUBPROCESS_FAILURE"
    from algolab.control.budget import BudgetLedger

    assert BudgetLedger(conn, producer="test").reservation_status(
        run.reservation_id) == "released"


def test_worker_invalid_metrics(config) -> None:
    conn, run_ids, _ = _expand(config, changes=[{"emit_invalid_metrics": True}])
    run_id = run_ids[-1]
    _bump_priority(conn, run_id)
    Worker(conn, config, worker_id="w-bad").run_once()
    run = RunRepository(conn, producer="test").get(run_id)
    assert run.status == "FAILED"
    assert run.error_code == "METRICS_INVALID"


def test_worker_stdout_limit_kills_run(config) -> None:
    small = config.model_copy(update={
        "execution": ExecutionConfig(max_stdout_bytes=512,
                                     max_stderr_bytes=512),
    })
    conn, run_ids, _ = _expand(small, changes=[{"print_bytes": 200_000}])
    run_id = run_ids[-1]
    _bump_priority(conn, run_id)
    Worker(conn, small, worker_id="w-lim").run_once()
    run = RunRepository(conn, producer="test").get(run_id)
    assert run.status == "FAILED"
    assert run.error_code == "ARTIFACT_LIMIT_EXCEEDED"


def test_worker_artifact_size_limit(config) -> None:
    small = config.model_copy(update={
        "execution": ExecutionConfig(max_artifact_bytes=1024),
    })
    conn, run_ids, _ = _expand(small, changes=[{"extra_bytes": 100_000}])
    run_id = run_ids[-1]
    _bump_priority(conn, run_id)
    Worker(conn, small, worker_id="w-size").run_once()
    run = RunRepository(conn, producer="test").get(run_id)
    assert run.status == "FAILED"
    assert run.error_code == "ARTIFACT_LIMIT_EXCEEDED"


def test_worker_unknown_workload_fails_run(config) -> None:
    conn, run_ids, _ = _expand(config)
    run_id = run_ids[0]
    with conn:
        conn.execute("UPDATE runs SET workload = 'nope' WHERE run_id = ?",
                     (run_id,))
    _bump_priority(conn, run_id)
    Worker(conn, config, worker_id="w-unk").run_once()
    run = RunRepository(conn, producer="test").get(run_id)
    assert run.status == "FAILED"
    assert run.error_code == "WORKLOAD_UNKNOWN"


def test_worker_env_is_allowlisted(config) -> None:
    """The subprocess must not see the parent's full environment."""
    import os

    conn, run_ids, _ = _expand(config)
    run_id = run_ids[0]
    from algolab.workloads import get_workload

    full_config = {
        **get_workload("quadratic_optimizer").defaults(),
        "max_iterations": 50,
    }
    with conn:
        conn.execute(
            "UPDATE runs SET config = ? WHERE run_id = ?",
            (json.dumps(full_config), run_id),
        )
    os.environ["ALGOLAB_SECRET_TEST"] = "topsecret"
    _bump_priority(conn, run_id)
    Worker(conn, config, worker_id="w-env").run_once()
    # Allowlisted env vars are prefixed ALGOLAB_* by the worker; anything
    # else must not leak. Check stdout capture did not print secrets.
    out = (config.storage.artifacts_dir / "runs" / run_id / "stdout.log").read_text()
    assert "topsecret" not in out
    env_snapshot = json.loads(
        (config.storage.artifacts_dir / "runs" / run_id
         / "environment.json").read_text())
    assert "ALGOLAB_SECRET_TEST" not in env_snapshot["env_allowlist"]


def test_worker_claims_until_queue_empty(config) -> None:
    conn, run_ids, _ = _expand(config)
    worker = Worker(conn, config, worker_id="w-once")
    claims = 0
    while worker.run_once():
        claims += 1
    assert claims == len(run_ids)
    repo = RunRepository(conn, producer="test")
    assert all(repo.get(rid).status == "SUCCEEDED" for rid in run_ids)
