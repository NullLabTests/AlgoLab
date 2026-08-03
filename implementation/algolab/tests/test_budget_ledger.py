"""Budget ledger: grants, reservations, charges, releases, caps, idempotency."""

import sqlite3

import pytest

from algolab.control.budget import (
    BudgetLedger,
    DuplicateOperation,
    InsufficientBudget,
    UnknownReservation,
)


@pytest.fixture
def ledger(conn) -> BudgetLedger:
    return BudgetLedger(conn, producer="test")


def test_grant_reflects_in_balance(ledger, conn) -> None:
    with conn:
        ledger.grant(100.0, cost=500.0)
    b = ledger.balance()
    assert b["granted_credits"] == 100.0
    assert b["available_credits"] == 100.0
    assert b["available_cost"] == 500.0


def test_reserve_locks_credits(ledger, conn) -> None:
    with conn:
        ledger.grant(100.0)
        rid = ledger.reserve(40.0)
    b = ledger.balance()
    assert b["available_credits"] == 60.0
    assert b["reserved_credits"] == 40.0
    assert isinstance(rid, str)


def test_reserve_over_available_refused(ledger, conn) -> None:
    with conn:
        ledger.grant(10.0)
        with pytest.raises(InsufficientBudget):
            ledger.reserve(10.5)


def test_monetary_limit_overrides_credits(ledger, conn) -> None:
    with conn:
        ledger.grant(100.0, cost=0.0)  # no monetary budget granted
        with pytest.raises(InsufficientBudget):
            ledger.reserve(5.0, cost=2.0)  # credits fine, cost not
    b = ledger.balance()
    assert b["available_credits"] == 100.0  # nothing was reserved


def test_charge_consumes_reservation(ledger, conn) -> None:
    with conn:
        ledger.grant(100.0)
        rid = ledger.reserve(30.0)
        ledger.charge(rid)
    b = ledger.balance()
    assert b["charged_credits"] == 30.0
    assert b["available_credits"] == 70.0
    assert b["reserved_credits"] == 0.0


def test_release_returns_credits(ledger, conn) -> None:
    with conn:
        ledger.grant(100.0)
        rid = ledger.reserve(30.0)
        ledger.release(rid)
    b = ledger.balance()
    assert b["available_credits"] == 100.0
    assert b["reserved_credits"] == 0.0


def test_charge_twice_rejected(ledger, conn) -> None:
    with conn:
        ledger.grant(100.0)
        rid = ledger.reserve(10.0)
        ledger.charge(rid)
        with pytest.raises(UnknownReservation):
            ledger.charge(rid)
    b = ledger.balance()
    assert b["charged_credits"] == 10.0


def test_charge_unknown_reservation(ledger, conn) -> None:
    with conn:
        with pytest.raises(UnknownReservation):
            ledger.charge("EVT-00000000")


def test_release_unknown_reservation(ledger, conn) -> None:
    with conn:
        with pytest.raises(UnknownReservation):
            ledger.release("EVT-00000000")


def test_idempotency_key_blocks_duplicate(ledger, conn) -> None:
    with conn:
        ledger.grant(100.0)
    key = "op-1"
    with pytest.raises(DuplicateOperation):
        with conn:
            ledger.grant(50.0, key=key)
            ledger.grant(50.0, key=key)
            # second grant raises; the whole transaction rolls back
    b = ledger.balance()
    assert b["granted_credits"] == 100.0


def test_all_mutations_emit_audit_events(ledger, conn) -> None:
    from algolab.storage.event_store import EventStore

    with conn:
        ledger.grant(50.0)
        rid = ledger.reserve(10.0)
        ledger.charge(rid)
        ledger.grant(5.0)
        rid2 = ledger.reserve(2.0)
        ledger.release(rid2)
    store = EventStore(conn)
    events = list(reversed(store.list_all(entity_type="budget")))
    mutations = [e.mutation for e in events]
    assert mutations == ["grant", "reserve", "charge", "grant", "reserve", "release"]


def test_ledger_entries_append_only(ledger, conn) -> None:
    with conn:
        ledger.grant(10.0)
    with pytest.raises(Exception) as excinfo:
        with conn:
            conn.execute("UPDATE ledger_entries SET amount_credits = 999")
    assert "append-only" in str(excinfo.value)
    with pytest.raises(sqlite3.IntegrityError):
        with conn:
            conn.execute("DELETE FROM ledger_entries")
