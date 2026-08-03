# ADR-0001 — M0 foundation architecture

- **Status:** Accepted
- **Date:** 2026-08-03
- **Applies to:** Milestone M0 (`planning/MILESTONES.md`)

## Context

M0 must deliver the contracts layer of AlgoLab: typed IDs, entity models,
lifecycle state machines, an append-only event store, a budget ledger,
JSON-schema manifest validation, configuration, and a CLI — with tests for
every invariant in `spec/foundation/001_CORE_ONTOLOGY.md`.

## Decision

- Package `src/algolab/{core,control,storage,validation,cli}` mirroring
  `spec/architecture/100_SYSTEM_ARCHITECTURE.md` so future milestones map 1:1.
- SQLite (single file, WAL, foreign keys) for M0; `PRAGMA user_version`
  tracks the schema version.
- Entities stored as immutable JSON payloads; the only mutable column is
  `status`, changed exclusively through `StateMachine.require_transition`.
- Interchange contracts are the canonical JSON Schemas (validated with
  `jsonschema`); Pydantic v2 models are runtime-only.
- Budget ledger: append-only `ledger_entries` (grant/reserve/charge/release)
  with a derived `reservations` state table and idempotency keys.

## Consequences

- Full provenance and replayability from day one; no migration needed later
  for audit semantics.
- Status-only mutation keeps the fail-closed contract simple.
- PostgreSQL migration (later milestone) only requires repository rewrites.

## Alternatives considered

- PostgreSQL from M0: rejected — operational cost not justified until
  distributed workers exist (M5).
- Object-store for entities: rejected — SQLite JSON columns are sufficient
  for v1 volumes and keep transactions atomic with audit events.