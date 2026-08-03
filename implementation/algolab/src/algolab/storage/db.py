"""SQLite connection factory and schema (MASTER_SPEC.md §12, 100 §Data Plane).

Append-only is enforced at the database level: UPDATE/DELETE on ``events``
and ``ledger_entries`` are rejected by triggers (fail closed).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    event_id    TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id   TEXT NOT NULL,
    mutation    TEXT NOT NULL,
    old_state   TEXT,
    new_state   TEXT,
    payload     TEXT NOT NULL DEFAULT '{}',
    producer    TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    trace_id    TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_entity
    ON events (entity_id, created_at);

CREATE TABLE IF NOT EXISTS entities (
    entity_id      TEXT PRIMARY KEY,
    entity_type    TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    status         TEXT NOT NULL,
    payload        TEXT NOT NULL,
    created_at     TEXT NOT NULL,
    creator        TEXT NOT NULL,
    trace_id       TEXT
);
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities (entity_type, status);

CREATE TABLE IF NOT EXISTS ledger_entries (
    entry_id       TEXT PRIMARY KEY,
    kind           TEXT NOT NULL CHECK (kind IN
                     ('grant', 'reserve', 'charge', 'release')),
    amount_credits REAL NOT NULL CHECK (amount_credits >= 0),
    amount_cost    REAL NOT NULL CHECK (amount_cost >= 0),
    currency       TEXT NOT NULL DEFAULT 'USD',
    entity_id      TEXT,
    ref_entry      TEXT,
    idempotency_key TEXT UNIQUE,
    producer       TEXT NOT NULL,
    created_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ledger_kind ON ledger_entries (kind, created_at);

CREATE TABLE IF NOT EXISTS reservations (
    reservation_id TEXT PRIMARY KEY,
    entity_id      TEXT,
    credits        REAL NOT NULL CHECK (credits >= 0),
    cost           REAL NOT NULL CHECK (cost >= 0),
    status         TEXT NOT NULL CHECK (status IN ('active', 'charged', 'released'))
);

CREATE TRIGGER IF NOT EXISTS events_no_update
BEFORE UPDATE ON events
BEGIN
    SELECT RAISE(ABORT, 'append-only violation: UPDATE on events is forbidden');
END;

CREATE TRIGGER IF NOT EXISTS events_no_delete
BEFORE DELETE ON events
BEGIN
    SELECT RAISE(ABORT, 'append-only violation: DELETE on events is forbidden');
END;

CREATE TRIGGER IF NOT EXISTS ledger_no_update
BEFORE UPDATE ON ledger_entries
BEGIN
    SELECT RAISE(ABORT, 'append-only violation: UPDATE on ledger_entries is forbidden');
END;

CREATE TRIGGER IF NOT EXISTS ledger_no_delete
BEFORE DELETE ON ledger_entries
BEGIN
    SELECT RAISE(ABORT, 'append-only violation: DELETE on ledger_entries is forbidden');
END;

CREATE TRIGGER IF NOT EXISTS entities_provenance_frozen
BEFORE UPDATE OF entity_id, entity_type, schema_version, payload,
created_at, creator ON entities
BEGIN
    SELECT RAISE(ABORT,
      'provenance violation: entity provenance columns are immutable');
END;
"""


class DatabaseError(RuntimeError):
    """Raised for schema or connection-level failures."""


def connect(path: Path | str, *, initialize: bool = True) -> sqlite3.Connection:
    """Open (and optionally initialize) the SQLite database.

    SQLite WAL is used so one process can read while another writes; foreign
    keys are enabled. In-memory databases are supported (path == ':memory:').
    """
    if str(path) == ":memory:":
        conn = sqlite3.connect(":memory:")
    else:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(p))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    if initialize:
        init_schema(conn)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create the schema and append-only triggers (idempotent)."""
    with conn:
        conn.executescript(_SCHEMA)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def check_append_only(conn: sqlite3.Connection) -> None:
    """Verify the append-only triggers are installed (defense in depth)."""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'trigger' "
        "AND name = 'events_no_update'"
    ).fetchone()
    if row is None:
        raise DatabaseError("events_no_update trigger is missing; refusing to proceed")
