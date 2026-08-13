"""Run persistence (M1 execution core).

Runs live in a dedicated ``runs`` table (schema v2) rather than the generic
``entities`` table: they carry queue mechanics (worker id, leases, heartbeats,
attempts, priority, next-eligible time, cancellation flag) and budget fields.
Every status change goes through the fail-closed run state machine and appends
an audit event in the same transaction. A rejected transition appends a
``transition_rejected`` audit event *before* re-raising.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from algolab.core.events import EventEnvelope
from algolab.core.ids import require
from algolab.core.state import (
    RUN_ACTIVE_STATUSES,
    RUN_MACHINE,
    RUN_TERMINAL_STATUSES,
    InvalidStateTransition,
)
from algolab.storage.event_store import EventStore


class RunNotFound(RuntimeError):
    """No such run in the ``runs`` table."""


class RunConflict(RuntimeError):
    """The run state does not permit the requested operation."""


@dataclass(frozen=True)
class RunSpec:
    """Everything needed to materialize one run row."""

    run_id: str
    experiment_id: str
    seed: int
    workload: str
    config: dict[str, Any]
    config_fingerprint: str
    next_eligible_at: str
    candidate_id: str | None = None
    is_baseline: bool = False
    priority: int = 0
    max_attempts: int = 1
    reservation_id: str | None = None
    credits_reserved: float = 0.0
    cost_reserved: float = 0.0
    trace_id: str | None = None


@dataclass(frozen=True)
class RunRow:
    """One row of the ``runs`` table (read model)."""

    run_id: str
    experiment_id: str
    candidate_id: str | None
    is_baseline: bool
    seed: int
    workload: str
    config: dict[str, Any]
    config_fingerprint: str
    metrics: dict[str, Any]
    status: str
    priority: int
    attempt_number: int
    max_attempts: int
    next_eligible_at: str
    worker_id: str | None
    claim_timestamp: str | None
    lease_expires_at: str | None
    heartbeat_at: str | None
    cancellation_requested: bool
    credits_reserved: float
    cost_reserved: float
    credits_charged: float
    cost_charged: float
    reservation_id: str | None
    artifact_dir: str | None
    error_code: str | None
    created_at: str
    started_at: str | None
    finished_at: str | None
    trace_id: str | None

    @property
    def is_terminal(self) -> bool:
        return self.status in RUN_TERMINAL_STATUSES

    @property
    def is_active(self) -> bool:
        return self.status in RUN_ACTIVE_STATUSES

    def to_manifest(self) -> dict[str, Any]:
        """Snapshot used for the run's ``manifest.json`` artifact."""
        return {
            "run_id": self.run_id,
            "experiment_id": self.experiment_id,
            "candidate_id": self.candidate_id,
            "is_baseline": self.is_baseline,
            "seed": self.seed,
            "workload": self.workload,
            "config": self.config,
            "config_fingerprint": self.config_fingerprint,
            "status": self.status,
            "attempt_number": self.attempt_number,
            "max_attempts": self.max_attempts,
            "priority": self.priority,
            "created_at": self.created_at,
        }


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _row_to_run(row: sqlite3.Row) -> RunRow:
    config = json.loads(row["config"] or "{}")
    assert isinstance(config, dict)
    metrics = json.loads(row["metrics"]) if row["metrics"] else {}
    assert isinstance(metrics, dict)
    return RunRow(
        run_id=str(row["run_id"]),
        experiment_id=str(row["experiment_id"]),
        candidate_id=row["candidate_id"],
        is_baseline=bool(row["is_baseline"]),
        seed=int(row["seed"]),
        workload=str(row["workload"]),
        config=config,
        config_fingerprint=str(row["config_fingerprint"]),
        metrics=metrics,
        status=str(row["status"]),
        priority=int(row["priority"]),
        attempt_number=int(row["attempt_number"]),
        max_attempts=int(row["max_attempts"]),
        next_eligible_at=str(row["next_eligible_at"]),
        worker_id=row["worker_id"],
        claim_timestamp=row["claim_timestamp"],
        lease_expires_at=row["lease_expires_at"],
        heartbeat_at=row["heartbeat_at"],
        cancellation_requested=bool(row["cancellation_requested"]),
        credits_reserved=float(row["credits_reserved"] or 0),
        cost_reserved=float(row["cost_reserved"] or 0),
        credits_charged=float(row["credits_charged"] or 0),
        cost_charged=float(row["cost_charged"] or 0),
        reservation_id=row["reservation_id"],
        artifact_dir=row["artifact_dir"],
        error_code=row["error_code"],
        created_at=str(row["created_at"]),
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        trace_id=row["trace_id"],
    )


