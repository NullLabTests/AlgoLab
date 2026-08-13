"""Compute-credit budget ledger (MASTER_SPEC.md §2, §9, §14).

Model
-----
- ``ledger_entries`` is append-only (grant / reserve / charge / release);
  reservation lifecycle state lives in a separate ``reservations`` table
  derived from entries.
- ``grant``    — adds credits/cost to the available pool.
- ``reserve``  — earmarks credits for a planned experiment; fails (closed)
  if credits *or* monetary cap would be exceeded.
- ``charge``   — converts an active reservation into consumption.
- ``release``  — returns an unused reservation to the pool.

Idempotency: every entry carries an idempotency key with a UNIQUE constraint;
repeating an operation with the same key is a no-op.

Monetary limits override compute-credit limits (MASTER_SPEC.md §2).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any

from algolab.core.ids import new_id

_ENTRY_KINDS = ("grant", "reserve", "charge", "release")
_EPSILON = 1e-9


class BudgetError(RuntimeError):
    """Base class for ledger failures."""


class InsufficientBudget(BudgetError):
    """Reservation refused: credits or monetary cap exceeded."""


class UnknownReservation(BudgetError):
    """Charging/releasing a reservation that does not exist or is not active."""


class DuplicateOperation(BudgetError):
    """An operation with this idempotency key already exists."""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _to_float(value: float) -> float:
    if value < 0:
        raise ValueError("amounts must be non-negative")
    return round(float(value), 6)


class BudgetLedger:
    """All operations take an open SQLite connection and a transaction."""

    def __init__(self, conn: sqlite3.Connection, producer: str = "algolab") -> None:
        self._conn = conn
        self._producer = producer

    # -- queries ---------------------------------------------------------

    def balance(self) -> dict[str, float]:
        """Credits/cost position.

        ``available = granted - charged - active_reserves``. Active reserves
        are read from the ``reservations`` table (ledger entries are
        append-only and never retract a reservation).
        """
        granted, granted_cost = self._sum("grant")
        charged, charged_cost = self._sum("charge")
        active = self._conn.execute(
            "SELECT COALESCE(SUM(credits), 0), COALESCE(SUM(cost), 0) "
            "FROM reservations WHERE status = 'active'"
        ).fetchone()
        reserved, reserved_cost = float(active[0]), float(active[1])
        return {
            "granted_credits": round(granted, 6),
            "granted_cost": round(granted_cost, 6),
            "reserved_credits": round(reserved, 6),
            "reserved_cost": round(reserved_cost, 6),
            "charged_credits": round(charged, 6),
            "charged_cost": round(charged_cost, 6),
            "available_credits": round(granted - reserved - charged, 6),
            "available_cost": round(granted_cost - reserved_cost - charged_cost, 6),
        }

    def _sum(self, kind: str) -> tuple[float, float]:
        row = self._conn.execute(
            "SELECT COALESCE(SUM(amount_credits), 0), "
            "COALESCE(SUM(amount_cost), 0) "
            "FROM ledger_entries WHERE kind = ?",
            (kind,),
        ).fetchone()
        return float(row[0]), float(row[1])

    def available(self) -> dict[str, float]:
        return self.balance()

    # -- mutations -------------------------------------------------------

    def grant(self, credits: float, cost: float = 0.0, *, key: str | None = None,
              entity_id: str | None = None, trace_id: str | None = None) -> str:
        """Grant *credits* (and optional *cost* budget) to the pool.

        Returns the entry id. Idempotent on *key*.
        """
        return self._insert_entry(
            kind="grant",
            credits=_to_float(credits),
            cost=_to_float(cost),
            key=key,
            entity_id=entity_id,
            trace_id=trace_id,
        )

    def reserve(self, credits: float, cost: float = 0.0, *, key: str | None = None,
                entity_id: str | None = None, trace_id: str | None = None) -> str:
        """Reserve *credits*/*cost* for *entity_id*.

        Raises:
            InsufficientBudget: if credits or monetary cap would be exceeded.
        """
        credits = _to_float(credits)
        cost = _to_float(cost)
        available = self.balance()
        if available["available_credits"] + _EPSILON < credits:
            raise InsufficientBudget(
                f"cannot reserve {credits} credits; only "
                f"{available['available_credits']} available"
            )
        if available["available_cost"] + _EPSILON < cost:
            raise InsufficientBudget(
                f"cannot reserve {cost} monetary units; only "
                f"{available['available_cost']} available (monetary limits "
                f"override compute-credit limits)"
            )
        entry_id = self._insert_entry(
            kind="reserve",
            credits=credits,
            cost=cost,
            key=key,
            entity_id=entity_id,
            trace_id=trace_id,
        )
        self._conn.execute(
            """
            INSERT INTO reservations (reservation_id, entity_id, credits, cost, status)
            VALUES (?, ?, ?, ?, 'active')
            """,
            (entry_id, entity_id, credits, cost),
        )
        return entry_id

    def charge(self, reservation_id: str, *, credits: float | None = None,
               cost: float | None = None, key: str | None = None,
               trace_id: str | None = None) -> None:
        """Convert an active reservation into consumption.

        When *credits*/*cost* are given they may be **less** than the
        reserved amounts (partial charge): the consumed portion is charged
        and the remainder is released back to the pool in the same
        transaction. An overrun (actual > reserved) is never charged beyond
        the reservation; the difference is recorded as an ``overrun`` audit
        event instead.
        """
        self._ensure_active(reservation_id, "charge")
        reserved_credits, reserved_cost = self._reservation_amounts(reservation_id)
        actual_credits = reserved_credits if credits is None else _to_float(credits)
        actual_cost = reserved_cost if cost is None else _to_float(cost)
        charge_credits = min(actual_credits, reserved_credits)
        charge_cost = min(actual_cost, reserved_cost)
        overrun_credits = actual_credits - reserved_credits
        overrun_cost = actual_cost - reserved_cost
        if overrun_credits > _EPSILON or overrun_cost > _EPSILON:
            self._append_event(
                mutation="overrun",
                entity_id=reservation_id,
                payload={
                    "reserved_credits": reserved_credits,
                    "reserved_cost": reserved_cost,
                    "actual_credits": actual_credits,
                    "actual_cost": actual_cost,
                    "overrun_credits": round(overrun_credits, 6),
                    "overrun_cost": round(overrun_cost, 6),
                },
                trace_id=trace_id,
            )
        self._insert_entry(
            kind="charge",
            credits=charge_credits,
            cost=charge_cost,
            key=key,
            entity_id=reservation_id,
            trace_id=trace_id,
            ref_entry=reservation_id,
        )
        if (
            charge_credits < reserved_credits - _EPSILON
            or charge_cost < reserved_cost - _EPSILON
        ):
            # Partial charge: return the un-consumed remainder to the pool.
            self._insert_entry(
                kind="release",
                credits=0.0,
                cost=0.0,
                key=None,
                entity_id=reservation_id,
                trace_id=trace_id,
                ref_entry=reservation_id,
            )
            self._conn.execute(
                "UPDATE reservations SET status = 'released' WHERE reservation_id = ?",
                (reservation_id,),
            )
        else:
            self._conn.execute(
                "UPDATE reservations SET status = 'charged' WHERE reservation_id = ?",
                (reservation_id,),
            )

    def release(self, reservation_id: str, *, key: str | None = None,
                trace_id: str | None = None) -> None:
        """Return an active reservation to the pool."""
        self._ensure_active(reservation_id, "release")
        self._insert_entry(
            kind="release",
            credits=0.0,
            cost=0.0,
            key=key,
            entity_id=reservation_id,
            trace_id=trace_id,
            ref_entry=reservation_id,
        )
        self._conn.execute(
            "UPDATE reservations SET status = 'released' WHERE reservation_id = ?",
            (reservation_id,),
        )

    # -- internals -------------------------------------------------------

    def reservation_status(self, reservation_id: str) -> str | None:
        """Current lifecycle state of a reservation (or None if unknown)."""
        row = self._conn.execute(
            "SELECT status FROM reservations WHERE reservation_id = ?",
            (reservation_id,),
        ).fetchone()
        return str(row[0]) if row is not None else None

    def _reservation_amounts(self, reservation_id: str) -> tuple[float, float]:
        row = self._conn.execute(
            "SELECT credits, cost FROM reservations WHERE reservation_id = ?",
            (reservation_id,),
        ).fetchone()
        if row is None:
            raise UnknownReservation(
                f"no reservation {reservation_id}; cannot proceed"
            )
        return _to_float(row[0]), _to_float(row[1])

    def _ensure_active(self, reservation_id: str, action: str) -> None:
        row = self._conn.execute(
            "SELECT status FROM reservations WHERE reservation_id = ?",
            (reservation_id,),
        ).fetchone()
        if row is None:
            raise UnknownReservation(
                f"no reservation {reservation_id}; cannot {action}"
            )
        if row[0] != "active":
            raise UnknownReservation(
                f"reservation {reservation_id} is {row[0]!r}, "
                f"not 'active'; cannot {action}"
            )

    def _insert_entry(self, *, kind: str, credits: float, cost: float,
                      key: str | None, entity_id: str | None, trace_id: str | None,
                      ref_entry: str | None = None) -> str:
        if kind not in _ENTRY_KINDS:
            raise ValueError(f"unknown ledger entry kind {kind!r}")
        entry_id = new_id("EVT")
        try:
            self._conn.execute(
                """
                INSERT INTO ledger_entries
                    (entry_id, kind, amount_credits, amount_cost, currency,
                     entity_id, ref_entry, idempotency_key, producer, created_at)
                VALUES (?, ?, ?, ?, 'USD', ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    kind,
                    _to_float(credits),
                    _to_float(cost),
                    entity_id,
                    ref_entry,
                    key,
                    self._producer,
                    _now(),
                ),
            )
        except sqlite3.IntegrityError as exc:
            if key is not None and "idempotency_key" in str(exc):
                raise DuplicateOperation(
                    f"operation with idempotency key {key!r} already applied"
                ) from exc
            raise BudgetError(f"ledger insert failed: {exc}") from exc
        self._append_event(
            mutation=kind,
            entity_id=entry_id,
            payload={"credits": _to_float(credits), "cost": _to_float(cost)},
            trace_id=trace_id,
        )
        return entry_id

    def _append_event(self, *, mutation: Any, entity_id: str,
                      payload: dict[str, Any], trace_id: str | None) -> None:
        self._conn.execute(
            """
            INSERT INTO events
                (event_id, entity_type, entity_id, mutation, old_state, new_state,
                 payload, producer, created_at, trace_id)
            VALUES (?, 'budget', ?, ?, NULL, NULL, ?, ?, ?, ?)
            """,
            (
                new_id("EVT"),
                entity_id,
                mutation,
                json.dumps(payload),
                self._producer,
                _now(),
                trace_id,
            ),
        )
