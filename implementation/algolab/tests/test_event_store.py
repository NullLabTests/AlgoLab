"""Append-only event store behavior."""

import sqlite3

import pytest

from algolab.core.events import EventEnvelope
from algolab.core.ids import new_id
from algolab.storage.event_store import EventStore


def _event(**overrides) -> EventEnvelope:
    defaults = {
        "entity_type": "hypothesis",
        "entity_id": new_id("HYP"),
        "mutation": "created",
    }
    defaults.update(overrides)
    return EventEnvelope(**defaults)


def test_append_and_read_back(conn) -> None:
    store = EventStore(conn)
    ev = _event()
    with conn:
        store.append(ev)
    assert store.count() == 1
    [read] = store.list_for_entity(ev.entity_id)
    assert read.event_id == ev.event_id
    assert read.mutation == "created"
    assert read.payload == {}


def test_append_is_idempotent(conn) -> None:
    store = EventStore(conn)
    ev = _event()
    with conn:
        store.append(ev)
        store.append(ev)
    assert store.count() == 1


def test_reject_malformed_entity_id(conn) -> None:
    store = EventStore(conn)
    ev = _event(entity_id="nonsense")
    with conn:
        with pytest.raises(ValueError):
            store.append(ev)
    assert store.count() == 0


def test_ordering_by_creation(conn) -> None:
    store = EventStore(conn)
    entity = new_id("HYP")
    first = _event(entity_id=entity, mutation="created")
    second = _event(entity_id=entity, mutation="status_changed",
                    old_state="draft", new_state="vetting")
    with conn:
        store.append(first)
        store.append(second)
    events = store.list_for_entity(entity)
    assert [e.mutation for e in events] == ["created", "status_changed"]


def test_update_on_events_blocked_by_trigger(conn) -> None:
    store = EventStore(conn)
    ev = _event()
    with conn:
        store.append(ev)
    with pytest.raises(Exception) as excinfo:
        with conn:
            conn.execute(
                "UPDATE events SET payload = '{}' WHERE event_id = ?",
                (ev.event_id,),
            )
    assert "append-only" in str(excinfo.value)


def test_delete_on_events_blocked_by_trigger(conn) -> None:
    store = EventStore(conn)
    ev = _event()
    with conn:
        store.append(ev)
    with pytest.raises(Exception) as excinfo:
        with conn:
            conn.execute("DELETE FROM events WHERE event_id = ?", (ev.event_id,))
    assert "append-only" in str(excinfo.value)


def test_update_budget_events_blocked(conn) -> None:
    store = EventStore(conn)
    ev = _event(entity_type="budget")
    with conn:
        store.append(ev)
    with pytest.raises(sqlite3.IntegrityError):
        with conn:
            conn.execute("UPDATE events SET payload = 'x'")