class RunRepository:
    """Persistence for the ``runs`` table. All methods run inside the
    caller's transaction."""

    def __init__(self, conn: sqlite3.Connection, producer: str = "algolab",
                 trace_id: str | None = None) -> None:
        self._conn = conn
        self._producer = producer
        self._trace_id = trace_id

    # -- creation ---------------------------------------------------------

    def create(self, spec: RunSpec) -> str:
        """Insert *spec* in ``CREATED`` state, then enqueue it.

        The experiment must exist and be ``approved`` (the expansion service
        guarantees this; the repository enforces it again — fail closed).
        """
        require(spec.run_id, "RUN")
        require(spec.experiment_id, "EXP")
        if spec.candidate_id is not None:
            require(spec.candidate_id, "CAND")
        self._require_experiment(spec.experiment_id, "approved")
        self._conn.execute(
            """
            INSERT INTO runs
                (run_id, experiment_id, candidate_id, is_baseline, seed,
                 workload, config, config_fingerprint, status, priority,
                 attempt_number, max_attempts, next_eligible_at,
                 credits_reserved, cost_reserved, reservation_id,
                 created_at, trace_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'CREATED', ?, 0, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                spec.run_id,
                spec.experiment_id,
                spec.candidate_id,
                1 if spec.is_baseline else 0,
                spec.seed,
                spec.workload,
                json.dumps(spec.config, sort_keys=True),
                spec.config_fingerprint,
                spec.priority,
                spec.max_attempts,
                spec.next_eligible_at,
                spec.credits_reserved,
                spec.cost_reserved,
                spec.reservation_id,
                _now(),
                spec.trace_id,
            ),
        )
        self._append_event(
            mutation="created",
            entity_id=spec.run_id,
            old_state=None,
            new_state="CREATED",
            payload={"experiment_id": spec.experiment_id, "seed": spec.seed},
        )
        self.transition(spec.run_id, "QUEUED",
                        payload={"next_eligible_at": spec.next_eligible_at})
        return spec.run_id

    # -- reads ------------------------------------------------------------

    def get(self, run_id: str) -> RunRow:
        """Fetch one run; raises :class:`RunNotFound` if absent."""
        require(run_id, "RUN")
        row = self._conn.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            raise RunNotFound(f"no run {run_id}")
        return _row_to_run(row)

    def list_runs(self, *, experiment_id: str | None = None,
                  status: str | None = None) -> list[RunRow]:
        """All runs, optionally filtered, ordered by created_at."""
        clauses: list[str] = []
        params: list[Any] = []
        if experiment_id is not None:
            clauses.append("experiment_id = ?")
            params.append(experiment_id)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(
            f"SELECT * FROM runs {where} ORDER BY created_at, run_id", params
        ).fetchall()
        return [_row_to_run(r) for r in rows]

    def count_eligible(self, now: str) -> int:
        """Runs currently eligible for claim (worker loop exit check)."""
        row = self._conn.execute(
            """
            SELECT COUNT(*) FROM runs
            WHERE status = 'QUEUED' AND next_eligible_at <= ?
              AND cancellation_requested = 0
            """,
            (now,),
        ).fetchone()
        return int(row[0])

    def count_by_status(self, experiment_id: str | None = None
                        ) -> dict[str, int]:
        """Run counts per status (used by aggregation and CLI)."""
        clauses = "WHERE experiment_id = ?" if experiment_id else ""
        params: tuple[Any, ...] = (experiment_id,) if experiment_id else ()
        counts = {s: 0 for s in RUN_MACHINE.states()}
        for row in self._conn.execute(
            f"SELECT status, COUNT(*) AS n FROM runs {clauses} "
            "GROUP BY status", params
        ).fetchall():
            counts[str(row["status"])] = int(row["n"])
        return counts

    # -- lifecycle --------------------------------------------------------

    def transition(self, run_id: str, target: str, *,
                   reason: str | None = None, error_code: str | None = None,
                   payload: dict[str, Any] | None = None) -> str:
        """Apply a state-machine transition atomically with its audit event.

        A rejected transition appends a ``transition_rejected`` audit event
        and re-raises :class:`InvalidStateTransition`.
        """
        row = self._conn.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            raise RunNotFound(f"no run {run_id}")
        current = str(row["status"])
        if not RUN_MACHINE.can_transition(current, target):
            self._append_event(
                mutation="transition_rejected",
                entity_id=run_id,
                old_state=current,
                new_state=target,
                payload={"reason": reason or "not permitted by run state machine"},
            )
            raise InvalidStateTransition(
                f"invalid transition {current!r} -> {target!r} for run {run_id}"
            )
        updates: list[str] = ["status = ?"]
        params: list[Any] = [target]
        if target in ("STARTING", "RUNNING") and row["started_at"] is None:
            updates.append("started_at = ?")
            params.append(_now())
        if target in RUN_TERMINAL_STATUSES:
            updates.append("finished_at = ?")
            params.append(_now())
        if error_code is not None:
            updates.append("error_code = ?")
            params.append(error_code)
        params.append(run_id)
        self._conn.execute(
            f"UPDATE runs SET {', '.join(updates)} WHERE run_id = ?", params
        )
        event_payload = dict(payload or {})
        if reason is not None:
            event_payload["reason"] = reason
        if error_code is not None:
            event_payload["error_code"] = error_code
        self._append_event(
            mutation="status_changed",
            entity_id=run_id,
            old_state=current,
            new_state=target,
            payload=event_payload,
        )
        return target

    # -- queue-field updates ---------------------------------------------

    def mark_claimed(self, run_id: str, worker_id: str, claim_timestamp: str,
                     lease_expires_at: str) -> None:
        self._conn.execute(
            """
            UPDATE runs SET worker_id = ?, claim_timestamp = ?,
                lease_expires_at = ?
            WHERE run_id = ?
            """,
            (worker_id, claim_timestamp, lease_expires_at, run_id),
        )
        self._append_event(
            mutation="claimed",
            entity_id=run_id,
            old_state=None,
            new_state=None,
            payload={"worker_id": worker_id,
                     "lease_expires_at": lease_expires_at},
        )

    def touch_heartbeat(self, run_id: str, worker_id: str, heartbeat_at: str,
                        lease_expires_at: str) -> None:
        self._conn.execute(
            """
            UPDATE runs SET heartbeat_at = ?, lease_expires_at = ?
            WHERE run_id = ? AND worker_id = ? AND status IN
                ('CLAIMED', 'STARTING', 'RUNNING')
            """,
            (heartbeat_at, lease_expires_at, run_id, worker_id),
        )

    def clear_claim(self, run_id: str) -> None:
        self._conn.execute(
            """
            UPDATE runs SET worker_id = NULL, claim_timestamp = NULL,
                lease_expires_at = NULL, heartbeat_at = NULL
            WHERE run_id = ?
            """,
            (run_id,),
        )

    def request_cancellation(self, run_id: str) -> str:
        """Request cancellation of *run_id*.

        A queued run is cancelled immediately; an active run gets the
        cancellation flag (the owning worker terminates it). Terminal runs
        are a no-op. Returns the run's status after the call.
        """
        row = self._conn.execute(
            "SELECT status, cancellation_requested, reservation_id "
            "FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            raise RunNotFound(f"no run {run_id}")
        status = str(row["status"])
        with self._conn:
            if status == "QUEUED" and not row["cancellation_requested"]:
                self.transition(run_id, "CANCELLED",
                                reason="cancelled while queued")
                self._release_reservation(
                    run_id, str(row["reservation_id"]))
                return "CANCELLED"
            if status in RUN_ACTIVE_STATUSES \
                    and not row["cancellation_requested"]:
                self._conn.execute(
                    "UPDATE runs SET cancellation_requested = 1 "
                    "WHERE run_id = ?",
                    (run_id,),
                )
                self._append_event(
                    mutation="cancel_requested",
                    entity_id=run_id,
                    old_state=status,
                    new_state=status,
                    payload={"by": self._producer},
                )
        return status

    def _release_reservation(self, run_id: str,
                             reservation_id: str | None) -> None:
        """Return an active reservation to the pool (immediate cancel)."""
        if reservation_id is None:
            return
        from algolab.control.budget import BudgetLedger

        ledger = BudgetLedger(self._conn, producer=self._producer)
        if ledger.reservation_status(reservation_id) == "active":
            ledger.release(reservation_id, key=f"release:{run_id}",
                           trace_id=self._trace_id)

    # -- result fields ----------------------------------------------------

    def set_metrics(self, run_id: str, metrics: dict[str, Any]) -> None:
        self._conn.execute(
            "UPDATE runs SET metrics = ? WHERE run_id = ?",
            (json.dumps(metrics, sort_keys=True), run_id),
        )

    def set_budget_charged(self, run_id: str, credits: float,
                           cost: float = 0.0) -> None:
        self._conn.execute(
            "UPDATE runs SET credits_charged = ?, cost_charged = ? "
            "WHERE run_id = ?",
            (credits, cost, run_id),
        )

    def set_artifact_dir(self, run_id: str, artifact_dir: str) -> None:
        self._conn.execute(
            "UPDATE runs SET artifact_dir = ? WHERE run_id = ?",
            (artifact_dir, run_id),
        )

    # -- recovery helpers -------------------------------------------------

    def expired_leases(self, now: str) -> list[str]:
        """Run ids whose worker lease has expired (recovery candidates)."""
        rows = self._conn.execute(
            """
            SELECT run_id FROM runs
            WHERE status IN ('CLAIMED', 'STARTING', 'RUNNING')
              AND lease_expires_at IS NOT NULL AND lease_expires_at < ?
            """,
            (now,),
        ).fetchall()
        return [str(r["run_id"]) for r in rows]

    def requeue(self, run_id: str, next_eligible_at: str) -> None:
        """Move an orphaned run back to the queue (caller ensures the
        ORPHANED -> QUEUED transition)."""
        self._conn.execute(
            """
            UPDATE runs SET next_eligible_at = ?, attempt_number =
                attempt_number + 1, worker_id = NULL, claim_timestamp = NULL,
                lease_expires_at = NULL, heartbeat_at = NULL
            WHERE run_id = ?
            """,
            (next_eligible_at, run_id),
        )

    # -- internals --------------------------------------------------------

    def _require_experiment(self, experiment_id: str, status: str) -> None:
        row = self._conn.execute(
            "SELECT entity_type, status FROM entities WHERE entity_id = ?",
            (experiment_id,),
        ).fetchone()
        if row is None or row["entity_type"] != "experiment":
            raise RunConflict(f"no experiment {experiment_id}")
        # Runs materialize only for approved-or-running experiments. The
        # expansion service is the only creator and enforces that first
        # expansion happens from 'approved' (idempotent re-expansion happens
        # while 'running').
        if row["status"] not in (status, "running"):
            raise RunConflict(
                f"experiment {experiment_id} has status {row['status']!r}, "
                f"expected {status!r} (or running)"
            )

    def _append_event(self, *, mutation: str, entity_id: str,
                      old_state: str | None, new_state: str | None,
                      payload: dict[str, Any] | None = None) -> None:
        EventStore(self._conn).append(
            EventEnvelope(
                entity_type="run",
                entity_id=entity_id,
                mutation=mutation,
                old_state=old_state,
                new_state=new_state,
                payload=payload or {},
                producer=self._producer,
                trace_id=self._trace_id,
            )
        )


__all__ = [
    "RunNotFound",
    "RunConflict",
    "RunSpec",
    "RunRow",
    "RunRepository",
]
