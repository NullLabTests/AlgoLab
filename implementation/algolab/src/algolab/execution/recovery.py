"""Run recovery service (M1; see ``docs/RECOVERY.md``).

Recovery is idempotent and crash-resilient:

1. **Orphan detection** — runs whose worker lease expired (``CLAIMED``,
   ``STARTING``, ``RUNNING`` with ``lease_expires_at < now``) are moved to
   ``ORPHANED`` with an audited reason.
2. **Artifact verification** — an orphan whose artifacts are complete and
   hash-verified (``completion.json`` + ``artifact_manifest.json`` +
   ``verify_manifest()``) is finalized as ``SUCCEEDED`` or ``FAILED``
   exactly once; budget is charged/released with a no-double-charge guard.
3. **Requeue / fail** — incomplete orphans with attempts remaining are
   requeued with backoff; exhausted orphans are failed.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from algolab.control.budget import BudgetError, BudgetLedger
from algolab.control.config import AlgolabConfig
from algolab.core.state import RUN_ACTIVE_STATUSES
from algolab.execution.artifacts import RunArtifacts
from algolab.execution.errors import ErrorCode
from algolab.storage.run_repository import RunRepository
from algolab.workloads import get_workload


@dataclass(frozen=True)
class RecoveryDecision:
    """One run reconciled by recovery."""

    run_id: str
    action: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"run_id": self.run_id, "action": self.action,
                "reason": self.reason}


@dataclass(frozen=True)
class RecoveryReport:
    """Summary of one ``recover-runs`` pass."""

    decisions: tuple[RecoveryDecision, ...]
    orphaned: int
    finalized_succeeded: int
    finalized_failed: int
    requeued: int
    failed: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "orphaned": self.orphaned,
            "finalized_succeeded": self.finalized_succeeded,
            "finalized_failed": self.finalized_failed,
            "requeued": self.requeued,
            "failed": self.failed,
            "decisions": [d.to_dict() for d in self.decisions],
        }


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class RecoveryError(RuntimeError):
    """Base class for recovery failures."""


def recover_runs(conn: sqlite3.Connection, config: AlgolabConfig,
                 producer: str | None = None) -> RecoveryReport:
    """Reconcile orphaned runs. Idempotent; safe to re-run."""
    producer = producer or config.producer
    repo = RunRepository(conn, producer=producer)
    now = _now()

    # 1. Orphan detection (lease expiry).
    for expired_id in repo.expired_leases(now):
        with conn:
            run = repo.get(expired_id)
            if run.status in RUN_ACTIVE_STATUSES:
                repo.transition(expired_id, "ORPHANED",
                                reason="worker lease expired",
                                error_code=ErrorCode.LEASE_EXPIRED.value)

    # 2. Process every orphan (also those left by a crashed recovery pass).
    decisions: list[RecoveryDecision] = []
    counts = {"orphaned": 0, "finalized_succeeded": 0,
              "finalized_failed": 0, "requeued": 0, "failed": 0}
    for orphan in repo.list_runs(status="ORPHANED"):
        decision = _reconcile_orphan(conn, config, repo, orphan, producer, now)
        counts[decision.action] += 1
        counts["orphaned"] += 1
        decisions.append(decision)
    return RecoveryReport(
        decisions=tuple(decisions),
        orphaned=counts["orphaned"],
        finalized_succeeded=counts["finalized_succeeded"],
        finalized_failed=counts["finalized_failed"],
        requeued=counts["requeued"],
        failed=counts["failed"],
    )


def _reconcile_orphan(conn: sqlite3.Connection, config: AlgolabConfig,
                      repo: RunRepository, run: Any, producer: str,
                      now: str) -> RecoveryDecision:
    artifacts = RunArtifacts(config.storage.artifacts_dir, run.run_id)

    if (
        artifacts.file_exists("completion.json")
        and artifacts.file_exists("artifact_manifest.json")
        and artifacts.verify_manifest()
    ):
        return _finalize_from_artifacts(conn, config, repo, run, artifacts,
                                        producer)

    if run.attempt_number < run.max_attempts - 1:
        backoff = config.recovery.requeue_backoff_seconds
        next_at = (
            datetime.fromisoformat(now) + timedelta(seconds=backoff)
        ).isoformat(timespec="seconds")
        with conn:
            repo.transition(run.run_id, "QUEUED",
                            reason="requeued after orphan (attempt "
                                   f"{run.attempt_number + 2})")
            repo.requeue(run.run_id, next_at)
        return RecoveryDecision(run.run_id, "requeued",
                                f"attempt {run.attempt_number + 1} of "
                                f"{run.max_attempts} lost its worker")

    with conn:
        _release_if_active(conn, config, run, producer)
        repo.transition(run.run_id, "FAILED",
                        reason="orphaned and attempts exhausted",
                        error_code=ErrorCode.ATTEMPTS_EXHAUSTED.value)
    return RecoveryDecision(run.run_id, "failed",
                            "attempts exhausted ("
                            f"{run.max_attempts})")


def _finalize_from_artifacts(conn: sqlite3.Connection, config: AlgolabConfig,
                             repo: RunRepository, run: Any,
                             artifacts: RunArtifacts,
                             producer: str) -> RecoveryDecision:
    try:
        completion = artifacts.read_json("completion.json")
    except (OSError, ValueError):
        return _incomplete(conn, config, repo, run, producer,
                           "completion.json unreadable")
    status = completion.get("status")
    if status not in ("SUCCEEDED", "FAILED", "CANCELLED"):
        return _incomplete(conn, config, repo, run, producer,
                           f"completion.json status {status!r}")

    if status == "SUCCEEDED":
        try:
            metrics = artifacts.read_json("metrics.json")
            adapter = get_workload(run.workload)
            adapter.validate_metrics(metrics)
        except (OSError, ValueError) as exc:
            return _incomplete(conn, config, repo, run, producer,
                               f"metrics unreadable/invalid: {exc}")
        error_code = None
    else:
        metrics = None
        error_code = completion.get("error_code")

    credits = float(completion.get("credits", 0.0))
    cost = float(completion.get("cost", 0.0))
    with conn:
        if status == "SUCCEEDED":
            _charge_if_uncharged(conn, config, run, credits, cost, producer)
        else:
            _release_if_active(conn, config, run, producer)
        if metrics is not None:
            repo.set_metrics(run.run_id, metrics)
        repo.set_artifact_dir(run.run_id, artifacts.dir.as_posix())
        repo.transition(run.run_id, status,
                        reason="recovered from orphan (artifacts verified)",
                        error_code=error_code)
    action = ("finalized_succeeded" if status == "SUCCEEDED"
              else "finalized_failed")
    return RecoveryDecision(run.run_id, action,
                            "artifacts hash-verified; "
                            f"completion.json says {status}")


def _incomplete(conn: sqlite3.Connection, config: AlgolabConfig, repo: Any,
                run: Any, producer: str, why: str) -> RecoveryDecision:
    """Orphan artifacts exist but are unusable — requeue or fail."""
    if run.attempt_number < run.max_attempts - 1:
        backoff = config.recovery.requeue_backoff_seconds
        next_at = (
            datetime.fromisoformat(_now()) + timedelta(seconds=backoff)
        ).isoformat(timespec="seconds")
        with conn:
            repo.transition(run.run_id, "QUEUED", reason=why)
            repo.requeue(run.run_id, next_at)
        return RecoveryDecision(run.run_id, "requeued", why)
    with conn:
        _release_if_active(conn, config, run, producer)
        repo.transition(run.run_id, "FAILED", reason=why,
                        error_code=ErrorCode.ARTIFACT_MISSING.value)
    return RecoveryDecision(run.run_id, "failed", why)


def _charge_if_uncharged(conn: sqlite3.Connection, config: AlgolabConfig,
                         run: Any, credits: float, cost: float,
                         producer: str) -> None:
    reservation_id = run.reservation_id
    if reservation_id is None or run.credits_charged != 0:
        return
    ledger = BudgetLedger(conn, producer=producer)
    if ledger.reservation_status(reservation_id) != "active":
        return
    try:
        ledger.charge(reservation_id, credits=credits, cost=cost,
                      key=f"recover-charge:{run.run_id}",
                      trace_id=run.trace_id)
        RunRepository(conn, producer=producer).set_budget_charged(
            run.run_id, credits, cost)
    except BudgetError as exc:
        raise RecoveryError(
            f"cannot charge reservation for run {run.run_id}: {exc}"
        ) from exc


def _release_if_active(conn: sqlite3.Connection, config: AlgolabConfig,
                       run: Any, producer: str) -> None:
    reservation_id = run.reservation_id
    if reservation_id is None:
        return
    ledger = BudgetLedger(conn, producer=producer)
    if ledger.reservation_status(reservation_id) != "active":
        return
    try:
        ledger.release(reservation_id, key=f"recover-release:{run.run_id}",
                       trace_id=run.trace_id)
    except BudgetError as exc:
        raise RecoveryError(
            f"cannot release reservation for run {run.run_id}: {exc}"
        ) from exc
