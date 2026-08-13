"""Partial budget charges and overrun recording (M1 accounting)."""

import pytest

from algolab.control.budget import BudgetLedger, UnknownReservation
from tests.conftest import grant


def _ledger(conn) -> BudgetLedger:
    return BudgetLedger(conn, producer="test")


def test_partial_charge_releases_remainder(conn) -> None:
    grant(conn, credits=100.0)
    ledger = _ledger(conn)
    with conn:
        res = ledger.reserve(10.0)
        assert ledger.balance()["available_credits"] == 90.0
        ledger.charge(res, credits=3.0, cost=0.0)
    balance = ledger.balance()
    assert balance["charged_credits"] == 3.0
    assert balance["available_credits"] == 97.0
    assert ledger.reservation_status(res) == "released"


def test_full_charge_is_unchanged_behavior(conn) -> None:
    grant(conn, credits=100.0)
    ledger = _ledger(conn)
    with conn:
        res = ledger.reserve(100.0)
        ledger.charge(res)
    assert ledger.balance()["charged_credits"] == 100.0
    assert ledger.reservation_status(res) == "charged"


def test_overrun_records_event_never_charges_more(conn) -> None:
    grant(conn, credits=100.0)
    ledger = _ledger(conn)
    with conn:
        res = ledger.reserve(10.0)
        ledger.charge(res, credits=40.0, cost=0.0)
    balance = ledger.balance()
    assert balance["charged_credits"] == 10.0  # capped at reservation
    from algolab.storage.event_store import EventStore

    overruns = [e for e in EventStore(conn).list_all()
                if e.mutation == "overrun"]
    assert len(overruns) == 1
    assert overruns[0].payload["overrun_credits"] == 30.0
    assert ledger.reservation_status(res) == "charged"


def test_reservation_cannot_be_charged_twice(conn) -> None:
    grant(conn, credits=100.0)
    ledger = _ledger(conn)
    with conn:
        res = ledger.reserve(10.0)
        ledger.charge(res)
    with pytest.raises(UnknownReservation):
        ledger.charge(res)


def test_release_only_once(conn) -> None:
    grant(conn, credits=100.0)
    ledger = _ledger(conn)
    with conn:
        res = ledger.reserve(10.0)
        ledger.release(res)
    with pytest.raises(UnknownReservation):
        ledger.release(res)
    assert ledger.reservation_status(res) == "released"
