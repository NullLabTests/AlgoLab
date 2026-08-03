# ADR-0004 — Budget ledger model

- **Status:** Accepted
- **Date:** 2026-08-03

## Context

`MASTER_SPEC.md` §2 defines one compute credit = one A100-80GB equivalent
GPU-hour and states monetary limits override compute-credit limits. §14
requires daily/total budget caps; §9 requires budget reservations.

## Decision

- Money movements live in the append-only `ledger_entries` table with kinds
  `grant`, `reserve`, `charge`, `release`; each entry carries an
  idempotency key (`UNIQUE`).
- Reservation lifecycle state (`active`/`charged`/`released`) is derived
  state in a separate `reservations` table.
- `reserve` fails closed (`InsufficientBudget`) if either credits or
  monetary budget is insufficient — enforcing the monetary override rule.
- `available = grants - charges - active_reserves`.
- Every ledger mutation also appends an audit event with entity type
  `budget` (same transaction).

## Consequences

- The ledger can be replayed from entries; balances are always derivable.
- M1's planner can reserve before scheduling and charge/release afterwards
  without rewriting history.

## Alternatives considered

- Single mutable `budget` row: rejected — loses history and idempotency.