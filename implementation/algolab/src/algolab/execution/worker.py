"""Worker process (M1).

``algolab worker`` claims runs from the persistent queue and executes them
as isolated subprocesses: argv lists only (``shell=False``), an explicit
environment allowlist, ``cwd`` = the run's artifact directory, an explicit
timeout, byte-limited stdout/stderr capture, heartbeat-based lease renewal,
and cancellation via SIGTERM/SIGKILL.

The worker owns one SQLite connection and executes one workload at a time.
"""

from __future__ import annotations

import logging
import os
import resource
import socket
import sqlite3
import subprocess
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from algolab.control.budget import BudgetError, BudgetLedger
from algolab.control.config import AlgolabConfig
from algolab.execution.artifacts import RunArtifacts
from algolab.execution.errors import ErrorCode
from algolab.execution.logging import log_event
from algolab.execution.queue import LeaseExpired, RunQueue
from algolab.storage.run_repository import (
    RunNotFound,
    RunRepository,
    RunRow,
)
from algolab.workloads import (
    WorkloadError,
    WorkloadUnknownError,
    get_workload,
)

logger = logging.getLogger("algolab.worker")

_TERMINATE_GRACE_SECONDS = 5.0
_POLL_INTERVAL_SECONDS = 0.25


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Worker:
    """Claim + execute runs. One connection, one workload at a time."""

    def __init__(self, conn: sqlite3.Connection, config: AlgolabConfig,
                 worker_id: str | None = None) -> None:
        self._conn = conn
        self._config = config
        self._worker_id = worker_id or (
            f"worker-{socket.gethostname()}-{os.getpid()}"
        )
        self._queue = RunQueue(conn, config)

    # -- public API -------------------------------------------------------

    def run_once(self) -> bool:
        """Claim at most one run and execute it. Returns True if claimed."""
        try:
            run = self._queue.claim_next(self._worker_id)
        except Exception as exc:  # noqa: BLE001 - keep the worker alive
            log_event(logger, "claim_failed", error=str(exc))
            return False
        if run is None:
            return False
        log_event(logger, "claim_success", run_id=run.run_id,
                  worker_id=self._worker_id, status=run.status)
        self._execute(run)
        return True

    def run_loop(self, poll_interval: float = 5.0) -> None:
        """Execute until the queue has no eligible runs, then exit 0."""
        log_event(logger, "worker_start",
                  worker_id=self._worker_id,
                  poll_interval=poll_interval)
        while True:
            if self.run_once():
                continue
            if not self._queue.has_eligible():
                log_event(logger, "worker_done", worker_id=self._worker_id)
                return
            time.sleep(poll_interval)

    # -- execution --------------------------------------------------------

    def _execute(self, run: RunRow) -> None:
        artifacts = RunArtifacts(self._config.storage.artifacts_dir, run.run_id)
        repo = RunRepository(self._conn, producer=self._config.producer,
                             trace_id=run.trace_id)
        log_event(logger, "run_start", run_id=run.run_id,
                  experiment_id=run.experiment_id, seed=run.seed)

        try:
            adapter = get_workload(run.workload)
        except WorkloadUnknownError:
            self._fail(run, ErrorCode.WORKLOAD_UNKNOWN,
                       reason=f"no adapter for workload {run.workload!r}")
            return

        try:
            artifacts.create()
            with self._conn:
                repo.transition(run.run_id, "STARTING",
                                reason="worker setup")
            artifacts.write_json("manifest.json", run.to_manifest())
            artifacts.write_json("resolved_config.json", run.config)
            artifacts.write_environment_snapshot(self._config, adapter.version)
            exit_code, metrics, outcome = self._run_subprocess(
                run, artifacts, adapter, repo
            )
        except Exception as exc:  # noqa: BLE001 - fail the run, keep worker alive
            log_event(logger, "run_setup_failed", run_id=run.run_id,
                      error=str(exc))
            self._fail(run, ErrorCode.RECOVERY_CONFLICT,
                       reason=f"worker error: {exc}")
            return

        self._finalize(run, artifacts, repo, exit_code, metrics, outcome)

    def _run_subprocess(self, run: RunRow, artifacts: RunArtifacts,
                        adapter: Any, repo: RunRepository
                        ) -> tuple[int | None, dict[str, Any] | None, str]:
        """Launch, supervise, and reap the workload subprocess.

        Returns ``(exit_code, metrics, outcome)`` where *outcome* is one of
        ``SUCCEEDED`` / ``FAILED`` / ``CANCELLED`` and *metrics* is populated
        on success.
        """
        argv = adapter.command(artifacts.dir, run.config, run.seed)
        env = self._build_env(run, artifacts)
        timeout = adapter.timeout_seconds(run.config)
        deadline = time.monotonic() + timeout

        rusage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
        wall_before = time.monotonic()
        try:
            proc = subprocess.Popen(
                argv,
                shell=False,
                cwd=artifacts.dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as exc:
            log_event(logger, "spawn_failed", run_id=run.run_id, error=str(exc))
            raise
        with self._conn:
            repo.transition(run.run_id, "RUNNING",
                            reason="subprocess spawned", payload={"pid": proc.pid})

        stdout_buf: list[str] = []
        stderr_buf: list[str] = []
        stdout_overflow = threading.Event()
        stderr_overflow = threading.Event()
        t_out = threading.Thread(
            target=_read_pipe, args=(proc.stdout, stdout_buf,
                                     self._config.execution.max_stdout_bytes,
                                     stdout_overflow), daemon=True)
        t_err = threading.Thread(
            target=_read_pipe, args=(proc.stderr, stderr_buf,
                                     self._config.execution.max_stderr_bytes,
                                     stderr_overflow), daemon=True)
        t_out.start()
        t_err.start()

        outcome = "SUCCEEDED"
        reason: str | None = None
        lease_lost = False
        last_heartbeat = time.monotonic()
        heartbeat_interval = self._config.execution.heartbeat_interval_seconds

        try:
            while proc.poll() is None:
                now = time.monotonic()
                if now >= deadline:
                    outcome = "FAILED"
                    reason = "timeout"
                    self._terminate(proc)
                    break
                if stdout_overflow.is_set() or stderr_overflow.is_set():
                    outcome = "FAILED"
                    reason = "output_limit"
                    self._terminate(proc)
                    break
                if self._cancellation_requested(run.run_id):
                    outcome = "CANCELLED"
                    self._terminate(proc)
                    break
                if now - last_heartbeat >= heartbeat_interval:
                    try:
                        self._queue.heartbeat(run.run_id, self._worker_id)
                        last_heartbeat = now
                    except LeaseExpired:
                        lease_lost = True
                        self._terminate(proc)
                        break
                time.sleep(_POLL_INTERVAL_SECONDS)
        finally:
            proc.wait()
            t_out.join(timeout=10)
            t_err.join(timeout=10)
            for pipe in (proc.stdout, proc.stderr):
                if pipe is not None:
                    pipe.close()

        # A workload may print its budget faster than the poll loop can
        # notice: re-check the overflow flags once the process has exited.
        if (
            outcome != "FAILED"
            and (stdout_overflow.is_set() or stderr_overflow.is_set())
        ):
            outcome = "FAILED"
            reason = "output_limit"

        exit_code = proc.returncode
        wall_seconds = time.monotonic() - wall_before
        rusage = resource.getrusage(resource.RUSAGE_CHILDREN)
        self._write_resource_usage(artifacts, exit_code, wall_seconds,
                                   rusage, rusage_before)
        self._write_logs(artifacts, stdout_buf, stderr_buf)

        if lease_lost:
            log_event(logger, "lease_lost", run_id=run.run_id,
                      worker_id=self._worker_id,
                      note="run left for recovery")
            return exit_code, None, "LEASE_LOST"

        if outcome == "CANCELLED":
            return exit_code, None, "CANCELLED"
        if outcome == "FAILED":
            if reason == "timeout":
                self._fail(run, ErrorCode.TIMEOUT,
                           reason=f"exceeded timeout of {timeout}s")
            else:
                self._fail(run, ErrorCode.ARTIFACT_LIMIT_EXCEEDED,
                           reason="stdout/stderr exceeded configured limits")
            return exit_code, None, "FAILED"
        if exit_code != 0:
            self._fail(run, ErrorCode.SUBPROCESS_FAILURE,
                       reason=f"exit code {exit_code}; "
                              f"stderr tail: {_tail(stderr_buf)}")
            return exit_code, None, "FAILED"

        metrics = self._read_metrics(run, artifacts, adapter)
        if metrics is None:
            return exit_code, None, "FAILED"
        if artifacts.total_size() > self._config.execution.max_artifact_bytes:
            self._fail(run, ErrorCode.ARTIFACT_LIMIT_EXCEEDED,
                       reason="artifact directory exceeds "
                              f"{self._config.execution.max_artifact_bytes} bytes")
            return exit_code, None, "FAILED"
        return exit_code, metrics, "SUCCEEDED"

    def _read_metrics(self, run: RunRow, artifacts: RunArtifacts,
                      adapter: Any) -> dict[str, Any] | None:
        try:
            adapter.validate_expected_artifacts(artifacts.dir)
        except WorkloadError as exc:
            self._fail(run, ErrorCode.ARTIFACT_MISSING, reason=str(exc))
            return None
        if not artifacts.file_exists("metrics.json"):
            self._fail(run, ErrorCode.METRICS_MISSING,
                       reason="workload did not produce metrics.json")
            return None
        try:
            metrics = artifacts.read_json("metrics.json")
            adapter.validate_metrics(metrics)
        except (WorkloadError, OSError, ValueError) as exc:
            self._fail(run, ErrorCode.METRICS_INVALID, reason=str(exc))
            return None
        return metrics

    def _finalize(self, run: RunRow, artifacts: RunArtifacts,
                  repo: RunRepository, exit_code: int | None,
                  metrics: dict[str, Any] | None, outcome: str) -> None:
        if outcome == "LEASE_LOST":
            return
        started = run.started_at or _utc_now()
        finished = _utc_now()
        credits = 0.0
        cost = 0.0
        final_status: str
        error_code: ErrorCode | None
        if outcome == "SUCCEEDED":
            final_status = "SUCCEEDED"
            error_code = None
            assert metrics is not None
            credits = round(
                float(metrics["compute_units"])
                * self._config.budget.compute_credit_rate,
                6,
            )
        elif outcome == "CANCELLED":
            final_status = "CANCELLED"
            error_code = ErrorCode.CANCELLED
        else:
            final_status = "FAILED"
            error_code = self._row_error_code(run.run_id) or ErrorCode.RECOVERY_CONFLICT

        with self._conn:
            ledger = BudgetLedger(self._conn, producer=self._config.producer)
            reservation_id = run.reservation_id
            if final_status == "SUCCEEDED" and reservation_id:
                if (
                    ledger.reservation_status(reservation_id) == "active"
                    and run.credits_charged == 0
                ):
                    try:
                        ledger.charge(
                            reservation_id,
                            credits=credits,
                            cost=cost,
                            key=f"charge:{run.run_id}",
                            trace_id=run.trace_id,
                        )
                        repo.set_budget_charged(run.run_id, credits, cost)
                    except BudgetError as exc:
                        log_event(logger, "charge_failed", run_id=run.run_id,
                                  error=str(exc))
                        final_status = "FAILED"
                        error_code = ErrorCode.RECOVERY_CONFLICT
            elif (
                reservation_id
                and ledger.reservation_status(reservation_id) == "active"
            ):
                try:
                    ledger.release(reservation_id, key=f"release:{run.run_id}",
                                   trace_id=run.trace_id)
                except BudgetError as exc:
                    log_event(logger, "release_failed", run_id=run.run_id,
                              error=str(exc))

            if final_status == "FAILED" and error_code is None:
                error_code = ErrorCode.RECOVERY_CONFLICT

            artifacts.write_artifact_manifest()
            artifacts.write_completion(
                status=final_status,
                error_code=error_code.value if error_code else None,
                exit_code=exit_code,
                started_at=started,
                finished_at=finished,
                credits=credits,
                cost=cost,
                reservation_id=run.reservation_id,
            )
            if metrics is not None:
                repo.set_metrics(run.run_id, metrics)
            repo.set_artifact_dir(run.run_id, artifacts.dir.as_posix())
            current_status = repo.get(run.run_id).status
            if current_status in ("SUCCEEDED", "FAILED", "CANCELLED"):
                # Already terminal (e.g. failed during subprocess supervision):
                # keep artifacts/completion in sync, skip the transition.
                final_status = current_status
                error_code = error_code or self._row_error_code(run.run_id)
            else:
                repo.transition(
                    run.run_id,
                    final_status,
                    reason="worker finalize",
                    error_code=error_code.value if error_code else None,
                )
        log_event(logger, "run_done", run_id=run.run_id,
                  status=final_status,
                  error_code=error_code.value if error_code else None,
                  exit_code=exit_code, credits=credits)

    # -- helpers ----------------------------------------------------------

    def _fail(self, run: RunRow, error_code: ErrorCode, *,
              reason: str) -> None:
        with self._conn:
            repo = RunRepository(self._conn, producer=self._config.producer,
                                 trace_id=run.trace_id)
            try:
                repo.transition(run.run_id, "FAILED", reason=reason,
                                error_code=error_code.value)
            except RunNotFound:
                pass
        log_event(logger, "run_failed", run_id=run.run_id,
                  error_code=error_code.value, reason=reason)

    def _row_error_code(self, run_id: str) -> ErrorCode | None:
        row = self._conn.execute(
            "SELECT error_code FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None or row["error_code"] is None:
            return None
        return ErrorCode(str(row["error_code"]))

    def _cancellation_requested(self, run_id: str) -> bool:
        row = self._conn.execute(
            "SELECT cancellation_requested FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            return False
        return bool(row["cancellation_requested"])

    def _build_env(self, run: RunRow, artifacts: RunArtifacts) -> dict[str, str]:
        env: dict[str, str] = {}
        for key in self._config.execution.env_allowlist:
            value = os.environ.get(key)
            if value is not None:
                env[key] = value
        env.update({
            "ALGOLAB_RUN_ID": run.run_id,
            "ALGOLAB_EXPERIMENT_ID": run.experiment_id,
            "ALGOLAB_SEED": str(run.seed),
            "ALGOLAB_WORKLOAD": run.workload,
            "ALGOLAB_CONFIG_PATH": str(artifacts.dir / "resolved_config.json"),
            "ALGOLAB_OUT_DIR": str(artifacts.dir),
        })
        return env

    @staticmethod
    def _terminate(proc: subprocess.Popen[Any]) -> None:
        if proc.poll() is not None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=_TERMINATE_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    def _write_logs(self, artifacts: RunArtifacts, stdout_buf: list[str],
                    stderr_buf: list[str]) -> None:
        _write_capped(artifacts.dir / "stdout.log", stdout_buf,
                      self._config.execution.max_stdout_bytes)
        _write_capped(artifacts.dir / "stderr.log", stderr_buf,
                      self._config.execution.max_stderr_bytes)

    def _write_resource_usage(self, artifacts: RunArtifacts,
                              exit_code: int | None, wall_seconds: float,
                              rusage_after: Any, rusage_before: Any) -> None:
        artifacts.write_json("resource_usage.json", {
            "schema_version": "1.0.0",
            "exit_code": exit_code,
            "wall_seconds": round(wall_seconds, 6),
            "user_cpu_seconds": round(
                rusage_after.ru_utime - rusage_before.ru_utime, 6),
            "system_cpu_seconds": round(
                rusage_after.ru_stime - rusage_before.ru_stime, 6),
            "max_rss_bytes": rusage_after.ru_maxrss * 1024,
        })


def _read_pipe(pipe: Any, sink: list[str], limit: int,
               overflow: threading.Event) -> None:
    """Read *pipe* into *sink* (capped at *limit* bytes, discarding excess)."""
    if pipe is None:
        return
    total = 0
    for line in pipe:
        total += len(line.encode("utf-8", "replace"))
        if total <= limit:
            sink.append(line)
        elif not overflow.is_set():
            overflow.set()


def _write_capped(path: Path, lines: list[str], limit: int) -> None:
    total = 0
    with open(path, "w", encoding="utf-8") as fh:
        for line in lines:
            fh.write(line)
            total += len(line.encode("utf-8", "replace"))
            if total >= limit:
                fh.write("\n[truncated]\n")
                break


def _tail(lines: list[str], n: int = 5) -> str:
    return "\n".join(lines[-n:])[-500:]
