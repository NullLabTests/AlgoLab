"""SQLite connection factory and schema (MASTER_SPEC.md §12, 100 §Data Plane).

Append-only is enforced at the database level: UPDATE/DELETE on ``events``
and ``ledger_entries`` are rejected by triggers (fail closed). Schema v3
adds the evidence archive (tasks, evidence, operator usage, search
episodes) whose scientific records are append-only as well; ``operator_stats``
is a derived aggregate recomputed from ``operator_uses``.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 3

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

# Schema v2 (M1 execution core): runs leave the entities table and gain
# structured queue mechanics; expansions record idempotent expansion events.
_V2_MIGRATION = """CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL REFERENCES entities(entity_id),
    candidate_id TEXT REFERENCES entities(entity_id),
    is_baseline INTEGER NOT NULL DEFAULT 0,
    seed INTEGER NOT NULL,
    workload TEXT NOT NULL,
    config TEXT NOT NULL,
    config_fingerprint TEXT NOT NULL UNIQUE,
    metrics TEXT,
    status TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 0,
    attempt_number INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 1,
    next_eligible_at TEXT NOT NULL,
    worker_id TEXT,
    claim_timestamp TEXT,
    lease_expires_at TEXT,
    heartbeat_at TEXT,
    cancellation_requested INTEGER NOT NULL DEFAULT 0,
    credits_reserved REAL NOT NULL DEFAULT 0,
    cost_reserved REAL NOT NULL DEFAULT 0,
    credits_charged REAL NOT NULL DEFAULT 0,
    cost_charged REAL NOT NULL DEFAULT 0,
    reservation_id TEXT,
    artifact_dir TEXT,
    error_code TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    trace_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_runs_queue
    ON runs (status, next_eligible_at, priority);
CREATE INDEX IF NOT EXISTS idx_runs_experiment
    ON runs (experiment_id, status);

CREATE TABLE IF NOT EXISTS expansions (
    expansion_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    run_ids TEXT NOT NULL,
    producer TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (experiment_id, idempotency_key)
);
"""

# Schema v3 (cumulative evidence archive): benchmark tasks, structured
# scientific evidence records, per-use operator logs, and search episodes.
# Scientific records (tasks, evidence, operator_uses) are append-only;
# operator_stats is a derived aggregate.
_V3_MIGRATION = """
CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    family TEXT NOT NULL,
    workload TEXT NOT NULL,
    description TEXT NOT NULL,
    baseline_config TEXT NOT NULL,
    search_space TEXT NOT NULL,
    seeds TEXT NOT NULL,
    primary_metric TEXT NOT NULL,
    direction TEXT NOT NULL,
    promotion_threshold REAL NOT NULL,
    ground_truth TEXT,
    credit_estimate REAL NOT NULL,
    created_at TEXT NOT NULL,
    producer TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(task_id),
    experiment_id TEXT NOT NULL,
    hypothesis_id TEXT NOT NULL,
    candidate_id TEXT NOT NULL,
    episode_id TEXT,
    operator_name TEXT NOT NULL,
    policy TEXT NOT NULL,
    primary_metric TEXT NOT NULL,
    direction TEXT NOT NULL,
    baseline_mean REAL,
    candidate_mean REAL,
    relative_delta REAL,
    ci_low REAL,
    ci_high REAL,
    p_value REAL,
    effect_size REAL,
    promotion_threshold REAL NOT NULL,
    outcome TEXT NOT NULL,
    credits_charged REAL NOT NULL,
    novelty INTEGER NOT NULL,
    replication_status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    producer TEXT NOT NULL,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_evidence_task ON evidence (task_id, created_at);
CREATE INDEX IF NOT EXISTS idx_evidence_outcome ON evidence (outcome, created_at);
CREATE INDEX IF NOT EXISTS idx_evidence_family ON evidence (task_id, operator_name);

