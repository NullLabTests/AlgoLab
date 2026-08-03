# ADR-0002 — Append-only enforcement at the database level

- **Status:** Accepted
- **Date:** 2026-08-03

## Context

The master specification requires immutable provenance (`MASTER_SPEC.md` §12,
ontology invariant 6) and an immutable audit log (§14). API-level discipline
alone is insufficient: future milestones will add more writers.

## Decision

- `events` and `ledger_entries` have `BEFORE UPDATE` / `BEFORE DELETE`
  triggers that `RAISE(ABORT, 'append-only violation: ...')`.
- Entity provenance columns (`entity_id`, `entity_type`, `schema_version`,
  `payload`, `created_at`, `creator`) have a `BEFORE UPDATE OF` trigger that
  aborts.
- All repository mutations write the data row and its audit event in one
  transaction, so a rejected event rolls back the whole mutation.
- `check_append_only()` verifies trigger installation at connection open
  (defense in depth).

## Consequences

- Violations fail closed with an explicit error message.
- Corrections follow the canonical pattern: a new record supersedes the old
  one; nothing is edited in place.

## Alternatives considered

- SQLite `security_delete` / `security_update` PRAGMAs: not supported in
  SQLite; triggers are the portable mechanism.