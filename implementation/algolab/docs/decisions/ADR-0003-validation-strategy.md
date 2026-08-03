# ADR-0003 — Validation strategy: JSON Schema at the boundary, Pydantic at runtime

- **Status:** Accepted
- **Date:** 2026-08-03

## Context

`OPENCODE_KICKOFF_PROMPT.md` requires "JSON-schema validation" and "Pydantic
for runtime models". The canonical schemas (`schemas/*.json`) are the
interchange contract; changing their meaning is forbidden.

## Decision

- The canonical schemas are copied byte-for-byte into
  `src/algolab/schemas/`; `tests/test_schemas_match_canonical.py` asserts
  byte-identity (skipped when run outside the monorepo).
- `algolab.validation.schema_validator.validate_manifest()` uses
  `jsonschema` Draft 2020-12 and is the *only* gate for manifests entering
  persistence (CLI and repositories).
- Pydantic models mirror the schemas for runtime ergonomics and validate
  additional invariants not expressible in the schemas (e.g., non-negative
  run credits).
- Schema drift is caught by the byte-identity test in CI.

## Consequences

- One contract source of truth; Pydantic cannot silently weaken it.
- `additionalProperties: false` is enforced by the schema validator, not by
  pydantic config.

## Alternatives considered

- Generating Pydantic models from the JSON Schemas: rejected for M0 —
  tooling churn outweighs the benefit until schemas stabilize.