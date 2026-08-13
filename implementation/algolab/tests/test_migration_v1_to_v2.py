"""Schema migration: v1 (M0) databases upgrade to v2 (M1) losslessly."""

import pytest

from algolab.storage.db import SCHEMA_VERSION, apply_schema, connect


def test_fresh_database_is_current_version(tmp_path) -> None:
    conn = connect(str(tmp_path / "fresh.sqlite3"), initialize=True)
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert version == SCHEMA_VERSION == 3
    for table in ("runs", "expansions", "evidence", "tasks"):
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        ).fetchone()
        assert row is not None, table
    conn.close()


def test_v1_database_upgrades_to_v2(tmp_path) -> None:
    path = tmp_path / "legacy.sqlite3"
    conn = connect(str(path), initialize=False)
    apply_schema(conn, 1)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
    # A v1 entity must survive the upgrade untouched.
    from algolab.storage.repositories import HypothesisRepository
    from tests.conftest import make_hypothesis

    with conn:
        hid = HypothesisRepository(conn, producer="test").create(
            make_hypothesis())
    conn.execute("PRAGMA user_version = 1")

    apply_schema(conn, 2)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
    row = conn.execute(
        "SELECT entity_type, status FROM entities WHERE entity_id = ?",
        (hid,),
    ).fetchone()
    assert row["entity_type"] == "hypothesis"
    conn.close()


def test_apply_schema_is_idempotent(tmp_path) -> None:
    conn = connect(str(tmp_path / "re.sqlite3"), initialize=True)
    apply_schema(conn, SCHEMA_VERSION)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
    conn.close()


def test_runs_table_has_queue_mechanics(tmp_path) -> None:
    conn = connect(str(tmp_path / "runs.sqlite3"), initialize=True)
    columns = {
        r[1] for r in conn.execute("PRAGMA table_info(runs)").fetchall()
    }
    for col in ("worker_id", "lease_expires_at", "heartbeat_at",
                "attempt_number", "max_attempts", "next_eligible_at",
                "cancellation_requested", "config_fingerprint",
                "reservation_id", "credits_reserved", "credits_charged"):
        assert col in columns, col
    conn.close()


def test_append_only_triggers_survive_migration(tmp_path) -> None:
    import sqlite3

    conn = connect(str(tmp_path / "triggers.sqlite3"), initialize=False)
    apply_schema(conn, 2)
    conn.execute(
        "INSERT INTO ledger_entries (entry_id, kind, amount_credits, "
        "amount_cost, producer, created_at) "
        "VALUES ('EVT-1', 'grant', 1.0, 0.0, 'test', '2026-01-01T00:00:00+00:00')")
    with pytest.raises(sqlite3.Error):
        conn.execute("UPDATE ledger_entries SET amount_credits = 0")
    conn.close()
