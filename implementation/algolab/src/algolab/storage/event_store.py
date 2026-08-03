"""Append-only event store.

Every state mutation appends an audit event *in the same transaction* as the
data change. Reads are supported for replay and lineage.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from algolab.core.events import EventEnvelope


class EventStoreError(RuntimeError):
    """Base class for event store failures."""


class EventStore:
    """Thin wrapper over the append-only ``events`` table."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def append(self, event: EventEnvelope) -> None:
        """Persist *event* idempotently within the current transaction.

        Re-inserting an already-present ``event_id`` is a no-op (at-least-once
        delivery safety).
        """
        event.validate_references()
        self._conn.execute(
            """
            INSERT OR IGNORE INTO events
                (event_id, entity_type, entity_id, mutation, old_state,
                 new_state, payload, producer, created_at, trace_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.entity_type,
                event.entity_id,
                event.mutation,
                event.old_state,
                event.new_state,
                json.dumps(event.payload, sort_keys=True),
                event.producer,
                event.created_at,
                event.trace_id,
            ),
        )

    def list_for_entity(self, entity_id: str) -> list[EventEnvelope]:
        """All events for one entity, in insertion order (rowid)."""
        rows = self._conn.execute(
            "SELECT * FROM events WHERE entity_id = ? ORDER BY rowid",
            (entity_id,),
        ).fetchall()
        return [self._row_to_envelope(r) for r in rows]

    def list_all(self, *, entity_type: str | None = None, limit: int = 1000
                 ) -> list[EventEnvelope]:
        """Recent events (most recent first), optionally filtered."""
        if entity_type is None:
            rows = self._conn.execute(
                "SELECT * FROM events ORDER BY rowid DESC LIMIT ?", (limit,)
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM events WHERE entity_type = ? "
                "ORDER BY rowid DESC LIMIT ?",
                (entity_type, limit),
            ).fetchall()
        return [self._row_to_envelope(r) for r in rows]

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM events").fetchone()
        return int(row[0])

    def _row_to_envelope(self, row: sqlite3.Row) -> EventEnvelope:
        return EventEnvelope(
            event_id=row["event_id"],
            entity_type=row["entity_type"],
            entity_id=row["entity_id"],
            mutation=row["mutation"],
            old_state=row["old_state"],
            new_state=row["new_state"],
            payload=json.loads(row["payload"] or "{}"),
            producer=row["producer"],
            trace_id=row["trace_id"],
            created_at=row["created_at"],
        )


def append_created_event(conn: sqlite3.Connection, *, entity_type: str,
                         entity_id: str, status: str, payload: dict[str, Any],
                         producer: str, trace_id: str | None = None) -> None:
    """Convenience: record a 'created' audit event for a new entity."""
    EventStore(conn).append(
        EventEnvelope(
            entity_type=entity_type,
            entity_id=entity_id,
            mutation="created",
            new_state=status,
            payload=payload,
            producer=producer,
            trace_id=trace_id,
        )
    )
