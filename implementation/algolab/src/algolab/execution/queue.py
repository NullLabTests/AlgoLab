"""Persistent run queue (M1).

Claims are atomic: a single ``BEGIN IMMEDIATE`` transaction selects the
highest-priority eligible run and updates it to ``CLAIMED`` in one
statement. Because SQLite serializes writers, two workers can never claim
the same run (no double claim).
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from algolab.control.config import AlgolabConfig
from algolab.core.state import InvalidStateTransition
from algolab.storage.run_repository import (
    RunRepository,
    RunRow,
)


class QueueError(RuntimeError):
    """Base class for queue failures."""


class ClaimConflict(QueueError):
    """A claim was attempted on a run another worker already owns."""


class LeaseExpired(QueueError):
    """This worker no longer owns the run (lease lost)."""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class RunQueue:
    """Claim/heartbeat/cancel operations over the ``runs`` table."""

    def __init__(self, conn: sqlite3.Connection,
                 config: AlgolabConfig) -> None:
        self._conn = conn
        self._config = config
        self._runs = RunRepository(conn, producer=config.producer)

    # -- claim ------------------------------------------------------------

    def claim_next(self, worker_id: str, now: str | None = None) -> RunRow | None:
        """Atomically claim the next eligible run for *worker_id*.

        Returns the claimed run, or ``None`` if the queue is empty/ineligible.
        Raises :class:`ClaimConflict` only if a race was detected (should not
        happen inside ``BEGIN IMMEDIATE``).

        Must not be called inside an existing transaction.
        """
        now = now or _now()
        if self._conn.in_transaction:
            raise QueueError("claim_next must run outside an open transaction")
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            row = self._conn.execute(
                """
                SELECT * FROM runs
                WHERE status = 'QUEUED' AND next_eligible_at <= ?
                  AND cancellation_requested = 0
                ORDER BY priority DESC, next_eligible_at, rowid
                LIMIT 1
                """,
                (now,),
            ).fetchone()
            if row is None:
                self._conn.commit()
                return None
            run_id = str(row["run_id"])
            cur = self._conn.execute(
                "UPDATE runs SET status = 'CLAIMED' WHERE run_id = ? "
                "AND status = 'QUEUED'",
                (run_id,),
            )
            if cur.rowcount != 1:
                raise ClaimConflict(
                    f"run {run_id} was claimed by another worker"
                )
            lease_expires_at = _lease_expiry(
                now, self._config.execution.lease_seconds
            )
            repo = RunRepository(
                self._conn,
                producer=self._config.producer,
                trace_id=row["trace_id"],
            )
            repo.mark_claimed(run_id, worker_id, now, lease_expires_at)
            claimed = repo.get(run_id)
            self._conn.commit()
            return claimed
        except BaseException:
            self._conn.rollback()
            raise

    # -- liveness ---------------------------------------------------------

    def heartbeat(self, run_id: str, worker_id: str,
                  now: str | None = None) -> None:
        """Extend the claim lease of a run this worker owns.

        Raises :class:`LeaseExpired` if the worker no longer owns the run.
        """
        now = now or _now()
        with self._conn:
            cur = self._conn.execute(
                """
                UPDATE runs SET heartbeat_at = ?, lease_expires_at = ?
                WHERE run_id = ? AND worker_id = ?
                  AND status IN ('CLAIMED', 'STARTING', 'RUNNING')
                """,
                (now, _lease_expiry(now, self._config.execution.lease_seconds),
                 run_id, worker_id),
            )
            if cur.rowcount != 1:
                raise LeaseExpired(
                    f"worker {worker_id} lost the lease on run {run_id}"
                )

    # -- cancellation -----------------------------------------------------

    def cancel(self, run_id: str) -> str:
        """Request cancellation; returns the run's status after the call."""
        try:
            return self._runs.request_cancellation(run_id)
        except InvalidStateTransition as exc:
            raise QueueError(f"cannot cancel run {run_id}: {exc}") from exc

    def has_eligible(self, now: str | None = None) -> bool:
        return self._runs.count_eligible(now or _now()) > 0


def _lease_expiry(now: str, lease_seconds: float) -> str:
    base = datetime.fromisoformat(now)
    from datetime import timedelta

    return (base + timedelta(seconds=lease_seconds)).isoformat(timespec="seconds")