CREATE TABLE IF NOT EXISTS operator_uses (
    use_id TEXT PRIMARY KEY,
    operator_name TEXT NOT NULL,
    task_id TEXT NOT NULL,
    experiment_id TEXT NOT NULL,
    episode_id TEXT,
    outcome TEXT NOT NULL,
    relative_delta REAL,
    credits_charged REAL NOT NULL,
    novel INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    producer TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_operator_uses_name ON operator_uses (operator_name);

CREATE TABLE IF NOT EXISTS operator_stats (
    operator_name TEXT PRIMARY KEY,
    attempts INTEGER NOT NULL,
    invalid_count INTEGER NOT NULL,
    success_count INTEGER NOT NULL,
    replicated_success_count INTEGER NOT NULL,
    sum_effect REAL NOT NULL,
    sum_effect_sq REAL NOT NULL,
    total_credits REAL NOT NULL,
    novelty_count INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS search_episodes (
    episode_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    policy TEXT NOT NULL,
    budget_credits REAL NOT NULL,
    credits_charged REAL NOT NULL,
    attempts INTEGER NOT NULL,
    discoveries INTEGER NOT NULL,
    failure_counts TEXT NOT NULL,
    operator_use_counts TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    seed INTEGER NOT NULL,
    producer TEXT NOT NULL,
    payload TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS tasks_no_update
BEFORE UPDATE ON tasks
BEGIN
    SELECT RAISE(ABORT, 'append-only violation: UPDATE on tasks is forbidden');
END;
CREATE TRIGGER IF NOT EXISTS tasks_no_delete
BEFORE DELETE ON tasks
BEGIN
    SELECT RAISE(ABORT, 'append-only violation: DELETE on tasks is forbidden');
END;
CREATE TRIGGER IF NOT EXISTS evidence_no_update
BEFORE UPDATE ON evidence
BEGIN
    SELECT RAISE(ABORT, 'append-only violation: UPDATE on evidence is forbidden');
END;
CREATE TRIGGER IF NOT EXISTS evidence_no_delete
BEFORE DELETE ON evidence
BEGIN
    SELECT RAISE(ABORT, 'append-only violation: DELETE on evidence is forbidden');
END;
CREATE TRIGGER IF NOT EXISTS operator_uses_no_update
BEFORE UPDATE ON operator_uses
BEGIN
    SELECT RAISE(ABORT, 'append-only violation: UPDATE on operator_uses is forbidden');
END;
CREATE TRIGGER IF NOT EXISTS operator_uses_no_delete
BEFORE DELETE ON operator_uses
BEGIN
    SELECT RAISE(ABORT, 'append-only violation: DELETE on operator_uses is forbidden');
END;
CREATE TRIGGER IF NOT EXISTS search_episodes_no_update
BEFORE UPDATE ON search_episodes
BEGIN
    SELECT RAISE(ABORT, 'append-only violation: UPDATE search_episodes forbidden');
END;
CREATE TRIGGER IF NOT EXISTS search_episodes_no_delete
BEFORE DELETE ON search_episodes
BEGIN
    SELECT RAISE(ABORT, 'append-only violation: DELETE search_episodes forbidden');
END;
"""

_MIGRATIONS: dict[int, str] = {
    2: _V2_MIGRATION,
    3: _V3_MIGRATION,
}


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
    conn.execute("PRAGMA busy_timeout=60000")
    conn.row_factory = sqlite3.Row
    if initialize:
        init_schema(conn)
    return conn


def apply_schema(conn: sqlite3.Connection, target_version: int) -> None:
    """Create the base schema, then apply migrations up to *target_version*.

    Idempotent: safe to call repeatedly on an existing database. The base
    schema corresponds to version 1 (M0); version 2 adds the M1 execution
    tables.
    """
    if target_version < 1:
        raise DatabaseError(f"schema target version must be >= 1, got {target_version}")
    current = int(conn.execute("PRAGMA user_version").fetchone()[0])
    if current < 1:
        conn.executescript(_SCHEMA)
        current = 1
        conn.execute("PRAGMA user_version = 1")
    for version in range(current + 1, target_version + 1):
        ddl = _MIGRATIONS.get(version)
        if ddl is None:
            raise DatabaseError(f"no migration defined for schema version {version}")
        conn.executescript(ddl)
        conn.execute(f"PRAGMA user_version = {version}")


def init_schema(conn: sqlite3.Connection) -> None:
    """Bring *conn* to the latest schema (idempotent)."""
    apply_schema(conn, SCHEMA_VERSION)


def check_append_only(conn: sqlite3.Connection) -> None:
    """Verify the append-only triggers are installed (defense in depth)."""
    for name in ("events_no_update", "evidence_no_update"):
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'trigger' "
            "AND name = ?",
            (name,),
        ).fetchone()
        if row is None:
            raise DatabaseError(
                f"{name} trigger is missing; refusing to proceed"
            )
